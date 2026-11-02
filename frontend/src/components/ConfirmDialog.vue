<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[90] flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60" @click="$emit('cancel')"></div>
      <div
        class="relative bg-slate-900 border border-slate-700 rounded-xl p-5 w-full max-w-md mx-4 shadow-2xl"
        role="dialog"
        :aria-modal="true"
        aria-labelledby="confirm-title"
        @keydown.esc="$emit('cancel')"
      >
        <h3 id="confirm-title" class="text-lg font-semibold mb-2">{{ title }}</h3>
        <p class="text-sm text-slate-300 mb-5 whitespace-pre-line">{{ message }}</p>
        <div class="flex gap-2 justify-end">
          <button
            type="button"
            ref="cancelRef"
            @click="$emit('cancel')"
            class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm"
          >{{ cancelLabel }}</button>
          <button
            type="button"
            ref="confirmRef"
            @click="$emit('confirm')"
            :class="[
              'px-4 py-2 rounded-lg text-sm font-semibold',
              tone === 'danger'
                ? 'bg-red-600 hover:bg-red-500 text-white'
                : 'bg-amber-500 hover:bg-amber-400 text-slate-950',
            ]"
          >{{ confirmLabel }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: 'Sicher?' },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Ja' },
  cancelLabel: { type: String, default: 'Abbrechen' },
  tone: { type: String, default: 'default' }, // 'default' | 'danger'
})
const emit = defineEmits(['confirm', 'cancel'])

const confirmRef = ref(null)
const cancelRef = ref(null)

watch(
  () => props.open,
  async (open) => {
    if (open) {
      await nextTick()
      ;(confirmRef.value || cancelRef.value)?.focus()
    }
  }
)
</script>
