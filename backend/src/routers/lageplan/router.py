"""
Lageplan-Editor API (eigenstaendige Komponente, spaeter in Anlagen-Formular integriert).

Endpunkte:
  GET  /api/lageplan/health   -> Health-Check
  GET  /api/lageplan/svg      -> rendert Layout als SVG (Query: layout=JSON-Base64 oder POST)
  POST /api/lageplan/pdf      -> rendert Layout als A4-PDF (via WeasyPrint-Service)
  POST /api/lageplan/save     -> speichert Layout (Phase 8)
"""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from src.config import settings
from src.routers.lageplan.schemas import Layout
from src.services.lageplan.svg_renderer import render_svg

logger = logging.getLogger(__name__)

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
    logger.info("PDF-Export: %d Elemente, Title=%r", len(layout.elements), layout.title)
    try:
        svg = render_svg(layout)
    except Exception as e:
        logger.exception("SVG-Renderfehler bei PDF-Export")
        raise HTTPException(status_code=500, detail=f"SVG-Renderfehler: {e.__class__.__name__}: {e}")

    try:
        html = _wrap_html(svg, layout)
    except Exception as e:
        logger.exception("HTML-Vorlagenfehler bei PDF-Export")
        raise HTTPException(status_code=500, detail=f"HTML-Vorlagenfehler: {e.__class__.__name__}: {e}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            r = await client.post(
                f"{WEASYPRINT_URL}/render",
                json={"html": html},
            )
        except httpx.RequestError as e:
            logger.exception("WeasyPrint nicht erreichbar")
            raise HTTPException(status_code=502, detail=f"WeasyPrint nicht erreichbar: {e}")
        if r.status_code != 200:
            logger.error("WeasyPrint lieferte HTTP %d: %s", r.status_code, r.text[:500])
            raise HTTPException(status_code=502, detail=f"WeasyPrint Fehler (HTTP {r.status_code}): {r.text[:300]}")
        logger.info("PDF-Export erfolgreich: %d Bytes", len(r.content))
        return Response(content=r.content, media_type="application/pdf")


def _wrap_html(svg: str, layout: Layout) -> str:
    """Bettet das SVG in eine A4-HTML-Vorlage fuer WeasyPrint."""
    from xml.sax.saxutils import escape

    # A4-Porträt (210mm breit, 297mm hoch) wie im Ziel-PDF
    title = escape(layout.title)
    # Gemarkung/Flur/Flurstück + Adresse aus metadata, falls vorhanden
    metadata = layout.metadata or {}
    adresse = (metadata.get("adresse") or "").strip()
    gemarkung = (metadata.get("gemarkung") or "").strip()
    flur = (metadata.get("flur") or "").strip()
    flurstueck = (metadata.get("flurstueck") or "").strip()
    meta_line = ""
    if gemarkung or flur or flurstueck:
        parts = []
        if gemarkung:
            parts.append(f"Gemarkung: {escape(gemarkung)}")
        if flur:
            parts.append(f"Flur: {escape(flur)}")
        if flurstueck:
            parts.append(f"Flurstück: {escape(flurstueck)}")
        meta_line = " — ".join(parts)
    # Adresse als eigene Zeile, nur wenn vorhanden
    address_line = f"<div style=\"font-size: 9pt; color: #444; margin-top: 2mm;\">{escape(adresse)}</div>" if adresse else ""

    return f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8"/>
<style>
  @page {{
    size: 210mm 297mm;
    margin: 0;
  }}
  body {{
    margin: 0;
    padding: 0;
    font-family: sans-serif;
  }}
</style>
</head>
<body>
  <div style="width: 210mm; height: 297mm; position: relative;">
    <!-- Header -->
    <div style="position: absolute; top: 10mm; left: 10mm; right: 10mm;">
      <div style="font-size: 14pt; font-weight: bold; line-height: 1.2;">{title}</div>
      {address_line}
      <div style="font-size: 9pt; color: #444; margin-top: 2mm;">{meta_line}</div>
    </div>
    <!-- N-Pfeil (Kompass) oben rechts -->
    <div style="position: absolute; top: 12mm; right: 15mm; text-align: center;">
      <div style="font-size: 10pt; font-weight: bold;">N</div>
      <div style="font-size: 14pt;">↑</div>
    </div>
    <!-- Plan-Bereich: SVG (297x210mm) 1:1 auf A4-Quer, zentral auf Portraet-Seite -->
    <div style="position: absolute; top: 60mm; left: 6.5mm; width: 297mm; height: 210mm;">
      {svg}
    </div>
  </div>
</body>
</html>'''
