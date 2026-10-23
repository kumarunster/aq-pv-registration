"""
Lageplan-Editor API (eigenstaendige Komponente, spaeter in Anlagen-Formular integriert).

Endpunkte:
  GET  /api/lageplan/health   -> Health-Check
  GET  /api/lageplan/svg      -> rendert Layout als SVG (Query: layout=JSON-Base64 oder POST)
  POST /api/lageplan/pdf      -> rendert Layout als A4-PDF (via WeasyPrint-Service)
  POST /api/lageplan/save     -> speichert Layout (Phase 8)
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from src.config import settings
from src.routers.lageplan.schemas import Layout
from src.services.lageplan.svg_renderer import render_svg

router = APIRouter(prefix="/api/lageplan", tags=["lageplan"])

# WeasyPrint-Service (eigenstaendiger Docker-Service, nur intern)
WEASYPRINT_URL = settings.weasyprint_url


@router.get("/health")
def health() -> dict:
    """Health-Endpunkt: laeuft das Lageplan-Backend?"""
    return {"status": "ok", "service": "lageplan", "version": "0.2.0"}


@router.post("/svg")
async def generate_svg(layout: Layout) -> Response:
    """Rendert das Layout als SVG (Vorschau/Download)."""
    svg = render_svg(layout)
    return Response(content=svg, media_type="image/svg+xml")


@router.post("/pdf")
async def generate_pdf(layout: Layout) -> Response:
    """
    Generiert ein A4-PDF aus dem Lageplan-Layout.

    Flow:
      1. Lageplan-Backend rendert das SVG.
      2. Das SVG wird in eine HTML-Vorlage eingebettet.
      3. Die Vorlage geht an den WeasyPrint-Service.
      4. WeasyPrint liefert das fertige A4-PDF.
    """
    svg = render_svg(layout)
    html = _wrap_html(svg, layout)

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            r = await client.post(
                f"{WEASYPRINT_URL}/render",
                json={"html": html},
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"WeasyPrint nicht erreichbar: {e}")
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"WeasyPrint Fehler: {r.text[:300]}")
        return Response(content=r.content, media_type="application/pdf")


def _wrap_html(svg: str, layout: Layout) -> str:
    """Bettet das SVG in eine A4-HTML-Vorlage fuer WeasyPrint."""
    from xml.sax.saxutils import escape

    return f'''<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"/></head>
<body style="margin:0">
  <div style="width: 210mm; height: 297mm; padding: 0; box-sizing: border-box; position: relative;">
    {svg}
  </div>
</body>
</html>'''
