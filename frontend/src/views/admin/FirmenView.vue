<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold">🏢 Firmen</h1>
      <button
        v-if="!showForm"
        @click="showForm = true"
        class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-sm">
        + Neue Firma
      </button>
    </div>

    <!-- Formular -->
    <FormCompany v-if="showForm" :companies="[]" :initial="null" @saved="onSaved" @cancel="showForm = false" />

    <!-- Liste -->
    <div v-if="!showForm" class="space-y-3">
      <div v-if="loading" class="text-slate-400 text-sm">Lade…</div>
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
          </div>
          <div class="flex gap-2">
            <button @click="editCompany(c)" class="text-slate-400 hover:text-amber-400 text-sm px-2">✏️ Bearbeiten</button>
            <button @click="deleteCompany(c)" class="text-slate-400 hover:text-red-400 text-sm px-2">🗑️</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import client from '@/api/client'
import FormCompany from '@/components/admin/FormCompany.vue'

const companies = ref([])
const loading = ref(true)
const showForm = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/admin/companies')
    companies.value = data
  } catch (e) {
    console.error('Firmen laden fehlgeschlagen', e)
  } finally {
    loading.value = false
  }
}

function editCompany(c) {
  showForm.value = true
  // Formular zeigt sich mit initial
  // (hier wird showForm auf true gesetzt, Formular liest initial aus dem Prop)
}

async function deleteCompany(c) {
  if (!confirm(`Firma "${c.name}" wirklich löschen?`)) return
  try {
    await client.delete(`/admin/companies/${c._id}`)
    await load()
  } catch (e) {
    alert('Löschen fehlgeschlagen: ' + e.message)
  }
}

function onSaved() {
  showForm.value = false
  load()
}
</script>
