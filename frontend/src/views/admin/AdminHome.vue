<template>
  <div class="max-w-3xl mx-auto">
    <h1 class="text-xl font-bold mb-4">Willkommen im Admin</h1>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="bg-slate-900 rounded-xl p-5 border border-slate-800">
        <h2 class="font-semibold mb-2">🏢 Firmen</h2>
        <p class="text-slate-400 text-sm mb-4">Stammdaten, Kontakte, Signatur-URL, Installer-ID</p>
        <RouterLink to="/admin/firmen" class="text-amber-400 text-sm">Öffnen →</RouterLink>
      </div>
      <div class="bg-slate-900 rounded-xl p-5 border border-slate-800">
        <h2 class="font-semibold mb-2">👤 Kunden & Anlagen</h2>
        <p class="text-slate-400 text-sm mb-4">Kunden anlegen, PV / Wallbox / Wärmepumpe erfassen</p>
        <RouterLink to="/admin/kunden" class="text-amber-400 text-sm">Öffnen →</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>
