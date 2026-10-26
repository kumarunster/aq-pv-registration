<template>
  <!-- Rechteck -->
  <v-group v-if="element.kind === 'rect'" :config="{ name: 'el-' + element.id, draggable: store?.activeTool === 'select' }" @click="emit('click', element)" @dragend="emit('dragend', element)">
    <v-rect :config="{ x: element.x, y: element.y, width: element.width, height: element.height, fill: element.fill, stroke: element.stroke, strokeWidth: element.stroke_width }" />
    <v-text v-if="element.label" :config="{ text: element.label, x: element.x + 4, y: element.y + 4, fontSize: 12, fill: '#1e3a8a', listening: false }" />
  </v-group>

  <!-- Schraffur -->
  <v-group v-else-if="element.kind === 'hatching'" :config="{ name: 'el-' + element.id, draggable: store?.activeTool === 'select' }" @click="emit('click', element)" @dragend="emit('dragend', element)">
    <v-line :config="{ points: flatPoints, closed: true, fill: konvaFill, stroke: element.stroke, strokeWidth: element.stroke_width, lineJoin: 'round' }" />
    <!-- Schraffur-Linien (vereinfacht: diagonale Linien im Polygon-Bounding-Box) -->
    <v-line v-for="(line, i) in hatchLines" :key="i" :config="{ points: line, stroke: element.stroke, strokeWidth: 0.5, opacity: 0.6 }" />
  </v-group>

  <!-- Pfeil -->
  <v-group v-else-if="element.kind === 'arrow'" :config="{ name: 'el-' + element.id, draggable: store?.activeTool === 'select' }" @click="emit('click', element)" @dragend="emit('dragend', element)">
    <v-line :config="{ points: [element.x1, element.y1, element.x2, element.y2], stroke: element.stroke, strokeWidth: element.stroke_width }" />
    <v-path :config="{ sceneFunc: drawArrowHead, scaleX: 1, scaleY: 1 }" />
  </v-group>

  <!-- Text: Konva.Label = Rect (Hintergrund) + Text, rendert zuverlässig -->
  <v-label v-else-if="element.kind === 'text'" :config="{ name: 'el-' + element.id, x: element.x, y: element.y, draggable: store?.activeTool === 'select' }" @click="emit('click', element)" @dragend="emit('dragend', element)">
    <v-rect
      :config="{
        width: textLabelWidth,
        height: textLabelHeight,
        fill: 'rgba(248, 250, 252, 0.92)',
        cornerRadius: 4,
        listening: false,
      }"
    />
    <v-text
      :config="{
        x: textPadding,
        y: textPadding,
        text: element.text,
        fontSize: element.font_size,
        fontFamily: 'Arial',
        fill: element.fill,
        width: element.width || 160,
        lineHeight: 1.2,
        wrap: 'word',
        visible: !editing,
        align: 'center',
        verticalAlign: 'middle',
      }"
      @dblclick="emit('edit', element)"
      @dbltap="emit('edit', element)"
    />
  </v-label>
</template>

<script setup>
import { computed } from 'vue'
import { Group as VGroup, Rect as VRect, Line as VLine, Text as VText, Path as VPath, Label as VLabel } from 'vue-konva'

const props = defineProps({
  element: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  store: { type: Object, default: null },
  // true, solange dieser Text gerade über die Textarea bearbeitet wird:
  // der Konva-Text wird dann ausgeblendet (wie `visible: !isEditing` im Beispiel)
  editing: { type: Boolean, default: false },
})
const emit = defineEmits(['click', 'dragend', 'edit', 'transform'])

// Konva.Label: Padding und Höhe für den Text-Block
const textPadding = 8
const textLineHeight = 1.2
const textLabelWidth = computed(() => (props.element.width || 160) + textPadding * 2)
const textLabelHeight = computed(() => {
  const lines = props.element.text ? props.element.text.split('\n').length : 1
  const fontSize = props.element.font_size || 24
  return lines * fontSize * textLineHeight + textPadding * 2
})

const flatPoints = computed(() => {
  if (props.element.kind !== 'hatching') return []
  const pts = []
  for (const [x, y] of props.element.points) pts.push(x, y)
  return pts
})

// Konva kennt kein fill="none" (das ist SVG). Ungültige Werte landen in
// ctx.fillStyle und werden ignoriert -> die Fläche wurde schwarz.
// null = wirklich keine Füllung.
const konvaFill = computed(() => {
  const f = props.element.fill
  return !f || f === 'none' ? null : f
})

// Schraffur: 45°-Linien y = x + d, geschnitten mit der Bounding-Box.
// Portiert aus backend/src/services/lageplan/svg_renderer.py::_hatch_lines --
// dort werden alle VIER Kanten geschnitten und der erste/letzte Treffer
// genommen. Die frühere Fassung verwarf eine Linie, sobald einer der beiden
// Endpunkte außerhalb lag, wodurch bei breiten Boxen fast nichts übrig blieb.
const hatchLines = computed(() => {
  if (props.element.kind !== 'hatching') return []
  const pts = props.element.points
  if (!pts || pts.length < 3) return []
  const xs = pts.map((p) => p[0])
  const ys = pts.map((p) => p[1])
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  // hatch_spacing ist in mm angegeben, die Zeichenfläche läuft mit 3 px/mm
  // (A4 quer = 297x210mm = 891x630 px). Vorher wurde der mm-Wert direkt als
  // Pixelabstand genommen -> Linien dreimal zu dicht.
  const MM_PX = 3
  const spacing = (props.element.hatch_spacing || 4) * MM_PX
  const lines = []
  // Bereich für y = x + d: Ecke oben rechts (maxX, minY) -> d = minY - maxX,
  // Ecke unten links (minX, maxY) -> d = maxY - minX. Vorher war der
  // Bereich vertauscht, dadurch fehlte oben rechts ein Streifen.
  for (let d = minY - maxX; d <= maxY - minX; d += spacing) {
    const c = []
    if (minY <= minX + d && minX + d <= maxY) c.push([minX, minX + d])
    if (minY <= maxX + d && maxX + d <= maxY) c.push([maxX, maxX + d])
    if (minX <= minY - d && minY - d <= maxX) c.push([minY - d, minY])
    if (minX <= maxY - d && maxY - d <= maxX) c.push([maxY - d, maxY])
    if (c.length >= 2) {
      const a = c[0], b = c[c.length - 1]
      lines.push([a[0], a[1], b[0], b[1]])
    }
  }
  return lines
})

function drawArrowHead(context, shape) {
  const el = props.element
  const size = el.arrowhead_size
  const angle = Math.atan2(el.y2 - el.y1, el.x2 - el.x1)
  context.beginPath()
  context.moveTo(el.x2, el.y2)
  context.lineTo(el.x2 - size * Math.cos(angle - Math.PI / 6), el.y2 - size * Math.sin(angle - Math.PI / 6))
  context.lineTo(el.x2 - size * Math.cos(angle + Math.PI / 6), el.y2 - size * Math.sin(angle + Math.PI / 6))
  context.closePath()
  context.fillStyle = el.stroke
  context.fill()
  // Konva erwartet, dass sceneFunc den Shape zurückgibt oder void
}
</script>
