"""Verwaltungs-API: Firmen + Kunden/Anlagen.

Gesc Huezt durch Oathkeeper (Kratos-Session erforderlich).
Der Oathkeeper header-Mutator setzt X-Kratos-Identity-ID/-Email/-Schema
und X-User-Id, die hier ausgelesen werden.
"""

import logging
from fastapi import APIRouter, HTTPException, Header
from fastapi.encoders import jsonable_encoder

from src.models.entities import (
    CompanyCreate,
    CompanyUpdate,
    CustomerCreate,
    CustomerUpdate,
)
from src.services import companies as company_repo
from src.services import customers as customer_repo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


def _admin_identity(
    x_kratos_identity_id: str | None,
    x_kratos_identity_email: str | None,
    x_kratos_identity_schema: str | None,
) -> dict:
    if not x_kratos_identity_id:
        logger.warning("Admin-Request ohne X-Kratos-Identity-ID")
        raise HTTPException(401, "Keine Identitaet (Oathkeeper-Mutator fehlt)")
    return {
        "id": x_kratos_identity_id,
        "email": x_kratos_identity_email,
        "schema": x_kratos_identity_schema,
    }


# ------------------------------------------------------------- Firmen

@router.get("/companies")
async def list_companies(
    active_only: bool = True,
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    return await company_repo.find_all(active_only=active_only)


@router.get("/companies/search")
async def search_companies(
    q: str = "",
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    return await company_repo.search(q)


@router.get("/companies/{company_id}")
async def get_company(
    company_id: str,
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    doc = await company_repo.get_by_id(company_id)
    if not doc:
        raise HTTPException(404, "Firma nicht gefunden")
    return doc


@router.post("/companies", status_code=201)
async def create_company(
    body: CompanyCreate,
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    identity = _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    data = body.model_dump()
    data["created_by"] = identity["id"]
    return await company_repo.create(data)


@router.put("/companies/{company_id}")
async def update_company(
    company_id: str,
    body: CompanyUpdate,
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    doc = await company_repo.update(company_id, body.model_dump())
    if not doc:
        raise HTTPException(404, "Firma nicht gefunden")
    return doc


@router.delete("/companies/{company_id}", status_code=204)
async def delete_company(
    company_id: str,
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    ok = await company_repo.delete(company_id)
    if not ok:
        raise HTTPException(404, "Firma nicht gefunden")


# ------------------------------------------------------------- Kunden

@router.get("/customers")
async def list_customers(
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    return await customer_repo.find_all()


@router.get("/customers/search")
async def search_customers(
    q: str = "",
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    return await customer_repo.search(q)


@router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: str,
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    doc = await customer_repo.get_by_id(customer_id)
    if not doc:
        raise HTTPException(404, "Kunde nicht gefunden")
    return doc


@router.post("/customers", status_code=201)
async def create_customer(
    body: CustomerCreate,
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    identity = _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    data = jsonable_encoder(body)
    data["created_by"] = identity["id"]
    doc = await customer_repo.create(data)
    return doc


@router.put("/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    doc = await customer_repo.update(customer_id, jsonable_encoder(body))
    if not doc:
        raise HTTPException(404, "Kunde nicht gefunden")
    return doc


@router.delete("/customers/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: str,
    x_kratos_identity_id: str | None = Header(default=None),
    x_kratos_identity_email: str | None = Header(default=None),
    x_kratos_identity_schema: str | None = Header(default=None),
):
    _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)
    ok = await customer_repo.delete(customer_id)
    if not ok:
        raise HTTPException(404, "Kunde nicht gefunden")
