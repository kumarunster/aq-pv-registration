from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import time

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
import httpx
import pytest

from nrm_api.app import create_app
from nrm_api.config import Settings
from nrm_api.drafts import DraftCreate, DraftError, DraftService, Journal, Site, account_scope
from nrm_api.providers import ENMClient, ENetzAdapter, SimplifierAdapter

SETTINGS = Settings("u", "p", "d" * 40)
AUTH = {"Authorization": "Bearer " + SETTINGS.api_key}


@pytest.mark.parametrize("provider", ["nrm", "enm", "mainzer", "enetz"])
def test_local_json_is_explicit_and_never_contacts_portal(tmp_path, provider):
    settings = replace(SETTINGS, draft_directory=str(tmp_path), enm_username="u", enm_password="p",
                       mainzer_username="u", mainzer_password="p", enetz_username="u", enetz_password="p")
    with TestClient(create_app(settings)) as api:
        adapter = api.app.state.providers[provider]
        http = adapter.client.http if isinstance(adapter, SimplifierAdapter) else adapter.http
        # Any accidental network operation fails this test.
        http.request = lambda *a, **kw: pytest.fail("local staging contacted a portal")
        payload = {"target": "local", "plant": {"module_power_kwp": 12.3, "operator": "Example"}}
        headers = {**AUTH, "Idempotency-Key": "request-1234"}
        path = f"/api/v1/providers/{provider}/drafts"
        first = api.post(path, json=payload, headers=headers)
        assert first.status_code == 201
        assert first.json()["storage"] == "local" and first.json()["submitted"] is False
        second = api.post(path, json=payload, headers=headers)
        assert second.json() == first.json()
        receipt = api.get(path + "/" + first.json()["id"], headers=AUTH)
        assert receipt.json()["input"]["plant"] == payload["plant"]
        changed = api.post(path, json={"target": "local", "plant": {"module_power_kwp": 99}}, headers=headers)
        assert changed.status_code == 409
        assert changed.json()["error"]["code"] == "idempotency_conflict"
        assert api.post(path, json={**payload, "submit": True}, headers=headers).status_code == 422
        assert api.post(path, json=payload, headers=AUTH).status_code == 422
    assert (tmp_path / "drafts.sqlite3").stat().st_mode & 0o777 == 0o600


class CartPortal:
    def __init__(self, *, timeout=False, existing=False):
        self.items = [{"id": "old"}] if existing else []
        self.creations = 0
        self.timeout = timeout
    def __call__(self, request):
        assert request.url.host == "netzportal.energienetze-mittelrhein.de"
        data = json.loads(request.content)
        if request.url.path == "/genToken/":
            return httpx.Response(200, json={"success": True, "result": "token"})
        method = data["BOMethod"]
        assert method in {"getCurrentUser", "getShoppingCart", "loadProductInformation", "addProductToShoppingCart"}
        if method == "getCurrentUser":
            result = {"currentUser": {"loginName": "u", "email": "u@example.invalid"}}
        elif method == "getShoppingCart":
            result = {"shoppingCart": {"items": self.items}}
        elif method == "loadProductInformation":
            result = {"product": {"id": 250, "name": "Anmeldung einer Erzeugungsanlage"}}
        else:
            self.creations += 1
            assert data["input"]["ignoreItemLimit"] is False
            assert data["input"]["product"]["id"] == 250
            self.items = [{"id": "draft-1", "productId": 250}]
            if self.timeout:
                raise httpx.ReadTimeout("unknown after create", request=request)
            result = {"success": True, "addedProductInformation": {"id": "draft-1"}}
        return httpx.Response(200, json={"success": True, "result": result})


def simplifier(portal):
    return SimplifierAdapter(ENMClient(SETTINGS, transport=httpx.MockTransport(portal)))


def test_cart_created_once_replayed_even_with_nonempty_cart_after_restart(tmp_path):
    portal = CartPortal()
    adapter = simplifier(portal)
    payload = DraftCreate(product_id=250)
    try:
        first = DraftService(Journal(tmp_path)).create("enm", adapter, payload, "key-12345")
        assert first["submitted"] is False and first["creation_verification"] == "read_back"
        # A new service/journal object simulates process restart.
        second = DraftService(Journal(tmp_path)).create("enm", adapter, payload, "key-12345")
        assert second == first and portal.creations == 1
    finally:
        adapter.close()


def test_existing_cart_never_replaced(tmp_path):
    portal = CartPortal(existing=True)
    adapter = simplifier(portal)
    try:
        with pytest.raises(DraftError, match="already exists"):
            DraftService(Journal(tmp_path)).create("enm", adapter, DraftCreate(product_id=250), "key-12345")
        assert portal.creations == 0 and portal.items == [{"id": "old"}]
    finally:
        adapter.close()


def test_uncertain_write_is_not_repeated(tmp_path):
    portal = CartPortal(timeout=True)
    adapter = simplifier(portal)
    payload = DraftCreate(product_id=250)
    service = DraftService(Journal(tmp_path))
    try:
        from nrm_api.errors import PortalTimeout
        with pytest.raises(PortalTimeout):
            service.create("enm", adapter, payload, "key-12345")
        with pytest.raises(DraftError) as error:
            DraftService(Journal(tmp_path)).create("enm", adapter, payload, "key-12345")
        assert error.value.code == "draft_outcome_uncertain" and portal.creations == 1
    finally:
        adapter.close()


def test_unmapped_json_fails_before_write(tmp_path):
    portal = CartPortal()
    adapter = simplifier(portal)
    try:
        with pytest.raises(DraftError) as error:
            DraftService(Journal(tmp_path)).create("enm", adapter, DraftCreate(product_id=250, plant={"kwp": 10}), "key-12345")
        assert error.value.status_code == 422 and portal.creations == 0
    finally:
        adapter.close()


def test_mainzer_remote_unavailable_does_not_create_entity_or_submission(tmp_path):
    settings = replace(SETTINGS, draft_directory=str(tmp_path), mainzer_username="u", mainzer_password="p")
    with TestClient(create_app(settings)) as api:
        api.app.state.providers["mainzer"].http.request = lambda *a, **kw: pytest.fail("unexpected Mainzer write")
        r = api.post("/api/v1/providers/mainzer/drafts", json={"target": "portal"},
                     headers={**AUTH, "Idempotency-Key": "key-12345"})
        assert r.status_code == 409 and r.json()["error"]["code"] == "portal_draft_unavailable"


def test_journal_claim_is_atomic_and_account_scoped(tmp_path):
    journal = Journal(tmp_path)
    def claim(_):
        try:
            journal.claim("provider:account", "key-12345", {"target": "portal"})
            return True
        except DraftError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(claim, range(2))) == 1
    assert journal.claim("provider:another-account", "key-12345", {"target": "portal"}) is None


def test_enetz_only_anlegen_is_submitted_and_draft_status_is_verified(tmp_path, monkeypatch):
    prefix = "formIdMeldungabgeben:"
    controls = '<input name="meldungId" value="" type="hidden"><input name="javax.faces.ViewState" value="private" type="hidden">'
    controls += '<select name="'+prefix+'sparteAuswahlId:sparte"><option value="Strom" selected>Strom</option></select>'
    for suffix in ["combinedLocationFields:idPlz:plz", "combinedLocationFields:idOrt:ort", "combinedLocationFields:idOrtsteil:ortsteil", "combinedLocationFields:idStrasse:strasse", "combinedLocationFields:idHausnummer:hausnummer", "anschlussmeldungBemerkungId:bemerkung"]:
        controls += '<input name="'+prefix+suffix+'" value="">'
    controls += '<select name="'+prefix+'anmeldungstypIdStrom:anmeldungstyp"><option value="expected">Bezugs-/ Liefermeldung</option></select>'
    controls += '<input type="submit" name="'+prefix+'anlegenButtonId" value="Anlegen"><input type="submit" name="final" value="Absenden">'
    form = BeautifulSoup('<form id="formIdMeldungabgeben">'+controls+'</form>', 'html.parser').find('form')
    adapter = ENetzAdapter("u", "p", 30)
    calls = []
    def request(method, url, **kwargs):
        assert method == "POST" and url.endswith("/secure/meldungabgeben/meldungabgeben.jsf")
        data = kwargs["data"]
        assert data[prefix+"anlegenButtonId"] == "Anlegen"
        assert "final" not in data
        assert data[prefix+"combinedLocationFields:idPlz:plz"] == "12345"
        calls.append(data)
        return httpx.Response(200, text='<input name="meldungId" value="123">')
    monkeypatch.setattr(adapter, 'request', request)
    monkeypatch.setattr(adapter, 'session', lambda: {"authenticated": True})
    monkeypatch.setattr(adapter, 'applications', lambda: [{"id": "123", "is_draft": True}])
    monkeypatch.setattr('nrm_api.drafts.enetz_creation_form', lambda a: form)
    payload = DraftCreate(site=Site(postal_code="12345", city="Example", street="Example Street", house_number="1"))
    try:
        result = DraftService(Journal(tmp_path)).create("enetz", adapter, payload, "key-12345")
        assert result["id"] == "123" and result["submitted"] is False
        assert len(calls) == 1
    finally:
        adapter.close()
