from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .client import NRMClient
from .config import Settings
from .errors import PortalError
from .models import ErrorResponse, InstallationList
from .platform import build_adapters, router
from .errors import ProviderNotConfigured
from .drafts import DraftService, Journal, Site, router as draft_router
from .vnbdigital import VNBDigitalClient

bearer = HTTPBearer(auto_error=False)


def create_app(settings: Settings | None = None, portal: NRMClient | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings or Settings.from_env()
        app.state.portal = portal or (NRMClient(app.state.settings) if app.state.settings.username else None)
        app.state.providers = build_adapters(app.state.settings, app.state.portal)
        directory = Path(app.state.settings.draft_directory) if app.state.settings.draft_directory else Path(__file__).resolve().parent.parent / ".state"
        app.state.drafts = DraftService(Journal(directory))
        try:
            yield
        finally:
            for provider in app.state.providers.values():
                provider.close()

    app = FastAPI(
        title="PV Netzanmeldung Multi-Provider API", version="0.4.0",
        description=(
            "Unofficial adapters for NRM, ENM, Mainzer Netze and e-netz Suedhessen. Read operations and limited draft initialization; no final submission. "
            "Lists the configured account's applications from Bestellungen / Alle. "
            "Uses server-side provider credentials; API callers authenticate with a separate bearer key."
        ), lifespan=lifespan,
    )

    @app.middleware("http")
    async def prevent_caching(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(PortalError)
    async def portal_error(request: Request, error: PortalError):
        provider = request.path_params.get("provider_id")
        code, message = error.code, error.message
        if provider and provider != "nrm":
            code = code.replace("nrm_", "portal_")
            message = message.replace("NRM", "The provider portal")
        body = {"error": {"code": code, "message": message}}
        if provider:
            body["error"]["provider"] = provider
        return JSONResponse(status_code=error.status_code, content=body)

    def authenticate(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> None:
        if (
            credentials is None
            or credentials.scheme.lower() != "bearer"
            or not secrets.compare_digest(
                credentials.credentials.encode(), request.app.state.settings.api_key.encode(),
            )
        ):
            raise HTTPException(
                status_code=401, detail="A valid API bearer key is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @app.get("/health", tags=["Operations"])
    def health() -> dict[str, str]:
        """Process liveness only; does not contact NRM or verify its availability."""
        return {"status": "ok", "version": "0.4.0"}

    @app.get(
        "/api/v1/installations", response_model=InstallationList,
        tags=["Installations"], dependencies=[Depends(authenticate)],
        responses={
            401: {"description": "Missing or invalid API bearer key"},
            502: {"model": ErrorResponse, "description": "NRM sign-in/session/schema error"},
            503: {"model": ErrorResponse, "description": "NRM unavailable or rate-limited"},
            504: {"model": ErrorResponse, "description": "NRM request timed out"},
        },
    )
    def list_installations(request: Request) -> InstallationList:
        """Fetch every application in NRM's current 'Alle' response, including closed ones.

        Each entry is an application/order-product, not a unique physical installation.
        No drafts or full technical system details are included in this first version.
        """
        if request.app.state.portal is None:
            raise ProviderNotConfigured()
        installations = request.app.state.portal.list_installations()
        return InstallationList(
            retrieved_at=datetime.now(timezone.utc), total=len(installations),
            installations=installations,
        )

    @app.post("/api/v1/network-operators/resolve", tags=["Network operators"], dependencies=[Depends(authenticate)])
    def resolve_network_operator(site: Site):
        """Read-only VNBdigital lookup for a house-level low-voltage address."""
        return VNBDigitalClient().resolve(site)

    app.include_router(router(authenticate))
    app.include_router(draft_router(authenticate))
    return app


app = create_app()
