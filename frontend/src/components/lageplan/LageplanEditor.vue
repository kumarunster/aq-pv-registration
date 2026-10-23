<template>
  <div class="max-w-6xl mx-auto space-y-4">
    <!-- Kopfzeile -->
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-2xl font-bold text-white">📐 Lageplan-Editor</h1>
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
      :store="store"
      :stage-width="1100"
      :stage-height="720"
      @preview-text="onPlaceText"
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
            />
          </label>
          <label>
            <span class="text-slate-400">Schriftgröße (mm)</span>
            <input
              v-model.number="store.selectedElement.font_size"
              type="number"
              min="2"
              class="mt-1 w-full px-2 py-1 rounded bg-slate-800 text-slate-200"
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
          />
        </label>
        <label v-if="store.selectedElement.kind !== 'text'">
          <span class="text-slate-400">Linienfarbe</span>
          <input
            v-model="store.selectedElement.stroke"
            type="color"
            class="mt-1 w-full px-2 py-1 rounded bg-slate-800 text-slate-200"
          />
        </label>

        <!-- Label -->
        <label class="col-span-2">
          <span class="text-slate-400">Label</span>
          <input
            v-model="store.selectedElement.label"
            class="mt-1 w-full px-2 py-1 rounded bg-slate-800 text-slate-200"
            placeholder="z.B. Grundstück, PV-Feld, Nord"
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
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import axios from 'axios'
import { useLayoutStore } from './useLayoutStore.js'
import LageplanStage from './LageplanStage.vue'

const store = useLayoutStore()
const fileInput = ref(null)
const pdfBusy = ref(false)

// Undo/Redo-Stack (Layout-Snapshots)
const history = ref([])
const historyIndex = ref(-1)

function snapshot() {
  history.value = history.value.slice(0, historyIndex.value + 1)
  history.value.push(JSON.parse(JSON.stringify(store.layout)))
  historyIndex.value = history.value.length - 1
}

function undo() {
  if (historyIndex.value <= 0) return
  historyIndex.value -= 1
  const snap = history.value[historyIndex.value]
  store.layout = { ...snap, elements: snap.elements.map(e => ({ ...e })) }
  store.selectedId = null
}

function redo() {
  if (historyIndex.value >= history.value.length - 1) return
  historyIndex.value += 1
  const snap = history.value[historyIndex.value]
  store.layout = { ...snap, elements: snap.elements.map(e => ({ ...e })) }
  store.selectedId = null
}

onMounted(() => {
  snapshot() // initiale Aufnahme
})

function onImportImage() {
  fileInput.value?.click()
}

function onFileChosen(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    store.setBackground(reader.result, 0, 0)
    snapshot()
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

function onPlaceText() {
  // wird vom Stage-Component als Event „preview-text" ausgelöst
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
    const res = await axios.post('/api/lageplan/pdf', store.layout, {
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
  snapshot()
}
</script>
