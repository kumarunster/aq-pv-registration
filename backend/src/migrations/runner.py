"""Schema-Migrations.

v1: Firmen + Kunden/Anlagen (v0.2.0)
v2: created_by fuer Installer-Trennung (v0.3.0)
"""

from datetime import datetime, timezone

SCHEMA_VERSION = 3

MIGRATIONS = {}


async def migration_1(db):
    """v1: Firmen- und Kunden-Collections + Indizes."""
    await db.create_collection("companies")
    await db.create_collection("customers")
    await db["companies"].create_index("name")
    await db["companies"].create_index("active")
    await db["customers"].create_index("lastname")
    await db["customers"].create_index("firstname")
    await db["customers"].create_index("address_city")
    await db["customers"].create_index("email")
    await db["schema"].update_one(
        {"_id": "meta"},
        {"$set": {"version": 1, "appliedAt": datetime.now(timezone.utc)}},
        upsert=True,
    )


async def migration_2(db):
    """v2: created_by-Index + Backfill (Admin = 000000000000000000000000)."""
    await db["customers"].create_index("created_by")
    # Bestehende Kunden (ohne created_by) dem Admin zuordnen
    await db["customers"].update_many(
        {"created_by": {"$exists": False}},
        {"$set": {"created_by": "000000000000000000000000"}},
    )
    await db["schema"].update_one(
        {"_id": "meta"},
        {"$set": {"version": 2, "appliedAt": datetime.now(timezone.utc)}},
        upsert=True,
    )


async def migration_3(db):
    """v3: ZEREZ-Abbild (zerez_units) + Index auf ZEREZ-ID."""
    await db.create_collection("zerez_units")
    await db["zerez_units"].create_index("zerez_id")
    await db["schema"].update_one(
        {"_id": "meta"},
        {"$set": {"version": 3, "appliedAt": datetime.now(timezone.utc)}},
        upsert=True,
    )


MIGRATIONS[1] = migration_1
MIGRATIONS[2] = migration_2
MIGRATIONS[3] = migration_3


async def run_all(db) -> None:
    """Alle ausstehenden Migrations laufen lassen."""
    meta = await db["schema"].find_one()
    version = meta["version"] if meta else 0
    for target in sorted(MIGRATIONS.keys()):
        if target > version:
            await MIGRATIONS[target](db)
            meta = await db["schema"].find_one()
            version = meta["version"] if meta else 0
            if version != target:
                await db["schema"].update_one(
                    {"_id": "meta"},
                    {"$set": {"version": target}},
                    upsert=True,
                )


async def pruefe_stand(db) -> None:
    """Prueft, ob das Schema aktuell ist."""
    meta = await db["schema"].find_one()
    version = meta["version"] if meta else 0
    if version != SCHEMA_VERSION:
        raise RuntimeError(
            f"Schema-Version {version} != erwartet {SCHEMA_VERSION}. "
            "Migrationscontainer laeusse erst starten."
        )


async def gelesene_version(db) -> int | None:
    meta = await db["schema"].find_one()
    return meta["version"] if meta else None
