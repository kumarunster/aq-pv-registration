<template>
  <section class="mt-4 p-4 border border-slate-700 rounded-xl" @click.stop>
    <h3 class="font-semibold">Netzanmeldung vorbereiten</h3>
    <p class="text-sm text-slate-400 mt-1">Gespeicherte Daten prüfen und Entwurf anstoßen. Kein endgültiges Absenden.</p>
    <div class="flex flex-wrap gap-3 mt-3">
      <label>Anlage
        <select v-model="index" class="input" @change="reset">
          <option v-for="(p, i) in customer.plants" :key="i" :value="i" :disabled="p.anlagetyp !== 'pv'">{{ i + 1 }} · {{ p.anlagetyp }} · {{ p.kwp || '–' }} kWp</option>
        </select>
      </label>
      <label>Netzbetreiber
        <select v-model="provider" class="input" @change="reset">
          <option value="nrm">NRM</option><option value="enm">ENM</option>
          <option value="mainzer">Mainzer Netze</option><option value="enetz">e-netz Südhessen</option>
        </select>
      </label>
      <label>Ziel
        <select v-model="target" class="input" @change="reset">
          <option value="local">Lokal vorbereiten</option><option value="portal" :disabled="provider === 'mainzer'">Portalentwurf</option>
        </select>
      </label>
      <label v-if="target === 'portal' && ['nrm', 'enm'].includes(provider)">Aktuelle PV-Produkt-ID
        <input v-model.number="productId" type="number" min="1" class="input" @input="job = null" />
      </label>
    </div>
    <p class="text-amber-300 text-sm my-3">{{ scope }}</p>
    <button class="px-3 py-2 bg-slate-700 rounded-lg" :disabled="busy" @click="loadPreview">Gespeicherte Daten zur Prüfung laden</button>
    <template v-if="preview">
      <pre class="mt-3 text-xs whitespace-pre-wrap max-h-96 overflow-auto bg-slate-950 p-3 rounded-lg">{{ JSON.stringify(preview.snapshot, null, 2) }}</pre>
      <label class="block mt-3"><input v-model="checked" type="checkbox" @change="job = null" /> Ich habe Betreiber-, Standort- und Installationsdaten geprüft.</label>
      <label class="block mt-2"><input v-model="accepted" type="checkbox" @change="job = null" /> Ich bestätige den oben beschriebenen Umfang und den ausgewählten Netzbetreiber.</label>
      <label class="block mt-2">Prüfvermerk<input v-model="note" class="input w-full" maxlength="2000" @input="job = null" /></label>
      <button class="mt-3 px-3 py-2 bg-slate-700 rounded-lg" :disabled="busy || !checked || !accepted || note.trim().length < 3" @click="review">Prüfung speichern</button>
    </template>
    <div v-if="job" class="mt-3">
      <p>Status: {{ job.state }} · Vorgang {{ job.id.slice(0, 12) }}</p>
      <button v-if="job.state === 'reviewed'" class="mt-2 px-3 py-2 bg-amber-500 text-slate-950 rounded-lg font-semibold" :disabled="busy" @click="start">{{ target === 'local' ? 'Lokale Vorbereitung starten' : 'Portalentwurf anlegen' }}</button>
      <p v-if="job.state === 'draft_created'" class="text-green-300">{{ job.result?.storage === 'local' ? 'JSON lokal vorbereitet.' : 'Portalentwurf erstellt.' }} Nicht abgesendet.</p>
      <p v-if="['pending', 'uncertain'].includes(job.state)" class="text-amber-300">Ergebnis offen. Portal und Servicejournal manuell prüfen; nicht erneut anstoßen.</p>
    </div>
    <p v-if="error" role="alert" class="text-red-300 mt-3">{{ error }}</p>
    <button class="block text-sm text-slate-400 mt-3" :disabled="busy" @click="loadJobs">Bisherige Vorgänge laden</button>
    <ul class="text-sm text-slate-400"><li v-for="j in jobs" :key="j.id">{{ j.provider }} · {{ j.payload.target }} · {{ j.state }} · {{ j.reviewed_at }}</li></ul>
  </section>
</template>
<script setup>
import { ref, computed } from 'vue'
import client from '@/api/client'
const props = defineProps({ customer: { type: Object, required: true } })
const index = ref(Math.max(0, props.customer.plants.findIndex(p => p.anlagetyp === 'pv')))
const provider = ref('nrm'), target = ref('local'), productId = ref(null)
const preview = ref(null), checked = ref(false), accepted = ref(false), note = ref(''), job = ref(null), jobs = ref([]), busy = ref(false), error = ref('')
const base = computed(() => `/admin/registration/customers/${props.customer._id}/plants/${index.value}`)
const scope = computed(() => target.value === 'local' ? 'Nur lokale JSON-Vorbereitung. Es entsteht kein Antrag im Netzportal.' : ['nrm', 'enm'].includes(provider.value) ? 'Nur leerer Produktentwurf. Standort, Betreiber und technische Daten werden noch nicht übertragen.' : 'Nur initiale Strommeldung mit Standort und Bemerkung. Noch keine vollständige PV-Anmeldung.')
function reset() { preview.value = null; job.value = null; checked.value = false; accepted.value = false; jobs.value = []; error.value = ''; if (provider.value === 'mainzer') target.value = 'local' }
async function run(fn) { busy.value = true; error.value = ''; try { await fn() } catch (e) { error.value = e.response?.data?.detail || 'Aktion fehlgeschlagen. Bei Startfehlern Vorgangsstatus laden und vor erneutem Versuch prüfen.' } finally { busy.value = false } }
function loadPreview() { reset(); return run(async () => { preview.value = (await client.get(base.value + '/preview')).data }) }
function review() { return run(async () => { job.value = (await client.post(base.value + '/review', { provider: provider.value, target: target.value, product_id: productId.value || null, expected_hash: preview.value.snapshot_hash, data_checked: checked.value, scope_accepted: accepted.value, review_note: note.value.trim() })).data }) }
function start() { return run(async () => { const id = job.value.id; try { job.value = (await client.post(`/admin/registration/jobs/${id}/start`, null, { timeout: 240000 })).data } catch (e) { job.value = null; throw e } }) }
function loadJobs() { return run(async () => { jobs.value = (await client.get(base.value + '/jobs')).data }) }
</script>
