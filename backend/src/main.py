"""Amelanq Netz-Anmeldung - Backend (PV-Anlagen, Wallboxen, Waermepumpen)."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import settings
from src.migrations.runner import gelesene_version, pruefe_stand, run_all
from src.routers import admin, status, installer, docs
from src.routers.lageplan.router import router as lageplan_router
from src.services import database
from src.version import VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starte Backend %s (env=%s)", VERSION, settings.app_env)
    await database.connect()
    # Migrations laufen erst bei Bedarf (Schema-Version nicht aktuell).
    await pruefe_stand(database.get_db())
    yield
    database.disconnect()
    logger.info("Backend beendet")


app = FastAPI(
    title="Amelanq Netz-Anmeldung",
    version=VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(status.router)
app.include_router(admin.router)
app.include_router(installer.router)
app.include_router(docs.router)
app.include_router(lageplan_router)




@app.get("/healthz", tags=["system"])
async def healthz():
    db_ok = await database.ping()
    schema = await gelesene_version(database.get_db()) if db_ok else None
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "up" if db_ok else "down",
        "version": app.version,
        "schemaVersion": schema,
        "env": settings.app_env,
    }


@app.post("/api/admin/migrate", tags=["admin"])
async def trigger_migrations():
    """Manuelle Migrations (einmalig bei Erststart)."""
    await run_all(database.get_db())
    return {"ok": True}
