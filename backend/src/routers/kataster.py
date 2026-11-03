"""Authenticated cadastral relay, shared by the admin and installer route groups."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from pymongo.errors import DuplicateKeyError

from src.services.database import get_db
from src.services.kataster import KatasterRelay, get_relay, public_result

router = APIRouter(tags=['liegenschaftskarte'])
ResultId = Annotated[str, Path(pattern=r'^[0-9a-f]{32}$')]


class AuszugRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    adresse: str = Field(min_length=5, max_length=300)
    breite_meter: float = Field(default=60, ge=10, le=1000, allow_inf_nan=False)
    nur_amtlich: StrictBool = True


def identity(x_kratos_identity_id: str | None = Header(default=None)) -> str:
    if not x_kratos_identity_id:
        raise HTTPException(401, 'Keine Identitaet (Oathkeeper-Mutator fehlt)')
    return x_kratos_identity_id


def route_prefix(request: Request) -> str:
    # Includes the caller's existing admin/installer authorization namespace.
    return request.url.path.split('/ergebnisse/', 1)[0].removesuffix('/auszug')


@router.get('/laender')
async def countries(user: str = Depends(identity), relay: KatasterRelay = Depends(get_relay)):
    return await relay.request('GET', '/laender')


@router.post('/auszug')
async def create_extract(
    body: AuszugRequest, request: Request, user: str = Depends(identity),
    relay: KatasterRelay = Depends(get_relay), db=Depends(get_db),
):
    result_id, result = await relay.create(body.model_dump())
    # Persist ownership before returning download URLs. Mongo's _id is unique;
    # duplicate upstream IDs must never overwrite another user's permissions.
    try:
        await db['liegenschaftskarten'].insert_one({
            '_id': result_id, 'created_by': user, 'created_at': datetime.now(timezone.utc),
            'result': result,
        })
    except DuplicateKeyError:
        raise HTTPException(502, 'Katasterdienst hat eine bereits vergebene Ergebnis-ID geliefert') from None
    return public_result(result, route_prefix(request), result_id)


@router.get('/ergebnisse/{result_id}/{filename}')
async def download(
    result_id: ResultId, filename: Literal['karte.png', 'grundstueck.json'], request: Request,
    user: str = Depends(identity), relay: KatasterRelay = Depends(get_relay), db=Depends(get_db),
):
    doc = await db['liegenschaftskarten'].find_one({'_id': result_id, 'created_by': user})
    if not doc:
        raise HTTPException(404, 'Kataster-Ergebnis nicht gefunden')
    headers = {'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'}
    if filename == 'grundstueck.json':
        headers['Content-Disposition'] = 'attachment; filename="grundstueck.json"'
        return JSONResponse(public_result(doc['result'], route_prefix(request), result_id), headers=headers)
    if not doc['result'].get('dateien', {}).get('bild'):
        raise HTTPException(404, 'Fuer dieses Ergebnis ist kein Kartenbild verfuegbar')
    content = await relay.image(result_id)
    headers['Content-Disposition'] = 'inline; filename="liegenschaftskarte.png"'
    return Response(content, media_type='image/png', headers=headers)
