<template>
  <div
    ref="containerRef"
    class="stage-container relative overflow-hidden bg-slate-950 rounded-xl border border-slate-800"
    :style="{ height: stageHeight }"
  >
    <v-stage
      ref="stageRef"
      :config="{ width: stageWidth, height: stageHeight, scaleX: scale, scaleY: scale, x: panX, y: panY }"
      @wheel="onWheel"
      @mousedown="onMouseDown"
      @mousemove="onMouseMove"
      @mouseup="onMouseUp"
    >
      <v-layer>
        <!-- Hintergrundbild (falls vorhanden) -->
        <v-image
          v-if="backgroundImage"
          :config="{
            x: 0,
            y: 0,
            width: backgroundImageWidth,
            height: backgroundImageHeight,
            image: backgroundImage,
          }"
        />
        <!-- Zeichenfläche (A4-Querformat, 297x210mm) -->
        <v-rect
          :config="{
            x: 0,
            y: 0,
            width: PAGE_W,
            height: PAGE_H,
            stroke: '#334155',
            strokeWidth: 1,
            listening: false,
          }"
        />
        <!-- Elemente -->
        <LageplanElement
          v-for="el in store.layout.elements"
          :key="el.id"
          :element="el"
          :selected="store.selectedId === el.id"
          @click="onElementClick(el)"
          @dragend="onElementDragEnd(el)"
          @transformend="onElementTransformEnd(el)"
        />
        <!-- Zeichen-Preview (während gezogen wird) -->
        <LageplanElement
          v-if="previewElement"
          :element="previewElement"
          :selected="false"
        />
      </v-layer>
    </v-stage>

    <!-- Toolbar überlagert -->
    <div class="absolute top-3 left-3 flex flex-col gap-1">
      <button
        v-for="tool in tools"
        :key="tool.id"
        :class="[
          'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
          store.activeTool === tool.id
            ? 'bg-blue-600 text-white'
            : 'bg-slate-800 text-slate-300 hover:bg-slate-700',
        ]"
        @click="store.activeTool = tool.id"
      >
        {{ tool.icon }} {{ tool.label }}
      </button>
    </div>

    <!-- Zoom-Anzeige unten rechts -->
    <div class="absolute bottom-3 right-3 text-xs text-slate-500">
      {{ Math.round(scale * 100) }} %
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import { Stage as VStage, Layer as VLayer, Rect as VRect, Image as VImage } from 'vue-konva'
import LageplanElement from './LageplanElement.vue'

const props = defineProps({
  store: { type: Object, required: true },
  stageWidth: { type: Number, default: 1200 },
  stageHeight: { type: Number, default: 800 },
})

const PAGE_W = 297 * 3 // mm -> px (3 px/mm => 891 px)
const PAGE_H = 210 * 3 // mm -> px (3 px/mm => 630 px)

const stageRef = ref(null)
const containerRef = ref(null)

// Zoom & Pan
const scale = ref(1)
const panX = ref((props.stageWidth - PAGE_W) / 2)
const panY = ref((props.stageHeight - PAGE_H) / 2)

// Hintergrundbild (Konva.Image)
const backgroundImage = ref(null)
const backgroundImageWidth = ref(0)
const backgroundImageHeight = ref(0)

watch(
  () => props.store.layout.background_image_url,
  (url) => {
    if (!url) {
      backgroundImage.value = null
      return
    }
    const img = new Image()
    img.onload = () => {
      // Skalierung: Hintergrund wird auf A4-Seite skaliert
      const aspect = img.width / img.height
      const targetW = PAGE_W
      const targetH = PAGE_H
      const fitW = Math.min(targetW, targetH * aspect)
      const fitH = Math.min(targetH, targetW / aspect)
      backgroundImage.value = img
      backgroundImageWidth.value = fitW
      backgroundImageHeight.value = fitH
      if (props.store.layout.background_image_width == null) {
        props.store.setBackground(url, img.width, img.height)
      }
    }
    img.src = url
  }
)

const tools = [
  { id: 'select', icon: '🖱️', label: 'Auswählen' },
  { id: 'rect', icon: '▭', label: 'Rechteck' },
  { id: 'hatching', icon: '▨', label: 'Schraffur' },
  { id: 'arrow', icon: '➤', label: 'Pfeil' },
  { id: 'text', icon: 'T', label: 'Text' },
]

// Zeichen-Logik
const previewElement = ref(null)
const isDrawing = ref(false)
const drawStart = ref({ x: 0, y: 0 })

function stagePoint() {
  const stage = stageRef.value?.getNode()
  const pointer = stage?.getPointerPosition()
  if (!pointer || !stage) return { x: 0, y: 0 }
  return {
    x: (pointer.x - panX.value) / scale.value,
    y: (pointer.y - panY.value) / scale.value,
  }
}

function onWheel(e) {
  e.evt.preventDefault()
  const factor = e.evt.deltaY > 0 ? 0.9 : 1.1
  const newScale = Math.min(5, Math.max(0.2, scale.value * factor))
  // Zoom um die Maus-Position
  const pointer = e.evt
  const px = (pointer.x - panX.value) / scale.value
  const py = (pointer.y - panY.value) / scale.value
  panX.value = pointer.x - px * newScale
  panY.value = pointer.y - py * newScale
  scale.value = newScale
}

function onMouseDown(e) {
  const tool = props.store.activeTool
  if (tool === 'select') {
    // Pan bei Leertaste oder Rechtsklick; sonst normal
    return
  }
  const p = stagePoint()
  isDrawing.value = true
  drawStart.value = p
  if (tool === 'rect') {
    previewElement.value = { id: 'preview', kind: 'rect', x: p.x, y: p.y, width: 0, height: 0, fill: '#dbeafe', stroke: '#1d4ed8', stroke_width: 1, label: '' }
  } else if (tool === 'arrow') {
    previewElement.value = { id: 'preview', kind: 'arrow', x1: p.x, y1: p.y, x2: p.x, y2: p.y, stroke: '#1d4ed8', stroke_width: 1.5, arrowhead_size: 8, label: '' }
  } else if (tool === 'hatching') {
    previewElement.value = { id: 'preview', kind: 'hatching', points: [[p.x, p.y]], fill: 'none', stroke: '#1d4ed8', stroke_width: 1, hatch_angle: 45, hatch_spacing: 4, label: '' }
  } else if (tool === 'text') {
    // Text: ein Mal klicken platziert, zweimal schließt
    const txt = prompt('Text:')
    if (txt) {
      props.store.addElement({ kind: 'text', x: p.x, y: p.y, text: txt, font_size: 12, fill: '#111827', label: txt })
    }
    previewElement.value = null
    isDrawing.value = false
  }
}

function onMouseMove() {
  if (!isDrawing.value) return
  const tool = props.store.activeTool
  const p = stagePoint()
  const s = drawStart.value
  if (tool === 'rect' && previewElement.value) {
    previewElement.value.x = Math.min(s.x, p.x)
    previewElement.value.y = Math.min(s.y, p.y)
    previewElement.value.width = Math.abs(p.x - s.x)
    previewElement.value.height = Math.abs(p.y - s.y)
  } else if (tool === 'arrow' && previewElement.value) {
    previewElement.value.x2 = p.x
    previewElement.value.y2 = p.y
  } else if (tool === 'hatching' && previewElement.value) {
    if (previewElement.value.points.length < 2) {
      previewElement.value.points.push([p.x, p.y])
    } else {
      previewElement.value.points[previewElement.value.points.length - 1] = [p.x, p.y]
    }
  }
}

function onMouseUp() {
  if (!isDrawing.value) return
  isDrawing.value = false
  const tool = props.store.activeTool
  const el = previewElement.value
  previewElement.value = null
  if (!el) return
  // Mindestgröße prüfen
  if (tool === 'rect' && (el.width > 5 && el.height > 5)) {
    props.store.addElement(el)
  } else if (tool === 'arrow') {
    const dx = el.x2 - el.x1
    const dy = el.y2 - el.y1
    if (Math.sqrt(dx * dx + dy * dy) > 5) {
      props.store.addElement(el)
    }
  } else if (tool === 'hatching' && el.points.length >= 3) {
    props.store.addElement(el)
  }
}

function onElementClick(el) {
  if (props.store.activeTool === 'select') {
    props.store.selectedId = el.id
  }
}
function onElementDragEnd(el) {
  // Konva hat x/y bereits aktualisiert
}
function onElementTransformEnd(el) {
  // Skalierung/Rotation wurde angewendet
}

onMounted(() => {
  // Stage-Size an Container anpassen
  if (containerRef.value) {
    // bereits via props gesetzt
  }
})
</script>
