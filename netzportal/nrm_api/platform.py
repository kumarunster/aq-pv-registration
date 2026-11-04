"""Shared provider routes; no caller-supplied upstream URLs or operation names."""
from dataclasses import replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from .client import NRMClient
from .config import Settings
from .errors import ProviderNotConfigured, UnsupportedOperation
from .providers import ENMClient, ENetzAdapter, MainzerAdapter, SimplifierAdapter


class ProviderId(str, Enum):
    nrm = "nrm"
    enm = "enm"
    mainzer = "mainzer"
    enetz = "enetz"


PROVIDERS = {
    "nrm": {"name": "NRM Netzdienste Rhein-Main", "platform": "Simplifier / Keycloak SAML",
            "url": "https://netzportal.nrm-netzdienste.de/appDirect/Kundenmarktplatz/index.html",
            "capabilities": ["draft_prepare", "local_drafts", "portal_draft_initializer", "session", "applications", "application_summary"], "limitations": ["Application summary only. Draft initializer creates an empty cart product; technical fields are not mapped; write not live verified."]},
    "enm": {"name": "Energienetze Mittelrhein", "platform": "Simplifier",
            "url": "https://netzportal.energienetze-mittelrhein.de/appDirect/Kundenmarktplatz/index.html",
            "capabilities": ["draft_prepare", "local_drafts", "portal_draft_initializer", "session", "applications", "application_summary", "catalog", "product_metadata"],
            "limitations": ["All-tab response; upstream pagination cap not established. Empty cart draft initializer only; write not live verified."]},
    "mainzer": {"name": "Mainzer Netze", "platform": "epilot / AWS Cognito SRP",
                "url": "https://installateure.mainzer-netze.de/login",
                "capabilities": ["draft_prepare", "local_drafts", "session", "menus", "applications", "application_details", "entities", "entity_details", "schemas", "workflow_catalog"],
                "limitations": ["Applications are opportunity entities. MFA/password changes require user action. Drafts are local only; remote Journey persistence unavailable."]},
    "enetz": {"name": "e-netz Suedhessen", "platform": "JavaServer Faces / session cookie",
              "url": "https://www.e-netz-suedhessen.de/installateurportal/",
              "capabilities": ["draft_prepare", "local_drafts", "portal_draft_initializer", "session", "menus", "notice_first_page", "notice_details", "applications", "application_visible_tab", "tasks_first_page", "registration_options"],
              "limitations": ["Notice acknowledgement may block operations (409). Details cover the currently rendered tab. Initial site draft writer not live verified. No automatic acknowledgements."]},
}


class ProviderInfo(BaseModel):
    id: ProviderId
    name: str
    platform: str
    url: str
    configured: bool
    capabilities: list[str]
    limitations: list[str]


class ProviderItems(BaseModel):
    provider: ProviderId
    retrieved_at: datetime
    total: int = Field(description="Number of records in this response; not physical-site count")
    items: list[dict[str, Any]]


class SessionInfo(BaseModel):
    provider: ProviderId
    authenticated: bool
    action_required: bool
    reason: str | None = None


def build_adapters(settings: Settings, nrm: NRMClient | None):
    clients = {}
    if nrm:
        clients["nrm"] = SimplifierAdapter(nrm)
    if settings.enm_username:
        clients["enm"] = SimplifierAdapter(ENMClient(replace(settings, username=settings.enm_username, password=settings.enm_password)))
    if settings.mainzer_username:
        clients["mainzer"] = MainzerAdapter(settings.mainzer_username, settings.mainzer_password, settings.timeout_seconds)
    if settings.enetz_username:
        clients["enetz"] = ENetzAdapter(settings.enetz_username, settings.enetz_password, settings.timeout_seconds)
    return clients


def router(authenticate):
    r = APIRouter(prefix="/api/v1/providers", tags=["Multi-provider"], dependencies=[Depends(authenticate)])

    def adapter(request, provider_id):
        instance = request.app.state.providers.get(provider_id.value)
        if instance is None:
            raise ProviderNotConfigured()
        return instance

    def required(instance, cls):
        if not isinstance(instance, cls):
            raise UnsupportedOperation()
        return instance

    @r.get("", response_model=list[ProviderInfo])
    def providers(request: Request):
        """Configured capabilities; does not sign in or claim live availability."""
        return [{"id": identity, **data, "configured": identity in request.app.state.providers}
                for identity, data in PROVIDERS.items()]

    @r.post("/{provider_id}/session", response_model=SessionInfo)
    def session(provider_id: ProviderId, request: Request):
        """Authenticate/verify server-side credentials. Never returns a portal token."""
        return {"provider": provider_id, **adapter(request, provider_id).session()}

    @r.get("/{provider_id}/applications", response_model=ProviderItems)
    def applications(provider_id: ProviderId, request: Request):
        """List provider-native application summaries. e-netz includes drafts and returns 409 when blocked by unread notices."""
        items = adapter(request, provider_id).applications()
        return ProviderItems(provider=provider_id, retrieved_at=datetime.now(timezone.utc), total=len(items), items=items)

    @r.get("/{provider_id}/applications/{application_id}")
    def application(provider_id: ProviderId, application_id: str, request: Request):
        """Mainzer: full readable opportunity. NRM/ENM: list summary, not form details."""
        return adapter(request, provider_id).application(application_id)

    @r.get("/{provider_id}/menus")
    def menus(provider_id: ProviderId, request: Request):
        """Mainzer: configured pages. e-netz: authenticated navigation links."""
        instance = adapter(request, provider_id)
        if not isinstance(instance, (MainzerAdapter, ENetzAdapter)):
            raise UnsupportedOperation()
        return instance.menus()

    @r.get("/{provider_id}/catalog")
    def catalog(provider_id: ProviderId, request: Request):
        """ENM product categories and catalog entries; does not create a cart draft."""
        instance = adapter(request, provider_id)
        if provider_id != ProviderId.enm:
            raise UnsupportedOperation()
        return instance.catalog()

    @r.get("/{provider_id}/products/{product_id}")
    def product(provider_id: ProviderId, request: Request, product_id: Annotated[int, Path(ge=1)]):
        """ENM product metadata/checklists. This is not an application form instance."""
        instance = adapter(request, provider_id)
        if provider_id != ProviderId.enm:
            raise UnsupportedOperation()
        return instance.product(product_id)

    @r.get("/{provider_id}/workflows")
    def workflows(provider_id: ProviderId, request: Request):
        """Mainzer: configured quick actions/Journey IDs, without executing them."""
        return required(adapter(request, provider_id), MainzerAdapter).workflows()

    @r.get("/{provider_id}/schemas")
    def schemas(provider_id: ProviderId, request: Request):
        """Mainzer's readable entity schemas and technical attribute definitions."""
        return required(adapter(request, provider_id), MainzerAdapter).schema_definitions()

    @r.get("/{provider_id}/entities/{schema}")
    def entities(provider_id: ProviderId, schema: str, request: Request,
                 offset: Annotated[int, Query(ge=0)] = 0,
                 limit: Annotated[int, Query(ge=1, le=100)] = 100):
        """Mainzer: paginated search, limited to the known portal entity types."""
        return required(adapter(request, provider_id), MainzerAdapter).search(schema, offset, limit)

    @r.get("/{provider_id}/entities/{schema}/{entity_id}")
    def entity(provider_id: ProviderId, schema: str, entity_id: str, request: Request):
        """Mainzer: read an entity through portal-user permissions."""
        return required(adapter(request, provider_id), MainzerAdapter).entity(schema, entity_id)

    @r.get("/{provider_id}/tasks")
    def tasks(provider_id: ProviderId, request: Request):
        """e-netz: first task page, with explicit incomplete scope."""
        return required(adapter(request, provider_id), ENetzAdapter).tasks()

    @r.get("/{provider_id}/registration-options")
    def registration_options(provider_id: ProviderId, request: Request):
        """e-netz: visible fields/options before 'Anlegen'; creates no application."""
        return required(adapter(request, provider_id), ENetzAdapter).registration_options()

    @r.get("/{provider_id}/notices")
    def notices(provider_id: ProviderId, request: Request):
        """e-netz: first notice page, explicitly marked incomplete; no acknowledgements."""
        return required(adapter(request, provider_id), ENetzAdapter).notices()

    @r.get("/{provider_id}/notices/{notice_id}")
    def notice(provider_id: ProviderId, notice_id: str, request: Request):
        """e-netz: read a notice without marking it as read."""
        return required(adapter(request, provider_id), ENetzAdapter).notice(notice_id)

    return r
