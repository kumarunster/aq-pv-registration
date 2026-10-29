"""ZEREZ-Abbild: Synchronisation der Zähler-Zertifikate (4105) nach MongoDB.

- Quelle: ZEREZ GraphQL API (URL in config.zerez_url, aus .env)
- Ziel: MongoDB Collection `zerez_units`
- Trigger:
  * Beim Backend-Start: wenn `zerez_units` leer ist (Initial-Pull, Hintergrund)
  * Manuell: POST /api/admin/zerez/sync
- Filter: is4105 = true
- Pagination: take=100, skip durch totalCount bis alles abgefragt ist
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from src.config import settings
from src.services import database

logger = logging.getLogger("zerez")

QUERY = """
query getUnitsForUnitsOverview($skip: Int, $take: Int, $where: UnitOverviewFilterInput, $order: [UnitOverviewSortInput!]) {
  unitOverview(skip: $skip, take: $take, where: $where, order: $order) {
    totalCount
    items {
      id
      modelName
      unitCode
      maxActivePower
      ratedVoltage
      certificateNormIssueDateDescriptions
      is4105
      category
      certificateHolderName
      isVerified
      primaryEnergySource
      certificateNumber
      validityStartDate
      validityEndDate
    }
  }
}
"""

WHERE = {"and": [{"is4105": {"eq": True}}]}
ORDER = {"createdAt": "DESC"}
PAGE_SIZE = 100

_syncing = False


async def _fetch_page(client: httpx.AsyncClient, skip: int) -> dict:
    body = {
        "operationName": "getUnitsForUnitsOverview",
        "variables": {"skip": skip, "take": PAGE_SIZE, "where": WHERE, "order": ORDER},
        "query": QUERY,
    }
    r = await client.post(settings.zerez_url, json=body)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"ZEREZ GraphQL-Fehler: {data['errors']}")
    return data["data"]["unitOverview"]


def _to_doc(item: dict) -> dict:
    """ZEREZ-Item -> Mongo-Dokument (zerez_id = ZEREZ-UUID)."""
    return {
        "zerez_id": item["id"],
        "modelName": item.get("modelName"),
        "unitCode": item.get("unitCode"),
        "maxActivePower": item.get("maxActivePower"),
        "ratedVoltage": item.get("ratedVoltage"),
        "certificateNormIssueDateDescriptions": item.get("certificateNormIssueDateDescriptions"),
        "is4105": item.get("is4105"),
        "category": item.get("category"),
        "certificateHolderName": item.get("certificateHolderName"),
        "isVerified": item.get("isVerified"),
        "primaryEnergySource": item.get("primaryEnergySource"),
        "certificateNumber": item.get("certificateNumber"),
        "validityStartDate": item.get("validityStartDate"),
        "validityEndDate": item.get("validityEndDate"),
    }


async def needs_sync() -> bool:
    """True, wenn das Abbild noch leer ist (Initial-Pull nötig)."""
    db = database.get_db()
    count = await db["zerez_units"].count_documents({})
    return count == 0


async def sync() -> dict:
    """Volle Synchronisation: alle is4105=true-Einträge ziehen und upserten."""
    global _syncing
    if _syncing:
        return {"ok": False, "detail": "Sync läuft bereits"}
    _syncing = True
    try:
        db = database.get_db()
        total = None
        skip = 0
        inserted = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                ov = await _fetch_page(client, skip)
                items = ov.get("items") or []
                if total is None:
                    total = ov.get("totalCount", 0)
                for item in items:
                    doc = _to_doc(item)
                    await db["zerez_units"].update_one(
                        {"zerez_id": doc["zerez_id"]},
                        {"$set": doc},
                        upsert=True,
                    )
                    inserted += 1
                skip += len(items)
                if not items or skip >= total:
                    break
                # freundlich zur API: kurze Pause zwischen Seiten
                await asyncio.sleep(0.2)
        logger.info("ZEREZ-Sync fertig: %s Einträge (totalCount=%s)", inserted, total)
        return {"ok": True, "synced": inserted, "totalCount": total}
    except Exception as e:
        logger.error("ZEREZ-Sync fehlgeschlagen: %s", e)
        return {"ok": False, "detail": str(e)}
    finally:
        _syncing = False


async def get_unit(zerez_id: str) -> dict | None:
    db = database.get_db()
    doc = await db["zerez_units"].find_one({"zerez_id": zerez_id})
    return doc


async def search(query: str, limit: int = 10) -> list[dict]:
    """Volltext-ähnliche Suche über unitCode/modelName/certificateNumber."""
    db = database.get_db()
    q = query.strip()
    if not q:
        return []
    import re
    pattern = re.escape(q)
    docs = await db["zerez_units"].find(
        {"$or": [{"unitCode": {"$regex": pattern, "$options": "i"}},
                {"modelName": {"$regex": pattern, "$options": "i"}},
                {"certificateNumber": {"$regex": pattern, "$options": "i"}}]}
    ).limit(limit).to_list(limit)
    return docs


async def start_background_if_needed() -> None:
    """Beim Backend-Start: Initial-Pull, wenn Abbild leer. Löst nicht blockierend."""
    try:
        if await needs_sync():
            logger.info("ZEREZ-Abbild leer - starte Hintergrund-Sync")
            asyncio.get_event_loop().create_task(_bg_sync())
    except Exception as e:
        logger.error("ZEREZ-Startprüfung fehlgeschlagen: %s", e)


async def _bg_sync() -> None:
    await asyncio.sleep(5)  # erst mal Backend-Start vollenden lassen
    result = await sync()
    logger.info("ZEREZ-Hintergrund-Sync: %s", result)
