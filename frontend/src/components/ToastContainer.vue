<template>
  <Teleport to="body">
    <div class="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm" v-if="toast.state.items.length">
      <div
        v-for="t in toast.state.items"
        :key="t.id"
        class="flex items-start gap-2 px-4 py-3 rounded-xl shadow-lg border text-sm animate-[toast-in_.2s_ease-out] "
        :class="[
          t.type === 'success' ? 'bg-emerald-900/90 border-emerald-700 text-emerald-100' : '',
          t.type === 'error' ? 'bg-red-900/90 border-red-700 text-red-100' : '',
          t.type === 'info' ? 'bg-slate-800/95 border-slate-600 text-slate-100' : '',
        ]"
        role="status"
      >
        <span class="text-base leading-none mt-0.5">
          {{ t.type === 'success' ? '✅' : t.type === 'error' ? '❌' : 'ℹ️' }}
        </span>
        <span class="flex-1 break-words">{{ t.message }}</span>
        <button
          type="button"
          class="text-slate-400 hover:text-white text-xs mt-0.5"
          @click="toast.dismiss(t.id)"
        >✕</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import toast from '@/api/toast'
</script>

<style>
@keyframes toast-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
