<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <header v-if="ready">
      <div class="bg-slate-900 border-b border-slate-800 sticky top-0 z-10">
        <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <RouterLink to="/" class="flex items-center gap-2">
            <span class="text-xl">⚡</span>
            <span class="font-semibold">Amelanq Netz-Anmeldung</span>
          </RouterLink>
          <nav class="flex items-center gap-1">
            <RouterLink
              to="/admin/firmen"
              class="px-3 py-1.5 rounded-lg text-sm"
              :class="isRoute('admin-firmen') ? 'bg-slate-800 text-amber-400' : 'text-slate-400 hover:bg-slate-800'"
            >
              🏢 Firmen
            </RouterLink>
            <RouterLink
              to="/admin/kunden"
              class="px-3 py-1.5 rounded-lg text-sm"
              :class="isRoute('admin-kunden') ? 'bg-slate-800 text-amber-400' : 'text-slate-400 hover:bg-slate-800'"
            >
              👤 Kunden
            </RouterLink>
            <button @click="logout" class="ml-2 px-3 py-1.5 rounded-lg text-sm text-slate-400 hover:text-red-400">
              Abmelden
            </button>
          </nav>
        </div>
      </div>
      <main class="max-w-6xl mx-auto px-4 py-6">
        <RouterView />
      </main>
    </header>
    <div v-else class="min-h-screen flex items-center justify-center text-slate-400">Prüfe Anmeldestatus…</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import auth from '@/api/auth'

const router = useRouter()
const route = useRoute()
const ready = ref(false)

let unguard = null

onMounted(async () => {
  // Session direkt bei Mount pruefen. Kein Router.beforeEach -
  // der kollidiert mit dem zentralen beforeEnter des Routes und
  // haengt die App bei "Pruefe Anmeldestatus...".
  const user = await auth.checkSession()
  if (user) {
    ready.value = true
  } else {
    router.push({ name: 'admin-login' })
  }
})

function isRoute(name) {
  return route.name === name
}

async function logout() {
  // Session-Cookie serverseitig loeschen, dann hart neu laden.
  await auth.logout('/admin/login')
  window.location.assign('/admin/login')
}
</script>
