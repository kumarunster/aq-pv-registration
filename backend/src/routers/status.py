"""Status-Routen. v0.1: nur Dummy-Endpunkte als Grundgeruest."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
async def status():
    """Dummy: zeigt, dass Backend und (später) Datenmodell leben.
    Wird bei Schritt 1 der Roadmap (Datenmodell) ausgebaut:
    Antragsstatistik nach Anlagenart und Netzbetreiber.
    """
    return {
        "app": "amelanq-netz-anmeldung",
        "status": "dummy",
        "anlagetypen": ["pv", "wallbox", "waermepumpe"],
        "antraege": 0,
    }
