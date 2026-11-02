<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold">👤 Meine Kunden</h1>
      <button
        v-if="!showForm"
        @click="openNew"
        class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-sm">
        + Neuer Kunde
      </button>
    </div>

    <!-- Suche -->
    <div v-if="!showForm" class="mb-4">
      <input
        v-model="query"
        @input="onSearch"
        class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm focus:border-amber-500 focus:outline-none"
        placeholder="Kunde suchen (Name, Ort, E-Mail) …"
      />
    </div>

    <!-- Formular -->
    <FormCustomer
      v-if="showForm"
      mode="installer"
      :initial="editing || null"
      @saved="onSaved"
      @cancel="closeForm"
      @dirty="onDirty"
    />

    <!-- Liste -->
    <div v-if="!showForm" class="space-y-3">
      <div v-if="loading" class="text-slate-400 text-sm">Lade…</div>
      <div v-else-if="loadError" class="bg-red-900/40 border border-red-700 rounded-xl p-4 text-sm text-red-300 flex items-center justify-between">
        <span>⚠️ Kunden laden fehlgeschlagen: {{ loadError }}</span>
        <button @click="load(query.value.trim())" class="px-3 py-1.5 bg-red-700 hover:bg-red-600 text-white rounded-lg text-sm">Retry</button>
      </div>
      <div v-else-if="customers.length === 0" class="bg-slate-900 rounded-xl p-6 text-center text-slate-400">
        {{ query ? 'Keine Kunden gefunden.' : 'Noch keine eigenen Kunden angelegt.' }}
      </div>
      <div v-for="c in customers" :key="c._id" class="bg-slate-900 rounded-xl p-4 border border-slate-800 hover:border-amber-500/50 cursor-pointer transition-colors" @click="editCustomer(c)">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-semibold text-lg">{{ c.firstname }} {{ c.lastname }}</h3>
            <p class="text-slate-400 text-sm mt-1">
              {{ c.address_street }}, {{ c.address_plz }} {{ c.address_city }}
            </p>
            <p v-if="c.email" class="text-slate-400 text-sm">{{ c.email }} · {{ c.phone }}</p>
            <div v-if="c.iban" class="text-slate-500 text-xs mt-1">IBAN: {{ c.iban }}</div>
            <div class="text-slate-500 text-xs mt-2">
              <span v-if="c.updated_at">Zuletzt geändert: {{ formatDate(c.updated_at) }}</span>
              <span v-else>Erstellt: {{ formatDate(c.created_at) }}</span>
            </div>
            <div v-if="c.plants && c.plants.length" class="mt-3">
              <div v-for="(p, i) in c.plants" :key="i" class="text-sm text-slate-400 bg-slate-800 rounded-lg px-3 py-2 mb-2">
                <span class="text-amber-400 font-medium">{{ anlagetypLabel(p.anlagetyp) }}</span>
                <span v-if="p.status" class="ml-2">
                  <span class="text-xs text-slate-500">Fortschritt: </span>
                  <span class="inline-flex items-center gap-0.5">
                    <span v-for="(step, si) in progressSteps(p.status)" :key="si"
                      :class="'w-2 h-2 rounded-full ' + (si < progressIdx(p.status) ? 'bg-green-500' : si === progressIdx(p.status) ? step.dot : 'bg-slate-600')"
                      :title="step.label"></span>
                  </span>
                  <span class="ml-1 text-xs text-slate-400">{{ statusLabel(p.status) }}</span>
                </span>
                <span v-if="p.kwp"> · {{ p.kwp }} kWp</span>
                <span v-if="p.kw"> · {{ p.kw }} kW</span>
                <span v-if="p.kwh"> · {{ p.kwh }} kWh</span>
                <span v-if="p.commission_date"> · Inbetriebnahme: {{ formatDate(p.commission_date) }}</span>
                <span v-if="p.panels"> · {{ p.panels.count }} Module {{ p.panels.manufacturer }}</span>
              </div>
            </div>
          </div>
          <div class="flex gap-2" @click.stop>
            <button @click="editCustomer(c)" class="text-slate-400 hover:text-amber-400 text-sm px-2">✏️ Bearbeiten</button>
            <button @click="deleteCustomer(c)" class="text-slate-400 hover:text-red-400 text-sm px-2">🗑️</button>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :open="confirmState.open"
      title="Kunde löschen"
      :message="`Kunde „${confirmState.customer?.firstname || ''} ${confirmState.customer?.lastname || ''}“ wirklich löschen?`"
      confirm-label="Löschen"
      cancel-label="Abbrechen"
      tone="danger"
      @confirm="doDelete"
      @cancel="confirmState.open = false"
    />

    <ConfirmDialog
      :open="dirtyDialog.open"
      title="Ungespeicherte Änderungen"
      :message="dirtyDialog.message"
      confirm-label="Änderungen verwerfen"
      cancel-label="Zurück zum Formular"
      tone="danger"
      @confirm="onDirtyDiscard"
      @cancel="dirtyDialog.open = false"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import installer from '@/api/installer'
import FormCustomer from '@/components/admin/FormCustomer.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import toast from '@/api/toast'
import { onBeforeRouteLeave, useRouter } from 'vue-router'

const customers = ref([])
const loading = ref(true)
const loadError = ref(null)
const showForm = ref(false)
const editing = ref(null)
const query = ref('')
const confirmState = reactive({ open: false, customer: null })
let searchTimer = null

// TASK-001: Dirty-Data-Guard (beforeunload + interne Navigation)
const router = useRouter()
const formDirty = ref(false)
const dirtyDialog = reactive({ open: false, message: '', action: null })

onMounted(load)

async function load(q = '') {
  loading.value = true
  loadError.value = null
  try {
    customers.value = q
      ? await installer.searchCustomers(q)
      : await installer.listCustomers()
  } catch (e) {
    console.error('Kunden laden fehlgeschlagen', e)
    loadError.value = e.message || 'Unbekannter Fehler'
  } finally {
    loading.value = false
  }
}

function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => load(query.value.trim()), 300)
}

function anlagetypLabel(t) {
  return { pv: 'PV', wallbox: 'Wallbox', waermepumpe: 'Wärmepumpe' }[t] || t
}

function statusLabel(s) {
  return { in_pruefung: 'In Prüfung', angemeldet: 'Angemeldet', abgeschlossen: 'Abgeschlossen' }[s] || s
}

const STEPS = [
  { key: 'in_pruefung', label: 'In Prüfung', dot: 'bg-yellow-500' },
  { key: 'angemeldet', label: 'Angemeldet', dot: 'bg-blue-500' },
  { key: 'abgeschlossen', label: 'Abgeschlossen', dot: 'bg-green-500' },
]
function progressSteps(current) {
  const idx = STEPS.findIndex(s => s.key === current)
  return STEPS.map((s, i) => ({ ...s, dot: i <= idx ? s.dot : 'bg-slate-600' }))
}
function progressIdx(current) {
  return STEPS.findIndex(s => s.key === current)
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('de-DE')
}

function openNew() {
  editing.value = null
  showForm.value = true
}

function closeForm() {
  // TASK-001: bei dirty → Confirm-Dialog statt sofortigen Schließen
  if (formDirty.value) {
    dirtyDialog.message = 'Es gibt ungespeicherte Änderungen. Wirst du das Formular wirklich schließen und die Änderungen verwerfen?'
    dirtyDialog.action = () => {
      showForm.value = false
      editing.value = null
      formDirty.value = false
    }
    dirtyDialog.open = true
  } else {
    showForm.value = false
    editing.value = null
  }
}

function onDirty(dirty) {
  formDirty.value = dirty
}

function onDirtyDiscard() {
  dirtyDialog.open = false
  const action = dirtyDialog.action
  dirtyDialog.action = null
  if (action) action()
}

function editCustomer(c) {
  editing.value = c
  showForm.value = true
}

async function deleteCustomer(c) {
  confirmState.customer = c
  confirmState.open = true
}

async function doDelete() {
  const c = confirmState.customer
  confirmState.open = false
  confirmState.customer = null
  if (!c) return
  try {
    await installer.deleteCustomer(c._id)
    toast.success('Kunde gelöscht')
    await load(query.value.trim())
  } catch (e) {
    toast.error('Löschen fehlgeschlagen: ' + e.message)
  }
}

function onSaved() {
  formDirty.value = false
  showForm.value = false
  editing.value = null
  toast.success('Kunde gespeichert')
  load(query.value.trim())
}
</script>
