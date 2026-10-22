<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <header class="bg-slate-900 border-b border-slate-800 sticky top-0 z-10">
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
    </header>
    <main class="max-w-6xl mx-auto px-4 py-6">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import auth from '@/api/auth'

const router = useRouter()
const route = useRoute()

function isRoute(name) {
  return route.name === name
}

async function logout() {
  // Serverseitig den Kratos-Session-Cookie loeschen.
  // Der Nginx-Endpoint /logout setzt den Cookie mit Max-Age=0 zurueck
  // (ersetzt den HttpOnly-Cookie im Browser) und leitet dann zur Login-Seite
  // zurueck. Danach hart neu laden, damit der Guard die neue Session-Abfrage
  // mit dem geleerten Cookie macht.
  await fetch('/logout', { method: 'GET', credentials: 'same-origin' })
  // hart neu laden (window.location.assign): der alte Vue-Routerguard und
  // jeder zustandsbehaftete Client (der noch "angemeldet" glaubt) werden
  // mit dem neuen Dokument ersetzt.
  window.location.assign('/installer/login')
}
</script>
