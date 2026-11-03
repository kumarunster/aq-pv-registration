"""Authenticated HTTP adapter for the observed NRM SAML and executeBO flows.

Deliberately exposes no generic business-object executor to API consumers.
No upstream mutation operations, JavaScript execution, or browser cookies.
"""
from datetime import datetime
import json
import re
import threading
import time
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
import httpx

from .config import Settings
from .errors import (
    AuthenticationError, PortalError, PortalTimeout, PortalUnavailable, SessionExpired,
)
from .models import Installation

PORTAL_ORIGIN = "https://netzportal.nrm-netzdienste.de"
LOGIN_ORIGIN = "https://np-login.nrm-netzdienste.de"
APP_NAME = "Kundenmarktplatz"
LOGIN_PATH = "/auth/realms/nrm_kundenportal/login-actions/authenticate"
SAML_PATH = "/authentication/saml/Keycloak/authenticate"


def checked_url(url: str, allowed_hosts: set[str] | None = None) -> str:
    """Restrict redirects/forms to the two observed HTTPS origins, including :443."""
    try:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.hostname not in (allowed_hosts or {urlsplit(PORTAL_ORIGIN).hostname, urlsplit(LOGIN_ORIGIN).hostname})
            or parts.port not in (None, 443)
            or parts.username is not None or parts.password is not None
        ):
            raise AuthenticationError()
    except ValueError:
        raise AuthenticationError() from None
    return url


def form_fields(form: Any) -> dict[str, str]:
    return {
        str(item["name"]): str(item.get("value", ""))
        for item in form.find_all("input", attrs={"name": True})
        if not item.has_attr("disabled") and item.get("type", "text") not in {"submit", "button"}
    }


class NRMClient:
    origin = PORTAL_ORIGIN
    allowed_hosts = {"netzportal.nrm-netzdienste.de", "np-login.nrm-netzdienste.de"}

    def __init__(self, settings: Settings, *, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self.http = httpx.Client(
            timeout=settings.timeout_seconds,
            follow_redirects=False,
            transport=transport,
            headers={"User-Agent": "nrm-netzanmeldung/0.1.0", "Accept-Language": "de-DE,de;q=0.9"},
        )
        self._token: str | None = None
        self._expires_at = 0.0
        self._email: str | None = None
        # Serialize sign-in and upstream calls; a worker owns one in-memory session.
        self._lock = threading.RLock()

    def close(self) -> None:
        self.http.close()
        self._invalidate()

    def _invalidate(self) -> None:
        self._token = None
        self._expires_at = 0
        self._email = None
        self.http.cookies.clear()

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Follow a bounded redirect chain; never forward auth headers cross-origin."""
        for _ in range(9):
            checked_url(url, self.allowed_hosts)
            try:
                response = self.http.request(method, url, **kwargs)
            except httpx.TimeoutException:
                raise PortalTimeout() from None
            except httpx.RequestError:
                raise PortalUnavailable() from None
            if response.status_code not in {301, 302, 303, 307, 308}:
                if response.status_code == 429 or response.status_code >= 500:
                    raise PortalUnavailable()
                return response
            location = response.headers.get("location")
            if not location:
                raise PortalError()
            destination = checked_url(urljoin(str(response.url), location), self.allowed_hosts)
            # Redirects carrying credentials/assertions must never replay a POST.
            if method == "POST" and response.status_code in {307, 308}:
                raise AuthenticationError()
            if urlsplit(destination).hostname != urlsplit(url).hostname:
                kwargs.pop("headers", None)
            if response.status_code == 303 or (method == "POST" and response.status_code in {301, 302}):
                method = "GET"
                kwargs.pop("data", None)
                kwargs.pop("json", None)
            kwargs.pop("params", None)
            url = destination
        raise AuthenticationError()

    def _login(self) -> None:
        self._invalidate()
        response = self._request(
            "GET", PORTAL_ORIGIN + "/authentication/saml/Keycloak",
            params={"appName": APP_NAME, "mode": "default"},
        )
        soup = BeautifulSoup(response.text, "html.parser")
        password = soup.find("input", attrs={"name": "password"})
        form = password.find_parent("form") if password else None
        if response.status_code != 200 or form is None or not form.get("action"):
            raise AuthenticationError()
        action = checked_url(urljoin(str(response.url), form["action"]))
        if urlsplit(action).hostname != urlsplit(LOGIN_ORIGIN).hostname or urlsplit(action).path != LOGIN_PATH:
            raise AuthenticationError()
        data = form_fields(form)
        data.update(username=self.settings.username, password=self.settings.password)
        response = self._request("POST", action, data=data)
        soup = BeautifulSoup(response.text, "html.parser")
        assertion = soup.find("input", attrs={"name": "SAMLResponse"})
        form = assertion.find_parent("form") if assertion else None
        if response.status_code != 200 or form is None or not form.get("action"):
            # Includes invalid credentials, MFA, CAPTCHA, password change and consent.
            raise AuthenticationError()
        action = checked_url(urljoin(str(response.url), form["action"]))
        if urlsplit(action).hostname != urlsplit(PORTAL_ORIGIN).hostname or urlsplit(action).path != SAML_PATH:
            raise AuthenticationError()
        response = self._request("POST", action, data=form_fields(form))
        if response.status_code != 200 or urlsplit(str(response.url)).path != SAML_PATH:
            raise AuthenticationError()
        # Read only the known JSON string fields in the callback; never execute scripts.
        token_match = re.search(r'"token"\s*:\s*("(?:[^"\\]|\\.)*")', response.text)
        expiry_match = re.search(r'var\s+expiresIn\s*=\s*"(\d+)"', response.text)
        if not token_match or not expiry_match:
            raise AuthenticationError()
        token = json.loads(token_match[1])
        if not isinstance(token, str) or not token:
            raise AuthenticationError()
        self._token = token
        self._expires_at = time.monotonic() + max(0, int(expiry_match[1]) - 60)
        user = self._bo("User", "getCurrentUser", {}).get("currentUser")
        if not isinstance(user, dict) or user.get("loginName") != self.settings.username:
            self._invalidate()
            raise AuthenticationError()
        email = user.get("email")
        if not isinstance(email, str) or not email:
            self._invalidate()
            raise AuthenticationError()
        self._email = email

    def _bo(self, name: str, method: str, data: dict[str, Any]) -> dict[str, Any]:
        response = self._request(
            "POST", self.origin + "/client/1.0/executeBO",
            headers={"SimplifierToken": self._token or "", "SimplifierApp": APP_NAME},
            json={"BOName": name, "BOMethod": method, "input": data, "parametrized": True},
        )
        if response.status_code in {401, 403}:
            raise SessionExpired()
        if response.status_code != 200:
            raise PortalError()
        try:
            payload = response.json()
        except ValueError:
            raise PortalError() from None
        if not isinstance(payload, dict) or payload.get("success") is not True:
            raise PortalError()
        result = payload.get("result")
        if not isinstance(result, dict) or result.get("success") is False:
            raise PortalError()
        return result

    def list_installations(self) -> list[Installation]:
        with self._lock:
            for attempt in range(2):
                try:
                    if not self._token or time.monotonic() >= self._expires_at:
                        self._login()
                    result = self._bo("ITIZ_KUN_Kundenapp", "listOrdersForUser", {
                        "tabKey": "all", "languageKey": "deDE",
                        "domain": urlsplit(self.origin).hostname,
                        "email": self._email, "offset": 0,
                    })
                    return normalize_installations(result)
                except SessionExpired:
                    self._invalidate()
                    if attempt:
                        raise
        raise PortalError()  # Unreachable, keeps the return contract explicit.


def normalize_installations(result: dict[str, Any]) -> list[Installation]:
    """One application/order-product per row; do not merge sites or parent orders."""
    products = result.get("allOrderProducts")
    if not isinstance(products, list):
        raise PortalError()
    normalized: list[Installation] = []
    seen: set[str] = set()
    for product in products:
        if not isinstance(product, dict):
            raise PortalError()
        identity = product.get("id")
        if isinstance(identity, bool) or not isinstance(identity, (str, int)) or str(identity) == "":
            raise PortalError()
        identity = str(identity)
        if identity in seen:
            raise PortalError()  # Unexpected duplicates should not silently hide entries.
        seen.add(identity)

        def text(key: str) -> str:
            value = product.get(key)
            if value is None:
                return ""
            if not isinstance(value, (str, int)) or isinstance(value, bool):
                raise PortalError()
            return str(value).strip()

        def boolean(key: str) -> bool:
            value = product.get(key)
            if not isinstance(value, bool):
                raise PortalError()
            return value

        date_text = text("orderDate")
        try:
            submitted_on = datetime.strptime(date_text, "%d.%m.%Y").date() if date_text else None
        except ValueError:
            raise PortalError() from None
        comments = product.get("newCommentsCount", 0)
        if isinstance(comments, bool) or not isinstance(comments, int) or comments < 0:
            raise PortalError()
        status_code = text("orderStatus")
        if not text("requestNumber") or not status_code:
            raise PortalError()
        normalized.append(Installation(
            id=identity,
            application_number=text("requestNumber"),
            order_id=text("orderId"),
            order_number=text("orderNumber"),
            order_product_number=text("orderProductNumber"),
            product_id=text("productId"),
            product_name=text("productName"),
            request_type=text("requestType"),
            request_type_name=text("requestTypeName"),
            status_code=status_code,
            status=(text("orderStatusName") or status_code).replace("_", " "),
            submitted_on=submitted_on,
            location=text("location"),
            applicant=text("customer"),
            connection_taker=text("connectionTaker"),
            division=text("divisions"),
            is_open=boolean("open"),
            is_closed=boolean("closed"),
            is_assigned=boolean("assigned"),
            unread_comments_count=comments,
        ))
    return normalized
