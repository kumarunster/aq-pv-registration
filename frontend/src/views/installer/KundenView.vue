<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold">👤 Meine Kunden</h1>
      <button @click="openNew" class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-sm">
        {{ showForm ? 'Formular schließen' : '+ Neuer Kunde' }}
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
    />

    <!-- Liste -->
    <div v-if="!showForm" class="space-y-3">
      <div v-if="loading" class="text-slate-400 text-sm">Lade…</div>
      <div v-else-if="customers.length === 0" class="bg-slate-900 rounded-xl p-6 text-center text-slate-400">
        {{ query ? 'Keine Kunden gefunden.' : 'Noch keine eigenen Kunden angelegt.' }}
      </div>
      <div v-for="c in customers" :key="c._id" class="bg-slate-900 rounded-xl p-4 border border-slate-800">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-semibold text-lg">{{ c.firstname }} {{ c.lastname }}</h3>
            <p class="text-slate-400 text-sm mt-1">
              {{ c.address_street }}, {{ c.address_plz }} {{ c.address_city }}
            </p>
            <p v-if="c.email" class="text-slate-400 text-sm">{{ c.email }} · {{ c.phone }}</p>
            <div v-if="c.iban" class="text-slate-500 text-xs mt-1">IBAN: {{ c.iban }}</div>
            <div v-if="c.plants && c.plants.length" class="mt-3">
              <div v-for="(p, i) in c.plants" :key="i" class="text-sm text-slate-400 bg-slate-800 rounded-lg px-3 py-2 mb-2">
                <span class="text-amber-400 font-medium">{{ anlagetypLabel(p.anlagetyp) }}</span>
                <span v-if="p.status" :class="'ml-2 px-1.5 py-0.5 rounded text-xs ' + statusBadgeClass(p.status)">{{ statusLabel(p.status) }}</span>
                <span v-if="p.kwp"> · {{ p.kwp }} kWp</span>
                <span v-if="p.kw"> · {{ p.kw }} kW</span>
                <span v-if="p.kwh"> · {{ p.kwh }} kWh</span>
                <span v-if="p.commission_date"> · Inbetriebnahme: {{ formatDate(p.commission_date) }}</span>
                <span v-if="p.panels"> · {{ p.panels.count }} Module {{ p.panels.manufacturer }}</span>
              </div>
            </div>
          </div>
          <div class="flex gap-2">
            <button @click="editCustomer(c)" class="text-slate-400 hover:text-amber-400 text-sm px-2">✏️ Bearbeiten</button>
            <button @click="deleteCustomer(c)" class="text-slate-400 hover:text-red-400 text-sm px-2">🗑️</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import installer from '@/api/installer'
import FormCustomer from '@/components/admin/FormCustomer.vue'

const customers = ref([])
const loading = ref(true)
const showForm = ref(false)
const editing = ref(null)
const query = ref('')
let searchTimer = null

onMounted(load)

async function load(q = '') {
  loading.value = true
  try {
    customers.value = q
      ? await installer.searchCustomers(q)
      : await installer.listCustomers()
  } catch (e) {
    console.error('Kunden laden fehlgeschlagen', e)
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

function statusBadgeClass(s) {
  return {
    in_pruefung: 'bg-yellow-900 text-yellow-300',
    angemeldet: 'bg-blue-900 text-blue-300',
    abgeschlossen: 'bg-green-900 text-green-300',
  }[s] || 'bg-slate-700 text-slate-300'
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
  showForm.value = false
  editing.value = null
}

function editCustomer(c) {
  editing.value = c
  showForm.value = true
}

async function deleteCustomer(c) {
  if (!confirm(`Kunde "${c.firstname} ${c.lastname}" wirklich löschen?`)) return
  try {
    await installer.deleteCustomer(c._id)
    await load(query.value.trim())
  } catch (e) {
    alert('Löschen fehlgeschlagen: ' + e.message)
  }
}

function onSaved() {
  closeForm()
  load(query.value.trim())
}
</script>
