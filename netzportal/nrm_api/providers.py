"""Provider adapters. Only verified read operations are exposed.

The JSF notice acknowledgement is deliberately not performed implicitly. Sessions
are per provider, held in memory, renewed once on rejection, and never returned.
"""
from datetime import datetime, timezone
import re
import threading
import time
from typing import Any, Callable
from urllib.parse import urlsplit, urljoin, urlencode, parse_qsl, urlunsplit

from bs4 import BeautifulSoup
import httpx
from pycognito.aws_srp import AWSSRP

from .client import NRMClient
from .config import Settings
from .errors import (
    ActionRequired, AuthenticationError, PortalError, PortalTimeout,
    PortalUnavailable, RecordNotFound, SessionExpired, UnsupportedOperation,
)


SECRET_KEYS = {
    "password", "j_password", "access_token", "accesstoken", "idtoken", "id_token",
    "refresh_token", "refreshtoken", "confirmation_token", "authorization", "simplifiertoken",
    "samlresponse", "javax.faces.viewstate", "uniquetoken", "client_secret",
}


def sanitize(value: Any) -> Any:
    """Exclude authentication material, including signed URLs, from public payloads."""
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()
                if k.lower() not in SECRET_KEYS and not k.lower().endswith("_token")}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str) and value.startswith(("https://", "http://")):
        parts = urlsplit(value)
        sensitive = {"token", "simplifiertoken", "signature", "x-amz-signature", "x-amz-credential", "x-amz-security-token"}
        if any(k.lower() in sensitive for k, v in parse_qsl(parts.query)):
            return None  # A stripped signed URL is not a usable download link.
    return value


class SimplifierAdapter:
    """Reuse NRM's tested HTTP transport/session handling for ENM and NRM."""
    def __init__(self, client: NRMClient):
        self.client = client

    def close(self):
        self.client.close()

    def call(self, operation: Callable[[], Any]):
        with self.client._lock:
            for attempt in range(2):
                try:
                    if not self.client._token or time.monotonic() >= self.client._expires_at:
                        self.client._login()
                    return operation()
                except SessionExpired:
                    self.client._invalidate()
                    if attempt:
                        raise
        raise PortalError()

    def session(self):
        def status():
            result = self.client._bo("User", "getCurrentUser", {})
            user = result.get("currentUser", {})
            if user.get("loginName") != self.client.settings.username:
                raise AuthenticationError()
            return {"authenticated": True, "action_required": False}
        return self.call(status)

    def applications(self):
        return [x.model_dump(mode="json") for x in self.client.list_installations()]

    def application(self, identity: str):
        return next((x for x in self.applications() if x["id"] == identity), None) or _not_found()

    def catalog(self):
        def load():
            categories = self.client._bo("ITIZ_KUN_Kundenapp", "loadCategoriesForUser", {"languageKey": "deDE"}).get("categories")
            if not isinstance(categories, list):
                raise PortalError()
            output = []
            for category in categories:
                subs = self.client._bo("ITIZ_KUN_Kundenapp", "loadSubCategoriesForUser", {
                    "languageKey": "deDE", "categoryId": category["id"],
                }).get("subCategories")
                if not isinstance(subs, list):
                    raise PortalError()
                # NRM has direct products for categories without subcategories.
                for sub in subs or [{"id": -1, "name": category.get("name", "")}]:
                    products = self.client._bo("ITIZ_KUN_Kundenapp", "loadProductsForUser", {
                        "languageKey": "deDE", "subCategoryId": sub["id"],
                    }).get("products")
                    if not isinstance(products, list):
                        raise PortalError()
                    output.append({
                        "category_id": str(category["id"]), "category": category.get("name", ""),
                        "subcategory_id": str(sub["id"]), "subcategory": sub.get("name", ""),
                        "products": [{k: p.get(k) for k in ["id", "name", "description", "divisions"]} for p in products],
                    })
            return sanitize(output)
        return self.call(load)

    def product(self, product_id: int):
        def load():
            x = self.client._bo("ITIZ_KUN_Kundenapp", "loadProductInformation", {
                "languageKey": "deDE", "productId": product_id, "bGetBase64": False,
            })
            if x.get("errorLoadProduct") or not isinstance(x.get("product"), dict):
                raise RecordNotFound()
            # Product catalog metadata, not an editable application or a form instance.
            return sanitize({k: x["product"].get(k) for k in [
                "id", "name", "description", "details", "requestType", "divisions",
                "isPlumberRequired", "checklists", "documents", "freeOfCharge", "priceAfterQuote",
            ]})
        return self.call(load)


class ENMClient(NRMClient):
    origin = "https://netzportal.energienetze-mittelrhein.de"
    allowed_hosts = {"netzportal.energienetze-mittelrhein.de"}

    def _login(self):
        self._invalidate()
        response = self._request("POST", self.origin + "/genToken/", json={
            "user": self.settings.username, "pass": self.settings.password,
        })
        if response.status_code != 200:
            raise AuthenticationError()
        try:
            data = response.json()
        except ValueError:
            raise AuthenticationError() from None
        if data.get("success") is not True or not isinstance(data.get("result"), str) or not data["result"]:
            raise AuthenticationError()
        self._token = data["result"]
        # Prefer the observed expiry header; conservative fallback for missing header.
        try:
            lifetime = int(response.headers.get("remainingTokenLifetime", "900"))
        except ValueError:
            lifetime = 900
        self._expires_at = time.monotonic() + max(0, lifetime - 60)
        user = self._bo("User", "getCurrentUser", {}).get("currentUser")
        if not isinstance(user, dict) or user.get("loginName", "").lower() != self.settings.username.lower() or not user.get("email"):
            self._invalidate()
            raise AuthenticationError()
        self._email = user["email"]


def _not_found():
    raise RecordNotFound()


class HTTPPortal:
    def __init__(self, username: str, password: str, timeout: float, *, transport=None):
        self.username, self.password = username, password
        self.http = httpx.Client(timeout=timeout, follow_redirects=False, transport=transport)
        self.lock = threading.RLock()
        self.expires_at = 0.0

    def close(self):
        self.http.close()
        self.expires_at = 0

    def request(self, method: str, url: str, *, allowed: set[str], **kwargs):
        for _ in range(9):
            parts = urlsplit(url)
            if parts.scheme != "https" or parts.hostname not in allowed or parts.port not in (None, 443) or parts.username or parts.password:
                raise AuthenticationError()
            try:
                r = self.http.request(method, url, **kwargs)
            except httpx.TimeoutException:
                raise PortalTimeout() from None
            except httpx.RequestError:
                raise PortalUnavailable() from None
            if r.status_code in {301, 302, 303, 307, 308}:
                if method == "POST" and r.status_code in {307, 308}:
                    raise AuthenticationError()
                destination = urljoin(str(r.url), r.headers.get("location", ""))
                if urlsplit(destination).hostname != parts.hostname:
                    raise AuthenticationError()
                if r.status_code == 303 or method == "POST":
                    method = "GET"
                    kwargs.pop("data", None)
                    kwargs.pop("json", None)
                kwargs.pop("params", None)
                url = destination
                continue
            if r.status_code in {401, 403}:
                raise SessionExpired()
            if r.status_code == 429 or r.status_code >= 500:
                raise PortalUnavailable()
            return r
        raise PortalError()

    def authenticated(self, operation):
        with self.lock:
            for attempt in range(2):
                try:
                    if time.monotonic() >= self.expires_at:
                        self.login()
                    return operation()
                except SessionExpired:
                    self.expires_at = 0
                    self.http.cookies.clear()
                    if attempt:
                        raise
        raise PortalError()


class MainzerAdapter(HTTPPortal):
    domain = "installateure.mainzer-netze.de"
    api = "https://customer-portal-api.sls.epilot.io"
    cognito = "https://cognito-idp.eu-central-1.amazonaws.com/"
    schemas = {"account", "contact", "file", "opportunity", "order", "portal_user", "contract", "meter", "meter_counter"}

    def json_request(self, method: str, path: str, *, public=False, **kwargs):
        headers = {"Origin": "https://" + self.domain, "Accept-Language": "de-DE", "x-time-zone": "Europe/Berlin"}
        if not public:
            headers["Authorization"] = "Bearer " + self.token
        r = self.request(method, self.api + path, allowed={urlsplit(self.api).hostname}, headers=headers, **kwargs)
        if r.status_code == 404:
            raise RecordNotFound()
        if r.status_code != 200:
            raise PortalError()
        try:
            return r.json()
        except ValueError:
            raise PortalError() from None

    def aws(self, action: str, data):
        r = self.request("POST", self.cognito, allowed={"cognito-idp.eu-central-1.amazonaws.com"}, headers={
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService." + action,
        }, json=data)
        if r.status_code != 200:
            raise AuthenticationError()
        try:
            return r.json()
        except ValueError:
            raise AuthenticationError() from None

    def login(self):
        self.token = ""
        config = self.json_request("GET", "/v2/portal/public/config", public=True, params={"domain": self.domain})
        try:
            details = config["cognito_details"]
            # Pin this provider's tenant. A changed config must be reviewed before auth.
            if details["cognito_user_pool_id"] != "eu-central-1_lFJTX8uhR" or details["cognito_user_pool_client_id"] != "6rblmfg9c20s17teutvp3d2c2q":
                raise AuthenticationError()
            srp = AWSSRP(self.username.lower(), self.password, details["cognito_user_pool_id"],
                         details["cognito_user_pool_client_id"], client=object())
            params = srp.get_auth_params()
            challenge = self.aws("InitiateAuth", {"AuthFlow": "USER_SRP_AUTH", "ClientId": srp.client_id, "AuthParameters": params})
            if challenge.get("ChallengeName") != "PASSWORD_VERIFIER":
                raise AuthenticationError()
            answer = srp.process_challenge(challenge["ChallengeParameters"], params)
            data = {"ClientId": srp.client_id, "ChallengeName": "PASSWORD_VERIFIER", "ChallengeResponses": answer}
            if challenge.get("Session"):
                data["Session"] = challenge["Session"]
            tokens = self.aws("RespondToAuthChallenge", data)
            if tokens.get("ChallengeName") or not isinstance(tokens.get("AuthenticationResult"), dict):
                raise AuthenticationError()
            auth = tokens["AuthenticationResult"]
            self.token = auth["IdToken"]
            if not isinstance(self.token, str) or not self.token:
                raise AuthenticationError()
            user = self.json_request("GET", "/v2/portal/user")["data"]
            emails = [e.get("email", "").lower() for e in user.get("email", []) if isinstance(e, dict)]
            if self.username.lower() not in emails:
                raise AuthenticationError()
            self.expires_at = time.monotonic() + max(0, int(auth["ExpiresIn"]) - 60)
        except (KeyError, TypeError, ValueError):
            self.token = ""
            raise AuthenticationError() from None

    def session(self):
        def verify():
            self.json_request("GET", "/v2/portal/user")
            return {"authenticated": True, "action_required": False}
        return self.authenticated(verify)

    def menus(self):
        def load():
            pages = self.json_request("GET", "/v2/portal/pages", params={"domain": self.domain})
            if not isinstance(pages, list):
                raise PortalError()
            return [{"id": p["id"], "slug": p["slug"],
                     "label": p.get("content", {}).get("label", {}).get("de", p["slug"]),
                     "is_public": p.get("is_public"), "hidden": (p.get("visibility") or {}).get("is_hidden", False)}
                    for p in pages if p.get("id") and p.get("slug")]
        return self.authenticated(load)

    def search(self, schema: str, offset: int, size: int):
        if schema not in self.schemas:
            raise UnsupportedOperation()
        def load():
            x = self.json_request("POST", "/v2/portal/entity:search", json={
                "slug": schema, "from": offset, "size": size, "hydrate": False,
                "fields": ["_id", "_title", "_schema", "status", "_created_at", "_updated_at",
                           "opportunity_number", "order_number", "delivery_address"],
            })
            if not isinstance(x, dict) or not isinstance(x.get("results"), list) or not isinstance(x.get("pagination"), dict):
                raise PortalError()
            return sanitize(x)
        return self.authenticated(load)

    def entity(self, schema: str, identity: str):
        if schema not in self.schemas:
            raise UnsupportedOperation()
        def load():
            x = self.json_request("POST", "/v2/portal/entity:get", json={"slug": schema, "entity_id": identity, "hydrate": True})
            if not isinstance(x, dict) or not isinstance(x.get("result"), dict):
                raise RecordNotFound()
            if x["result"].get("_id") != identity:
                raise PortalError()
            return sanitize(x["result"])
        return self.authenticated(load)

    def applications(self):
        # The dashboard's application list uses opportunity, NOT order.
        result, offset, expected = [], 0, None
        for _ in range(100):
            page = self.search("opportunity", offset, 100)
            pagination = page["pagination"]
            if expected is None:
                expected = pagination.get("total")
            elif pagination.get("total") != expected:
                raise PortalError()  # Concurrent list changes: ask the caller to retry.
            records = page["results"]
            result.extend(records)
            if not pagination.get("has_more"):
                ids = [r.get("_id") for r in result]
                if len(ids) != len(set(ids)) or (isinstance(expected, int) and len(result) != expected):
                    raise PortalError()
                return result
            if not records:
                raise PortalError()
            offset += len(records)
        raise PortalError()  # Explicit error rather than a silently truncated result.

    def application(self, identity: str):
        return self.entity("opportunity", identity)

    def workflows(self):
        def load():
            pages = self.json_request("GET", "/v2/portal/pages", params={"domain": self.domain})
            if not isinstance(pages, list):
                raise PortalError()
            return [{"page": p.get("slug"), "id": b.get("id"),
                     "title": b.get("props", {}).get("content", {}).get("title", {}).get("de", ""),
                     "action": b.get("props", {}).get("content", {}).get("action"),
                     "target": b.get("props", {}).get("content", {}).get("link"),
                     "visibility": b.get("props", {}).get("visibility", {}),
                     "implemented_execution": False}
                    for p in pages for b in p.get("blocks", {}).values() if b.get("type") == "quick_action"]
        return self.authenticated(load)

    def schema_definitions(self):
        def load():
            x = self.json_request("GET", "/v2/portal/schemas")
            if not isinstance(x, dict) or not isinstance(x.get("schemas"), list):
                raise PortalError()
            return sanitize(x)
        return self.authenticated(load)


class ENetzAdapter(HTTPPortal):
    origin = "https://www.e-netz-suedhessen.de"
    base = origin + "/installateurportal/"
    allowed = {"www.e-netz-suedhessen.de"}
    info_path = "/installateurportal/secure/portalinformation.jsf"

    def page(self, path: str):
        r = self.request("GET", self.origin + path, allowed=self.allowed)
        if r.status_code != 200:
            raise PortalError()
        soup = BeautifulSoup(r.text, "html.parser")
        if soup.select_one('input[name="j_password"]'):
            raise SessionExpired()
        if self.username not in soup.get_text(" ", strip=True):
            raise AuthenticationError()
        return r, soup

    def login(self):
        self.http.cookies.clear()
        r = self.request("GET", self.base + "secure/portalaufgabe.jsf", allowed=self.allowed)
        soup = BeautifulSoup(r.text, "html.parser")
        form = soup.select_one("form#login")
        if r.status_code != 200 or form is None or not form.select_one('input[name="j_password"]'):
            raise AuthenticationError()
        # JS in the observed form sets this fixed, same-origin destination.
        data = {i["name"]: i.get("value", "") for i in form.select('input[name]')}
        data.update(j_username=self.username, j_password=self.password)
        r = self.request("POST", self.base + "secure/j_security_check", allowed=self.allowed, data=data)
        soup = BeautifulSoup(r.text, "html.parser")
        if r.status_code != 200 or soup.select_one('input[name="j_password"]') or self.username not in soup.get_text(" ", strip=True):
            raise AuthenticationError()
        self.expires_at = time.monotonic() + 600

    @staticmethod
    def blocked(soup):
        return "Bitte bestätigen Sie die aktuellen Informationen" in soup.get_text(" ", strip=True)

    def session(self):
        def check():
            r, soup = self.page("/installateurportal/secure/meldungabgeben/meldungstatus.jsf")
            gated = urlsplit(str(r.url)).path == self.info_path
            return {"authenticated": True, "action_required": gated,
                    "reason": "unread_portal_notices" if gated else None}
        return self.authenticated(check)

    def menus(self):
        def load():
            r, soup = self.page(self.info_path)
            return [{"label": a.get_text(" ", strip=True), "path": a["href"]}
                    for a in soup.select('a[href]')
                    if a["href"].startswith("/installateurportal/secure/") and a.get_text(" ", strip=True) != "Details"]
        return self.authenticated(load)

    def notices(self):
        def load():
            r, soup = self.page(self.info_path)
            table = soup.find("table", id=lambda x: x and "informationenTableId:table" in x)
            if table is None:
                raise PortalError()
            records = []
            for row in table.select("tbody > tr"):
                cells = row.find_all("td", recursive=False)
                detail = row.find("a", href=lambda x: x and "portalinformation-details.jsf" in x)
                if detail:
                    query = dict(parse_qsl(urlsplit(detail["href"]).query))
                    records.append({"id": query.get("portalinformationId"),
                                    "cells": [c.get_text(" ", strip=True) for c in cells]})
            return {"action_required": self.blocked(soup), "notices": records,
                    "scope": "first_page", "complete": False,
                    "note": "Portal notice table is paginated; no acknowledgement is performed."}
        return self.authenticated(load)

    def notice(self, identity: str):
        if not identity.isdigit():
            raise RecordNotFound()
        def load():
            r, soup = self.page("/installateurportal/secure/portalinformation-details.jsf?portalinformationId=" + identity)
            if urlsplit(str(r.url)).path != "/installateurportal/secure/portalinformation-details.jsf":
                raise RecordNotFound()
            for node in soup.select("script,style,noscript,nav,header,footer"):
                node.decompose()
            main = soup.select_one("form#formId") or soup.select_one("main")
            if main is None:
                raise PortalError()
            return {"id": identity, "text": main.get_text("\n", strip=True)}
        return self.authenticated(load)

    def status_pages(self):
        """Read the JSF status table, including all pages, without invoking row actions."""
        path = "/installateurportal/secure/meldungabgeben/meldungstatus.jsf"
        response, soup = self.page(path)
        seen_pages = set()
        for _ in range(100):
            if urlsplit(str(response.url)).path == self.info_path:
                raise ActionRequired()
            table = soup.find("table", id="formId:auswertungenTableId:table")
            form = soup.select_one("form#formId")
            if table is None or form is None:
                raise PortalError()
            current = form.find("input", attrs={"name": "currentPageNumber"})
            if current is None or current.get("value") in seen_pages:
                raise PortalError()
            seen_pages.add(current.get("value"))
            yield soup, table
            button = next((i for i in form.select('input[type="submit"]')
                           if i.get("value") == ">" and "auswertungenTableId" in i.get("name", "")), None)
            if button is None:
                raise PortalError()
            if button.has_attr("disabled"):
                return
            # Full JSF form state, unchanged filters, and ONLY the verified next-page action.
            data = {}
            for i in form.select("input[name], select[name], textarea[name]"):
                kind = i.get("type", "text")
                if kind in {"submit", "button", "file", "password"} or i.has_attr("disabled"):
                    continue
                if kind in {"checkbox", "radio"} and not i.has_attr("checked"):
                    continue
                if i.name == "select":
                    option = i.select_one("option[selected]") or i.find("option")
                    data[i["name"]] = option.get("value", "") if option else ""
                else:
                    data[i["name"]] = i.get("value", "") if i.name == "input" else i.get_text()
            data[button["name"]] = button["value"]
            action = urljoin(str(response.url), form.get("action", ""))
            if urlsplit(action).path != path:
                raise PortalError()
            response = self.request("POST", action, allowed=self.allowed, data=data)
            soup = BeautifulSoup(response.text, "html.parser")
            if response.status_code != 200:
                raise PortalError()
            if soup.select_one('input[name="j_password"]'):
                raise SessionExpired()
        raise PortalError()

    @staticmethod
    def status_records(table):
        records = []
        for row in table.select("tbody > tr"):
            link = next((a for a in row.select("a[href]") if a.get_text(" ", strip=True) == "Details"), None)
            if link is None:
                # An empty table may render one colspan placeholder, not an application.
                if any(c.get_text(strip=True) for c in row.find_all("td", recursive=False)):
                    raise PortalError()
                continue
            parts = urlsplit(link["href"])
            query = dict(parse_qsl(parts.query))
            identity = query.get("meldungId", "")
            if not identity.isdigit() or parts.path != "/installateurportal/secure/meldungabgeben/meldungabgeben.jsf" or query.get("anschlussmeldungAction"):
                raise PortalError()
            cells = [c.get_text(" ", strip=True) for c in row.find_all("td", recursive=False)]
            if len(cells) < 9:
                raise PortalError()
            records.append({"id": identity, "status": cells[0], "type": cells[1],
                            "connection_object_number": cells[2], "location": cells[3],
                            "city": cells[4], "submitted_on_display": cells[5], "division": cells[6],
                            "is_draft": cells[0] == "in Vorbereitung", "detail_path": link["href"]})
        return records

    def applications(self):
        def load():
            items = [item for soup, table in self.status_pages() for item in self.status_records(table)]
            if len({x["id"] for x in items}) != len(items):
                raise PortalError()
            return items
        return self.authenticated(load)

    def application(self, identity):
        def load():
            record = next((i for i in self.applications() if i["id"] == identity), None)
            if record is None:
                raise RecordNotFound()
            r, soup = self.page(record["detail_path"])
            if urlsplit(str(r.url)).path == self.info_path:
                raise ActionRequired()
            form = soup.select_one("form#formIdMeldungabgeben")
            if form is None:
                raise PortalError()
            return {"summary": record, "fields": self.read_fields(form),
                    "scope": "currently_rendered_tab", "complete": False,
                    "note": "Other tabs and conditional fields are not fetched. No form is saved."}
        return self.authenticated(load)

    @staticmethod
    def read_fields(form):
        fields = []
        for item in form.select("input[name],select[name],textarea[name]"):
            kind = item.get("type", "text")
            if kind in {"hidden", "submit", "button", "password", "file"}:
                continue
            name = item["name"]
            if name.lower() in SECRET_KEYS:
                continue
            label = form.find("label", attrs={"for": item.get("id")})
            field = {"name": name, "label": label.get_text(" ", strip=True) if label else name,
                     "type": item.name if item.name != "input" else kind,
                     "disabled": item.has_attr("disabled")}
            if item.name == "select":
                field["options"] = [{"value": option.get("value", ""), "label": option.get_text(" ", strip=True),
                                     "selected": option.has_attr("selected")} for option in item.find_all("option")]
            elif kind in {"checkbox", "radio"}:
                field["checked"] = item.has_attr("checked")
            else:
                field["value"] = item.get_text() if item.name == "textarea" else item.get("value", "")
            fields.append(field)
        return fields

    def registration_options(self):
        def load():
            r, soup = self.page("/installateurportal/secure/meldungabgeben/meldungabgeben.jsf?nextView=new")
            if urlsplit(str(r.url)).path == self.info_path:
                raise ActionRequired()
            form = soup.select_one("form#formIdMeldungabgeben")
            if form is None:
                raise PortalError()
            return {"fields": self.read_fields(form), "created_application": False}
        return self.authenticated(load)

    def tasks(self):
        def load():
            r, soup = self.page("/installateurportal/secure/portalaufgabe.jsf")
            if urlsplit(str(r.url)).path == self.info_path:
                raise ActionRequired()
            table = soup.find("table", id="formId:portalaufgabeTableId:table")
            if table is None:
                raise PortalError()
            rows = [[c.get_text(" ", strip=True) for c in row.find_all("td", recursive=False)]
                    for row in table.select("tbody > tr")]
            return {"items": [row for row in rows if any(row)], "scope": "first_page", "complete": False}
        return self.authenticated(load)
