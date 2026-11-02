<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold">🏢 Firmen</h1>
      <button
        v-if="!showForm"
        @click="openNew"
        class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-sm">
        + Neue Firma
      </button>
    </div>

    <!-- Formular -->
    <FormCompany v-if="showForm" :companies="[]" :initial="editing || null" @saved="onSaved" @cancel="closeForm" @dirty="onDirty" />

    <!-- Liste -->
    <div v-if="!showForm" class="space-y-3">
      <div v-if="loading" class="text-slate-400 text-sm">Lade…</div>
      <div v-else-if="loadError" class="bg-red-900/40 border border-red-700 rounded-xl p-4 text-sm text-red-300 flex items-center justify-between">
        <span>⚠️ Firmen laden fehlgeschlagen: {{ loadError }}</span>
        <button @click="load" class="px-3 py-1.5 bg-red-700 hover:bg-red-600 text-white rounded-lg text-sm">Retry</button>
      </div>
      <div v-else-if="companies.length === 0" class="bg-slate-900 rounded-xl p-6 text-center text-slate-400">
        Noch keine Firmen angelegt.
      </div>
      <div v-for="c in companies" :key="c._id" class="bg-slate-900 rounded-xl p-4 border border-slate-800">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="font-semibold text-lg">{{ c.name }}</h3>
            <p class="text-slate-400 text-sm mt-1">
              {{ c.address_street }}, {{ c.address_plz }} {{ c.address_city }}
            </p>
            <p v-if="c.contact" class="text-slate-400 text-sm">
              Kontakt: {{ c.contact }} · {{ c.phone }} · {{ c.email }}
            </p>
            <div v-if="c.installer_id || c.installer_origin_vnb" class="text-slate-500 text-xs mt-2">
              Installer: <span class="text-slate-400">{{ c.installer_id || '–' }}</span>
              <span v-if="c.installer_origin_vnb"> · Ursprung: {{ c.installer_origin_vnb }}</span>
            </div>
            <div v-if="c.signature_url" class="text-slate-500 text-xs mt-1">
              <a :href="c.signature_url" target="_blank" class="text-amber-400 hover:underline">Signatur ansehen</a>
            </div>
            <!-- P2-10: Kunden/Anlagen-Zusammenfassung -->
            <div v-if="stats[c._id]" class="text-slate-400 text-xs mt-2">
              👥 {{ stats[c._id].customers }} Kunde{{ stats[c._id].customers === 1 ? '' : 'n' }} · 🔌 {{ stats[c._id].plants }} Anlage{{ stats[c._id].plants === 1 ? '' : 'n' }}
            </div>
          </div>
          <div class="flex gap-2">
            <button @click="editCompany(c)" class="text-slate-400 hover:text-amber-400 text-sm px-2">✏️ Bearbeiten</button>
            <button @click="deleteCompany(c)" class="text-slate-400 hover:text-red-400 text-sm px-2">🗑️</button>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :open="confirmState.open"
      title="Firma löschen"
      :message="`Firma „${confirmState.company?.name || ''}“ wirklich löschen?`"
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
import client from '@/api/client'
import FormCompany from '@/components/admin/FormCompany.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import toast from '@/api/toast'
import { onBeforeRouteLeave, useRouter } from 'vue-router'

const companies = ref([])
const stats = ref({})
const loading = ref(true)
const loadError = ref(null)
const showForm = ref(false)
const editing = ref(null)
const confirmState = reactive({ open: false, company: null })

// TASK-001: Dirty-Data-Guard (beforeunload + interne Navigation)
const router = useRouter()
const formDirty = ref(false)
const dirtyDialog = reactive({ open: false, message: '', action: null })

onMounted(load)

async function load() {
  loading.value = true
  loadError.value = null
  try {
    const { data } = await client.get('/admin/companies')
    companies.value = data
    // P2-10: Kunden/Anlagen-Zusammenfassung nachladen
    try {
      const s = await client.get('/admin/companies/stats')
      stats.value = s.data
    } catch { stats.value = {} }
  } catch (e) {
    console.error('Firmen laden fehlgeschlagen', e)
    loadError.value = e.message || 'Unbekannter Fehler'
  } finally {
    loading.value = false
  }
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

function editCompany(c) {
  editing.value = c
  showForm.value = true
}

function onSaved() {
  formDirty.value = false
  showForm.value = false
  editing.value = null
  load()
}

function deleteCompany(c) {
  confirmState.company = c
  confirmState.open = true
}

async function doDelete() {
  const c = confirmState.company
  confirmState.open = false
  confirmState.company = null
  if (!c) return
  try {
    await client.delete(`/admin/companies/${c._id}`)
    toast.success('Firma gelöscht')
    await load()
  } catch (e) {
    toast.error('Löschen fehlgeschlagen: ' + e.message)
  }
}
</script>
