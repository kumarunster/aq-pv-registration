<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold">👤 Kunden & Anlagen</h1>
      <button @click="openNew" class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-sm">
        {{ showForm ? 'Formular schließen' : '+ Neuer Kunde' }}
      </button>
    </div>

    <!-- Formular -->
    <FormCustomer v-if="showForm" :companies="companies" :initial="editing || null" @saved="onSaved" @cancel="closeForm" />

    <!-- Liste -->
    <div v-if="!showForm">
      <!-- Suche + Filter + Pagination -->
      <div class="bg-slate-900 rounded-xl p-4 border border-slate-800 mb-4">
        <div class="flex flex-wrap items-center gap-3">
          <input
            v-model="search" @input="debouncedLoad"
            class="input flex-1 min-w-48" type="search" placeholder="🔍 Suche: Name, Ort, E-Mail, Straße…"
          />
          <select v-model="statusFilter" @change="onFilterChange" class="input w-auto">
            <option value="">Alle Status</option>
            <option value="in_pruefung">In Prüfung</option>
            <option value="angemeldet">Angemeldet</option>
            <option value="abgeschlossen">Abgeschlossen</option>
          </select>
        </div>
        <div class="flex items-center justify-between mt-3 text-sm text-slate-400">
          <span v-if="total !== null">{{ total }} Kunden</span>
          <span>{{ loading ? '…' : `Seite ${page + 1} von ${totalPages || 1}` }}</span>
        </div>
      </div>

      <div v-if="loading" class="text-slate-400 text-sm py-4 text-center">Lade…</div>
      <div v-else-if="customers.length === 0" class="bg-slate-900 rounded-xl p-6 text-center text-slate-400">
        Keine Kunden gefunden.
      </div>
      <div v-else class="space-y-3">
        <div v-for="c in customers" :key="c._id" class="bg-slate-900 rounded-xl p-4 border border-slate-800 hover:border-amber-500/50 cursor-pointer transition-colors" @click="editCustomer(c)">
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-semibold text-lg">{{ c.firstname }} {{ c.lastname }}</h3>
              <p class="text-slate-400 text-sm mt-1">
                {{ c.address_street }}, {{ c.address_plz }} {{ c.address_city }}
              </p>
              <p v-if="c.email" class="text-slate-400 text-sm">{{ c.email }} · {{ c.phone }}</p>
              <div v-if="c.iban" class="text-slate-500 text-xs mt-1">IBAN: {{ c.iban }}</div>
              <!-- Anlagen-Zusammenfassung (P2): keine inline-Chips bei vielen Anlagen -->
              <div v-if="c.plants && c.plants.length" class="mt-3 flex flex-wrap items-center gap-1.5">
                <span class="text-sm text-slate-300">🔌 {{ c.plants.length }} Anlage{{ c.plants.length !== 1 ? 'n' : '' }}</span>
                <span class="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">🟡 {{ plantCounts(c).in_pruefung }}</span>
                <span class="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">🔵 {{ plantCounts(c).angemeldet }}</span>
                <span class="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">🟢 {{ plantCounts(c).abgeschlossen }}</span>
                <span v-if="plantCounts(c).offen" class="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-500">{{ plantCounts(c).offen }} offen</span>
                <span v-if="plantCounts(c).no_lageplan" class="text-xs px-2 py-0.5 rounded-full bg-red-900/60 text-red-300">⚠ {{ plantCounts(c).no_lageplan }} PV ohne Lageplan</span>
              </div>
              <!-- Erste Anlagen als Vorschau (max 3), Rest im Formular -->
              <div v-if="c.plants && c.plants.length" class="mt-2 space-y-1">
                <div v-for="(p, i) in c.plants.slice(0, 3)" :key="i" class="text-xs text-slate-400 bg-slate-800 rounded-lg px-3 py-1.5">
                  <span class="text-amber-400 font-medium">{{ anlagetypLabel(p.anlagetyp) }}</span>
                  <span class="ml-1">{{ plantAddressShort(c, p) }}</span>
                  <span v-if="p.kwp"> · {{ p.kwp }} kWp</span>
                  <span v-if="p.kw && !p.kwp"> · {{ p.kw }} kW</span>
                  <span v-if="p.status" class="ml-1 text-slate-500">· {{ statusLabel(p.status) }}</span>
                </div>
                <div v-if="c.plants.length > 3" class="text-xs text-slate-500">… und {{ c.plants.length - 3 }} weitere (im Formular)</div>
              </div>
            </div>
            <div class="flex gap-2" @click.stop>
              <button @click="editCustomer(c)" class="text-slate-400 hover:text-amber-400 text-sm px-2">✏️ Bearbeiten</button>
              <button @click="deleteCustomer(c)" class="text-slate-400 hover:text-red-400 text-sm px-2">🗑️</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 mt-6">
        <button :disabled="page === 0" @click="changePage(-1)" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 rounded-lg text-sm">← Vorherige</button>
        <span class="text-slate-400 text-sm px-2">Seite {{ page + 1 }} / {{ totalPages }}</span>
        <button :disabled="page >= totalPages - 1" @click="changePage(1)" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 rounded-lg text-sm">Nächste →</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import client from '@/api/client'
import FormCustomer from '@/components/admin/FormCustomer.vue'

const customers = ref([])
const companies = ref([])
const loading = ref(true)
const showForm = ref(false)
const editing = ref(null)

const search = ref('')
const statusFilter = ref('')
const page = ref(0)
const limit = 25
const total = ref(null)
const totalPages = computed(() => total.value ? Math.ceil(total.value / limit) : 0)

let debounceTimer = null

onMounted(load)

function debouncedLoad() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { page.value = 0; load() }, 300)
}

function onFilterChange() {
  page.value = 0
  load()
}

function changePage(delta) {
  page.value = Math.max(0, page.value + delta)
  load()
}

async function load() {
  loading.value = true
  try {
    const params = { limit, offset: page.value * limit }
    if (search.value.trim()) params.q = search.value.trim()
    if (statusFilter.value) params.status = statusFilter.value
    const [cust, comp] = await Promise.all([
      client.get('/admin/customers', { params }),
      client.get('/admin/companies'),
    ])
    customers.value = cust.data.items
    total.value = cust.data.total
    companies.value = comp.data
  } catch (e) {
    console.error('Kunden laden fehlgeschlagen', e)
  } finally {
    loading.value = false
  }
}

import toast from '@/api/toast'

function anlagetypLabel(t) {
  return { pv: 'PV', wallbox: 'Wallbox', waermepumpe: 'Wärmepumpe' }[t] || t
}

// P2: Anlagen-Zusammenfassung statt 200 inline-Chips
function plantCounts(c) {
  const counts = { in_pruefung: 0, angemeldet: 0, abgeschlossen: 0, offen: 0, no_lageplan: 0 }
  for (const p of c.plants || []) {
    if (p.status) counts[p.status] = (counts[p.status] || 0) + 1
    else counts.offen++
    if (p.anlagetyp === 'pv' && !p.lageplan) counts.no_lageplan++
  }
  return counts
}

function plantAddressShort(c, p) {
  if (p.address_from_customer !== false && c.address_street) {
    return c.address_street
  }
  return [p.address_street, p.address_city].filter(Boolean).join(', ') || '–'
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
    await client.delete(`/admin/customers/${c._id}`)
    await load()
  } catch (e) {
    toast.error('Löschen fehlgeschlagen: ' + e.message)
  }
}

function onSaved() {
  closeForm()
  load()
}
</script>
