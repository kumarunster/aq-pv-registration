"""
Lageplan-Datenmodell (JSON-Schema als einzige Quelle der Wahrheit).

Koordinatensystem:
  - Alle Koordinaten sind in MILLIMETERN, bezogen auf den A4-Ausgabemaßstab.
  - Ursprung (0, 0) = oben links der Zeichenfläche.
  - x wächst nach rechts, y wächst nach unten.
  - Die Zeichenfläche entspricht dem A4-Querformat (297mm x 210mm).

Elemente:
  - rect:      Rechteck (Grundstück / Gebäude)
  - hatching:  Schraffur (Fläche)
  - arrow:     Pfeil (Ausrichtung / Weg)
  - text:      Textbeschriftung
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, field_validator


class ElementKind(str, Enum):
    RECT = "rect"
    HATCHING = "hatching"
    ARROW = "arrow"
    TEXT = "text"


class RectElement(BaseModel):
    """Rechteck-Element (x, y, width, height in mm)."""
    id: str = Field(..., min_length=1)
    kind: Literal[ElementKind.RECT] = ElementKind.RECT
    x: float = Field(..., ge=0)
    y: float = Field(..., ge=0)
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    fill: str = Field(default="#dbeafe", pattern=r"^#[0-9a-fA-F]{6}$")
    stroke: str = Field(default="#1d4ed8", pattern=r"^#[0-9a-fA-F]{6}$")
    stroke_width: float = Field(default=1.0, gt=0)
    label: str = Field(default="", max_length=200)
    rotation: float = Field(default=0.0, description="Rotation in Grad um den Mittelpunkt")


class HatchingElement(BaseModel):
    """Schraffur-Element (polygonale Fläche)."""
    id: str = Field(..., min_length=1)
    kind: Literal[ElementKind.HATCHING] = ElementKind.HATCHING
    points: list[tuple[float, float]] = Field(..., min_length=3)
    fill: str = Field(default="none", pattern=r"^#[0-9a-fA-F]{6}$|none")
    stroke: str = Field(default="#1d4ed8", pattern=r"^#[0-9a-fA-F]{6}$")
    stroke_width: float = Field(default=1.0, gt=0)
    hatch_angle: float = Field(default=45.0)
    hatch_spacing: float = Field(default=4.0, gt=0)
    label: str = Field(default="", max_length=200)
    rotation: float = Field(default=0.0, description="Rotation in Grad um den Mittelpunkt")


class ArrowElement(BaseModel):
    """Pfeil-Element (start/end in mm)."""
    id: str = Field(..., min_length=1)
    kind: Literal[ElementKind.ARROW] = ElementKind.ARROW
    x1: float = Field(..., ge=0)
    y1: float = Field(..., ge=0)
    x2: float = Field(..., ge=0)
    y2: float = Field(..., ge=0)
    stroke: str = Field(default="#1d4ed8", pattern=r"^#[0-9a-fA-F]{6}$")
    stroke_width: float = Field(default=1.5, gt=0)
    arrowhead_size: float = Field(default=8.0, gt=0)
    label: str = Field(default="", max_length=200)
    rotation: float = Field(default=0.0, description="Rotation in Grad um den Mittelpunkt")


class TextElement(BaseModel):
    """Text-Element (Position + Inhalt + Schriftgröße)."""
    id: str = Field(..., min_length=1)
    kind: Literal[ElementKind.TEXT] = ElementKind.TEXT
    x: float = Field(..., ge=0)
    y: float = Field(..., ge=0)
    text: str = Field(..., min_length=1, max_length=500)
    font_size: float = Field(default=12.0, gt=0)
    fill: str = Field(default="#111827", pattern=r"^#[0-9a-fA-F]{6}$")
    label: str = Field(default="", max_length=200)
    width: Optional[float] = Field(default=None, gt=0, description="Breite in px (Editor)")
    rotation: float = Field(default=0.0, description="Rotation in Grad um den Mittelpunkt")


# Union aller Elementarten
Element = RectElement | HatchingElement | ArrowElement | TextElement


class Layout(BaseModel):
    """Kompletter Lageplan (Hintergrundbild + Elemente + Metadaten)."""
    title: str = Field(default="Lageplan", min_length=1, max_length=200)
    background_image_url: Optional[str] = Field(
        default=None,
        description="URL oder Base64-Data-URI des Hintergrundbildes",
    )
    background_image_width: Optional[float] = Field(default=None, gt=0)
    background_image_height: Optional[float] = Field(default=None, gt=0)
    elements: list[Element] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    @field_validator("elements")
    @classmethod
    def validate_unique_ids(cls, elements: list[Element]) -> list[Element]:
        ids = [e.id for e in elements]
        if len(ids) != len(set(ids)):
            raise ValueError("Element-IDs müssen eindeutig sein")
        return elements
