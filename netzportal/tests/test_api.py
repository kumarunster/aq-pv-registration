import json
import time
from urllib.parse import parse_qs

import httpx
from fastapi.testclient import TestClient
import pytest

from nrm_api.app import create_app
from nrm_api.client import NRMClient, normalize_installations
from nrm_api.config import Settings
from nrm_api.errors import AuthenticationError, PortalError

SETTINGS = Settings("test-user", "test-password", "a" * 40)
BASE = "https://netzportal.nrm-netzdienste.de"
IDP = "https://np-login.nrm-netzdienste.de"


def product(identity=101, *, closed=False):
    return {
        "id": identity, "requestNumber": str(identity), "orderId": "10",
        "orderNumber": "10", "orderProductNumber": "20", "productId": "56",
        "productName": "PV registration", "requestType": "Netzeinspeisung",
        "requestTypeName": "Netzeinspeisung", "orderStatus": "Zur_Korrektur",
        "orderStatusName": "Zur_Korrektur", "orderDate": "06.10.2026",
        "location": "12345 Example City\nExample Street 5",
        "customer": "Example Applicant\nDifferent Street 124",
        "connectionTaker": "", "divisions": "Strom", "open": not closed,
        "closed": closed, "assigned": False, "newCommentsCount": 1,
    }


class PortalFixture:
    def __init__(self, products=None, *, expire_once=False, login_action=None):
        self.products = products if products is not None else [product()]
        self.logins = 0
        self.list_calls = 0
        self.expire_once = expire_once
        self.login_action = login_action or IDP + "/auth/realms/nrm_kundenportal/login-actions/authenticate?session=example"

    def __call__(self, request):
        path = request.url.path
        if path == "/authentication/saml/Keycloak":
            self.logins += 1
            return httpx.Response(302, headers={"Location": IDP + "/start"})
        if path == "/start":
            return httpx.Response(200, text=(
                f'<form action="{self.login_action}"><input name="username">'
                '<input name="password" type="password">'
                '<input type="hidden" name="csrf" value="expected"></form>'
            ))
        if path.endswith("login-actions/authenticate"):
            body = parse_qs(request.content.decode())
            assert body == {"username": ["test-user"], "password": ["test-password"], "csrf": ["expected"]}
            return httpx.Response(200, text=(
                f'<form action="{BASE}:443/authentication/saml/Keycloak/authenticate">'
                '<input name="SAMLResponse" value="assertion">'
                '<input name="RelayState" value="relay"></form>'
            ))
        if path == "/authentication/saml/Keycloak/authenticate":
            assert parse_qs(request.content.decode())["SAMLResponse"] == ["assertion"]
            return httpx.Response(200, text=(
                '<script>var expiresIn = "43200";var oMessage = '
                '{"result":{"token":"fixture-token","username":"test-user"},"success":true};</script>'
            ))
        assert path == "/client/1.0/executeBO"
        assert request.headers["SimplifierToken"] == "fixture-token"
        assert request.headers["SimplifierApp"] == "Kundenmarktplatz"
        payload = json.loads(request.content)
        # Strict read-only allowlist: any unexpected business operation fails the test.
        if (payload["BOName"], payload["BOMethod"]) == ("User", "getCurrentUser"):
            return httpx.Response(200, json={"success": True, "result": {
                "currentUser": {"loginName": "test-user", "email": "example@example.invalid"},
                "success": True,
            }})
        assert (payload["BOName"], payload["BOMethod"]) == ("ITIZ_KUN_Kundenapp", "listOrdersForUser")
        assert payload["input"] == {
            "tabKey": "all", "languageKey": "deDE", "domain": "netzportal.nrm-netzdienste.de",
            "email": "example@example.invalid", "offset": 0,
        }
        self.list_calls += 1
        if self.expire_once and self.list_calls == 1:
            return httpx.Response(401)
        return httpx.Response(200, json={"success": True, "result": {"allOrderProducts": self.products}})


def client_for(fixture):
    return NRMClient(SETTINGS, transport=httpx.MockTransport(fixture))


def test_full_http_login_all_entries_cache_and_expiry():
    fixture = PortalFixture([product(101), product(102, closed=True)])
    with TestClient(create_app(SETTINGS, client_for(fixture))) as api:
        for _ in range(2):
            response = api.get("/api/v1/installations", headers={"Authorization": "Bearer " + SETTINGS.api_key})
            assert response.status_code == 200
            body = response.json()
            assert body["total"] == 2
            assert [p["id"] for p in body["installations"]] == ["101", "102"]
            assert body["installations"][1]["is_closed"] is True
            assert body["installations"][0]["submitted_on"] == "2026-10-06"
            assert body["installations"][0]["status"] == "Zur Korrektur"
            assert "Different Street" in body["installations"][0]["applicant"]
            assert "Example Street" in body["installations"][0]["location"]
            assert "fixture-token" not in response.text
            assert response.headers["cache-control"] == "no-store"
        assert fixture.logins == 1
        api.app.state.portal._expires_at = time.monotonic() - 1
        assert api.get("/api/v1/installations", headers={"Authorization": "Bearer " + SETTINGS.api_key}).status_code == 200
        assert fixture.logins == 2


def test_unauthorized_does_not_contact_nrm():
    fixture = PortalFixture()
    with TestClient(create_app(SETTINGS, client_for(fixture))) as api:
        for headers in [{}, {"Authorization": "Bearer wrong"}]:
            assert api.get("/api/v1/installations", headers=headers).status_code == 401
        assert fixture.logins == 0
        assert api.get("/health").status_code == 200
        schema = api.get("/openapi.json").json()
        assert schema["paths"]["/api/v1/installations"]["get"]["security"]


def test_expired_session_reauthenticates_once():
    fixture = PortalFixture(expire_once=True)
    client = client_for(fixture)
    try:
        assert len(client.list_installations()) == 1
        assert fixture.logins == 2
        assert fixture.list_calls == 2
    finally:
        client.close()


def test_permanent_expiry_is_bounded_and_sanitized():
    fixture = PortalFixture()
    def handler(request):
        if request.url.path == "/client/1.0/executeBO" and b'listOrdersForUser' in request.content:
            return httpx.Response(403, text="sensitive upstream error")
        return fixture(request)
    with TestClient(create_app(SETTINGS, client_for(handler))) as api:
        response = api.get("/api/v1/installations", headers={"Authorization": "Bearer " + SETTINGS.api_key})
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "nrm_session_expired"
        assert "sensitive" not in response.text
        assert fixture.logins == 2


def test_credentials_never_submitted_to_unexpected_origin():
    fixture = PortalFixture(login_action="https://unexpected.example/login")
    client = client_for(fixture)
    try:
        with pytest.raises(AuthenticationError):
            client.list_installations()
        assert fixture.logins == 1
    finally:
        client.close()


@pytest.mark.parametrize("result", [
    {}, {"allOrderProducts": None}, {"allOrderProducts": "invalid"},
    {"allOrderProducts": [product(), product()]},
    {"allOrderProducts": [dict(product(), orderDate="not a date")]},
    {"allOrderProducts": [dict(product(), open="true")]},
])
def test_schema_drift_is_not_reported_as_empty_success(result):
    with pytest.raises(PortalError):
        normalize_installations(result)


def test_empty_account():
    assert normalize_installations({"allOrderProducts": []}) == []


def test_timeout_is_sanitized():
    def fail(request):
        raise httpx.ReadTimeout("sensitive URL", request=request)
    with TestClient(create_app(SETTINGS, client_for(fail))) as api:
        response = api.get("/api/v1/installations", headers={"Authorization": "Bearer " + SETTINGS.api_key})
        assert response.status_code == 504
        assert "sensitive" not in response.text
