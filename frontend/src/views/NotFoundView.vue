<template>
  <div class="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center">
    <div class="text-center">
      <h1 class="text-5xl font-bold mb-4">404</h1>
      <p class="text-slate-400">Seite nicht gefunden.</p>
      <RouterLink to="/" class="text-sky-400 underline">Zum Start</RouterLink>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>
