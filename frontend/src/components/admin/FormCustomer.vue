<template>
  <form @submit.prevent="save" class="bg-slate-900 rounded-xl p-5 border border-slate-800 mb-4">
    <div class="flex items-center justify-between mb-4">
      <h2 class="font-semibold text-lg">{{ initial ? 'Kunde bearbeiten' : 'Neuer Kunde' }}</h2>
      <!-- Haupt-Tabs: Kunde | Anlagen -->
      <div class="flex gap-1">
        <button type="button" @click="mainTab = 'kunde'"
          :class="mainTab === 'kunde'
            ? 'px-4 py-1.5 bg-amber-500 text-slate-950 font-semibold rounded-lg text-sm'
            : 'px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm'">
          👤 Kunde
        </button>
        <button type="button" @click="mainTab = 'anlagen'"
          :class="mainTab === 'anlagen'
            ? 'px-4 py-1.5 bg-amber-500 text-slate-950 font-semibold rounded-lg text-sm'
            : 'px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm'">
          🔌 Anlagen ({{ form.plants.length }})
        </button>
      </div>
    </div>

    <!-- ============================== TAB: KUNDE ============================== -->
    <div v-if="mainTab === 'kunde'">
      <section>
        <h3 class="text-sm font-semibold text-amber-400 mb-3">👤 Stammdaten</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-slate-400 mb-1">Vorname *</label>
            <input v-model="form.firstname" class="input" required />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">Nachname *</label>
            <input v-model="form.lastname" class="input" required />
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm text-slate-400 mb-1">Straße + Nr *</label>
            <input v-model="form.address_street" class="input" required />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">PLZ *</label>
            <input v-model="form.address_plz" class="input" required />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">Ort *</label>
            <input v-model="form.address_city" class="input" required />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">Telefon</label>
            <input v-model="form.phone" class="input" />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">E-Mail</label>
            <input v-model="form.email" type="email" class="input" />
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm text-slate-400 mb-1">IBAN</label>
            <input v-model="form.iban" class="input" placeholder="DE00 0000 0000 …" />
          </div>
        </div>
      </section>

      <!-- Firma (nur im Admin-Modus) -->
      <section v-if="!isInstaller()" class="mt-6">
        <h3 class="text-sm font-semibold text-amber-400 mb-3">🏢 Firma (Installer / Betreiber)</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="md:col-span-2">
            <label class="block text-sm text-slate-400 mb-1">Firma *</label>
            <select v-model="form.company_id" class="input" required>
              <option value="" disabled>— Firma wählen —</option>
              <option v-for="c in companies" :key="c._id" :value="c._id">{{ c.name }}</option>
            </select>
            <p v-if="companies.length === 0" class="text-slate-500 text-xs mt-1">
              Noch keine Firmen angelegt — zuerst unter „Firmen" anlegen.
            </p>
          </div>
        </div>
      </section>
    </div>

    <!-- ============================== TAB: ANLAGEN ============================== -->
    <div v-if="mainTab === 'anlagen'">
      <!-- Suchleiste + Add -->
      <div class="flex flex-wrap items-center gap-3 mb-3">
        <input
          v-model="plantSearch"
          class="input flex-1 min-w-48" type="search"
          placeholder="🔍 Anlagen suchen: Adresse, MStR, ZEREZ-ID …"
        />
        <select v-model="plantStatusFilter" class="input w-auto">
          <option value="">Alle Status</option>
          <option value="in_pruefung">In Prüfung</option>
          <option value="angemeldet">Angemeldet</option>
          <option value="abgeschlossen">Abgeschlossen</option>
        </select>
        <button type="button" @click="addPlant" class="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm">
          + Anlage hinzufügen
        </button>
      </div>

      <div v-if="form.plants.length === 0" class="text-slate-500 text-sm bg-slate-800 rounded-lg p-4">
        Noch keine Anlage. Über „+ Anlage hinzufügen" eine PV-Anlage, Wallbox oder Wärmepumpe erfassen.
      </div>

      <!-- Paginierte Anlagenliste -->
      <div v-else>
        <div class="flex items-center justify-between text-sm text-slate-400 mb-2">
          <span>{{ plantFiltered.length }} von {{ form.plants.length }} Anlagen</span>
          <span v-if="plantTotalPages > 1">Seite {{ plantPage + 1 }} von {{ plantTotalPages }}</span>
        </div>

        <div class="border border-slate-700 rounded-lg overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-slate-800 text-slate-400 text-xs">
                <th class="p-2 text-left">#</th>
                <th class="p-2 text-left">Typ</th>
                <th class="p-2 text-left">Adresse</th>
                <th class="p-2 text-left">Status</th>
                <th class="p-2 text-left">Leistung</th>
                <th class="p-2 text-left">Lageplan</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in plantPageItems" :key="row.i"
                class="border-t border-slate-700 cursor-pointer hover:bg-slate-800/60"
                :class="{ 'bg-slate-800': editingPlant === row.i }"
                @click="openPlant(row.i)">
                <td class="p-2 text-slate-500">{{ row.i + 1 }}</td>
                <td class="p-2">{{ anlagetypLabel(row.p.anlagetyp) }}</td>
                <td class="p-2">{{ plantAddressShort(row.p) }}</td>
                <td class="p-2">{{ statusLabel(row.p.status) || '–' }}</td>
                <td class="p-2">{{ row.p.kwp ? row.p.kwp + ' kWp' : row.p.kw ? row.p.kw + ' kW' : '–' }}</td>
                <td class="p-2">{{ row.p.lageplan ? '✅' : (row.p.anlagetyp === 'pv' ? '⚠️' : '–') }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="plantTotalPages > 1" class="flex items-center justify-center gap-2 mt-3">
          <button :disabled="plantPage === 0" @click="plantPage--; " class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 rounded-lg text-sm">← Vorherige</button>
          <span class="text-slate-400 text-sm px-2">{{ plantPage + 1 }} / {{ plantTotalPages }}</span>
          <button :disabled="plantPage >= plantTotalPages - 1" @click="plantPage++" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 rounded-lg text-sm">Nächste →</button>
        </div>
      </div>

      <!-- Anlage-Editor (offen, wenn eine Anlage ausgewählt ist) -->
      <div v-if="editingPlant !== null" class="mt-4 bg-slate-800 rounded-xl p-4 border border-amber-500/40">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-semibold">Anlage {{ editingPlant + 1 }} bearbeiten</span>
          <div class="flex gap-2">
            <button type="button" @click="removePlant(editingPlant)" class="text-slate-400 hover:text-red-400 text-sm">🗑️ Entfernen</button>
            <button type="button" @click="editingPlant = null" class="text-slate-400 hover:text-amber-400 text-sm">✕ Schließen</button>
          </div>
        </div>
        <PlantForm :plant="form.plants[editingPlant]" :onUpdate="updatePlant" :index="editingPlant"
          :isInstaller="isInstaller()" :customerId="form.customer_id" @open-lageplan="openLageplan" />
      </div>
    </div>

    <div class="flex gap-2 pt-4">
      <button type="submit" :disabled="saving" class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-sm disabled:opacity-50">
        {{ saving ? 'Speichert…' : (initial ? 'Speichern' : 'Kunde anlegen') }}
      </button>
      <button type="button" @click="$emit('cancel')" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm">
        Abbrechen
      </button>
    </div>
  </form>

  <!-- 📐 Lageplan-Editor: Fullscreen-Dialog -->
  <Teleport to="body">
    <div v-if="lageplanDialog" class="fixed inset-0 z-50 bg-slate-950 overflow-y-auto">
      <div class="max-w-7xl mx-auto p-4">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-lg font-bold">📐 Lageplan — Anlage {{ lageplanDialog.plantIndex + 1 }}</h2>
          <button type="button" @click="closeLageplan" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm">
            ✖️ Schließen (ohne Speichern)
          </button>
        </div>
        <LageplanEditor ref="lageplanEditorRef" :initial-layout="lageplanDialog.initialLayout" />
        <div class="flex gap-2 mt-3 pb-6">
          <button type="button" @click="saveLageplan" class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-sm">
            ✅ Lageplan speichern
          </button>
          <button type="button" @click="closeLageplan" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm">
            Abbrechen
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, h, defineComponent } from 'vue'
import client from '@/api/client'
import toast from '@/api/toast'
import * as docsApi from '@/api/docs'
import { zerezSearch } from '@/api/client'
import LageplanEditor from '@/components/lageplan/LageplanEditor.vue'
import { useLayoutStore } from '@/components/lageplan/useLayoutStore.js'

const props = defineProps({
  companies: { type: Array, default: () => [] },
  initial: { type: Object, default: null },
  // 'admin' = mit Firmen-Auswahl, 'installer' = eigene Kunden (kein Firmen-Select)
  mode: { type: String, default: 'admin' },
})
const emit = defineEmits(['saved', 'cancel'])

const isInstaller = () => props.mode === 'installer'

// Haupt-Tabs: 'kunde' | 'anlagen'
const mainTab = ref('kunde')

// Anlagen-Tab: Suche, Filter, Pagination (client-side, alles liegt im Form-State)
const plantSearch = ref('')
const plantStatusFilter = ref('')
const plantPage = ref(0)
const PLANT_PAGE_SIZE = 20
const editingPlant = ref(null)

const plantFiltered = computed(() => {
  const q = plantSearch.value.trim().toLowerCase()
  return form.plants.map((p, i) => ({ p, i }))
    .filter(({ p }) => {
      if (plantStatusFilter.value && p.status !== plantStatusFilter.value) return false
      if (q) {
        const hay = [p.address_street, p.mstr_see_plant, p.mstr_eeg, p.notes,
          ...(p.inverters || []).map(iv => iv.manufacturer + ' ' + iv.type + ' ' + (iv.zerez_id || ''))
        ].join(' ').toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
})
const plantTotalPages = computed(() => Math.max(1, Math.ceil(plantFiltered.value.length / PLANT_PAGE_SIZE)))
const plantPageItems = computed(() =>
  plantFiltered.value.slice(plantPage.value * PLANT_PAGE_SIZE, (plantPage.value + 1) * PLANT_PAGE_SIZE)
)
watch([plantSearch, plantStatusFilter], () => { plantPage.value = 0 })

function plantAddressShort(p) {
  if (p.address_from_customer !== false && form.address_street) {
    return `${form.address_street}, ${form.address_plz} ${form.address_city}`
  }
  return [p.address_street, p.address_plz, p.address_city].filter(Boolean).join(', ') || '–'
}

function anlagetypLabel(t) {
  return { pv: 'PV', wallbox: 'Wallbox', waermepumpe: 'Wärmepumpe' }[t] || t
}

function statusLabel(s) {
  return { in_pruefung: 'In Prüfung', angemeldet: 'Angemeldet', abgeschlossen: 'Abgeschlossen' }[s] || ''
}

function openPlant(i) {
  editingPlant.value = i
}

// TUB-Bezug: Checklisten-Punkte (Dokumentationsfotos)
const CHECKLIST_ITEMS = [
  'Erdungsanlage',
  'Hauptpotentialschiene',
  'SLS Schalter',
  'Überspannungsschutz',
  'Berührungsschutz',
  'Hausanschlusskasten',
  'Zählerschrank',
  'Abstände',
  'Netzanschluss',
  'Meterschrank / Messumformer',
]
const DEFAULT_CHECKLIST = () => CHECKLIST_ITEMS.map((label) => ({ label, status: 'offen', image_url: null }))

const emptyPlant = () => ({
  anlagetyp: 'pv',
  commission_date: '',
  kwp: '',
  kw: '',
  kwh: '',
  // Anlage-Adresse (wie beim Kunden, aber pro Anlage)
  address_from_customer: true,
  address_street: '',
  address_plz: '',
  address_city: '',
  phone: '',
  email: '',
  // Grundstueckdaten (separate Felder)
  gemarkung: '',
  flur: '',
  flurstueck: '',
  panels: { manufacturer: '', type: '', count: 0, kwp: '' },
  inverters: [],
  battery: null,
  mstr_see_plant: '',
  mstr_eeg: '',
  mstr_see_battery: '',
  notes: '',
  status: null,
  checklist: DEFAULT_CHECKLIST(),
})

// PlantForm als inline-Komponente (klein genug für dieses Formular)
const PlantForm = defineComponent({
  name: 'PlantForm',
  props: ['plant', 'index', 'onUpdate', 'isInstaller', 'customerId'],
  emits: ['open-lageplan'],
  setup(p, { emit }) {
    function set(key, val) {
      p.onUpdate(p.index, key, val)
    }
    function addInverter() {
      const inv = { manufacturer: '', type: '', kw: '', zerez_id: '' }
      p.plant.inverters.push(inv)
      set('inverters', [...p.plant.inverters])
    }
    function removeInverter(i) {
      p.plant.inverters.splice(i, 1)
      set('inverters', [...p.plant.inverters])
    }
    function setInverter(i, key, val) {
      p.plant.inverters[i][key] = val
      set('inverters', [...p.plant.inverters])
    }

    // 📋 ZEREZ Typeahead für Inverter-Hersteller
    const zerezQuery = ref('')
    const activeZerezIndex = ref(-1)
    const zerezResults = ref([])
    const zerezOpen = ref(false)
    const zerezLoading = ref(false)

    let zerezTimer = null
    function onZerezInput(i, e) {
      const v = e.target.value
      setInverter(i, 'manufacturer', v)
      activeZerezIndex.value = i
      zerezQuery.value = v
      clearTimeout(zerezTimer)
      if (v.length >= 3) {
        zerezLoading.value = true
        zerezOpen.value = true
        zerezTimer = setTimeout(async () => {
          try {
            const results = await zerezSearch(v, p.isInstaller)
            zerezResults.value = results.slice(0, 50)
          } catch (err) {
            zerezResults.value = []
          } finally {
            zerezLoading.value = false
          }
        }, 300)
      } else {
        zerezOpen.value = false
        zerezResults.value = []
      }
    }

    function selectZerez(i, result) {
      // Daten übernehmen: manufacturer, type (modelName), kw (maxActivePower), zerez_id (unitCode)
      const inv = { ...p.plant.inverters[i] }
      inv.manufacturer = result.certificateHolderName || inv.manufacturer
      inv.type = result.modelName || inv.type
      inv.kw = String(result.maxActivePower || inv.kw)
      inv.zerez_id = result.unitCode || inv.zerez_id
      const invs = [...p.plant.inverters]
      invs[i] = inv
      set('inverters', invs)
      zerezOpen.value = false
      zerezResults.value = []
      zerezQuery.value = ''
    }

    function closeZerez() {
      zerezOpen.value = false
      zerezResults.value = []
    }
    // Status-Stepper: 4 Schritte
    const STATUS_STEPS = [
      { key: 'in_pruefung',    label: 'In Prüfung',  color: 'bg-yellow-500 border-yellow-500 text-yellow-300' },
      { key: 'angemeldet',     label: 'Angemeldet',   color: 'bg-blue-500 border-blue-500 text-blue-300' },
      { key: 'abgeschlossen',  label: 'Abgeschlossen', color: 'bg-green-500 border-green-500 text-green-300' },
    ]
    function statusStepper(plant, setFn, isInstaller) {
      const currentIdx = STATUS_STEPS.findIndex(st => st.key === plant.status)
      // -1 = not set, 0 = in_pruefung, 1 = angemeldet, 2 = abgeschlossen
      const steps = [
        { key: null, label: 'Angelegt', color: 'bg-slate-500 border-slate-500 text-slate-300' },
        ...STATUS_STEPS,
      ]
      // Build the stepper: circles connected by lines
      const children = []
      steps.forEach((st, i) => {
        const isActive = i === currentIdx + 1  // current step (1-indexed)
        const isDone = i < currentIdx + 1 && currentIdx >= 0  // completed
        const isClickable = !isInstaller && st.key !== null
        // Circle
        children.push(
          h('div', {
            class: 'relative flex flex-col items-center flex-1',
            key: st.key || 'start',
            style: isClickable ? 'cursor:pointer' : '',
            onClick: isClickable ? () => setFn('status', st.key) : undefined,
          }, [
            h('div', {
              class: 'w-8 h-8 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-colors ' +
                (isActive ? st.color : isDone ? 'bg-green-700 border-green-600 text-green-200' : 'bg-slate-800 border-slate-600 text-slate-500'),
            }, isDone && !isActive ? '✓' : (i + 1)),
            h('span', {
              class: 'text-[10px] mt-1 text-slate-400 whitespace-nowrap',
            }, st.label),
          ])
        )
        // Connector line (not after last)
        if (i < steps.length - 1) {
          const lineActive = i < currentIdx  // line is "done" if step i is completed
          children.push(
            h('div', {
              class: 'flex-1 h-0.5 mx-1 -mt-5',
              style: {
                backgroundColor: lineActive ? '#22c55e' : '#334155',
              },
            })
          )
        }
      })
      return h('div', { class: 'bg-slate-900 rounded-lg p-3 border border-slate-700' }, [
        h('h4', { class: 'text-xs font-semibold text-slate-400 mb-2' }, '📊 Fortschritt'),
        h('div', { class: 'flex items-center' }, children),
      ])
    }

    // 📋 Checkliste El. Installation
    function checklistSection(plant) {
      const items = plant.checklist && plant.checklist.length ? plant.checklist : []
      const rows = items.map((it, i) => {
        const done = it.status === 'erledigt'
        const na = it.status === 'nicht_anwendbar'
        return h('div', { class: 'flex items-center justify-between py-1.5 border-b border-slate-700 last:border-0', key: i }, [
          h('div', { class: 'flex items-center gap-2 flex-1' }, [
            h('button', {
              type: 'button',
              class: 'px-2 py-0.5 rounded text-xs ' +
                (done ? 'bg-green-700 text-green-200' : na ? 'bg-slate-600 text-slate-300' : 'bg-slate-800 text-slate-400'),
              onClick: () => {
                const items2 = [...plant.checklist]
                items2[i] = { ...items2[i], status: done ? 'offen' : na ? 'offen' : 'erledigt' }
                set('checklist', items2)
              },
              title: done ? 'Zurück auf offen' : na ? 'Zurück auf offen' : 'Als erledigt markieren',
            }, done ? '✓' : na ? 'N/A' : '○'),
            h('span', { class: 'text-sm ' + (done ? 'text-slate-500 line-through' : 'text-slate-300') }, it.label),
            it.image_url ? h('span', { class: 'text-xs text-green-400' }, '📷') : null,
          ]),
          h('div', { class: 'flex items-center gap-1' }, [
            h('button', {
              type: 'button',
              class: 'text-xs text-slate-400 hover:text-slate-200 px-1',
              title: 'Nicht anwendbar',
              onClick: () => {
                const items2 = [...plant.checklist]
                items2[i] = { ...items2[i], status: it.status === 'nicht_anwendbar' ? 'offen' : 'nicht_anwendbar' }
                set('checklist', items2)
              },
            }, 'N/A'),
            it.image_url
              ? h('a', {
                  href: docsApi.imageUrl(p.customerId, p.index, it.image_url),
                  target: '_blank',
                  class: 'text-xs text-blue-400 hover:text-blue-300 px-1',
                }, '📷')
              : h('label', {
                  class: 'text-xs text-amber-500 hover:text-amber-400 cursor-pointer px-1',
                  style: { display: 'inline-block' },
                }, [
                  h('input', {
                    type: 'file',
                    accept: 'image/*',
                    class: 'hidden',
                    onChange: async (e) => {
                      const f = e.target.files[0]
                      if (!f) return
                      try {
                        const r = await docsApi.uploadImage(p.customerId, p.index, f)
                        const items2 = [...plant.checklist]
                        items2[i] = { ...items2[i], image_url: r.blob_key }
                        set('checklist', items2)
                      } catch (err) {
                        alert('Upload fehlgeschlagen: ' + err.message)
                      }
                    },
                  }),
                  '📷 Foto',
                ]),
          ]),
        ])
      })
      return h('div', { class: 'bg-slate-900 rounded-lg p-3 border border-slate-700' }, [
        h('h4', { class: 'text-xs font-semibold text-slate-400 mb-2' }, '📋 Checkliste El. Installation'),
        h('p', { class: 'text-[10px] text-slate-500 mb-2' }, 'Dokumentationsfotos: nicht jeder Punkt braucht ein Foto.'),
        rows.length ? h('div', rows) : h('div', { class: 'text-xs text-slate-500' }, 'Keine Checkliste.'),
      ])
    }

    return () => h('div', { class: 'space-y-4' }, [
      // 📊 Fortschritt (ganz oben)
      statusStepper(p.plant, set, p.isInstaller),

      // 📍 Anlage-Adresse
      h('div', { class: 'bg-slate-900 rounded-lg p-3 border border-slate-700' }, [
        h('div', { class: 'flex items-center justify-between mb-2' }, [
          h('h4', { class: 'text-xs font-semibold text-slate-400' }, '📍 Anlage-Adresse'),
          h('label', { class: 'flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer' }, [
            h('input', {
              type: 'checkbox',
              checked: p.plant.address_from_customer,
              onChange: (e) => set('address_from_customer', e.target.checked),
              class: 'accent-amber-500 w-3.5 h-3.5',
            }),
            'Adresse vom Kunden übernehmen',
          ]),
        ]),
        // Adresszeilen nur anzeigen, wenn das Häkchen NICHT gesetzt ist
        ...(!p.plant.address_from_customer
          ? [h('div', { class: 'space-y-2' }, [
              h('div', [
                h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'Straße + Hausnummer'),
                h('input', { class: 'input', value: p.plant.address_street, onInput: (e) => set('address_street', e.target.value) }),
              ]),
              h('div', { class: 'grid grid-cols-1 md:grid-cols-2 gap-2' }, [
                h('div', [
                  h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'PLZ'),
                  h('input', { class: 'input', value: p.plant.address_plz, onInput: (e) => set('address_plz', e.target.value) }),
                ]),
                h('div', [
                  h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'Ort'),
                  h('input', { class: 'input', value: p.plant.address_city, onInput: (e) => set('address_city', e.target.value) }),
                ]),
              ]),
            ])]
          : [h('div', { class: 'text-xs text-slate-500' }, 'Adresse wird vom Kunden übernommen: ', h('span', { class: 'text-slate-300' }, p.plant.address_street ? `${p.plant.address_street}, ${p.plant.address_plz} ${p.plant.address_city}` : '…'))]),
      ]),

      // 🏡 Grundstueckdaten (separate Felder)
      h('div', { class: 'bg-slate-900 rounded-lg p-3 border border-slate-700' }, [
        h('h4', { class: 'text-xs font-semibold text-slate-400 mb-2' }, '🏡 Grundstueck'),
        h('div', { class: 'grid grid-cols-1 md:grid-cols-3 gap-2' }, [
          h('div', [
            h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'Gemarkung'),
            h('input', { class: 'input', value: p.plant.gemarkung, onInput: (e) => set('gemarkung', e.target.value) }),
          ]),
          h('div', [
            h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'Flur'),
            h('input', { class: 'input', value: p.plant.flur, onInput: (e) => set('flur', e.target.value) }),
          ]),
          h('div', [
            h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'Flurstueck'),
            h('input', { class: 'input', value: p.plant.flurstueck, onInput: (e) => set('flurstueck', e.target.value) }),
          ]),
        ]),
      ]),

      h('div', { class: 'grid grid-cols-1 md:grid-cols-3 gap-3' }, [
        h('div', [
          h('label', { class: 'block text-sm text-slate-400 mb-1' }, 'Anlagetyp *'),
          h('select', {
            class: 'input',
            value: p.plant.anlagetyp,
            onChange: (e) => set('anlagetyp', e.target.value),
          }, [
            ['pv', 'PV-Anlage'],
            ['wallbox', 'Wallbox'],
            ['waermepumpe', 'Wärmepumpe'],
          ].map(([v, l]) => h('option', { value: v, key: v }, l))),
        ]),
        h('div', [
          h('label', { class: 'block text-sm text-slate-400 mb-1' }, 'Inbetriebnahme (TT.MM.JJJJ)'),
          h('input', {
            class: 'input',
            value: p.plant.commission_date,
            placeholder: '09.12.2024',
            onInput: (e) => set('commission_date', e.target.value),
          }),
        ]),
        h('div', [
          h('label', { class: 'block text-sm text-slate-400 mb-1' }, 'kW (Leistung)'),
          h('input', {
            class: 'input',
            value: p.plant.kw,
            placeholder: '6',
            onInput: (e) => set('kw', e.target.value),
          }),
        ]),
      ]),

      // PV-spezifisch
      p.plant.anlagetyp === 'pv'
        ? h('div', { class: 'space-y-3' }, [
            h('div', { class: 'grid grid-cols-1 md:grid-cols-3 gap-3' }, [
              h('div', [
                h('label', { class: 'block text-sm text-slate-400 mb-1' }, 'kWp (Nennleistung)'),
                h('input', {
                  class: 'input',
                  value: p.plant.kwp,
                  placeholder: '6,9',
                  onInput: (e) => set('kwp', e.target.value),
                }),
              ]),
              h('div', [
                h('label', { class: 'block text-sm text-slate-400 mb-1' }, 'Speicher (kWh)'),
                h('input', {
                  class: 'input',
                  value: p.plant.kwh,
                  placeholder: '5,1',
                  onInput: (e) => set('kwh', e.target.value),
                }),
              ]),
              h('div'),
            ]),
            // Module
            h('div', { class: 'bg-slate-900 rounded-lg p-3 border border-slate-700' }, [
              h('h4', { class: 'text-xs font-semibold text-slate-400 mb-2' }, 'PV-Module'),
              h('div', { class: 'grid grid-cols-1 md:grid-cols-4 gap-2' }, [
                h('input', { class: 'input', placeholder: 'Hersteller', value: p.plant.panels.manufacturer, onInput: (e) => set('panels', { ...p.plant.panels, manufacturer: e.target.value }) }),
                h('input', { class: 'input', placeholder: 'Typ', value: p.plant.panels.type, onInput: (e) => set('panels', { ...p.plant.panels, type: e.target.value }) }),
                h('input', { class: 'input', placeholder: 'Anzahl', type: 'number', value: String(p.plant.panels.count), onInput: (e) => set('panels', { ...p.plant.panels, count: parseInt(e.target.value) || 0 }) }),
                h('input', { class: 'input', placeholder: 'kWp', value: p.plant.panels.kwp, onInput: (e) => set('panels', { ...p.plant.panels, kwp: e.target.value }) }),
              ]),
            ]),
            // MStR
            h('div', { class: 'bg-slate-900 rounded-lg p-3 border border-slate-700' }, [
              h('h4', { class: 'text-xs font-semibold text-slate-400 mb-2' }, 'MStR (Marktstammdaten-Register)'),
              h('div', { class: 'grid grid-cols-1 md:grid-cols-3 gap-2' }, [
                h('input', { class: 'input', placeholder: 'SEE Anlage', value: p.plant.mstr_see_plant, onInput: (e) => set('mstr_see_plant', e.target.value) }),
                h('input', { class: 'input', placeholder: 'EEG-Anlage', value: p.plant.mstr_eeg, onInput: (e) => set('mstr_eeg', e.target.value) }),
                h('input', { class: 'input', placeholder: 'SEE Speicher', value: p.plant.mstr_see_battery, onInput: (e) => set('mstr_see_battery', e.target.value) }),
              ]),
            ]),
          ])
        : null,

      // Wechselrichter (alle Anlagetypen)
      h('div', { class: 'relative bg-slate-900 rounded-lg p-3 border border-slate-700' }, [
        h('div', { class: 'flex items-center justify-between mb-2' }, [
          h('h4', { class: 'text-xs font-semibold text-slate-400' }, 'Wechselrichter / Ladepunkte'),
          h('button', { type: 'button', onClick: addInverter, class: 'text-xs text-amber-400' }, '+ Hinzufügen'),
        ]),
        p.plant.inverters.map((inv, i) =>
          h('div', { class: 'grid grid-cols-1 md:grid-cols-5 gap-2 mb-2', key: i }, [
            h('div', [
              h('input', {
                class: 'input',
                placeholder: 'Hersteller / Modell (min. 4 Zeichen, z. B. sungrow sh10)',
                value: inv.manufacturer,
                onInput: (e) => onZerezInput(i, e),
                onFocus: () => { if (zerezQuery.value.length >= 4) zerezOpen.value = true },
                onBlur: () => setTimeout(closeZerez, 200),
              }),
            ]),
            h('input', { class: 'input', placeholder: 'Typ', value: inv.type, onInput: (e) => setInverter(i, 'type', e.target.value) }),
            h('input', { class: 'input', placeholder: 'kW', value: inv.kw, onInput: (e) => setInverter(i, 'kw', e.target.value) }),
            h('input', { class: 'input', placeholder: 'ZEREZ-ID', value: inv.zerez_id, onInput: (e) => setInverter(i, 'zerez_id', e.target.value) }),
            h('button', { type: 'button', onClick: () => removeInverter(i), class: 'text-slate-400 hover:text-red-400 text-sm' }, '🗑️'),
          ])
        ),
        p.plant.inverters.length === 0 ? h('div', { class: 'text-slate-500 text-xs' }, 'Kein Wechselrichter erfasst.') : null,
        // ZEREZ Typeahead: full-width, UNTER der Inverter-Sektion (deckt nichts ab)
        (zerezOpen.value && (zerezResults.value.length || zerezLoading.value))
          ? h('div', {
              class: 'relative mt-2 z-50 bg-slate-800 border border-slate-600 rounded-lg shadow-xl max-h-64 overflow-y-auto',
              onClick: (e) => e.stopPropagation(),
            }, [
              zerezLoading.value
                ? h('div', { class: 'p-2 text-xs text-slate-400' }, 'Lade…')
                : zerezResults.value.length
                  ? h('table', { class: 'w-full text-xs' }, [
                      h('thead', [
                        h('tr', { class: 'text-slate-500 border-b border-slate-700' }, [
                          h('th', { class: 'p-1.5 text-left' }, 'Hersteller'),
                          h('th', { class: 'p-1.5 text-left' }, 'Model'),
                          h('th', { class: 'p-1.5 text-left' }, 'kW'),
                          h('th', { class: 'p-1.5 text-left' }, 'ZEREZ-ID'),
                          h('th', { class: 'p-1.5 text-left' }, 'Voltage'),
                        ]),
                      ]),
                      h('tbody', zerezResults.value.map((r, ri) =>
                        h('tr', {
                          key: ri,
                          class: 'cursor-pointer hover:bg-slate-700',
                          onClick: () => selectZerez(activeZerezIndex.value, r),
                        }, [
                          h('td', { class: 'p-1.5' }, r.certificateHolderName || '–'),
                          h('td', { class: 'p-1.5' }, r.modelName || '–'),
                          h('td', { class: 'p-1.5' }, r.maxActivePower != null ? r.maxActivePower : '–'),
                          h('td', { class: 'p-1.5' }, r.unitCode || '–'),
                          h('td', { class: 'p-1.5' }, r.ratedVoltage != null ? r.ratedVoltage : '–'),
                        ])
                      )),
                    ])
                  : h('div', { class: 'p-2 text-xs text-slate-400' }, 'Keine Treffer.'),
            ])
          : null,
      ]),

      // Speicher (PV + Wärmepumpe)
      (p.plant.anlagetyp === 'pv' || p.plant.anlagetyp === 'waermepumpe')
        ? h('div', { class: 'bg-slate-900 rounded-lg p-3 border border-slate-700' }, [
            h('h4', { class: 'text-xs font-semibold text-slate-400 mb-2' }, p.plant.anlagetyp === 'pv' ? 'Batteriespeicher' : 'Pufferspeicher'),
            p.plant.battery
              ? h('div', { class: 'grid grid-cols-1 md:grid-cols-3 gap-2' }, [
                  h('input', { class: 'input', placeholder: 'Hersteller', value: p.plant.battery.manufacturer, onInput: (e) => set('battery', { ...p.plant.battery, manufacturer: e.target.value }) }),
                  h('input', { class: 'input', placeholder: 'Typ', value: p.plant.battery.type, onInput: (e) => set('battery', { ...p.plant.battery, type: e.target.value }) }),
                  h('input', { class: 'input', placeholder: 'kWh', value: p.plant.battery.kwh, onInput: (e) => set('battery', { ...p.plant.battery, kwh: e.target.value }) }),
                ])
              : h('button', { type: 'button', onClick: () => set('battery', { manufacturer: '', type: '', kwh: '' }), class: 'text-xs text-amber-400' }, '+ Speicher hinzufügen'),
          ])
        : null,

      // 📋 Checkliste El. Installation
      checklistSection(p.plant),

      // 📐 Lageplan (PV: Pflichtfeld, sonst optional)
      h('div', { class: 'bg-slate-900 rounded-lg p-3 border border-slate-700' }, [
        h('div', { class: 'flex items-center justify-between' }, [
          h('div', { class: 'flex items-center gap-2' }, [
            h('h4', { class: 'text-xs font-semibold text-slate-400' }, '📐 Lageplan'),
            p.plant.anlagetyp === 'pv'
              ? h('span', { class: 'text-[10px] bg-red-900 text-red-300 px-1.5 py-0.5 rounded' }, 'Pflichtfeld')
              : null,
          ]),
          h('div', { class: 'flex items-center gap-3' }, [
            h('span', {
              class: 'text-xs',
              style: p.plant.lageplan ? 'color: #4ade80' : 'color: #64748b',
            }, p.plant.lageplan ? '✓ erfasst' : 'noch leer'),
            h('button', {
              type: 'button',
              onClick: () => emit('open-lageplan', p.index),
              class: 'px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-lg',
            }, p.plant.lageplan ? 'Bearbeiten' : 'Erstellen'),
          ]),
        ]),
      ]),

      // Notizen
      h('div', [
        h('label', { class: 'block text-sm text-slate-400 mb-1' }, 'Notizen'),
        h('textarea', { class: 'input', rows: 2, value: p.plant.notes, onInput: (e) => set('notes', e.target.value) }),
      ]),
    ])
  },
})

const form = reactive({
  customer_id: '',
  firstname: '',
  lastname: '',
  address_street: '',
  address_plz: '',
  address_city: '',
  phone: '',
  email: '',
  iban: '',
  company_id: '',
  plants: [],
})
const saving = ref(false)

// 📐 Lageplan-Dialog (Fullscreen)
const lageplanDialog = ref(null) // { plantIndex, initialLayout }
const lageplanEditorRef = ref(null)
const layoutStore = useLayoutStore()

onMounted(() => {
  if (props.initial) {
    form.customer_id = props.initial._id || props.initial.id || ''
    form.firstname = props.initial.firstname || ''
    form.lastname = props.initial.lastname || ''
    form.address_street = props.initial.address_street || ''
    form.address_plz = props.initial.address_plz || ''
    form.address_city = props.initial.address_city || ''
    form.phone = props.initial.phone || ''
    form.email = props.initial.email || ''
    form.iban = props.initial.iban || ''
    form.plants = props.initial.plants?.length
      ? props.initial.plants.map(p => ({
          ...emptyPlant(),
          ...p,
          // Adresse: Häkchen => Adresse vom Kunden, sonst eigene Felder
          address_from_customer: p.address_from_customer !== false,
          address_street: p.address_from_customer === false ? (p.address_street || '') : '',
          address_plz: p.address_from_customer === false ? (p.address_plz || '') : '',
          address_city: p.address_from_customer === false ? (p.address_city || '') : '',
          checklist: p.checklist && p.checklist.length ? p.checklist : DEFAULT_CHECKLIST(),
          panels: p.panels || emptyPlant().panels,
          battery: p.battery || null,
          inverters: p.inverters || [],
        }))
      : []
  }
})


function addPlant() {
  form.plants.push(emptyPlant())
  mainTab.value = 'anlagen'
  editingPlant.value = form.plants.length - 1
  plantPage.value = plantTotalPages.value - 1
}

function removePlant(i) {
  form.plants.splice(i, 1)
  if (editingPlant.value === i) editingPlant.value = null
  else if (editingPlant.value !== null && editingPlant.value > i) editingPlant.value--
}

function updatePlant(i, key, val) {
  form.plants[i][key] = val
}

// 📐 Lageplan: Dialog öffnen/schließen
function plantAddressLine(p) {
  if (!p) return ''
  return [p.address_street, p.address_plz, p.address_city].filter(Boolean).join(', ')
}

function openLageplan(i) {
  const p = form.plants[i]
  if (!p) return
  // Adresse: Häkchen => Kundendaten, sonst eigene Adressfelder
  const adresse = p.address_from_customer !== false
    ? plantAddressLine(form)
    : plantAddressLine(p)
  const title = `Lageplan ${p.anlagetyp === 'pv' ? 'PV-Anlage' : p.anlagetyp} ${form.lastname || ''} ${form.firstname || ''}`.trim()
  const existing = p.lageplan || null
  const initialLayout = existing ? { ...existing } : { title, background_image_url: null, background_image_width: null, background_image_height: null, elements: [], metadata: {} }
  // Titel/Adresse/Grundstueck immer frisch vorbefuellen (auch ueber alten metadata)
  initialLayout.title = title
  initialLayout.metadata = { ...(existing?.metadata || {}), adresse, gemarkung: p.gemarkung || '', flur: p.flur || '', flurstueck: p.flurstueck || '' }
  // Store zuruecksetzen (modulweit geteilt!) damit der Editor frisch startet
  layoutStore.clearAll()
  layoutStore.layout.background_image_url = initialLayout.background_image_url
  layoutStore.layout.background_image_width = initialLayout.background_image_width
  layoutStore.layout.background_image_height = initialLayout.background_image_height
  lageplanDialog.value = { plantIndex: i, initialLayout }
}

function saveLageplan() {
  if (!lageplanDialog.value) return
  const i = lageplanDialog.value.plantIndex
  const editor = lageplanEditorRef.value
  const layout = editor ? editor.getLayout() : null
  if (layout) {
    // Adresse/Grundstueck aktuell in den metadata spiegeln (PDF-Header)
    const p = form.plants[i]
    if (p && layout.metadata) {
      const adresse = p.address_from_customer !== false ? plantAddressLine(form) : plantAddressLine(p)
      layout.metadata = { ...layout.metadata, adresse, gemarkung: p.gemarkung || '', flur: p.flur || '', flurstueck: p.flurstueck || '' }
    }
    form.plants[i].lageplan = layout
  }
  lageplanDialog.value = null
}

function closeLageplan() {
  lageplanDialog.value = null
}

// Datum TT.MM.JJJJ -> ISO
function toISO(d) {
  if (!d) return null
  const [dd, mm, yyyy] = d.split('.')
  if (!dd || !mm || !yyyy) return null
  return `${yyyy}-${mm}-${dd}`
}

async function save() {
  // PV-Anlagen benötigen einen Lageplan (Pflichtfeld, Roadmap Phase 5e)
  const pvWithout = form.plants.filter(p => p.anlagetyp === 'pv' && !p.lageplan)
  if (pvWithout.length) {
    toast.error(`PV-Anlage(n) ohne Lageplan: ${pvWithout.map((p,i)=>`Anlage ${form.plants.indexOf(p)+1}`).join(', ')}. Bitte zuerst den Lageplan erstellen.`)
    return
  }
  saving.value = true
  try {
    const payload = {
      firstname: form.firstname,
      lastname: form.lastname,
      address_street: form.address_street,
      address_plz: form.address_plz,
      address_city: form.address_city,
      phone: form.phone || null,
      email: form.email || null,
      iban: form.iban || null,
    }
    // Firmen-ID nur im Admin-Modus; Installer-Anlagen bekommen company_id: null
    if (form.plants.length && (isInstaller() || form.company_id)) {
      payload.plants = form.plants.map(p => ({
        anlagetyp: p.anlagetyp,
        commission_date: toISO(p.commission_date),
        company_id: isInstaller() ? null : form.company_id,
        kwp: p.kwp || null,
        kw: p.kw || null,
        kwh: p.kwh || null,
        // Anlage-Adresse (separate Felder, nur wenn Häkchen NICHT gesetzt)
        address_from_customer: p.address_from_customer !== false,
        address_street: p.address_from_customer === false ? (p.address_street || null) : null,
        address_plz: p.address_from_customer === false ? (p.address_plz || null) : null,
        address_city: p.address_from_customer === false ? (p.address_city || null) : null,
        // Grundstueckdaten
        gemarkung: p.gemarkung || null,
        flur: p.flur || null,
        flurstueck: p.flurstueck || null,
        panels: p.panels && p.panels.manufacturer ? p.panels : null,
        inverters: p.inverters || [],
        battery: p.battery || null,
        mstr_see_plant: p.mstr_see_plant || null,
        mstr_eeg: p.mstr_eeg || null,
        mstr_see_battery: p.mstr_see_battery || null,
        notes: p.notes || null,
        status: p.status || null,
        checklist: p.checklist || [],
        lageplan: p.lageplan || null,
        documents: p.documents || [],
      }))
    }
    const base = isInstaller() ? '/installer/customers' : '/admin/customers'
    let doc
    if (props.initial) {
      doc = (await client.put(`${base}/${props.initial._id}`, payload)).data
    } else {
      doc = (await client.post(base, payload)).data
    }
    if (doc && (doc._id || doc.id)) {
      form.customer_id = doc._id || doc.id
    }
    emit('saved')
  } catch (e) {
    toast.error('Speichern fehlgeschlagen: ' + e.message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.input {
  @apply w-full bg-slate-800 rounded-lg px-3 py-2 text-sm border border-slate-700 focus:border-amber-500 focus:outline-none;
}
</style>
