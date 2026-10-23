"""
SVG-Renderer: wandelt das Lageplan-Layout in ein A4-SVG um.

Koordinatensystem: mm (1 mm = 1 SVG-Einheit), A4-Querformat 297x210.
Wird vom PDF-Endpoint als SVG-in-HTML an WeasyPrint übergeben.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

from src.routers.lageplan.schemas import (
    ArrowElement,
    HatchingElement,
    RectElement,
    TextElement,
)


def render_svg(layout) -> str:
    """Rendert das komplette Layout als SVG-String (A4-Querformat)."""
    parts: list[str] = []
    parts.append(
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 297 210" width="297mm" height="210mm">'
    )
    # Hintergrundbild (WeasyPrint kann SVG-<image> mit data-URI rendern)
    if layout.background_image_url:
        parts.append(
            f'<image x="0" y="0" width="297" height="210" '
            f'preserveAspectRatio="xMidYMid meet" '
            f'href="{layout.background_image_url}"/>'
        )
    # Elemente in Reihenfolge
    for el in layout.elements:
        parts.append(_render_element(el))
    # Rahmen + Titel
    parts.append('<rect x="0.5" y="0.5" width="296" height="209" fill="none" stroke="#334155" stroke-width="0.4"/>')
    parts.append(
        f'<text x="5" y="7" font-family="sans-serif" font-size="6" fill="#111827">{escape(layout.title)}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _render_element(el) -> str:
    if isinstance(el, RectElement):
        return (
            f'<rect x="{el.x}" y="{el.y}" width="{el.width}" height="{el.height}" '
            f'fill="{el.fill}" stroke="{el.stroke}" stroke-width="{el.stroke_width}"/>'
            + (_label(el, el.x + 1, el.y + 3) if el.label else "")
        )
    if isinstance(el, HatchingElement):
        pts = " ".join(f"{x},{y}" for x, y in el.points)
        body = (
            f'<polygon points="{pts}" fill="{el.fill}" '
            f'stroke="{el.stroke}" stroke-width="{el.stroke_width}"/>'
        )
        # Schraffur: einfache 45°-Linien innerhalb des Bounding-Box
        body += _hatch_lines(el)
        if el.label:
            cx, cy = _centroid(el.points)
            body += _label(el, cx, cy)
        return f'<g>{body}</g>'
    if isinstance(el, ArrowElement):
        arrow = _arrow_head(el)
        return (
            f'<line x1="{el.x1}" y1="{el.y1}" x2="{el.x2}" y2="{el.y2}" '
            f'stroke="{el.stroke}" stroke-width="{el.stroke_width}"/>'
            f'<polygon points="{arrow}" fill="{el.stroke}"/>'
            + (_label(el, el.x2 + 1, el.y2) if el.label else "")
        )
    if isinstance(el, TextElement):
        return (
            f'<text x="{el.x}" y="{el.y}" font-family="sans-serif" '
            f'font-size="{el.font_size / 2.835}" fill="{el.fill}">{escape(el.text)}</text>'
        )
    return ""


def _label(el, x: float, y: float) -> str:
    size = 3.0  # ~ 8.5pt in mm
    return f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="#1e3a8a">{escape(el.label)}</text>'


def _arrow_head(el: ArrowElement) -> str:
    import math

    size = el.arrowhead_size / 3.0  # px->mm (Frontend nutzt 3px/mm)
    angle = math.atan2(el.y2 - el.y1, el.x2 - el.x1)
    x1 = el.x2 - size * math.cos(angle - math.pi / 6)
    y1 = el.y2 - size * math.sin(angle - math.pi / 6)
    x2 = el.x2 - size * math.cos(angle + math.pi / 6)
    y2 = el.y2 - size * math.sin(angle + math.pi / 6)
    return f"{el.x2},{el.y2} {x1},{y1} {x2},{y2}"


def _centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n)


def _hatch_lines(el: HatchingElement) -> str:
    # Diagonale 45°-Linien im Bounding-Box, Abstand = hatch_spacing (mm)
    xs = [p[0] for p in el.points]
    ys = [p[1] for p in el.points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    lines: list[str] = []
    d = min_x - max_y
    while d < max_x - min_y:
        # y = x + d -> Schnittpunkte mit Bounding-Box
        candidates = []
        # x = min_x -> y = min_x + d
        if min_y <= min_x + d <= max_y:
            candidates.append((min_x, min_x + d))
        # x = max_x -> y = max_x + d
        if min_y <= max_x + d <= max_y:
            candidates.append((max_x, max_x + d))
        # y = min_y -> x = min_y - d
        if min_x <= min_y - d <= max_x:
            candidates.append((min_y - d, min_y))
        # y = max_y -> x = max_y - d
        if min_x <= max_y - d <= max_x:
            candidates.append((max_y - d, max_y))
        if len(candidates) >= 2:
            (x1, y1), (x2, y2) = candidates[0], candidates[-1]
            lines.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{el.stroke}" stroke-width="0.2" opacity="0.6"/>'
            )
        d += el.hatch_spacing
    return "".join(lines)
