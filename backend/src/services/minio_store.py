"""MinIO (S3-kompatibel) Blob-Storage fuer Dokumentations-Bilder.

Muster: Nebenkosten-Stack (minio + put_object/get_object).
"""
from __future__ import annotations

import io

from minio import Minio

from src.config import settings

_client: Minio | None = None


def get_minio() -> Minio | None:
    """Lazy init. None => nicht konfiguriert (Dev-fallback)."""
    global _client
    if _client is None:
        try:
            endpoint = settings.minio_endpoint.replace("http://", "").replace("https://", "")
            use_ssl = settings.minio_endpoint.startswith("https")
            _client = Minio(
                endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=use_ssl,
            )
            if not _client.bucket_exists(settings.minio_bucket):
                _client.make_bucket(settings.minio_bucket)
        except Exception:
            return None
    return _client


def upload_bytes(blob_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload nach MinIO, liefert den blob_key zurueck."""
    client = get_minio()
    if not client:
        raise RuntimeError("MinIO nicht erreichbar")
    client.put_object(
        settings.minio_bucket,
        blob_key,
        io.BytesIO(data),
        len(data),
        content_type=content_type,
    )
    return blob_key


def download_bytes(blob_key: str) -> tuple[bytes, str]:
    """Lade Objekt, liefert (bytes, content_type)."""
    client = get_minio()
    if not client:
        raise RuntimeError("MinIO nicht erreichbar")
    resp = client.get_object(settings.minio_bucket, blob_key)
    try:
        data = resp.read()
        ct = resp.headers.get("Content-Type", "application/octet-stream")
    finally:
        resp.close()
        resp.release_conn()
    return data, ct


def delete_blob(blob_key: str) -> None:
    client = get_minio()
    if not client:
        return
    try:
        client.remove_object(settings.minio_bucket, blob_key)
    except Exception:
        pass
