"""Installer-Kunden-Repo: nur eigene Kunden/Anlagen.

Ein Installer hat eine Kratos-Identity. Alle von ihm angelegten
Kunden tragen `created_by` = seine Kratos-Identity-ID.
Er sieht nur die eigenen.
"""

from src.services import customers as customer_repo
from src.services.database import get_db, serialize


async def find_my_customers(installer_id: str) -> list[dict]:
    db = get_db()
    docs = await db["customers"].find({"created_by": installer_id}).to_list(length=5000)
    return [serialize(d) for d in docs]


async def get_my_customer(installer_id: str, customer_id: str) -> dict | None:
    """Kunde nur wenn created_by = installer_id."""
    from bson import ObjectId
    db = get_db()
    try:
        oid = ObjectId(customer_id)
    except Exception:
        return None
    doc = await db["customers"].find_one({"_id": oid, "created_by": installer_id})
    return serialize(doc)


async def create_my_customer(installer_id: str, data: dict) -> dict:
    """Kunde anlegen, created_by = installer_id."""
    data["created_by"] = installer_id
    return await customer_repo.create(data)


async def update_my_customer(installer_id: str, customer_id: str, data: dict) -> dict | None:
    """Kunde aktualisieren, nur wenn created_by = installer_id."""
    from bson import ObjectId
    db = get_db()
    try:
        oid = ObjectId(customer_id)
    except Exception:
        return None
    existing = await db["customers"].find_one({"_id": oid, "created_by": installer_id})
    if not existing:
        return None
    return await customer_repo.update(customer_id, data)


async def delete_my_customer(installer_id: str, customer_id: str) -> bool:
    """Kunde loeschen, nur wenn created_by = installer_id."""
    from bson import ObjectId
    db = get_db()
    try:
        oid = ObjectId(customer_id)
    except Exception:
        return False
    result = await db["customers"].delete_one({"_id": oid, "created_by": installer_id})
    return result.deleted_count == 1
