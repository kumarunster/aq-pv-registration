#!/usr/bin/env python3
"""Refact FormCustomer.vue: Kunde/Anlagen-Tabs + paginierte Anlagenliste."""
import re

p = 'frontend/src/components/admin/FormCustomer.vue'
s = open(p).read()

# ---------------------------------------------------------------- template
OLD_TEMPLATE = """<template>
  <form @submit.prevent="save" class="bg-slate-900 rounded-xl p-5 border border-slate-800 space-y-6 mb-4">
    <h2 class="font-semibold text-lg">{{ initial ? 'Kunde bearbeiten' : 'Neuer Kunde' }}</h2>

    <!-- Kunden-Stammdaten -->
    <section>
      <h3 class="text-sm font-semibold text-amber-400 mb-3">👤 Kunde</h3>
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
    <section v-if="!isInstaller()">
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

    <!-- Anlagen -->
    <section>
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold text-amber-400">🔌 Anlagen</h3>
        <button type="button" @click="addPlant" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm">
          + Anlage hinzufügen
        </button>
      </div>
      <div v-if="form.plants.length === 0" class="text-slate-500 text-sm bg-slate-800 rounded-lg p-4">
        Noch keine Anlage. Über „+ Anlage hinzufügen" eine PV-Anlage, Wallbox oder Wärmepumpe erfassen.
      </div>
      <!-- Anlagen-Tabs: nur das aktive Formular ist im DOM (v-if),
           damit ZEREZ-Typeahead/State pro Anlage sauber bleibt -->
      <div class="flex flex-wrap gap-1.5 mb-3">
        <button v-for="(p, i) in form.plants" :key="'tab'+i" type="button"
          @click="activePlant = i"
          :class="activePlant === i
            ? 'px-3 py-1.5 bg-amber-500 text-slate-950 font-semibold rounded-lg text-sm'
            : 'px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm'"
        >
          {{ plantTabLabel(p, i) }}
        </button>
      </div>
      <div v-for="(p, i) in form.plants" :key="i" v-show="activePlant === i" class="bg-slate-800 rounded-xl p-4 border border-slate-700">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-semibold">Anlage {{ i + 1 }}</span>
          <button type="button" @click="removePlant(i)" class="text-slate-400 hover:text-red-400 text-sm">🗑️ Entfernen</button>
        </div>
        <PlantForm v-if="activePlant === i" :plant="p" :onUpdate="updatePlant" :index="i" :isInstaller="isInstaller()" :customerId="form.customer_id" @open-lageplan="openLageplan(i)" />
      </div>
    </section>

    <div class="flex gap-2 pt-2">
      <button type="submit" :disabled="saving" class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-sm disabled:opacity-50">
        {{ saving ? 'Speichert…' : (initial ? 'Speichern' : 'Kunde anlegen') }}
      </button>
      <button type="button" @click="$emit('cancel')" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm">
        Abbrechen
      </button>
    </div>
  </form>"""

NEW_TEMPLATE = """<template>
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
  </form>"""

assert OLD_TEMPLATE in s, "OLD_TEMPLATE nicht gefunden"
s = s.replace(OLD_TEMPLATE, NEW_TEMPLATE)

# ---------------------------------------------------------------- script additions
OLD_SCRIPT_START = """const isInstaller = () => props.mode === 'installer'"""
NEW_SCRIPT_START = """const isInstaller = () => props.mode === 'installer'

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
}"""
assert OLD_SCRIPT_START in s
s = s.replace(OLD_SCRIPT_START, NEW_SCRIPT_START)

# import computed + watch
OLD_IMPORT = "import { ref, reactive, onMounted, h, defineComponent } from 'vue'"
NEW_IMPORT = "import { ref, reactive, computed, watch, onMounted, h, defineComponent } from 'vue'"
assert OLD_IMPORT in s
s = s.replace(OLD_IMPORT, NEW_IMPORT)

# addPlant: go to anlagen tab, open new plant
OLD_ADDPLANT = """function addPlant() {
  form.plants.push(emptyPlant())
  activePlant.value = form.plants.length - 1
}"""
NEW_ADDPLANT = """function addPlant() {
  form.plants.push(emptyPlant())
  mainTab.value = 'anlagen'
  editingPlant.value = form.plants.length - 1
  plantPage.value = plantTotalPages.value - 1
}"""
assert OLD_ADDPLANT in s
s = s.replace(OLD_ADDPLANT, NEW_ADDPLANT)

# removePlant: close editor if that plant was open
OLD_REMOVEPLANT = """function removePlant(i) {
  form.plants.splice(i, 1)
  if (activePlant.value >= form.plants.length) activePlant.value = Math.max(0, form.plants.length - 1)
}"""
NEW_REMOVEPLANT = """function removePlant(i) {
  form.plants.splice(i, 1)
  if (editingPlant.value === i) editingPlant.value = null
  else if (editingPlant.value !== null && editingPlant.value > i) editingPlant.value--
}"""
assert OLD_REMOVEPLANT in s
s = s.replace(OLD_REMOVEPLANT, NEW_REMOVEPLANT)

# remove the old activePlant + plantTabLabel (no longer used)
OLD_ACTIVEPLANT = """const activePlant = ref(0)

function plantTabLabel(p, i) {
  const typ = { pv: 'PV', wallbox: 'Wallbox', waermepumpe: 'WP' }[p.anlagetyp] || '?'
  const done = p.lageplan ? ' ✓' : p.anlagetyp === 'pv' ? ' ⚠' : ''
  return `Anlage ${i + 1} · ${typ}${done}`
}
"""
assert OLD_ACTIVEPLANT in s
s = s.replace(OLD_ACTIVEPLANT, "")

open(p, 'w').write(s)
print("FormCustomer.vue refactored: Kunde/Anlagen-Tabs + paginierte Anlagenliste")
