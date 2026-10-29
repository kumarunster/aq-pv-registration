"""Kunden und Anlagen - Repository.

Jeder Kunde hat eine oder mehrere Anlagen. Struktur:
  customers: { _id, firstname, lastname, address, phone, email, iban, plants: [...] }

Anlagen liegen inline als list[dict] im customer-Doc. Jede Anlage
hat ihren eigenen anlagetyp, company_id, und optionale Komponenten.
"""

from src.services.database import get_db, serialize


async def find_all() -> list[dict]:
    db = get_db()
    docs = await db["customers"].find({}).to_list(length=5000)
    return [serialize(d) for d in docs]


async def get_by_id(customer_id: str) -> dict | None:
    from bson import ObjectId
    db = get_db()
    try:
        oid = ObjectId(customer_id)
    except Exception:
        return None
    doc = await db["customers"].find_one({"_id": oid})
    return serialize(doc)


async def create(data: dict) -> dict:
    """Neuen Kunden mit (optional) Anlagen anlegen."""
    db = get_db()
    doc = {
        "firstname": data.get("firstname"),
        "lastname": data.get("lastname"),
        "address_street": data.get("address_street"),
        "address_plz": data.get("address_plz"),
        "address_city": data.get("address_city"),
        "phone": data.get("phone"),
        "email": data.get("email"),
        "iban": data.get("iban"),
        "plants": data.get("plants", []),
        "created_by": data.get("created_by"),
        "created_at": None,  # wird unten gesetzt
    }
    from datetime import datetime, timezone
    doc["created_at"] = datetime.now(timezone.utc)
    result = await db["customers"].insert_one(doc)
    created = await db["customers"].find_one({"_id": result.inserted_id})
    return serialize(created)


async def update(customer_id: str, data: dict) -> dict | None:
    """Kunde aktualisieren (Namen/Adresse/etc.).

    Falls data["plants"] gesetzt ist, wird die Anlage-Liste ersetzt.
    """
    from bson import ObjectId
    db = get_db()
    try:
        oid = ObjectId(customer_id)
    except Exception:
        return None
    update_fields = {k: v for k, v in data.items() if v is not None and k != "plants"}
    update_doc = {"$set": update_fields}
    if "plants" in data and data["plants"] is not None:
        update_doc["$set"]["plants"] = data["plants"]
    if not update_doc:
        return await get_by_id(customer_id)
    result = await db["customers"].find_one_and_update(
        {"_id": oid}, update_doc, return_document=True
    )
    return serialize(result)


async def delete(customer_id: str) -> bool:
    from bson import ObjectId
    db = get_db()
    try:
        oid = ObjectId(customer_id)
    except Exception:
        return False
    result = await db["customers"].delete_one({"_id": oid})
    return result.deleted_count == 1


async def search(query: str) -> list[dict]:
    import re
    db = get_db()
    if not query:
        return await find_all()
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    docs = await db["customers"].find({
        "$or": [
            {"firstname": pattern},
            {"lastname": pattern},
            {"address_city": pattern},
            {"email": pattern},
        ]
    }).to_list(length=500)
    return [serialize(d) for d in docs]
