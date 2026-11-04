"""Admin-only registration relay. No arbitrary URLs, credentials or final submission."""
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Path
from pydantic import BaseModel, ConfigDict, Field
from src.routers.admin import _admin_identity
from src.services import registration as service
from src.services.database import get_db


def require_admin(
    x_kratos_identity_id: str | None = Header(None),
    x_kratos_identity_email: str | None = Header(None),
    x_kratos_identity_schema: str | None = Header(None),
):
    return _admin_identity(x_kratos_identity_id, x_kratos_identity_email, x_kratos_identity_schema)


class Review(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_operator_id: str = Field(min_length=1, max_length=100)
    target: Literal['local', 'portal'] = 'local'
    product_id: int | None = Field(None, ge=1)
    expected_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    review_note: str = Field(min_length=3, max_length=2000)
    data_checked: Literal[True]
    scope_accepted: Literal[True]


router = APIRouter(prefix='/api/admin/registration', tags=['admin-registration'], dependencies=[Depends(require_admin)])


@router.get('/providers')
async def providers():
    return await service.relay('GET', '/api/v1/providers')


@router.get('/customers/{customer_id}/plants/{plant_index}/preview')
async def preview(customer_id: str, plant_index: int = Path(ge=0)):
    return await service.preview(customer_id, plant_index)


@router.post('/customers/{customer_id}/plants/{plant_index}/review', status_code=201)
async def review(body: Review, customer_id: str, plant_index: int = Path(ge=0), admin=Depends(require_admin)):
    return await service.review(customer_id, plant_index, body, admin)


@router.post('/jobs/{job_id}/start')
async def start(job_id: str, admin=Depends(require_admin)):
    return await service.start(job_id, admin)


@router.get('/customers/{customer_id}/plants/{plant_index}/jobs')
async def jobs(customer_id: str, plant_index: int = Path(ge=0)):
    records = await get_db()['registration_jobs'].find({'customer_id': customer_id, 'plant_index': plant_index}).sort('reviewed_at', -1).to_list(length=100)
    return [service.public(record) for record in records]
