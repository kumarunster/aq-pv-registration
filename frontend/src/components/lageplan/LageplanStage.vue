<template>
  <div
    ref="containerRef"
    class="stage-container relative overflow-hidden bg-slate-950 rounded-xl border border-slate-800"
    :style="{ height: stageHeight + 'px' }"
  >
    <v-stage
      ref="stageRef"
      :config="{ width: stageWidth, height: stageHeight, scaleX: scale, scaleY: scale, x: panX, y: panY }"
      @wheel="onWheel"
      @mousedown="onMouseDown"
      @mousemove="onMouseMove"
      @mouseup="onMouseUp"
      @click="handleStageClick"
      @tap="handleStageClick"
    >
      <v-layer ref="layerRef">
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
          :store="store"
          :selected="store.selectedId === el.id"
          :editing="editingId === el.id"
          @click="onElementClick(el)"
          @dragend="onElementDragEnd(el)"
          @edit="startTextEdit(el)"
          @transform="onTextTransform(el)"
        />
        <!-- Zeichen-Preview (während gezogen wird) -->
        <LageplanElement
          v-if="previewElement"
          :element="previewElement"
          :selected="false"
        />
        <!-- EIN Transformer für den ganzen Layer (Konva-Standard) -->
        <v-transformer ref="trRef" :config="{ boundBoxFunc: boundBoxFunc }" />
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
import { ref, reactive, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { Stage as VStage, Layer as VLayer, Rect as VRect, Image as VImage, Transformer as VTransformer } from 'vue-konva'
import LageplanElement from './LageplanElement.vue'

const props = defineProps({
  store: { type: Object, required: true },
  stageWidth: { type: Number, default: 1200 },
  stageHeight: { type: Number, default: 800 },
})
const emit = defineEmits(['layoutChange'])

const PAGE_W = 297 * 3 // mm -> px (3 px/mm => 891 px)
const PAGE_H = 210 * 3 // mm -> px (3 px/mm => 630 px)

const stageRef = ref(null)
const layerRef = ref(null)
const trRef = ref(null)
const containerRef = ref(null)
// ID des Text-Elements, das gerade über die Textarea bearbeitet wird
const editingId = ref(null)

// Mindestgröße beim Skalieren
function boundBoxFunc(oldBox, newBox) {
  return newBox.width < 4 || newBox.height < 4 ? oldBox : newBox
}

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
    // Schraffur: orange Linien auf transparentem Grund, Umriss ebenfalls orange.
    // 'none' bleibt der Store-/Backend-Wert; LageplanElement macht daraus null für Konva.
    previewElement.value = { id: 'preview', kind: 'hatching', points: [[p.x, p.y]], fill: 'none', stroke: '#f97316', stroke_width: 1, hatch_angle: 45, hatch_spacing: 4, label: '' }
  } else if (tool === 'text') {
    // Leeres Text-Element anlegen und sofort im Canvas editieren
    // (kein prompt() mehr). Bleibt es leer, wird es wieder entfernt.
    // addElement liefert die neue ID zurück und setzt selectedId bereits selbst
    const id = props.store.addElement({
      kind: 'text', x: p.x, y: p.y, text: '', width: 160,
      font_size: 24, fill: '#111827', label: '',
    })
    previewElement.value = null
    isDrawing.value = false
    nextTick(() => {
      const created = props.store.layout.elements.find((e) => e.id === id)
      if (created) startTextEdit(created, true)
    })
    emit('layoutChange')
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
    // Wie beim Rechteck: aus Start- und Aktuellpunkt ein 4-Punkt-Polygon
    const x1 = Math.min(s.x, p.x), y1 = Math.min(s.y, p.y)
    const x2 = Math.max(s.x, p.x), y2 = Math.max(s.y, p.y)
    previewElement.value.points = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
  }
}

function onMouseUp() {
  if (!isDrawing.value) return
  isDrawing.value = false
  const tool = props.store.activeTool
  const el = previewElement.value
  previewElement.value = null
  if (!el) return
  // Vorschau-ID verwerfen: sonst bekommt jedes Element die ID 'preview'
  // und addElement vergibt wegen `element.id || nextId()` nie eine neue.
  delete el.id
  // Mindestgröße prüfen
  if (tool === 'rect' && (el.width > 5 && el.height > 5)) {
    props.store.addElement(el)
    emit('layoutChange')
  } else if (tool === 'arrow') {
    const dx = el.x2 - el.x1
    const dy = el.y2 - el.y1
    if (Math.sqrt(dx * dx + dy * dy) > 5) {
      props.store.addElement(el)
      emit('layoutChange')
    }
  } else if (tool === 'hatching' && el.points.length >= 3) {
    const xs = el.points.map((q) => q[0])
    const ys = el.points.map((q) => q[1])
    const w = Math.max(...xs) - Math.min(...xs)
    const h = Math.max(...ys) - Math.min(...ys)
    if (w > 5 && h > 5) {
      props.store.addElement(el)
      emit('layoutChange')
    }
  }
}

function onElementClick(el) {
  console.log('[LP] onElementClick', el.id, 'tool=', props.store.activeTool)
  if (props.store.activeTool === 'select') {
    props.store.selectedId = el.id
    console.log('[LP] selectedId gesetzt ->', props.store.selectedId)
    attachTransformer(el.id)
  }
}
function onElementDragEnd(el) {
  // Konva hat die Position auf dem Node geändert; zurück in den Store.
  const layerNode = layerRef.value?.getNode?.()
  const node = layerNode?.findOne('.el-' + el.id)
  if (!node) return
  el.x = node.x()
  el.y = node.y()
  attachTransformer(el.id)
  emit('layoutChange')
}

// --- Transformer an das ausgewählte Element hängen (Konva-Beispiel) ---
function attachTransformer(id) {
  const layerNode = layerRef.value?.getNode?.()
  const trNode = trRef.value?.getNode?.()
  if (!layerNode || !trNode) return
  const node = id ? layerNode.findOne('.el-' + id) : null
  // Text wird nur in der Breite gezogen (Umbruch statt Verzerrung),
  // alles andere bekommt die vollen Anker.
  const el = props.store.layout.elements.find((e) => e.id === id)
  trNode.enabledAnchors(
    el?.kind === 'text'
      ? ['middle-left', 'middle-right']
      : ['top-left', 'top-center', 'top-right', 'middle-left', 'middle-right', 'bottom-left', 'bottom-center', 'bottom-right']
  )
  trNode.nodes(node ? [node] : [])
  trNode.moveToTop()
  layerNode.batchDraw()
}

// Beim Ziehen an der Breite: scaleX in width zurückrechnen, scaleX zurücksetzen.
// Dadurch bricht der Text um, statt in die Breite gezogen zu werden.
function onTextTransform(el) {
  const layerNode = layerRef.value?.getNode?.()
  const labelNode = layerNode?.findOne('.el-' + el.id)
  const textNode = labelNode?.findOne('Text')
  if (!labelNode || !textNode) return
  const newWidth = Math.max(30, textNode.width() * labelNode.scaleX())
  el.width = newWidth
  textNode.width(newWidth)
  labelNode.scaleX(1)
  layerNode.batchDraw()
}

// Text direkt im Canvas bearbeiten: DOM-Textarea exakt über den Konva-Text legen.
// Portiert aus Kolyas Konva-Beispiel; zusätzlich mit getAbsoluteScale(),
// weil unsere Stage zoom- und verschiebbar ist.
function startTextEdit(el, isNew = false) {
  const layerNode = layerRef.value?.getNode?.()
  const stageNode = stageRef.value?.getNode?.()
  const labelNode = layerNode?.findOne('.el-' + el.id)
  const textNode = labelNode?.findOne('Text')
  if (!stageNode || !textNode) return

  editingId.value = el.id
  const trNode = trRef.value?.getNode?.()
  trNode?.nodes([])
  layerNode.batchDraw()

  const scale = textNode.getAbsoluteScale().x
  const pos = textNode.absolutePosition()
  const stageBox = stageNode.container().getBoundingClientRect()

  const ta = document.createElement('textarea')
  document.body.appendChild(ta)
  ta.value = el.text || ''
  ta.style.position = 'absolute'
  ta.style.top = stageBox.top + window.scrollY + pos.y + 'px'
  ta.style.left = stageBox.left + window.scrollX + pos.x + 'px'
  ta.style.width = (el.width || 160) * scale + 'px'
  ta.style.fontSize = textNode.fontSize() * scale + 'px'
  ta.style.fontFamily = textNode.fontFamily()
  ta.style.lineHeight = textNode.lineHeight()
  ta.style.color = textNode.fill()
  ta.style.textAlign = textNode.align()
  ta.style.border = 'none'
  ta.style.padding = '0px'
  ta.style.margin = '0px'
  ta.style.overflow = 'hidden'
  ta.style.background = 'none'
  ta.style.outline = 'none'
  ta.style.resize = 'none'
  ta.style.zIndex = '50'
  ta.style.transformOrigin = 'left top'
  const rot = textNode.getAbsoluteRotation ? textNode.getAbsoluteRotation() : textNode.rotation()
  ta.style.transform = rot ? 'rotateZ(' + rot + 'deg)' : ''
  ta.style.height = 'auto'
  ta.style.height = ta.scrollHeight + 3 + 'px'

  let closed = false
  function cleanup() {
    if (closed) return
    closed = true
    window.removeEventListener('click', onOutside)
    window.removeEventListener('touchstart', onOutside)
    if (ta.parentNode) ta.parentNode.removeChild(ta)
    editingId.value = null
    nextTick(() => attachTransformer(props.store.selectedId))
  }
  function commit() {
    const v = ta.value
    cleanup()
    const target = props.store.layout.elements.find((e) => e.id === el.id)
    if (!target) return
    emit('layoutChange')
    if (!v.trim()) {
      // leer gelassen -> neu angelegtes Element wieder entfernen
      props.store.removeElement(target.id)
      props.store.selectedId = null
      return
    }
    target.text = v
    target.label = v
  }
  function cancel() {
    cleanup()
    const target = props.store.layout.elements.find((e) => e.id === el.id)
    if (target && isNew && !(target.text || '').trim()) {
      props.store.removeElement(target.id)
      props.store.selectedId = null
    }
  }
  function onOutside(ev) {
    if (ev.target !== ta) commit()
  }

  ta.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); commit(); return }
    if (ev.key === 'Escape') { cancel(); return }
    // Höhe mitwachsen lassen
    requestAnimationFrame(() => {
      ta.style.height = 'auto'
      ta.style.height = ta.scrollHeight + 'px'
    })
  })
  // Fokus erst setzen, wenn der auslösende Klick fertig verarbeitet ist —
  // sonst zieht der Browser den Fokus gleich wieder auf <body> zurück
  // (gemessen: document.activeElement war BODY, Tastatureingaben gingen ins Leere).
  setTimeout(() => {
    ta.focus()
    ta.setSelectionRange(ta.value.length, ta.value.length)
    window.addEventListener('click', onOutside)
    window.addEventListener('touchstart', onOutside)
  })
}

watch(
  () => props.store.selectedId,
  (id) => nextTick(() => attachTransformer(id))
)

// Klick auf Stage oder Hintergrundbild = Abwahl
function handleStageClick(e) {
  const stageNode = stageRef.value?.getNode?.()
  const target = e.target
  console.log('[LP] handleStageClick target=', target?.getClassName?.(), 'name=', target?.name?.(), 'isStage=', target === stageNode)
  if (props.store.activeTool !== 'select') return
  if (target === stageNode || target.getClassName?.() === 'Image') {
    props.store.selectedId = null
    console.log('[LP] abgewaehlt')
  }
}

onMounted(() => {
  // Stage-Size an Container anpassen
  if (containerRef.value) {
    // bereits via props gesetzt
  }
})
</script>
