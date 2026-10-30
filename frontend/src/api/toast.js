import { reactive } from 'vue'

// Einfaches globales Toast-System ohne externe Dependencies.
// Aufruf: toast.success('...') / toast.error('...') / toast.info('...')
// Anzeige: <ToastContainer /> in App.vue
const state = reactive({ items: [] })
let nextId = 1

function push(type, message, duration = 4000) {
  const id = nextId++
  state.items.push({ id, type, message, duration })
  if (duration > 0) {
    setTimeout(() => {
      state.items = state.items.filter(t => t.id !== id)
    }, duration)
  }
}

const toast = {
  success: (msg, duration) => push('success', msg, duration),
  error: (msg, duration) => push('error', msg, duration ?? 6000),
  info: (msg, duration) => push('info', msg, duration),
  dismiss: (id) => {
    state.items = state.items.filter(t => t.id !== id)
  },
  state,
}

export default toast
