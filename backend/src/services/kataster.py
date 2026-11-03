"""Bounded HTTP relay to the private cadastral service (no caller-supplied URLs)."""
from __future__ import annotations

import json
import re
from copy import deepcopy

import httpx
from fastapi import HTTPException

from src.config import settings

RESULT_PATH = re.compile(r"/ergebnisse/([0-9a-f]{32})/(karte\.png|grundstueck\.json)\Z")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_IMAGE_BYTES = 15 * 1024 * 1024


class KatasterRelay:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    async def request(self, method: str, path: str, *, payload=None, image=False):
        limit = MAX_IMAGE_BYTES if image else MAX_JSON_BYTES
        timeout = httpx.Timeout(settings.kataster_timeout_seconds, connect=5.0)
        try:
            async with httpx.AsyncClient(
                base_url=settings.kataster_url.rstrip('/'), timeout=timeout,
                follow_redirects=False, trust_env=False, transport=self.transport,
            ) as client:
                async with client.stream(method, path, json=payload) as response:
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > limit:
                            raise HTTPException(502, 'Kataster-Antwort ist zu gross')
                    status = response.status_code
                    content_type = response.headers.get('content-type', '').split(';', 1)[0].lower()
        except httpx.TimeoutException:
            raise HTTPException(504, 'Zeitlimit beim Katasterdienst erreicht') from None
        except httpx.RequestError:
            raise HTTPException(502, 'Katasterdienst nicht erreichbar') from None

        if status not in (200, 201):
            # Preserve actionable errors; never expose internal hostnames or traceback bodies.
            if status in (400, 404, 415, 422, 429):
                try:
                    data = json.loads(content)
                except (ValueError, UnicodeError):
                    data = {}
                if not isinstance(data, dict):
                    data = {}
                detail = {'code': data.get('code', 'KATASTER_ERROR'),
                          'meldung': data.get('meldung', 'Katasterabfrage fehlgeschlagen')}
                raise HTTPException(status, detail, headers={'Retry-After': '10'} if status == 429 else None)
            raise HTTPException(502, 'Katasterdienst meldet einen Fehler')
        if image:
            if content_type != 'image/png' or not content.startswith(PNG_SIGNATURE):
                raise HTTPException(502, 'Katasterdienst lieferte kein PNG')
            return bytes(content)
        if content_type != 'application/json':
            raise HTTPException(502, 'Katasterdienst lieferte kein JSON')
        try:
            data = json.loads(content)
        except (ValueError, UnicodeError):
            raise HTTPException(502, 'Ungueltige Kataster-Antwort') from None
        if not isinstance(data, dict):
            raise HTTPException(502, 'Ungueltige Kataster-Antwort')
        return data

    async def create(self, payload: dict) -> tuple[str, dict]:
        result = await self.request('POST', '/auszug', payload=payload)
        files = result.get('dateien')
        if not isinstance(files, dict) or result.get('status') not in ('ok', 'teilweise'):
            raise HTTPException(502, 'Ungueltige Kataster-Antwort')
        metadata_path = files.get('json')
        match = RESULT_PATH.fullmatch(metadata_path) if isinstance(metadata_path, str) else None
        if not match or match[2] != 'grundstueck.json':
            raise HTTPException(502, 'Ungueltiger Kataster-Ergebnispfad')
        result_id = match[1]
        image_path = files.get('bild')
        if image_path is not None and image_path != f'/ergebnisse/{result_id}/karte.png':
            raise HTTPException(502, 'Ungueltiger Kataster-Bildpfad')
        return result_id, result

    async def image(self, result_id: str) -> bytes:
        if not re.fullmatch(r'[0-9a-f]{32}', result_id):
            raise HTTPException(404, 'Kataster-Ergebnis nicht gefunden')
        return await self.request('GET', f'/ergebnisse/{result_id}/karte.png', image=True)


def public_result(result: dict, prefix: str, result_id: str) -> dict:
    """Only backend URLs leave the relay; internal upstream links are discarded."""
    result = deepcopy(result)
    has_image = bool(result.get('dateien', {}).get('bild'))
    result['dateien'] = {
        'json': f'{prefix}/ergebnisse/{result_id}/grundstueck.json',
        'bild': f'{prefix}/ergebnisse/{result_id}/karte.png' if has_image else None,
    }
    return result


def get_relay() -> KatasterRelay:
    return KatasterRelay()
