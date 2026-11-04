<template>
  <div class="rounded-lg border border-slate-700 bg-slate-900 p-3 space-y-2" data-testid="kataster-lookup" :aria-busy="loading">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <span class="text-sm font-semibold text-slate-200">Katasterdaten zur Anlage</span>
      <button type="button" data-testid="kataster-load" @click="$emit('load')"
        :disabled="busy || !address.complete"
        class="px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed">
        {{ loading ? 'Katasterdaten werden geladen…' : plant.kataster ? 'Karte & Grundstücksdaten neu laden' : 'Karte & Grundstücksdaten laden' }}
      </button>
    </div>
    <p class="text-xs text-slate-400">{{ address.text || 'Noch keine Anlagenadresse angegeben.' }}</p>
    <p v-if="!address.complete" class="text-xs text-amber-300">Bitte Straße mit Hausnummer, fünfstellige PLZ und Ort ergänzen.</p>
    <div role="status" aria-live="polite" class="flex flex-wrap gap-x-4 gap-y-1 text-xs">
      <span v-if="loading" class="text-blue-300">Adresse wird gesucht, Karte und Grundstücksdaten werden abgerufen…</span>
      <template v-else>
        <span :class="hasBackground ? 'text-green-400' : 'text-slate-400'">{{ hasBackground ? '✓ Hintergrundbild geladen' : 'Hintergrundbild noch nicht geladen' }}</span>
        <span :class="hasProperty ? 'text-green-400' : 'text-slate-400'">{{ hasProperty ? '✓ Grundstücksinfos gefunden' : 'Grundstücksinfos noch nicht gefunden' }}</span>
      </template>
    </div>
    <p v-if="message" class="text-xs text-amber-300">{{ message }}</p>
    <p v-if="error" role="alert" class="text-xs text-red-300">{{ error }}</p>
    <p v-if="notice" class="text-xs text-amber-300">{{ notice }}</p>
    <p v-if="plant.lageplan?.elements?.length" class="text-xs text-slate-400">Vorhandene Zeichnungen bleiben erhalten. Nach dem Laden die Ausrichtung im Lageplan prüfen.</p>
    <p class="text-[11px] text-slate-500">Kartenausschnitt: 60 Meter Breite. Änderungen werden mit „Speichern“ in der Anlage gesichert.</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { plantAddress, propertyFound, backgroundFound, katasterMessage } from '@/lib/kataster'
const props = defineProps({ plant: Object, customer: Object, loading: Boolean, busy: Boolean, error: String, notice: String })
defineEmits(['load'])
const address = computed(() => plantAddress(props.plant, props.customer))
const hasProperty = computed(() => propertyFound(props.plant, props.customer))
const hasBackground = computed(() => backgroundFound(props.plant, props.customer))
const message = computed(() => katasterMessage(props.plant, props.customer))
</script>
