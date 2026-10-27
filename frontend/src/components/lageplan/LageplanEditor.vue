<template>
  <div class="max-w-6xl mx-auto space-y-4">
    <!-- Kopfzeile -->
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-col">
        <h1 class="text-2xl font-bold text-white">📐 Lageplan-Editor</h1>
        <span class="text-xs text-slate-500">
          Build: {{ new Date(BUILD_TIME).toLocaleString('de-DE') }}
        </span>
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          class="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-sm hover:bg-slate-700"
          @click="onImportImage"
        >
          📷 Hintergrundbild
        </button>
        <button
          class="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-sm hover:bg-slate-700"
          @click="onExportJson"
        >
          ⬇️ JSON
        </button>
        <button
          class="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-sm hover:bg-slate-700"
          :disabled="historyIndex <= 0"
          @click="undo"
        >
          ↩️ Undo
        </button>
        <button
          class="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-sm hover:bg-slate-700"
          :disabled="historyIndex >= history.length - 1"
          @click="redo"
        >
          ↪️ Redo
        </button>
        <button
          class="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-500 disabled:opacity-50"
          :disabled="pdfBusy"
          @click="onExportPdf"
        >
          {{ pdfBusy ? '⏳ PDF wird erzeugt…' : '📄 PDF' }}
        </button>
      </div>
    </div>

    <!-- Editor-Stage -->
    <LageplanStage
      ref="stageRef"
      :store="store"
      :stage-width="1100"
      :stage-height="720"
      @preview-text="onPlaceText"
      @layout-change="onStageChange"
    />

    <!-- Eigenschaften-Panel -->
    <div
      v-if="store.selectedElement"
      class="bg-slate-900 rounded-xl p-4 border border-slate-800 space-y-3"
    >
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-white">
          Eigenschaften: {{ store.selectedElement.kind }}
          <span class="text-slate-500">
            ({{ store.selectedElement.label || 'ohne Label' }})
          </span>
        </h3>
        <button
          class="px-2 py-1 rounded bg-red-900/40 text-red-300 text-xs hover:bg-red-900/60"
          @click="removeSelected"
        >
          🗑️ Löschen
        </button>
      </div>

      <div class="grid grid-cols-2 gap-3 text-sm">
        <!-- Text-Element: Text + Schriftgröße -->
        <template v-if="store.selectedElement.kind === 'text'">
          <label class="col-span-2">
            <span class="text-slate-400">Text</span>
            <input
              v-model="store.selectedElement.text"
              class="mt-1 w-full px-2 py-1 rounded bg-slate-800 text-slate-200"
              @change="onFieldChanged('text')"
            />
          </label>
          <label>
            <span class="text-slate-400">Schriftgröße (mm)</span>
            <input
              v-model.number="store.selectedElement.font_size"
              type="number"
              min="2"
              class="mt-1 w-full px-2 py-1 rounded bg-slate-800 text-slate-200"
              @change="onFieldChanged('font_size')"
            />
          </label>
        </template>

        <!-- Farbe: alle außer Text -->
        <label v-if="store.selectedElement.kind !== 'text'">
          <span class="text-slate-400">Füllfarbe</span>
          <input
            v-model="store.selectedElement.fill"
            type="color"
            class="mt-1 w-full px-2 py-1 rounded bg-slate-800 text-slate-200"
            @change="onFieldChanged('fill')"
          />
        </label>
        <label v-if="store.selectedElement.kind !== 'text'">
          <span class="text-slate-400">Linienfarbe</span>
          <input
            v-model="store.selectedElement.stroke"
            type="color"
            class="mt-1 w-full px-2 py-1 rounded bg-slate-800 text-slate-200"
            @change="onFieldChanged('stroke')"
          />
        </label>

        <!-- Label -->
        <label class="col-span-2">
          <span class="text-slate-400">Label</span>
          <input
            v-model="store.selectedElement.label"
            class="mt-1 w-full px-2 py-1 rounded bg-slate-800 text-slate-200"
            placeholder="z.B. Grundstück, PV-Feld, Nord"
            @change="onFieldChanged('label')"
          />
        </label>
      </div>
    </div>
    <p v-else class="text-xs text-slate-500">
      Mit „Auswählen" + Klick auf ein Element kannst du es hier bearbeiten.
    </p>

    <!-- Bild-Upload (verborgen) -->
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      class="hidden"
      @change="onFileChosen"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import { BUILD_TIME } from '@/build-time'
import axios from 'axios'
import { useLayoutStore } from './useLayoutStore.js'
import LageplanStage from './LageplanStage.vue'

const store = useLayoutStore()
const fileInput = ref(null)
const stageRef = ref(null)
const pdfBusy = ref(false)

// Undo/Redo-Stack (Layout-Snapshots).
// commitSnapshot() = 'Neue Änderung' -> alte Redo-Zweige verwerfen,
// Aufnahme anhängen. snapshot() = 'Zustand wiederhergestellt' (Undo/Redo/
// initiale Aufnahme) -> History nicht verändern.
const history = ref([])
const historyIndex = ref(-1)

function commitSnapshot() {
  const snap = JSON.parse(JSON.stringify(store.layout))
  history.value = history.value.slice(0, historyIndex.value + 1)
  history.value.push(snap)
  if (history.value.length > 100) history.value.shift()
  historyIndex.value = history.value.length - 1
}

function restore(snap) {
  // layout ist reactive: Array-Referenzen müssen bleiben, sonst verlieren
  // die Stage-Komponenten ihre Beobachtung. content() schreibt die
  // Snapshot-Daten in die vorhandenen Arrays, ersetzt aber die Referenzen.
  const next = JSON.parse(JSON.stringify(snap))
  const cur = store.layout
  cur.title = next.title
  cur.background_image_url = next.background_image_url
  cur.background_image_width = next.background_image_width
  cur.background_image_height = next.background_image_height
  cur.metadata = next.metadata
  cur.elements.length = 0
  for (const el of next.elements) cur.elements.push(el)
  if (store.selectedId && !next.elements.some((e) => e.id === store.selectedId)) {
    store.selectedId = null
  }
}

function undo() {
  if (historyIndex.value <= 0) return
  historyIndex.value -= 1
  restore(history.value[historyIndex.value])
}

function redo() {
  if (historyIndex.value >= history.value.length - 1) return
  historyIndex.value += 1
  restore(history.value[historyIndex.value])
}

// Panel-Änderungen (v-model schreibt direkt in store.selectedElement):
// erst aufnehmen, wenn sich der Zustand wirklich geändert hat.
function onFieldChanged() {
  if (!store.selectedElement) return
  const snap = JSON.parse(JSON.stringify(store.layout))
  if (historyIndex.value >= 0 && JSON.stringify(snap) === JSON.stringify(history.value[historyIndex.value])) return
  commitSnapshot()
}

onMounted(() => {
  commitSnapshot() // initiale Aufnahme
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})

function onKeydown(e) {
  if (!(e.ctrlKey || e.metaKey)) return
  const k = e.key.toLowerCase()
  if (k === 'z' && !e.shiftKey) {
    e.preventDefault()
    undo()
  } else if (k === 'z' && e.shiftKey) {
    e.preventDefault()
    redo()
  } else if (k === 'y') {
    e.preventDefault()
    redo()
  }
}

function onImportImage() {
  fileInput.value?.click()
}

function onFileChosen(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const img = new Image()
  const url = URL.createObjectURL(file)
  img.onload = () => {
    const reader = new FileReader()
    reader.onload = () => {
      store.setBackground(reader.result, img.width, img.height)
      commitSnapshot()
    }
    reader.readAsDataURL(file)
    URL.revokeObjectURL(url)
  }
  img.src = url
  e.target.value = ''
}

function onPlaceText() {
  // wird vom Stage-Component als Event „preview-text" ausgelöst
}

function onStageChange() {
  commitSnapshot()
}

function onExportJson() {
  const blob = new Blob([JSON.stringify(store.layout, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${store.layout.title || 'lageplan'}.json`
  a.click()
  URL.revokeObjectURL(url)
}

async function onExportPdf() {
  pdfBusy.value = true
  try {
    // Vor dem Export: alle Konva-Nodes abfragen und die echten
    // Positionen/Rotationen/Skalierungen aus der Transformationsmatrix
    // in eine Kopie des Layouts schreiben (Store bleibt unverändert).
    const exportLayout = stageRef.value?.syncFromCanvas?.() || store.layout
    const res = await axios.post('/api/lageplan/pdf', exportLayout, {
      responseType: 'blob',
      timeout: 90000,
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${store.layout.title || 'lageplan'}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    alert('PDF-Fehler: ' + (err.response?.data ? JSON.stringify(err.response.data) : err.message))
  } finally {
    pdfBusy.value = false
  }
}

function removeSelected() {
  if (!store.selectedId) return
  store.removeElement(store.selectedId)
  commitSnapshot()
}
</script>
