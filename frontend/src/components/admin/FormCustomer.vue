<template>
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
      <div v-for="(p, i) in form.plants" :key="i" class="bg-slate-800 rounded-xl p-4 mb-3 border border-slate-700">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-semibold">Anlage {{ i + 1 }}</span>
          <button type="button" @click="removePlant(i)" class="text-slate-400 hover:text-red-400 text-sm">🗑️ Entfernen</button>
        </div>
        <PlantForm :plant="p" :onUpdate="updatePlant" :index="i" />
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
  </form>
</template>

<script setup>
import { ref, reactive, onMounted, h, defineComponent } from 'vue'
import client from '@/api/client'

const props = defineProps({
  companies: { type: Array, default: () => [] },
  initial: { type: Object, default: null },
  // 'admin' = mit Firmen-Auswahl, 'installer' = eigene Kunden (kein Firmen-Select)
  mode: { type: String, default: 'admin' },
})
const emit = defineEmits(['saved', 'cancel'])

const isInstaller = () => props.mode === 'installer'

const emptyPlant = () => ({
  anlagetyp: 'pv',
  commission_date: '',
  kwp: '',
  kw: '',
  kwh: '',
  // Anlage-Adresse (wie beim Kunden, aber pro Anlage)
  address_street: '',
  address_plz: '',
  address_city: '',
  phone: '',
  email: '',
  iban: '',
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
})

// PlantForm als inline-Komponente (klein genug für dieses Formular)
const PlantForm = defineComponent({
  name: 'PlantForm',
  props: ['plant', 'index', 'onUpdate'],
  setup(p) {
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
    return () => h('div', { class: 'space-y-4' }, [
      // 📍 Anlage-Adresse (wie beim Kunden, separate Felder)
      h('div', { class: 'bg-slate-900 rounded-lg p-3 border border-slate-700' }, [
        h('h4', { class: 'text-xs font-semibold text-slate-400 mb-2' }, '📍 Anlage-Adresse'),
        h('div', { class: 'grid grid-cols-1 md:grid-cols-3 gap-2' }, [
          h('div', { class: 'md:col-span-2' }, [
            h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'Straße + Nr'),
            h('input', { class: 'input', value: p.plant.address_street, onInput: (e) => set('address_street', e.target.value) }),
          ]),
          h('div', [
            h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'PLZ'),
            h('input', { class: 'input', value: p.plant.address_plz, onInput: (e) => set('address_plz', e.target.value) }),
          ]),
          h('div', [
            h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'Ort'),
            h('input', { class: 'input', value: p.plant.address_city, onInput: (e) => set('address_city', e.target.value) }),
          ]),
          h('div', [
            h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'Telefon'),
            h('input', { class: 'input', value: p.plant.phone, onInput: (e) => set('phone', e.target.value) }),
          ]),
          h('div', [
            h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'E-Mail'),
            h('input', { class: 'input', type: 'email', value: p.plant.email, onInput: (e) => set('email', e.target.value) }),
          ]),
          h('div', { class: 'md:col-span-3' }, [
            h('label', { class: 'block text-xs text-slate-500 mb-1' }, 'IBAN'),
            h('input', { class: 'input', value: p.plant.iban, placeholder: 'DE00 0000 0000 …', onInput: (e) => set('iban', e.target.value) }),
          ]),
        ]),
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
      h('div', { class: 'bg-slate-900 rounded-lg p-3 border border-slate-700' }, [
        h('div', { class: 'flex items-center justify-between mb-2' }, [
          h('h4', { class: 'text-xs font-semibold text-slate-400' }, 'Wechselrichter / Ladepunkte'),
          h('button', { type: 'button', onClick: addInverter, class: 'text-xs text-amber-400' }, '+ Hinzufügen'),
        ]),
        p.plant.inverters.map((inv, i) =>
          h('div', { class: 'grid grid-cols-1 md:grid-cols-5 gap-2 mb-2', key: i }, [
            h('input', { class: 'input', placeholder: 'Hersteller', value: inv.manufacturer, onInput: (e) => setInverter(i, 'manufacturer', e.target.value) }),
            h('input', { class: 'input', placeholder: 'Typ', value: inv.type, onInput: (e) => setInverter(i, 'type', e.target.value) }),
            h('input', { class: 'input', placeholder: 'kW', value: inv.kw, onInput: (e) => setInverter(i, 'kw', e.target.value) }),
            h('input', { class: 'input', placeholder: 'ZEREZ-ID', value: inv.zerez_id, onInput: (e) => setInverter(i, 'zerez_id', e.target.value) }),
            h('button', { type: 'button', onClick: () => removeInverter(i), class: 'text-slate-400 hover:text-red-400 text-sm' }, '🗑️'),
          ])
        ),
        p.plant.inverters.length === 0 ? h('div', { class: 'text-slate-500 text-xs' }, 'Kein Wechselrichter erfasst.') : null,
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

      // Notizen
      h('div', [
        h('label', { class: 'block text-sm text-slate-400 mb-1' }, 'Notizen'),
        h('textarea', { class: 'input', rows: 2, value: p.plant.notes, onInput: (e) => set('notes', e.target.value) }),
      ]),
    ])
  },
})

const form = reactive({
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

onMounted(() => {
  if (props.initial) {
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
          // Anlage-Adresse: aus Kundendaten vorbefuellen (optional ueberschreiben)
          address_street: p.address_street || props.initial.address_street || '',
          address_plz: p.address_plz || props.initial.address_plz || '',
          address_city: p.address_city || props.initial.address_city || '',
          phone: p.phone || props.initial.phone || '',
          email: p.email || props.initial.email || '',
          iban: p.iban || props.initial.iban || '',
          panels: p.panels || emptyPlant().panels,
          battery: p.battery || null,
          inverters: p.inverters || [],
        }))
      : []
  }
})

function addPlant() {
  form.plants.push(emptyPlant())
}

function removePlant(i) {
  form.plants.splice(i, 1)
}

function updatePlant(i, key, val) {
  form.plants[i][key] = val
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
    alert(`PV-Anlage(n) ohne Lageplan: ${pvWithout.map((p,i)=>`Anlage ${form.plants.indexOf(p)+1}`).join(', ')}. Bitte zuerst den Lageplan erstellen.`)
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
        // Anlage-Adresse (separate Felder)
        address_street: p.address_street || null,
        address_plz: p.address_plz || null,
        address_city: p.address_city || null,
        phone: p.phone || null,
        email: p.email || null,
        iban: p.iban || null,
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
        lageplan: p.lageplan || null,
        documents: p.documents || [],
      }))
    }
    const base = isInstaller() ? '/installer/customers' : '/admin/customers'
    if (props.initial) {
      await client.put(`${base}/${props.initial._id}`, payload)
    } else {
      await client.post(base, payload)
    }
    emit('saved')
  } catch (e) {
    alert('Speichern fehlgeschlagen: ' + e.message)
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
