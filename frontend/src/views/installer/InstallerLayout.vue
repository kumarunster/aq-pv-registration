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
              to="/installer/kunden"
              class="px-3 py-1.5 rounded-lg text-sm"
              :class="isRoute('installer-kunden') ? 'bg-slate-800 text-amber-400' : 'text-slate-400 hover:bg-slate-800'"
            >
              👤 Meine Kunden
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
import { ref, onBeforeMount, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import auth from '@/api/auth'

const router = useRouter()
const route = useRoute()
const ready = ref(false)

let unguard = null

onBeforeMount(() => {
  // EIGENER Guard: Prüft die Session immer, bevor die Seite gerendert wird.
  // Der zentrale beforeEnter reicht NICHT, weil die Browser-Zurück-Taste
  // aus dem BFCache kommt und den Guard überspringt. Der eigene Guard
  // läuft dagegen bei jedem Route-Event - auch beim Zurück-Klicken.
  unguard = router.beforeEach(async (to) => {
    if (to.meta.public) { ready.value = true; return }
    const user = await auth.checkSession()
    if (!user) { ready.value = false; return { name: 'installer-login' } }
    ready.value = true
  })
})

onBeforeUnmount(() => { if (unguard) unguard() })

function isRoute(name) {
  return route.name === name
}

async function logout() {
  // Session-Cookie serverseitig loeschen, dann hart neu laden.
  await auth.logout('/installer/login')
  window.location.assign('/installer/login')
}
</script>
