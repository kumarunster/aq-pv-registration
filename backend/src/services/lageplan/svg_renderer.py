"""
SVG-Renderer: wandelt das Lageplan-Layout in ein SVG um.

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
    # Hintergrundbild: linksbündig (0,0) wie im Editor
    # Der Editor positioniert das Bild bei x=0, y=0 (linksbündig).
    if layout.background_image_url and layout.background_image_width and layout.background_image_height:
        img_w = layout.background_image_width
        img_h = layout.background_image_height
        aspect = img_w / img_h
        fit_w = min(297.0, 210.0 * aspect)
        fit_h = min(210.0, 297.0 / aspect)
        parts.append(
            f'<image x="0" y="0" width="{fit_w:.3f}" height="{fit_h:.3f}" '
            f'href="{layout.background_image_url}"/>'
        )
    elif layout.background_image_url:
        # Fallback: volle Seite, wenn keine Bildmaße verfügbar
        parts.append(
            f'<image x="0" y="0" width="297" height="210" '
            f'href="{layout.background_image_url}"/>'
        )
    # Elemente in Reihenfolge
    for el in layout.elements:
        parts.append(_render_element(el))
    parts.append("</svg>")
    return "\n".join(parts)


# Editor-Koordinaten sind in px (3 px/mm); SVG-PDF sind in mm.
def _mm(px: float) -> float:
    """Rechnet Editor-Pixel in A4-millimeter um."""
    return px / 3.0


def _mm2(points) -> str:
    return " ".join(f"{_mm(x):.3f},{_mm(y):.3f}" for x, y in points)


def _render_element(el) -> str:
    if isinstance(el, RectElement):
        return (
            f'<rect x="{_mm(el.x):.3f}" y="{_mm(el.y):.3f}" '
            f'width="{_mm(el.width):.3f}" height="{_mm(el.height):.3f}" '
            f'fill="{el.fill}" stroke="{el.stroke}" stroke-width="{el.stroke_width / 3.0:.3f}"/>'
            + (_label(el, _mm(el.x) + 1, _mm(el.y) + 3) if el.label else "")
        )
    if isinstance(el, HatchingElement):
        pts = _mm2(el.points)
        body = (
            f'<polygon points="{pts}" fill="{el.fill}" '
            f'stroke="{el.stroke}" stroke-width="{el.stroke_width / 3.0:.3f}"/>'
        )
        body += _hatch_lines(el)
        if el.label:
            cx, cy = _mm(*_centroid(el.points))
            body += _label(el, cx, cy)
        return f'<g>{body}</g>'
    if isinstance(el, ArrowElement):
        arrow = _arrow_head(el)
        return (
            f'<line x1="{_mm(el.x1):.3f}" y1="{_mm(el.y1):.3f}" '
            f'x2="{_mm(el.x2):.3f}" y2="{_mm(el.y2):.3f}" '
            f'stroke="{el.stroke}" stroke-width="{el.stroke_width / 3.0:.3f}"/>'
            f'<polygon points="{arrow}" fill="{el.stroke}"/>'
            + (_label(el, _mm(el.x2) + 1, _mm(el.y2)) if el.label else "")
        )
    if isinstance(el, TextElement):
        font_mm = _mm(el.font_size)
        width_mm = _mm(getattr(el, 'width', 160))
        height_mm = _mm(32)
        return (
            f'<g>'
            f'<rect x="{_mm(el.x):.3f}" y="{_mm(el.y):.3f}" '
            f'width="{width_mm:.3f}" height="{height_mm:.3f}" '
            f'fill="rgba(248,250,252,0.92)" rx="1.3"/>'
            f'<text x="{_mm(el.x) + width_mm / 2:.3f}" '
            f'y="{_mm(el.y) + height_mm / 2 + font_mm / 3:.3f}" '
            f'font-family="sans-serif" font-size="{font_mm:.3f}" '
            f'text-anchor="middle" fill="{el.fill}">{escape(el.text)}</text>'
            f'</g>'
        )
    return ""


def _label(el, x: float, y: float) -> str:
    size = 3.0
    return f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="#1e3a8a">{escape(el.label)}</text>'


def _arrow_head(el: ArrowElement) -> str:
    import math
    # Alle Koordinaten in mm umrechnen
    ex2 = _mm(el.x2)
    ey2 = _mm(el.y2)
    size = _mm(el.arrowhead_size)
    angle = math.atan2(el.y2 - el.y1, el.x2 - el.x1)
    x1 = ex2 - size * math.cos(angle - math.pi / 6)
    y1 = ey2 - size * math.sin(angle - math.pi / 6)
    x2 = ex2 - size * math.cos(angle + math.pi / 6)
    y2 = ey2 - size * math.sin(angle + math.pi / 6)
    return f"{ex2},{ey2} {x1:.3f},{y1:.3f} {x2:.3f},{y2:.3f}"


def _centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n)


def _hatch_lines(el: HatchingElement) -> str:
    xs = [p[0] for p in el.points]
    ys = [p[1] for p in el.points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    lines: list[str] = []
    d = min_x - max_y
    while d < max_x - min_y:
        candidates = []
        if min_y <= min_x + d <= max_y:
            candidates.append((min_x, min_x + d))
        if min_y <= max_x + d <= max_y:
            candidates.append((max_x, max_x + d))
        if min_x <= min_y - d <= max_x:
            candidates.append((min_y - d, min_y))
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
