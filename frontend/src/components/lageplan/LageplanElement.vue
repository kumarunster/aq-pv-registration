<template>
  <!-- Rechteck -->
  <v-group v-if="element.kind === 'rect'" :config="{ draggable: store?.activeTool === 'select' }" @click="emit('click', element)" @dragend="emit('dragend', element)" @transformend="emit('transformend', element)">
    <v-rect :config="{ x: element.x, y: element.y, width: element.width, height: element.height, fill: element.fill, stroke: element.stroke, strokeWidth: element.stroke_width }" />
    <v-transformer v-if="selected" :config="{ boundBoxFunc: (oldBox, newBox) => (newBox.width < 4 || newBox.height < 4 ? oldBox : newBox) }" />
    <v-text v-if="element.label" :config="{ text: element.label, x: element.x + 4, y: element.y + 4, fontSize: 12, fill: '#1e3a8a', listening: false }" />
  </v-group>

  <!-- Schraffur -->
  <v-group v-else-if="element.kind === 'hatching'" :config="{ draggable: store?.activeTool === 'select' }" @click="emit('click', element)" @dragend="emit('dragend', element)">
    <v-line :config="{ points: flatPoints, closed: true, fill: element.fill, stroke: element.stroke, strokeWidth: element.stroke_width, lineJoin: 'round' }" />
    <!-- Schraffur-Linien (vereinfacht: diagonale Linien im Polygon-Bounding-Box) -->
    <v-line v-for="(line, i) in hatchLines" :key="i" :config="{ points: line, stroke: element.stroke, strokeWidth: 0.5, opacity: 0.6 }" />
  </v-group>

  <!-- Pfeil -->
  <v-group v-else-if="element.kind === 'arrow'" :config="{ draggable: store?.activeTool === 'select' }" @click="emit('click', element)" @dragend="emit('dragend', element)">
    <v-line :config="{ points: [element.x1, element.y1, element.x2, element.y2], stroke: element.stroke, strokeWidth: element.stroke_width }" />
    <v-path :config="{ sceneFunc: drawArrowHead, scaleX: 1, scaleY: 1 }" />
  </v-group>

  <!-- Text -->
  <v-group v-else-if="element.kind === 'text'" :config="{ draggable: store?.activeTool === 'select' }" @click="emit('click', element)" @dragend="emit('dragend', element)">
    <v-text :config="{ text: element.text, x: element.x, y: element.y, fontSize: element.font_size, fill: element.fill }" />
  </v-group>
</template>

<script setup>
import { computed } from 'vue'
import { Group as VGroup, Rect as VRect, Line as VLine, Text as VText, Transformer as VTransformer, Path as VPath } from 'vue-konva'

const props = defineProps({
  element: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  store: { type: Object, default: null },
})
const emit = defineEmits(['click', 'dragend', 'transformend'])

const flatPoints = computed(() => {
  if (props.element.kind !== 'hatching') return []
  const pts = []
  for (const [x, y] of props.element.points) pts.push(x, y)
  return pts
})

// Vereinfachte Schraffur: diagonale Linien im Bounding-Box
const hatchLines = computed(() => {
  if (props.element.kind !== 'hatching') return []
  const pts = props.element.points
  const xs = pts.map(p => p[0])
  const ys = pts.map(p => p[1])
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const lines = []
  const spacing = props.element.hatch_spacing || 4
  for (let d = minX - maxY; d < maxX - minY; d += spacing) {
    // Linie mit Steigung 1 (45°): y = x + d
    const x1 = Math.max(minX, -d)
    const y1 = x1 + d
    const x2 = Math.min(maxX, -d + (maxY - minY) + (maxX - minX))
    // einfachere Variante: Schnittpunkte mit Bounding-Box
    let x1b = minX, y1b = x1b + d
    let x2b = maxX, y2b = x2b + d
    // auf Bounding-Box clampen
    if (y1b < minY || y1b > maxY) continue
    if (y2b < minY || y2b > maxY) continue
    lines.push([x1b, y1b, x2b, y2b])
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
