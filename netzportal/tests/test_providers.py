import json
import time
from dataclasses import replace
from urllib.parse import parse_qs

import httpx
from fastapi.testclient import TestClient
import pytest

from nrm_api.app import create_app
from nrm_api.config import Settings
from nrm_api.errors import AuthenticationError, PortalError, PortalTimeout
from nrm_api.providers import ENMClient, ENetzAdapter, MainzerAdapter, SimplifierAdapter, sanitize
from test_api import product

SETTINGS = Settings("test-user", "test-password", "b" * 40)
AUTH = {"Authorization": "Bearer " + SETTINGS.api_key}


def test_enm_login_stays_on_enm_and_reuses_session():
    calls = []
    def handle(request):
        assert request.url.host == "netzportal.energienetze-mittelrhein.de"
        calls.append(request.url.path)
        data = json.loads(request.content)
        if request.url.path == "/genToken/":
            assert data == {"user": "test-user", "pass": "test-password"}
            return httpx.Response(200, json={"success": True, "result": "secret-token"}, headers={"remainingTokenLifetime": "3600"})
        assert request.url.path == "/client/1.0/executeBO"
        assert request.headers["SimplifierToken"] == "secret-token"
        if data["BOMethod"] == "getCurrentUser":
            return httpx.Response(200, json={"success": True, "result": {"currentUser": {"loginName": "test-user", "email": "test@example.invalid"}}})
        assert data["BOMethod"] == "listOrdersForUser"
        assert data["input"]["domain"] == "netzportal.energienetze-mittelrhein.de"
        return httpx.Response(200, json={"success": True, "result": {"allOrderProducts": [product()]}})
    client = ENMClient(SETTINGS, transport=httpx.MockTransport(handle))
    try:
        assert client.list_installations()[0].id == "101"
        assert client.list_installations()[0].id == "101"
        assert calls.count("/genToken/") == 1
    finally:
        client.close()


def test_mainzer_actual_srp_exchange_and_tenant_pinning(monkeypatch):
    # Stub just SRP mathematics; transport still checks the real wire-level flow.
    class SRP:
        def __init__(self, username, password, pool_id, client_id, client):
            assert username == "test-user" and password == "test-password"
            self.client_id = client_id
        def get_auth_params(self):
            return {"USERNAME": "test-user", "SRP_A": "fake-public-ephemeral"}
        def process_challenge(self, challenge, params):
            assert challenge == {"salt": "fixture"}
            return {"USERNAME": "test-user", "PASSWORD_CLAIM_SIGNATURE": "signature"}
    monkeypatch.setattr("nrm_api.providers.AWSSRP", SRP)
    seen = []
    def handle(request):
        seen.append(request.url.path)
        if request.url.host == "cognito-idp.eu-central-1.amazonaws.com":
            body = json.loads(request.content)
            assert "PASSWORD" not in body.get("AuthParameters", {})
            if request.headers["X-Amz-Target"].endswith("InitiateAuth"):
                assert body["AuthFlow"] == "USER_SRP_AUTH"
                return httpx.Response(200, json={"ChallengeName": "PASSWORD_VERIFIER", "ChallengeParameters": {"salt": "fixture"}, "Session": "challenge-session"})
            assert body["Session"] == "challenge-session"
            return httpx.Response(200, json={"AuthenticationResult": {"IdToken": "secret-id-token", "ExpiresIn": 3600}})
        assert request.url.host == "customer-portal-api.sls.epilot.io"
        if request.url.path.endswith("public/config"):
            return httpx.Response(200, json={"cognito_details": {
                "cognito_user_pool_id": "eu-central-1_lFJTX8uhR", "cognito_user_pool_client_id": "6rblmfg9c20s17teutvp3d2c2q"}})
        assert request.headers["Authorization"] == "Bearer secret-id-token"
        assert request.url.path == "/v2/portal/user"
        return httpx.Response(200, json={"data": {"email": [{"email": "test-user"}]}})
    adapter = MainzerAdapter("test-user", "test-password", 30, transport=httpx.MockTransport(handle))
    try:
        assert adapter.session()["authenticated"] is True
        assert adapter.session()["authenticated"] is True
        assert seen.count("/v2/portal/public/config") == 1
    finally:
        adapter.close()


def test_mainzer_refuses_changed_tenant_before_srp():
    def handle(request):
        assert request.url.path == "/v2/portal/public/config"
        return httpx.Response(200, json={"cognito_details": {"cognito_user_pool_id": "unexpected", "cognito_user_pool_client_id": "unexpected"}})
    adapter = MainzerAdapter("u", "p", 30, transport=httpx.MockTransport(handle))
    try:
        with pytest.raises(AuthenticationError):
            adapter.session()
    finally:
        adapter.close()


def authenticated_mainzer(handler):
    adapter = MainzerAdapter("u", "p", 30, transport=httpx.MockTransport(handler))
    adapter.token, adapter.expires_at = "test-token", time.monotonic() + 3600
    return adapter


def test_mainzer_applications_pagination_includes_all_opportunities():
    def handle(request):
        assert request.url.path == "/v2/portal/entity:search"
        body = json.loads(request.content)
        assert body["slug"] == "opportunity"  # Never silently query the empty order list.
        start = body["from"]
        return httpx.Response(200, json={"results": [{"_id": str(start)}], "pagination": {"total": 2, "has_more": start == 0}})
    adapter = authenticated_mainzer(handle)
    try:
        assert [x["_id"] for x in adapter.applications()] == ["0", "1"]
    finally:
        adapter.close()


def test_mainzer_paging_does_not_hide_duplicates_or_truncation():
    def handle(request):
        body = json.loads(request.content)
        return httpx.Response(200, json={"results": [{"_id": "same-id"}], "pagination": {"total": 2, "has_more": body["from"] == 0}})
    adapter = authenticated_mainzer(handle)
    try:
        with pytest.raises(PortalError):
            adapter.applications()
    finally:
        adapter.close()


def test_enetz_login_read_gate_and_notices_no_implicit_acknowledgement():
    posts = []
    info = '''<html>Angemeldet als u
    <p>Bitte bestätigen Sie die aktuellen Informationen.</p>
    <a href="/installateurportal/secure/meldungabgeben/meldungstatus.jsf">Meldungsstatus</a>
    <table id="formId:informationenTableId:table"><tbody><tr><td>59</td><td>Notice title</td>
    <td><a href="/installateurportal/secure/portalinformation-details.jsf?portalinformationId=123">Details</a></td>
    </tr></tbody></table></html>'''
    def handle(request):
        if request.method == "POST":
            posts.append(request.url.path)
            assert request.url.path == "/installateurportal/secure/j_security_check"
            assert parse_qs(request.content.decode()) == {"j_username": ["u"], "j_password": ["p"], "uniqueToken": ["csrf"]}
            return httpx.Response(302, headers={"Location": "/installateurportal/secure/portalinformation.jsf"})
        if request.url.path.endswith("portalaufgabe.jsf"):
            return httpx.Response(200, text='<form id="login"><input name="uniqueToken" value="csrf"><input name="j_password"></form>')
        if request.url.path.endswith("meldungstatus.jsf"):
            return httpx.Response(302, headers={"Location": "/installateurportal/secure/portalinformation.jsf"})
        assert request.url.path.endswith("portalinformation.jsf")
        return httpx.Response(200, text=info)
    adapter = ENetzAdapter("u", "p", 30, transport=httpx.MockTransport(handle))
    with TestClient(create_app(SETTINGS)) as api:
        api.app.state.providers["enetz"] = adapter
        session = api.post("/api/v1/providers/enetz/session", headers=AUTH)
        assert session.status_code == 200 and session.json()["action_required"] is True
        response = api.get("/api/v1/providers/enetz/applications", headers=AUTH)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "portal_action_required"
        notices = api.get("/api/v1/providers/enetz/notices", headers=AUTH).json()
        assert notices["complete"] is False and notices["scope"] == "first_page"
        assert notices["notices"][0]["id"] == "123"
        assert posts == ["/installateurportal/secure/j_security_check"]


def test_provider_routes_auth_missing_credentials_and_unsupported():
    with TestClient(create_app(SETTINGS)) as api:
        assert api.get("/api/v1/providers").status_code == 401
        assert api.post("/api/v1/providers/mainzer/session", headers=AUTH).status_code == 503
        assert api.get("/api/v1/providers/unknown/applications", headers=AUTH).status_code == 422
        assert api.get("/api/v1/providers/nrm/notices", headers=AUTH).status_code == 501
        assert api.get("/api/v1/providers/nrm/entities/opportunity?limit=101", headers=AUTH).status_code == 422
        assert all(not x["configured"] for x in api.get("/api/v1/providers", headers=AUTH).json() if x["id"] != "nrm")


def test_provider_specific_configuration_without_nrm():
    settings = replace(SETTINGS, username="", password="", enm_username="u", enm_password="p")
    with TestClient(create_app(settings)) as api:
        assert api.get("/api/v1/installations", headers=AUTH).status_code == 503
        assert [x["id"] for x in api.get("/api/v1/providers", headers=AUTH).json() if x["configured"]] == ["enm"]


def test_secrets_and_signed_urls_are_not_returned():
    result = sanitize({"password": "secret", "confirmation_token": "secret", "nested": {
        "accessToken": "secret", "url": "https://example.invalid/file?X-Amz-Signature=secret",
        "name": "PV installation"}})
    assert result == {"nested": {"url": None, "name": "PV installation"}}


def test_enetz_status_pages_only_use_next_page_submit():
    def html(page, identity, last=False):
        disabled = 'disabled="disabled"' if last else ''
        return f'''Angemeldet als u<form id="formId" action="/installateurportal/secure/meldungabgeben/meldungstatus.jsf">
        <input name="javax.faces.ViewState" type="hidden" value="private-state">
        <input name="currentPageNumber" type="hidden" value="{page}">
        <input type="submit" name="formId:auswertungenTableId:next" value=">" {disabled}>
        <input type="submit" name="dangerous:delete" value="Löschen">
        <table id="formId:auswertungenTableId:table"><tbody><tr>
        <td>in Vorbereitung</td><td>Bezugs-/ Liefermeldung</td><td></td><td>Example address</td>
        <td>City</td><td></td><td>Strom</td><td></td><td><a href="/installateurportal/secure/meldungabgeben/meldungabgeben.jsf?meldungId={identity}&amp;nextView=edit">Details</a></td>
        </tr></tbody></table></form>'''
    def handle(request):
        assert request.url.path.endswith("meldungstatus.jsf")
        if request.method == "POST":
            data = parse_qs(request.content.decode())
            assert data["formId:auswertungenTableId:next"] == [">"]
            assert "dangerous:delete" not in data
            assert data["javax.faces.ViewState"] == ["private-state"]
            return httpx.Response(200, text=html(2, 102, True))
        return httpx.Response(200, text=html(1, 101))
    adapter = ENetzAdapter("u", "p", 30, transport=httpx.MockTransport(handle))
    adapter.expires_at = time.monotonic() + 3600
    try:
        records = adapter.applications()
        assert [r["id"] for r in records] == ["101", "102"]
        assert all(r["is_draft"] for r in records)
        assert "private-state" not in json.dumps(records)
    finally:
        adapter.close()
