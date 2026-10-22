<template>
  <form @submit.prevent="save" class="bg-slate-900 rounded-xl p-5 border border-slate-800 space-y-4 mb-4">
    <h2 class="font-semibold">{{ initial ? 'Firma bearbeiten' : 'Neue Firma anlegen' }}</h2>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label class="block text-sm text-slate-400 mb-1">Name *</label>
        <input v-model="form.name" class="input" required />
      </div>
      <div>
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
        <label class="block text-sm text-slate-400 mb-1">Kontakt</label>
        <input v-model="form.contact" class="input" />
      </div>
      <div>
        <label class="block text-sm text-slate-400 mb-1">Telefon</label>
        <input v-model="form.phone" class="input" />
      </div>
      <div>
        <label class="block text-sm text-slate-400 mb-1">E-Mail</label>
        <input v-model="form.email" type="email" class="input" />
      </div>
      <div>
        <label class="block text-sm text-slate-400 mb-1">Installer-ID</label>
        <input v-model="form.installer_id" class="input" />
      </div>
      <div class="md:col-span-2">
        <label class="block text-sm text-slate-400 mb-1">Ursprung (vorheriger Netzbetreiber)</label>
        <input v-model="form.installer_origin_vnb" class="input" />
      </div>
      <div class="md:col-span-2">
        <label class="block text-sm text-slate-400 mb-1">Signatur-URL</label>
        <input v-model="form.signature_url" class="input" placeholder="https://…" />
      </div>
    </div>

    <div class="flex gap-2">
      <button type="submit" :disabled="saving" class="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-sm disabled:opacity-50">
        {{ saving ? 'Speichert…' : (initial ? 'Speichern' : 'Anlegen') }}
      </button>
      <button type="button" @click="$emit('cancel')" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm">
        Abbrechen
      </button>
    </div>
  </form>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import client from '@/api/client'

const props = defineProps(['companies', 'initial'])
const emit = defineEmits(['saved', 'cancel'])

const empty = {
  name: '',
  address_street: '',
  address_plz: '',
  address_city: '',
  contact: '',
  phone: '',
  email: '',
  installer_id: '',
  installer_origin_vnb: '',
  signature_url: '',
}

const form = ref({ ...empty })
const saving = ref(false)

onMounted(() => {
  if (props.initial) {
    form.value = {
      ...empty,
      ...props.initial,
    }
  }
})

async function save() {
  saving.value = true
  try {
    const payload = { ...form.value }
    if (props.initial) {
      await client.put(`/admin/companies/${props.initial._id}`, payload)
    } else {
      await client.post('/admin/companies', payload)
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
