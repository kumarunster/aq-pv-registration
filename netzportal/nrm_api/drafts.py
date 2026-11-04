"""Explicit draft creation. No final-submit operation exists in this module.

Writes are never passed to the read adapters' retry helpers. A persistent intent
journal prevents blind repetition after an uncertain response or process crash.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path as FilePath
import sqlite3
import threading
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit, urljoin
from uuid import uuid4
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, Header, Request, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import PortalError, ActionRequired, ProviderNotConfigured, RecordNotFound
from .platform import ProviderId
from .providers import SimplifierAdapter, ENetzAdapter, MainzerAdapter, sanitize


class DraftError(PortalError):
    def __init__(self, code: str, message: str, status: int = 409):
        self.code, self.message, self.status_code = code, message, status
        super().__init__(message)


class Site(BaseModel):
    model_config = ConfigDict(extra="forbid")
    postal_code: str = Field(pattern=r"^\d{5}$")
    city: str = Field(min_length=1, max_length=200)
    street: str = Field(min_length=1, max_length=200)
    house_number: str = Field(min_length=1, max_length=30)
    district: str = Field(default="", max_length=200)


class DraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: Literal["portal", "local"] = "portal"
    product_id: int | None = Field(default=None, ge=1, description="NRM/ENM: current PV catalog product ID")
    site: Site | None = None
    note: str = Field(default="", max_length=2000)
    plant: dict[str, Any] = Field(default_factory=dict, description="Local JSON staging only; not yet mapped to portal equipment fields")


class DraftResult(BaseModel):
    provider: ProviderId
    id: str
    storage: Literal["portal", "local"]
    status: Literal["draft"] = "draft"
    submitted: Literal[False] = False
    creation_verification: Literal["read_back", "local_commit"]
    fields_saved: list[str]
    limitations: list[str]


class Journal:
    """SQLite transaction claims persist across workers/restarts. No auth secrets."""
    def __init__(self, directory: FilePath):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = directory / "drafts.sqlite3"
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        self.path.chmod(0o600)
        with self.db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS operations (
                provider TEXT NOT NULL, request_key TEXT NOT NULL, fingerprint TEXT NOT NULL,
                state TEXT NOT NULL, result TEXT, payload TEXT, created_at TEXT NOT NULL,
                PRIMARY KEY(provider, request_key))""")

    @contextmanager
    def db(self):
        with sqlite3.connect(self.path, timeout=30) as db:
            yield db

    def replay(self, provider: str, key: str, payload: dict):
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self.db() as db:
            row = db.execute("SELECT fingerprint,state,result FROM operations WHERE provider=? AND request_key=?", (provider, key)).fetchone()
        if row is None:
            return None
        if row[0] != fingerprint:
            raise DraftError("idempotency_conflict", "This key was already used with different data.")
        if row[1] == "complete":
            return json.loads(row[2])
        raise DraftError("draft_outcome_uncertain", "An earlier attempt may have created a draft. Inspect the portal before another attempt; this key will not run again.")

    def claim(self, provider: str, key: str, payload: dict):
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT fingerprint,state,result FROM operations WHERE provider=? AND request_key=?", (provider, key)).fetchone()
            if row:
                if row[0] != fingerprint:
                    raise DraftError("idempotency_conflict", "This key was already used with different data.")
                if row[1] == "complete":
                    return json.loads(row[2])
                raise DraftError("draft_outcome_uncertain", "An earlier attempt may have created a draft. Inspect the portal before another attempt; this key will not run again.")
            db.execute("INSERT INTO operations VALUES(?,?,?,?,?,?,?)", (
                provider, key, fingerprint, "pending", None,
                json.dumps(payload, ensure_ascii=False) if payload.get("target") == "local" else None,
                datetime.now(timezone.utc).isoformat(),
            ))
        return None

    def complete(self, provider, key, result):
        with self.db() as db:
            db.execute("UPDATE operations SET state='complete',result=? WHERE provider=? AND request_key=?",
                       (json.dumps(result), provider, key))

    def get(self, provider, identity):
        with self.db() as db:
            for result, payload in db.execute("SELECT result,payload FROM operations WHERE provider=? AND state='complete'", (provider,)):
                value = json.loads(result)
                if value["id"] == identity:
                    return {**value, **({"input": json.loads(payload)} if payload else {})}
        raise RecordNotFound()


def account_scope(provider, adapter):
    username = adapter.client.settings.username if isinstance(adapter, SimplifierAdapter) else adapter.username
    return provider + ":" + hashlib.sha256(username.lower().encode()).hexdigest()


def ensure_session(adapter):
    # Read-only session validation/renewal is allowed BEFORE the write; not around it.
    adapter.session()


def cart(adapter: SimplifierAdapter):
    result = adapter.client._bo("ITIZ_KUN_Kundenapp", "getShoppingCart", {"languageKey": "deDE"})
    value = result.get("shoppingCart")
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        raise PortalError()
    return value


def pv_product(adapter: SimplifierAdapter, product_id: int):
    data = adapter.client._bo("ITIZ_KUN_Kundenapp", "loadProductInformation", {
        "languageKey": "deDE", "productId": product_id, "bGetBase64": False,
    })
    product = data.get("product")
    if data.get("errorLoadProduct") or not isinstance(product, dict):
        raise RecordNotFound()
    name = str(product.get("name", "")).lower()
    if not ("anmeldung" in name and ("photovoltaik" in name or "erzeugungsanlage" in name)):
        raise DraftError("not_a_pv_registration_product", "Choose a current PV/generation registration catalog product.", 422)
    return product


def jsf_state(form):
    """Preserve values and duplicate hidden names, excluding all submit actions."""
    fields: dict[str, list[str]] = {}
    for item in form.select("input[name],select[name],textarea[name]"):
        kind = item.get("type", "text")
        if kind in {"submit", "button", "file", "password"} or item.has_attr("disabled"):
            continue
        if kind in {"checkbox", "radio"} and not item.has_attr("checked"):
            continue
        if item.name == "select":
            selected = item.select("option[selected]") or item.select("option")[:1]
            values = [x.get("value", "") for x in selected]
        else:
            values = [item.get_text() if item.name == "textarea" else item.get("value", "")]
        fields.setdefault(item["name"], []).extend(values)
    return fields


def enetz_creation_form(adapter: ENetzAdapter):
    response, soup = adapter.page("/installateurportal/secure/meldungabgeben/meldungabgeben.jsf?nextView=new")
    if urlsplit(str(response.url)).path == adapter.info_path:
        raise ActionRequired()
    form = soup.select_one("form#formIdMeldungabgeben")
    if form is None:
        raise PortalError()
    source = "formIdMeldungabgeben:sparteAuswahlId:sparte"
    select = form.find("select", attrs={"name": source})
    if select is None or not select.find("option", value="Strom"):
        raise PortalError()
    data = jsf_state(form)
    data.update({source: "Strom", "javax.faces.partial.ajax": "true", "javax.faces.source": source,
                 "javax.faces.partial.execute": "@all", "javax.faces.partial.render": "@all",
                 "javax.faces.behavior.event": "change", "javax.faces.partial.event": "change"})
    response = adapter.request("POST", adapter.base + "secure/meldungabgeben/meldungabgeben.jsf",
                               allowed=adapter.allowed, data=data, headers={"Faces-Request": "partial/ajax"})
    if response.status_code != 200:
        raise PortalError()
    try:
        root = ET.fromstring(response.text)
        html = next(x.text for x in root.findall(".//update") if x.get("id") == "javax.faces.ViewRoot")
    except (ET.ParseError, StopIteration):
        raise PortalError() from None
    soup = BeautifulSoup(html, "html.parser")
    form = soup.select_one("form#formIdMeldungabgeben")
    if form is None:
        raise PortalError()
    # The partial response may supply a newer ViewState outside the ViewRoot update.
    state = next((x.text for x in root.findall(".//update") if "ViewState" in x.get("id", "") and x.get("id") != "javax.faces.ViewRoot"), None)
    if state:
        for i in form.select('input[name="javax.faces.ViewState"]'):
            i["value"] = state
    existing = form.find("input", attrs={"name": "meldungId"})
    if existing is not None and existing.get("value"):
        raise DraftError("unexpected_existing_draft", "The new form unexpectedly references an existing application.")
    return form


class DraftService:
    def __init__(self, journal: Journal):
        self.journal = journal

    def prepare(self, provider, adapter, product_id=None):
        if isinstance(adapter, SimplifierAdapter):
            with adapter.client._lock:
                ensure_session(adapter)
                existing = cart(adapter)["items"]
                product = pv_product(adapter, product_id) if product_id else None
                return {"provider": provider, "portal_creation_supported": True,
                        "can_create_now": not existing and product is not None,
                        "requires": ["product_id"], "existing_cart_items": len(existing),
                        "product": {"id": product.get("id"), "name": product.get("name")} if product else None,
                        "scope": "empty_cart_product", "technical_fields_mapped": False,
                        "no_final_submission": True,
                        "write_live_verified": False}
        if isinstance(adapter, ENetzAdapter):
            with adapter.lock:
                ensure_session(adapter)
                form = enetz_creation_form(adapter)
                return {"provider": provider, "portal_creation_supported": True, "can_create_now": True,
                        "requires": ["site.postal_code", "site.city", "site.street", "site.house_number"],
                        "fields": adapter.read_fields(form), "scope": "initial_electricity_registration",
                        "no_final_submission": True, "write_live_verified": False}
        if isinstance(adapter, MainzerAdapter):
            with adapter.lock:
                ensure_session(adapter)
                actions = adapter.workflows()
                pv = next((a for a in actions if a.get("action") == "journey" and "Erzeugungs" in a.get("title", "")), None)
                if pv is None:
                    raise PortalError()
                journey_id = pv["target"]
                response = adapter.request("GET", "https://journey-config.sls.epilot.io/v1/journey/configuration/" + journey_id,
                                           allowed={"journey-config.sls.epilot.io"}, headers={"Authorization": "Bearer " + adapter.token})
                if response.status_code != 200:
                    raise PortalError()
                config = response.json()
                # Saving a Journey definition or creating a Submission is NOT a draft.
                return {"provider": provider, "portal_creation_supported": False, "can_create_now": False,
                        "journey_id": journey_id, "saving_progress": sanitize(config.get("settings", {}).get("savingProgress")),
                        "reason": "No verified portal draft persistence for this Journey; submission endpoints are excluded.",
                        "local_staging_supported": True, "no_final_submission": True}
        raise PortalError()

    def create(self, provider, adapter, payload: DraftCreate, key: str):
        if payload.target == "portal":
            if isinstance(adapter, MainzerAdapter):
                raise DraftError("portal_draft_unavailable", "The Mainzer PV Journey has no verified remote draft persistence. Use target=local; no submission is performed.")
            if payload.plant:
                raise DraftError("technical_mapping_not_implemented", "Technical plant JSON can currently be staged with target=local only; it will not be silently ignored.", 422)
            if isinstance(adapter, SimplifierAdapter):
                if not payload.product_id:
                    raise DraftError("product_id_required", "NRM/ENM require an explicit current PV catalog product_id.", 422)
                if payload.site or payload.note:
                    raise DraftError("field_mapping_not_implemented", "The cart initializer creates an empty product. Site/note are not mapped; use target=local to stage them.", 422)
            elif isinstance(adapter, ENetzAdapter):
                if payload.site is None:
                    raise DraftError("site_required", "e-netz requires a real site address before Anlegen.", 422)
                if payload.product_id:
                    raise DraftError("unsupported_product_id", "e-netz uses the Bezugs-/Liefermeldung form, not a Simplifier product_id.", 422)
        scope = account_scope(provider, adapter)
        mutex = adapter.client._lock if isinstance(adapter, SimplifierAdapter) else adapter.lock
        with mutex:
            replay = self.journal.replay(scope, key, payload.model_dump(mode="json"))
            if replay is not None:
                return replay
            # Read-only preflight errors do not consume the idempotency key.
            prepared = None
            if payload.target == "portal":
                ensure_session(adapter)
                if isinstance(adapter, SimplifierAdapter):
                    if cart(adapter)["items"]:
                        raise DraftError("existing_cart_draft", "A cart draft already exists. It will not be deleted, replaced, or merged.")
                    prepared = pv_product(adapter, payload.product_id)
                elif isinstance(adapter, ENetzAdapter):
                    prepared = enetz_creation_form(adapter)
            # The journal claim precedes the one potentially persistent portal write.
            replay = self.journal.claim(scope, key, payload.model_dump(mode="json"))
            if replay is not None:
                return replay
            if payload.target == "local":
                result = DraftResult(provider=provider, id=str(uuid4()), storage="local",
                                     creation_verification="local_commit", fields_saved=["request_json"],
                                     limitations=["Stored by this API only; no portal application has been created."]).model_dump(mode="json")
            elif isinstance(adapter, SimplifierAdapter):
                result = self.create_cart(provider, adapter, prepared)
            elif isinstance(adapter, ENetzAdapter):
                result = self.create_enetz(provider, adapter, prepared, payload)
            else:
                raise PortalError()
            self.journal.complete(scope, key, result)
            return result

    @staticmethod
    def create_cart(provider, adapter, product):
        # This is the single whitelisted creation call, never wrapped in retry logic.
        client_id = hashlib.sha256((provider + ":" + adapter.client.settings.username).encode()).hexdigest()
        response = adapter.client._bo("ITIZ_KUN_Kundenapp", "addProductToShoppingCart", {
            "clientId": client_id, "languageKey": "deDE", "product": product,
            "returnShoppingCart": True, "ignoreItemLimit": False,
            "businessProcessAlreadyInShoppingCartMessage": "Existing draft; no replacement allowed.",
            "nonMatchingCurrencyMessage": "Currency conflict.",
            "productAddToShoppingCartFailedMessage": "Draft initialization failed.",
        })
        added = response.get("addedProductInformation")
        if response.get("success") is not True or not isinstance(added, dict) or added.get("id") is None:
            raise DraftError("draft_outcome_uncertain", "Draft creation could not be confirmed. Inspect the cart; do not blindly retry.")
        identity = str(added["id"])
        current = cart(adapter)["items"]
        if not any(str(i.get("id")) == identity for i in current):
            raise DraftError("draft_outcome_uncertain", "The created cart product was not found on read-back.")
        return DraftResult(provider=provider, id=identity, storage="portal", creation_verification="read_back",
                           fields_saved=["product_id"], limitations=[
                               "Empty cart product initialized; site, operator and technical fields are not populated.",
                               "No completed application, document upload, acceptance or final submission.",
                           ]).model_dump(mode="json")

    @staticmethod
    def create_enetz(provider, adapter, form, payload):
        data = jsf_state(form)
        site = payload.site
        mapping = {
            "postal_code": "combinedLocationFields:idPlz:plz", "city": "combinedLocationFields:idOrt:ort",
            "district": "combinedLocationFields:idOrtsteil:ortsteil", "street": "combinedLocationFields:idStrasse:strasse",
            "house_number": "combinedLocationFields:idHausnummer:hausnummer",
        }
        for field, suffix in mapping.items():
            name = "formIdMeldungabgeben:" + suffix
            if form.find(attrs={"name": name}) is None:
                raise PortalError()
            data[name] = getattr(site, field)
        source = "formIdMeldungabgeben:sparteAuswahlId:sparte"
        data[source] = "Strom"
        kind_name = "formIdMeldungabgeben:anmeldungstypIdStrom:anmeldungstyp"
        kind = form.find("select", attrs={"name": kind_name})
        option = next((o for o in kind.find_all("option") if o.get_text(" ", strip=True) == "Bezugs-/ Liefermeldung"), None) if kind else None
        button_name = "formIdMeldungabgeben:anlegenButtonId"
        button = form.find("input", attrs={"name": button_name, "value": "Anlegen"})
        if option is None or button is None or button.has_attr("disabled"):
            raise PortalError()
        data[kind_name] = option["value"]
        note = "formIdMeldungabgeben:anschlussmeldungBemerkungId:bemerkung"
        if form.find(attrs={"name": note}) is None:
            raise PortalError()
        data[note] = payload.note
        data[button_name] = "Anlegen"
        response = adapter.request("POST", adapter.base + "secure/meldungabgeben/meldungabgeben.jsf",
                                   allowed=adapter.allowed, data=data)
        if response.status_code != 200:
            raise DraftError("draft_outcome_uncertain", "e-netz did not confirm creation. Inspect the portal before retrying.")
        dom = BeautifulSoup(response.text, "html.parser")
        identity = dom.find("input", attrs={"name": "meldungId"})
        identity = identity.get("value", "") if identity else ""
        if not identity.isdigit():
            raise DraftError("draft_not_confirmed", "No new e-netz draft ID was returned. Validation may have failed; inspect the portal before retrying.")
        # Verify actual persistence and draft status through the read-only status list.
        record = next((i for i in adapter.applications() if i["id"] == identity), None)
        if record is None or record.get("is_draft") is not True:
            raise DraftError("draft_outcome_uncertain", "The new record could not be verified as in Vorbereitung.")
        return DraftResult(provider=provider, id=identity, storage="portal", creation_verification="read_back",
                           fields_saved=["site", "note", "Strom", "Bezugs-/Liefermeldung"],
                           limitations=["Only the initial electricity registration is created; PV/operator/technical tabs remain unfilled."]).model_dump(mode="json")


def router(authenticate):
    r = APIRouter(prefix="/api/v1/providers", tags=["Drafts (no final submission)"], dependencies=[Depends(authenticate)])

    def adapter(request, provider):
        value = request.app.state.providers.get(provider.value)
        if value is None:
            raise ProviderNotConfigured()
        return value

    @r.get("/{provider_id}/drafts/prepare")
    def prepare(provider_id: ProviderId, request: Request, product_id: Annotated[int | None, Query(ge=1)] = None):
        """Read-only preflight (e-netz includes transient Strom selection); creates no application."""
        return request.app.state.drafts.prepare(provider_id.value, adapter(request, provider_id), product_id)

    @r.post("/{provider_id}/drafts", response_model=DraftResult, status_code=201)
    def create(provider_id: ProviderId, request: Request, payload: DraftCreate,
               idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]):
        """Create a portal draft or explicitly local staging record. Never finalize/submit.

        NRM/ENM initialize empty cart products only. e-netz saves the initial site.
        Mainzer remote draft creation is unavailable for the inspected Journey.
        A timeout is NOT automatically retried. Use the same key to retrieve a completed result.
        """
        return request.app.state.drafts.create(provider_id.value, adapter(request, provider_id), payload, idempotency_key)

    @r.get("/{provider_id}/drafts/{draft_id}")
    def get(provider_id: ProviderId, draft_id: str, request: Request):
        """Read this API's creation receipt/local JSON; not a fresh remote form read."""
        return request.app.state.drafts.journal.get(account_scope(provider_id.value, adapter(request, provider_id)), draft_id)

    return r
