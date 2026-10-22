<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
    <div class="max-w-md w-full mx-4 p-8 bg-slate-900 rounded-2xl shadow-xl border border-slate-800">
      <h1 class="text-xl font-bold mb-6">Installer-Login</h1>
      <form @submit.prevent="doLogin" class="space-y-4">
        <div>
          <label class="block text-sm text-slate-400 mb-1">E-Mail</label>
          <input
            v-model="email"
            type="email"
            class="w-full bg-slate-800 rounded-lg px-4 py-2.5 border border-slate-700 focus:border-amber-500 focus:outline-none"
            placeholder="installer@amelanq.com"
            required
          />
        </div>
        <div>
          <label class="block text-sm text-slate-400 mb-1">Passwort</label>
          <input
            v-model="password"
            type="password"
            class="w-full bg-slate-800 rounded-lg px-4 py-2.5 border border-slate-700 focus:border-amber-500 focus:outline-none"
            required
          />
        </div>
        <div v-if="error" class="text-red-400 text-sm">{{ error }}</div>
        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg py-2.5 transition disabled:opacity-50"
        >
          {{ loading ? 'Anmelden…' : 'Anmelden' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import auth from '@/api/auth'

const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function doLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(email.value, password.value, '/installer/login')
    router.push('/installer')
  } catch (e) {
    const msg = e.response?.data?.ui?.messages?.find(m => m.type === 'error')?.text
    error.value = msg || 'Login fehlgeschlagen'
  } finally {
    loading.value = false
  }
}
</script>
