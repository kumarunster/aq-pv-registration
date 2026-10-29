"""Installer-API: eigene Kunden/Anlagen.

Oathkeeper praegelt die Kratos-Session per header_mutator
(X-Kratos-Identity-ID) auf das Backend. Die Routen filtern
strikt auf created_by = <Identity-ID>.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Header

from src.models.entities import CustomerCreate, CustomerUpdate
from src.services import installer_customers as repo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/installer", tags=["installer"])


def _installer_id(x_kratos_identity_id: str | None) -> str:
    if not x_kratos_identity_id:
        logger.warning(
            "Installer-Request ohne X-Kratos-Identity-ID: %s",
            dict(x_kratos_identity_id=x_kratos_identity_id),
        )
        raise HTTPException(401, "Keine Identitaet (Oathkeeper-Mutator fehlt)")
    return x_kratos_identity_id


@router.get("/customers")
async def list_my_customers(x_kratos_identity_id: str | None = Header(default=None)):
    return await repo.find_my_customers(_installer_id(x_kratos_identity_id))


@router.get("/customers/search")
async def search_my_customers(q: str = "", x_kratos_identity_id: str | None = Header(default=None)):
    from src.services.database import get_db, serialize
    import re
    db = get_db()
    if q:
        pattern = re.compile(re.escape(q), re.IGNORECASE)
        q_filter = {"$or": [{"firstname": pattern}, {"lastname": pattern},
                             {"address_city": pattern}, {"email": pattern}]}
    else:
        q_filter = {}
    docs = await db["customers"].find({**q_filter, "created_by": _installer_id(x_kratos_identity_id)}).to_list(length=500)
    return [serialize(d) for d in docs]


@router.get("/customers/{customer_id}")
async def get_my_customer(customer_id: str, x_kratos_identity_id: str | None = Header(default=None)):
    doc = await repo.get_my_customer(_installer_id(x_kratos_identity_id), customer_id)
    if not doc:
        raise HTTPException(404, "Kunde nicht gefunden")
    return doc


@router.post("/customers", status_code=201)
async def create_my_customer(body: CustomerCreate, x_kratos_identity_id: str | None = Header(default=None)):
    data = body.model_dump()
    if getattr(body, "plants", None):
        data["plants"] = body.plants
    return await repo.create_my_customer(_installer_id(x_kratos_identity_id), data)


@router.put("/customers/{customer_id}")
async def update_my_customer(customer_id: str, body: CustomerUpdate, x_kratos_identity_id: str | None = Header(default=None)):
    doc = await repo.update_my_customer(_installer_id(x_kratos_identity_id), customer_id, body.model_dump())
    if not doc:
        raise HTTPException(404, "Kunde nicht gefunden")
    return doc


@router.delete("/customers/{customer_id}", status_code=204)
async def delete_my_customer(customer_id: str, x_kratos_identity_id: str | None = Header(default=None)):
    ok = await repo.delete_my_customer(_installer_id(x_kratos_identity_id), customer_id)
    if not ok:
        raise HTTPException(404, "Kunde nicht gefunden")
