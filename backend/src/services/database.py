"""MongoDB-Zugriff (motor, async) + Serialisierung."""

import logging
from datetime import date, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from src.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


async def connect() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.mongo_uri)
    # Touch, damit Verbindungsfehler sofort sichtbar werden:
    await _client.admin.command("ping")


def disconnect() -> None:
    """Client schließen (motor >= 3.0: sync Methode)."""
    global _client
    if _client is not None:
        client, _client = _client, None
        client.close()


def get_db():
    if _client is None:
        raise RuntimeError("Database nicht verbunden")
    return _client[settings.mongo_database]


async def ping() -> bool:
    if _client is None:
        return False
    try:
        await _client.admin.command("ping")
        return True
    except Exception:
        return False


# ------------------------------------------------------------- Serialisierung

def serialize(doc: dict | None) -> dict | None:
    """Mongo-Document -> JSON-taugliches dict.

    - ObjectId wird zu String
    - datetime wird zu ISO-String
    - None bleibt None
    """
    if doc is None:
        return None
    return {
        k: (
            str(v) if isinstance(v, ObjectId)
            else v.isoformat() if isinstance(v, (datetime, date))
            else serialize(v) if isinstance(v, dict)
            else v
        )
        for k, v in doc.items()
    }
