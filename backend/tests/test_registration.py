import asyncio
from datetime import datetime, timedelta, timezone
from copy import deepcopy
from unittest.mock import AsyncMock

import httpx
import pytest
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from src.routers.registration import router
from src.services import registration as reg

ADMIN = {'X-Kratos-Identity-ID': 'admin-1', 'X-Kratos-Identity-Schema': 'admin'}

@pytest.fixture
def system(monkeypatch, mongomock_motor_db):
    db = mongomock_motor_db
    monkeypatch.setattr(reg, 'get_db', lambda: db)
    import src.routers.registration as routes
    monkeypatch.setattr(routes, 'get_db', lambda: db)
    customer = {'_id': '123', 'firstname': 'Test', 'lastname': 'Betreiber', 'address_street': 'Testweg 12a',
                'address_plz': '12345', 'address_city': 'Testort', 'updated_at': '2026-11-03T00:00:00Z',
                'plants': [{'anlagetyp': 'pv', 'address_from_customer': True, 'kwp': '10', 'inverters': []}]}
    monkeypatch.setattr(reg.customers, 'get_by_id', AsyncMock(side_effect=lambda _: deepcopy(customer)))
    monkeypatch.setattr(reg.companies, 'get_by_id', AsyncMock(return_value=None))
    relay = AsyncMock(return_value={'id': 'draft-1', 'provider': 'enm', 'storage': 'local', 'status': 'draft', 'submitted': False})
    monkeypatch.setattr(reg, 'relay', relay)
    app = FastAPI(); app.include_router(router)
    return app, db, customer, relay

async def request(system, method, path, headers=ADMIN, **kwargs):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=system[0]), base_url='http://test') as client:
        return await client.request(method, '/api/admin/registration' + path, headers=headers, **kwargs)

async def approve(system, **changes):
    data = (await request(system, 'GET', '/customers/123/plants/0/preview')).json()
    body = {'provider': 'enm', 'target': 'local', 'expected_hash': data['snapshot_hash'],
            'review_note': 'Daten und Umfang geprueft', 'data_checked': True, 'scope_accepted': True, **changes}
    return await request(system, 'POST', '/customers/123/plants/0/review', json=body)

@pytest.mark.asyncio
@pytest.mark.parametrize('headers,code', [({},401), ({'X-Kratos-Identity-ID':'installer-1','X-Kratos-Identity-Schema':'installer'},403), ({'X-Kratos-Identity-ID':'user'},403)])
@pytest.mark.parametrize('method,path', [('GET','/providers'),('GET','/customers/123/plants/0/preview'),('POST','/customers/123/plants/0/review'),('POST','/jobs/no/start'),('GET','/customers/123/plants/0/jobs')])
async def test_admin_only(system, headers, code, method, path):
    r = await request(system, method, path, headers=headers, json={})
    assert r.status_code == code
    system[3].assert_not_awaited()

@pytest.mark.asyncio
async def test_no_unreviewed_start(system):
    assert (await request(system,'POST','/jobs/missing/start')).status_code == 404
    system[3].assert_not_awaited()

@pytest.mark.asyncio
async def test_review_acknowledgement_and_no_submit(system):
    assert (await approve(system, data_checked=False)).status_code == 422
    assert (await approve(system, scope_accepted=False)).status_code == 422
    assert (await approve(system, submit=True)).status_code == 422
    system[3].assert_not_awaited()

@pytest.mark.asyncio
async def test_preview_change_before_approval(system):
    data = (await request(system,'GET','/customers/123/plants/0/preview')).json()
    system[2]['plants'][0]['kwp'] = '20'
    assert (await approve(system, expected_hash=data['snapshot_hash'])).status_code == 409

@pytest.mark.asyncio
async def test_changed_snapshot_blocks_start(system):
    job = (await approve(system)).json()
    system[2]['plants'][0]['kwp'] = '20'
    assert (await request(system,'POST',f"/jobs/{job['id']}/start")).status_code == 409
    system[3].assert_not_awaited()

@pytest.mark.asyncio
async def test_other_admin_and_expiry(system):
    job = (await approve(system)).json()
    other = {**ADMIN, 'X-Kratos-Identity-ID':'admin-2'}
    assert (await request(system,'POST',f"/jobs/{job['id']}/start",headers=other)).status_code == 403
    await system[1]['registration_jobs'].update_one({'_id':job['id']},{'$set':{'reviewed_at':datetime.now(timezone.utc)-timedelta(hours=1)}})
    assert (await request(system,'POST',f"/jobs/{job['id']}/start")).status_code == 409
    system[3].assert_not_awaited()

@pytest.mark.asyncio
async def test_concurrent_start_and_repeat_review_no_duplicate(system):
    job = (await approve(system)).json()
    results = await asyncio.gather(*[request(system,'POST',f"/jobs/{job['id']}/start") for _ in range(4)])
    assert all(r.status_code == 200 for r in results)
    assert system[3].await_count == 1
    args = system[3].call_args
    assert args.args == ('POST','/api/v1/providers/enm/drafts')
    assert args.kwargs['key'] == job['id']
    assert args.kwargs['payload']['plant']['installation']['kwp'] == '10'
    repeated = (await approve(system)).json()
    assert repeated['state'] == 'draft_created'
    assert repeated['submitted'] is False
    assert 'started_by' in repeated

@pytest.mark.asyncio
async def test_timeout_blocks_further_attempts(system):
    job = (await approve(system)).json()
    system[3].side_effect = HTTPException(502,'private upstream data')
    r = await request(system,'POST',f"/jobs/{job['id']}/start")
    assert r.status_code == 502
    assert 'private upstream' not in r.text
    r = await request(system,'POST',f"/jobs/{job['id']}/start")
    assert r.json()['state'] == 'uncertain'
    assert system[3].await_count == 1
    assert (await approve(system)).json()['state'] == 'uncertain'

@pytest.mark.asyncio
async def test_stale_pending_crash_is_not_replayed(system):
    job = (await approve(system)).json()
    await system[1]['registration_jobs'].update_one({'_id':job['id']},{'$set':{'state':'pending'}})
    assert (await request(system,'POST',f"/jobs/{job['id']}/start")).json()['state'] == 'pending'
    system[3].assert_not_awaited()

@pytest.mark.asyncio
async def test_mainzer_remote_blocked(system):
    assert (await approve(system,provider='mainzer',target='portal')).status_code == 409
    system[3].assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize('provider',['nrm','enm','mainzer','enetz'])
async def test_local_all_providers(system,provider):
    r = await approve(system,provider=provider)
    assert r.status_code == 201
    assert r.json()['payload']['target'] == 'local'

@pytest.mark.asyncio
async def test_address_source_and_portal_payloads(system):
    plant = system[2]['plants'][0]
    plant.update(address_from_customer=False,address_street='Anlagenweg 99',address_plz='54321',address_city='Anlagenort')
    r = await approve(system,provider='enetz',target='portal')
    assert r.json()['payload']['site']['street'] == 'Anlagenweg'
    assert r.json()['payload']['site']['house_number'] == '99'
    assert (await approve(system,provider='enm',target='portal')).status_code == 422
    r = await approve(system,provider='enm',target='portal',product_id=250)
    assert r.json()['payload'] == {'target':'portal','product_id':250}

@pytest.mark.asyncio
async def test_invalid_plant_or_address(system):
    system[2]['plants'][0]['anlagetyp'] = 'wallbox'
    assert (await request(system,'GET','/customers/123/plants/0/preview')).status_code == 422
    system[2]['plants'][0]['anlagetyp'] = 'pv'
    system[2]['address_street'] = 'Ohne Hausnummer'
    assert (await approve(system)).status_code == 422

@pytest.mark.asyncio
async def test_changed_company_invalidates_review(system,monkeypatch):
    system[2]['plants'][0]['company_id'] = 'company'
    company = {'name':'Firma'}
    monkeypatch.setattr(reg.companies,'get_by_id',AsyncMock(side_effect=lambda _:deepcopy(company)))
    job = (await approve(system)).json()
    company['name'] = 'Andere Firma'
    assert (await request(system,'POST',f"/jobs/{job['id']}/start")).status_code == 409

@pytest.mark.asyncio
async def test_relay_secret_stays_server_side(monkeypatch):
    # Exercise the real relay with an in-memory service transport.
    seen = []
    async def respond(request):
        seen.append(request)
        return httpx.Response(200,json={'ok':True})
    real_client = httpx.AsyncClient
    monkeypatch.setattr(reg.settings,'netzportal_api_key','private-test-key')
    monkeypatch.setattr(reg.httpx,'AsyncClient',lambda **kwargs:real_client(transport=httpx.MockTransport(respond),**kwargs))
    assert await reg.relay('GET','/api/v1/providers') == {'ok':True}
    assert seen[0].headers['Authorization'] == 'Bearer private-test-key'
    assert str(seen[0].url) == 'http://na-netzportal:8080/api/v1/providers'

@pytest.mark.asyncio
async def test_unexpected_submission_response_is_uncertain(system):
    job = (await approve(system)).json()
    system[3].return_value = {'id':'wrong', 'provider':'enm', 'storage':'local', 'status':'draft', 'submitted':True}
    assert (await request(system,'POST',f"/jobs/{job['id']}/start")).status_code == 502
    stored = await system[1]['registration_jobs'].find_one({'_id':job['id']})
    assert stored['state'] == 'uncertain'
