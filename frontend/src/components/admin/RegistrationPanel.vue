<template>
  <section class="mt-4 p-4 border border-slate-700 rounded-xl" @click.stop>
    <h3 class="font-semibold">Netzanmeldung · Anlage {{ plantIndex + 1 }}</h3>
    <p class="text-sm text-slate-400 mt-1">Gespeicherte Daten prüfen und Entwurf anstoßen. Kein endgültiges Absenden.</p>
    <p class="text-xs text-slate-400 mt-2">Zur Ermittlung wird ausschließlich die gespeicherte Anlagenadresse an VNBdigital übermittelt.</p>
    <div class="flex flex-wrap gap-3 mt-3">
      <div>
        <span class="text-sm text-slate-400">Automatisch ermittelter Netzbetreiber</span>
        <p v-if="operator">{{ operator.name }}</p>
        <p v-else>{{ busy ? 'Ermittlung über die Anlagenadresse läuft…' : 'Noch kein eindeutiger Treffer.' }}</p>
        <a v-if="operator" :href="operator.url" target="_blank" rel="noopener noreferrer" class="text-sm text-amber-400">Ergebnis auf VNBdigital</a>
      </div>
      <label>Ziel
        <select v-model="target" class="input" :disabled="busy || !resolved" @change="resetApproval">
          <option value="local">Lokal vorbereiten</option><option value="portal" :disabled="provider === 'mainzer'">Portalentwurf</option>
        </select>
      </label>
      <label v-if="target === 'portal' && ['nrm', 'enm'].includes(provider)">Aktuelle PV-Produkt-ID
        <input :disabled="busy" v-model.number="productId" type="number" min="1" class="input" @input="resetApproval" />
      </label>
    </div>
    <p class="text-amber-300 text-sm my-3">{{ scope }}</p>
    <button type="button" class="px-3 py-2 bg-slate-700 rounded-lg" :disabled="busy" @click="loadPreview">Anlagenadresse und Daten erneut prüfen</button>
    <p v-if="lookupMessage" :role="preview?.network_operator?.status === 'unsupported' ? 'alert' : 'status'" class="text-amber-300 mt-3">{{ lookupMessage }}</p>
    <p v-if="preview?.network_operator?.location" class="text-sm text-slate-400 mt-2">Geprüfte Adresse: {{ preview.network_operator.location.title }} · Niederspannung · Quelle: VNBdigital</p>
    <template v-if="preview && resolved">
      <pre class="mt-3 text-xs whitespace-pre-wrap max-h-96 overflow-auto bg-slate-950 p-3 rounded-lg">{{ JSON.stringify(preview.snapshot, null, 2) }}</pre>
      <label class="block mt-3"><input :disabled="busy" v-model="checked" type="checkbox" @change="job = null" /> Ich habe Betreiber-, Standort- und Installationsdaten geprüft.</label>
      <label class="block mt-2"><input :disabled="busy" v-model="accepted" type="checkbox" @change="job = null" /> Ich bestätige den oben beschriebenen Umfang und den ermittelten Netzbetreiber.</label>
      <label class="block mt-2">Prüfvermerk<input :disabled="busy" v-model="note" class="input w-full" maxlength="2000" @input="resetApproval" /></label>
      <button type="button" class="mt-3 px-3 py-2 bg-slate-700 rounded-lg" :disabled="busy || !checked || !accepted || note.trim().length < 3" @click="review">Prüfung speichern</button>
    </template>
    <div v-if="job" class="mt-3">
      <p>Status: {{ job.state }} · Vorgang {{ job.id.slice(0, 12) }}</p>
      <button type="button" v-if="job.state === 'reviewed'" class="mt-2 px-3 py-2 bg-amber-500 text-slate-950 rounded-lg font-semibold" :disabled="busy" @click="start">{{ target === 'local' ? 'Lokale Vorbereitung starten' : 'Portalentwurf anlegen' }}</button>
      <p v-if="job.state === 'draft_created'" class="text-green-300">{{ job.result?.storage === 'local' ? 'JSON lokal vorbereitet.' : 'Portalentwurf erstellt.' }} Nicht abgesendet.</p>
      <p v-if="['pending', 'uncertain'].includes(job.state)" class="text-amber-300">Ergebnis offen. Portal und Servicejournal manuell prüfen; nicht erneut anstoßen.</p>
    </div>
    <p v-if="error" role="alert" class="text-red-300 mt-3">{{ error }}</p>
    <button type="button" class="block text-sm text-slate-400 mt-3" :disabled="busy" @click="loadJobs">Bisherige Vorgänge laden</button>
    <ul class="text-sm text-slate-400"><li v-for="j in jobs" :key="j.id">{{ j.provider }} · {{ j.payload.target }} · {{ j.state }} · {{ j.reviewed_at }}</li></ul>
  </section>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import client from '@/api/client'
const props = defineProps({ customerId: { type: String, required: true }, plantIndex: { type: Number, required: true } })
const target = ref('local'), productId = ref(null)
const preview = ref(null), checked = ref(false), accepted = ref(false), note = ref(''), job = ref(null), jobs = ref([]), busy = ref(false), error = ref('')
const base = computed(() => `/admin/registration/customers/${props.customerId}/plants/${props.plantIndex}`)
const provider = computed(() => preview.value?.network_operator?.provider)
const operator = computed(() => preview.value?.network_operator?.operator)
const resolved = computed(() => preview.value?.network_operator?.status === 'resolved')
const lookupMessage = computed(() => ({
  not_found: 'Kein genauer Adresstreffer mit zuständigem Niederspannungsnetzbetreiber. Bitte Anlagenadresse prüfen.',
  ambiguous_address: 'Die Anlagenadresse ist nicht eindeutig. Bitte Adresse präzisieren; es wird kein Betreiber geraten.',
  ambiguous_operator: 'Mehrere Niederspannungsnetzbetreiber gefunden. Vor der Anmeldung muss die Zuordnung geklärt werden.',
  unsupported: `Der Netzbetreiber „${operator.value?.name || 'Unbekannt'}“ ist noch nicht im System aufgenommen. Bitte lassen Sie diesen Netzbetreiber zuerst im System aufnehmen. Bis dahin kann die Netzanmeldung nicht gestartet werden.`,
}[preview.value?.network_operator?.status] || ''))
const scope = computed(() => target.value === 'local' ? 'Nur lokale JSON-Vorbereitung. Es entsteht kein Antrag im Netzportal.' : ['nrm', 'enm'].includes(provider.value) ? 'Nur leerer Produktentwurf. Standort, Betreiber und technische Daten werden noch nicht übertragen.' : 'Nur initiale Strommeldung mit Standort und Bemerkung. Noch keine vollständige PV-Anmeldung.')
function resetApproval() { job.value = null; checked.value = false; accepted.value = false; error.value = '' }
async function run(fn) { busy.value = true; error.value = ''; try { await fn() } catch (e) { error.value = e.response?.data?.detail || 'Aktion fehlgeschlagen. Bei Startfehlern Vorgangsstatus laden und vor erneutem Versuch prüfen.' } finally { busy.value = false } }
function loadPreview() { resetApproval(); preview.value = null; return run(async () => {
  preview.value = (await client.get(base.value + '/preview', { timeout: 120000 })).data
  if (provider.value === 'mainzer') target.value = 'local'
}) }
function review() { return run(async () => { job.value = (await client.post(base.value + '/review', {
  target: target.value, product_id: productId.value || null, expected_hash: preview.value.snapshot_hash,
  expected_operator_id: operator.value.id, data_checked: checked.value, scope_accepted: accepted.value, review_note: note.value.trim()
}, { timeout: 120000 })).data }) }
function start() { return run(async () => { const id = job.value.id; try { job.value = (await client.post(`/admin/registration/jobs/${id}/start`, null, { timeout: 240000 })).data } catch (e) { job.value = null; throw e } }) }
function loadJobs() { return run(async () => { jobs.value = (await client.get(base.value + '/jobs')).data }) }
onMounted(loadPreview)
</script>
