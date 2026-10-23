/**
 * Lageplan-Datenmodell (spiegelt backend/src/routers/lageplan/schemas.py).
 *
 * Koordinatensystem:
 *   - Alle Koordinaten in MILLIMETERN, bezogen auf A4-Querformat.
 *   - Ursprung (0,0) = oben links; x nach rechts, y nach unten.
 */

export type ElementKind = 'rect' | 'hatching' | 'arrow' | 'text';

export interface BaseElement {
  id: string;
  kind: ElementKind;
  label: string;
}

export interface RectElement extends BaseElement {
  kind: 'rect';
  x: number;
  y: number;
  width: number;
  height: number;
  fill: string;
  stroke: string;
  stroke_width: number;
}

export interface HatchingElement extends BaseElement {
  kind: 'hatching';
  points: [number, number][];
  fill: string;
  stroke: string;
  stroke_width: number;
  hatch_angle: number;
  hatch_spacing: number;
}

export interface ArrowElement extends BaseElement {
  kind: 'arrow';
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  stroke: string;
  stroke_width: number;
  arrowhead_size: number;
}

export interface TextElement extends BaseElement {
  kind: 'text';
  x: number;
  y: number;
  text: string;
  font_size: number;
  fill: string;
}

export type LageplanElement =
  | RectElement
  | HatchingElement
  | ArrowElement
  | TextElement;

export interface Layout {
  title: string;
  background_image_url: string | null;
  background_image_width?: number;
  background_image_height?: number;
  elements: LageplanElement[];
  metadata: Record<string, unknown>;
}
