"""Admin-reviewed immutable registration snapshots and a bounded service relay."""
import hashlib
import json
import re
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from src.config import settings
from src.services import customers, companies
from src.services.database import get_db


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


async def snapshot(customer_id, plant_index):
    customer = await customers.get_by_id(customer_id)
    if not customer or plant_index >= len(customer.get('plants') or []):
        raise HTTPException(404, 'Kunde oder Anlage nicht gefunden')
    plant = customer['plants'][plant_index]
    if plant.get('anlagetyp') != 'pv':
        raise HTTPException(422, 'Automatisierung ist derzeit nur fuer PV-Anlagen vorgesehen')
    if plant.get('status') not in ('in_pruefung', 'angemeldet', 'abgeschlossen'):
        raise HTTPException(409, 'Netzanmeldung ist erst ab Anlagenstatus In Pruefung freigegeben')
    company = await companies.get_by_id(plant['company_id']) if plant.get('company_id') else None
    operator = {k: customer.get(k) for k in ('firstname', 'lastname', 'address_street', 'address_plz', 'address_city', 'phone', 'email')}
    return {'customer_id': customer_id, 'plant_index': plant_index, 'operator': operator,
            'plant': plant, 'licensed_company': company, 'customer_updated_at': customer.get('updated_at')}


def site_for(data):
    operator, plant = data['operator'], data['plant']
    address = operator if plant.get('address_from_customer', True) else plant
    street = (address.get('address_street') or '').strip()
    match = re.fullmatch(r'(.+?)\s+(\d+\S*(?:\s*[-/]\s*\d+\S*)?)', street)
    if not match or not re.fullmatch(r'\d{5}', address.get('address_plz') or '') or not address.get('address_city'):
        raise HTTPException(422, 'Anlagenadresse benoetigt Strasse mit Hausnummer, fuenfstellige PLZ und Ort')
    site = {'postal_code': address['address_plz'], 'city': address['address_city'],
            'street': match[1], 'house_number': match[2]}
    return site


async def resolve_operator(data):
    return await relay('POST', '/api/v1/network-operators/resolve', payload=site_for(data))


async def preview(customer_id, plant_index):
    data = await snapshot(customer_id, plant_index)
    resolution = await resolve_operator(data)
    return {'snapshot': data, 'snapshot_hash': digest(data), 'network_operator': resolution}


def resolved_provider(resolution):
    if (resolution.get('status') != 'resolved' or resolution.get('provider') not in ('nrm', 'enm', 'mainzer', 'enetz')
            or not (resolution.get('operator') or {}).get('id')):
        raise HTTPException(409, 'Kein eindeutig angebundener Netzbetreiber ermittelt; Adresse und VNBdigital-Ergebnis pruefen')
    return resolution['provider']


def payload_for(data, provider, target, product_id):
    operator, plant = data['operator'], data['plant']
    required = ('firstname', 'lastname', 'address_street', 'address_plz', 'address_city')
    if any(not str(operator.get(k) or '').strip() for k in required):
        raise HTTPException(422, 'Betreibername und Adresse muessen vollstaendig sein')
    site = site_for(data)
    if target == 'local':
        return {'target': 'local', 'site': site, 'plant': {'operator': operator, 'installation': plant, 'licensed_company': data['licensed_company']}}
    if provider == 'mainzer':
        raise HTTPException(409, 'Mainzer unterstuetzt derzeit ausschliesslich lokale Vorbereitung')
    if provider in ('nrm', 'enm'):
        if not product_id:
            raise HTTPException(422, 'Aktuelle PV-Produkt-ID erforderlich')
        return {'target': 'portal', 'product_id': product_id}
    return {'target': 'portal', 'site': site, 'note': (plant.get('notes') or '')[:2000]}


def scope_for(provider, target):
    if target == 'local':
        return 'Nur lokale JSON-Vorbereitung im Netzportal-Service; keine Portalanmeldung.'
    if provider in ('nrm', 'enm'):
        return 'Nur leerer Produktentwurf im Warenkorb. Betreiber, Standort und technische Daten werden noch nicht uebertragen.'
    return 'Nur initiale Strommeldung mit Standort/Bemerkung. Noch keine vollstaendige PV-Anmeldung.'


async def relay(method, path, *, payload=None, key=None):
    if not settings.netzportal_api_key:
        raise HTTPException(503, 'Netzportal-Service ist nicht konfiguriert')
    headers = {'Authorization': 'Bearer ' + settings.netzportal_api_key}
    if key:
        headers['Idempotency-Key'] = key
    try:
        async with httpx.AsyncClient(timeout=settings.netzportal_timeout_seconds, follow_redirects=False, trust_env=False) as client:
            response = await client.request(method, settings.netzportal_url.rstrip('/') + path, headers=headers, json=payload)
        if response.status_code >= 300:
            # Do not forward raw portal output or service authentication errors.
            raise HTTPException(502, 'Netzportal-Service hat die Aktion nicht bestaetigt. Vorgangsstatus pruefen.')
        return response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, 'Keine bestaetigte Antwort vom Netzportal-Service. Nicht blind erneut starten.')


async def review(customer_id, plant_index, body, admin):
    data = await snapshot(customer_id, plant_index)
    if digest(data) != body.expected_hash:
        raise HTTPException(409, "Daten seit Vorschau geaendert; Vorschau neu laden")
    resolution = await resolve_operator(data)
    provider = resolved_provider(resolution)
    if resolution['operator']['id'] != body.expected_operator_id:
        raise HTTPException(409, 'Netzbetreiber hat sich seit der Vorschau geaendert; erneut pruefen')
    payload = payload_for(data, provider, body.target, body.product_id)
    scope = scope_for(provider, body.target)
    fingerprint = digest(data)
    operation_id = digest({'customer': customer_id, 'index': plant_index, 'fingerprint': fingerprint,
                           'provider': provider, 'payload': payload})
    record = {'_id': operation_id, 'customer_id': customer_id, 'plant_index': plant_index,
              'provider': provider, 'snapshot_hash': fingerprint, 'snapshot': data,
              'network_operator': resolution, 'payload': payload, 'scope': scope, 'state': 'reviewed', 'reviewed_by': admin['id'],
              'reviewed_at': datetime.now(timezone.utc), 'review_note': body.review_note,
              'submitted': False}
    collection = get_db()['registration_jobs']
    try:
        await collection.insert_one(record)
    except DuplicateKeyError:
        record = await collection.find_one({'_id': operation_id})
        if record['state'] == 'reviewed':
            # Refresh approval atomically, never reset a started/uncertain job.
            await collection.update_one({'_id': operation_id, 'state': 'reviewed'}, {'$set': {
                'reviewed_by': admin['id'], 'reviewed_at': datetime.now(timezone.utc), 'review_note': body.review_note, 'network_operator': resolution}})
            record = await collection.find_one({'_id': operation_id})
    return public(record)


def public(record):
    return {**{k: v for k, v in record.items() if k not in ('_id', 'snapshot_hash')}, 'id': record['_id']}


async def start(job_id, admin):
    collection = get_db()['registration_jobs']
    record = await collection.find_one({'_id': job_id})
    if not record:
        raise HTTPException(404, 'Pruefung nicht gefunden')
    if record['state'] != 'reviewed':
        # A duplicate start only reads the stored outcome; never replays the write.
        return public(record)
    if record['reviewed_by'] != admin['id']:
        raise HTTPException(403, 'Die Daten muessen vom ausloesenden Admin selbst geprueft werden')
    now = datetime.now(timezone.utc)
    reviewed_at = record['reviewed_at'].replace(tzinfo=timezone.utc)
    if (now - reviewed_at).total_seconds() > 1800:
        raise HTTPException(409, 'Pruefung abgelaufen; Daten erneut pruefen')
    current = await snapshot(record['customer_id'], record['plant_index'])
    if digest(current) != record['snapshot_hash']:
        raise HTTPException(409, 'Installationsdaten wurden geaendert; erneute Pruefung erforderlich')
    resolution = await resolve_operator(current)
    if (resolved_provider(resolution) != record['provider']
            or resolution['operator']['id'] != (record.get('network_operator') or {}).get('operator', {}).get('id')):
        raise HTTPException(409, 'Netzbetreiber-Zuordnung geaendert; erneute Pruefung erforderlich')
    # The lookup can take several HTTP exchanges; check status/data again afterwards.
    latest = await snapshot(record['customer_id'], record['plant_index'])
    if digest(latest) != record['snapshot_hash']:
        raise HTTPException(409, 'Installationsdaten waehrend der Netzbetreibersuche geaendert; erneut pruefen')
    claimed = await collection.find_one_and_update(
        {'_id': job_id, 'state': 'reviewed', 'reviewed_by': admin['id'], 'reviewed_at': record['reviewed_at']},
        {'$set': {'state': 'pending', 'started_by': admin['id'], 'started_at': now}}, return_document=True)
    if not claimed:
        return public(await collection.find_one({'_id': job_id}))
    # This operation has no automatic retry. A process crash leaves pending.
    try:
        result = await relay('POST', f"/api/v1/providers/{record['provider']}/drafts", payload=record['payload'], key=job_id)
        if (result.get('submitted') is not False or result.get('status') != 'draft' or not result.get('id')
                or result.get('provider') != record['provider'] or result.get('storage') != record['payload']['target']):
            raise HTTPException(502, 'Unerwartete Antwort; Ergebnis muss manuell geprueft werden')
    except Exception:
        await collection.update_one({'_id': job_id}, {'$set': {'state': 'uncertain', 'error': 'Ergebnis unklar. Portal und Servicejournal manuell pruefen; keine automatische Wiederholung.'}})
        raise HTTPException(502, 'Ergebnis unklar. Vorgang wurde gesperrt; Portal und Servicejournal pruefen.')
    await collection.update_one({'_id': job_id}, {'$set': {'state': 'draft_created', 'result': result, 'completed_at': datetime.now(timezone.utc)}})
    return public(await collection.find_one({'_id': job_id}))
