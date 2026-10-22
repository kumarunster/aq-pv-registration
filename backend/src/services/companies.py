"""Firmen-Repository. CRUD + Suche."""

from src.services.database import get_db, serialize


async def find_all(active_only: bool = True) -> list[dict]:
    db = get_db()
    q = {"active": True} if active_only else {}
    docs = await db["companies"].find(q).to_list(length=1000)
    return [serialize(d) for d in docs]


async def get_by_id(company_id: str) -> dict | None:
    from bson import ObjectId
    db = get_db()
    try:
        oid = ObjectId(company_id)
    except Exception:
        return None
    doc = await db["companies"].find_one({"_id": oid})
    return serialize(doc)


async def create(data: dict) -> dict:
    db = get_db()
    result = await db["companies"].insert_one(data)
    doc = await db["companies"].find_one({"_id": result.inserted_id})
    return serialize(doc)


async def update(company_id: str, data: dict) -> dict | None:
    from bson import ObjectId
    db = get_db()
    try:
        oid = ObjectId(company_id)
    except Exception:
        return None
    # Nur gesetzte Felder updaten (None = nicht gesetzt).
    update_fields = {k: v for k, v in data.items() if v is not None}
    if not update_fields:
        return await get_by_id(company_id)
    result = await db["companies"].find_one_and_update(
        {"_id": oid}, {"$set": update_fields}, return_document=True
    )
    return serialize(result)


async def delete(company_id: str) -> bool:
    from bson import ObjectId
    db = get_db()
    try:
        oid = ObjectId(company_id)
    except Exception:
        return False
    result = await db["companies"].delete_one({"_id": oid})
    return result.deleted_count == 1


async def search(query: str) -> list[dict]:
    """Volltext-Suche ueber Name, Stadt, Kontakt, E-Mail."""
    db = get_db()
    if not query:
        return await find_all()
    import re
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    docs = await db["companies"].find({
        "$or": [
            {"name": pattern},
            {"address_city": pattern},
            {"contact": pattern},
            {"email": pattern},
        ]
    }).to_list(length=500)
    return [serialize(d) for d in docs]
