"""Dokumentations-Bilder: Upload/Download/Loeschen.

Objekt-Keys:  customers/<customer_id>/plants/<plant_index>/<timestamp>-<filename>
Auth:         ueber Oathkeeper (Admin/Installer) wie die restliche API.
"""
from __future__ import annotations

import io
import re
import time
from fastapi import APIRouter, Header, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse

from src.routers.installer import _installer_id
from src.services import customers as customer_repo
from src.services import minio_store

router = APIRouter(prefix="/api/docs", tags=["docs"])


def _safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name or "bild.jpg")


@router.post("/customers/{customer_id}/plants/{plant_index}/upload")
async def upload_image(
    customer_id: str,
    plant_index: int,
    file: UploadFile = File(...),
    x_kratos_identity_id: str | None = Header(default=None),
):
    if not x_kratos_identity_id:
        raise HTTPException(401, "Keine Identitaet")
    doc = await customer_repo.get_by_id(customer_id)
    if not doc:
        raise HTTPException(404, "Kunde nicht gefunden")
    if plant_index < 0 or plant_index >= len(doc.get("plants", [])):
        raise HTTPException(404, "Anlage nicht gefunden")

    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Datei zu gross (max 15 MB)")

    ts = int(time.time())
    key = f"customers/{customer_id}/plants/{plant_index}/{ts}-{_safe_filename(file.filename)}"
    try:
        minio_store.upload_bytes(key, data, file.content_type or "application/octet-stream")
    except Exception as e:
        raise HTTPException(502, f"Upload fehlgeschlagen: {e}")

    return {"blob_key": key, "size": len(data), "content_type": file.content_type}


@router.get("/customers/{customer_id}/plants/{plant_index}/{blob_key:path}")
async def download_image(
    customer_id: str,
    plant_index: int,
    blob_key: str,
    x_kratos_identity_id: str | None = Header(default=None),
):
    if not x_kratos_identity_id:
        raise HTTPException(401, "Keine Identitaet")
    doc = await customer_repo.get_by_id(customer_id)
    if not doc:
        raise HTTPException(404, "Kunde nicht gefunden")
    if plant_index < 0 or plant_index >= len(doc.get("plants", [])):
        raise HTTPException(404, "Anlage nicht gefunden")
    # blob_key muss in den customer-scoped Praefix passen
    prefix = f"customers/{customer_id}/plants/{plant_index}/"
    if not blob_key.startswith(prefix):
        raise HTTPException(400, "Ungueltiger blob_key")
    try:
        data, ct = minio_store.download_bytes(blob_key)
    except Exception:
        raise HTTPException(404, "Bild nicht gefunden")
    return StreamingResponse(io.BytesIO(data), media_type=ct)


@router.delete("/customers/{customer_id}/plants/{plant_index}/{blob_key:path}")
async def delete_image(
    customer_id: str,
    plant_index: int,
    blob_key: str,
    x_kratos_identity_id: str | None = Header(default=None),
):
    if not x_kratos_identity_id:
        raise HTTPException(401, "Keine Identitaet")
    doc = await customer_repo.get_by_id(customer_id)
    if not doc:
        raise HTTPException(404, "Kunde nicht gefunden")
    prefix = f"customers/{customer_id}/plants/{plant_index}/"
    if not blob_key.startswith(prefix):
        raise HTTPException(400, "Ungueltiger blob_key")
    minio_store.delete_blob(blob_key)
    return {"ok": True}
