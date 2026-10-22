<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
    <div class="max-w-2xl w-full mx-4 p-8 bg-slate-900 rounded-2xl shadow-xl border border-slate-800">
      <div class="flex items-center gap-3 mb-6">
        <div class="w-12 h-12 bg-amber-500 rounded-xl flex items-center justify-center text-2xl">⚡</div>
        <div>
          <h1 class="text-2xl font-bold">Amelanq Netz-Anmeldung</h1>
          <p class="text-slate-400 text-sm">PV-Anlagen · Wallboxen · Wärmepumpen</p>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <button
          v-for="item in menu"
          :key="item.route"
          @click="go(item.route)"
          class="group bg-slate-800 hover:bg-slate-750 rounded-xl p-5 text-left transition border border-slate-700 hover:border-amber-500/40"
        >
          <div class="text-2xl mb-2">{{ item.icon }}</div>
          <div class="font-semibold mb-1">{{ item.title }}</div>
          <div class="text-slate-400 text-sm">{{ item.desc }}</div>
        </button>
      </div>

      <div class="text-slate-500 text-sm">
        Status: <span :class="backendStatus ? 'text-emerald-400' : 'text-amber-400'">
          {{ backendStatus ? 'Backend online' : 'Backend nicht erreichbar' }}
        </span>
        <span v-if="schemaVersion !== null"> · Schema v{{ schemaVersion }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import client from '@/api/client'

const router = useRouter()
const backendStatus = ref(null)
const schemaVersion = ref(null)

const menu = [
  {
    icon: '🏢',
    title: 'Firmen',
    desc: 'Stammdaten, Kontakte, Signatur',
    route: '/admin/firmen',
  },
  {
    icon: '👤',
    title: 'Kunden & Anlagen',
    desc: 'Kunden, PV, Wallbox, Wärmepumpe',
    route: '/admin/kunden',
  },
]

function go(route) {
  router.push(route)
}

onMounted(async () => {
  try {
    const { data } = await client.get('/status')
    backendStatus.value = true
  } catch {
    backendStatus.value = false
  }
  try {
    const { data } = await client.get('/healthz')
    schemaVersion.value = data.schemaVersion
  } catch {}
})
</script>
