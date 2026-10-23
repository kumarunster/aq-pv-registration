import { reactive, ref, computed } from 'vue'
import { nanoid } from 'nanoid' // wir brauchen unique IDs; wir bauen sie selbst, nanoid nicht installiert

let counter = 0
function nextId() {
  counter += 1
  return `el-${Date.now()}-${counter}`
}

/**
 * Zentrales Datenmodell für den Lageplan-Editor.
 * Spiegelung: backend/src/routers/lageplan/schemas.py
 */
export function useLayoutStore() {
  const layout = reactive({
    title: 'Lageplan',
    background_image_url: null,
    background_image_width: null,
    background_image_height: null,
    elements: [],
    metadata: {},
  })

  const selectedId = ref(null)
  const activeTool = ref('select') // 'select' | 'rect' | 'hatching' | 'arrow' | 'text'

  const selectedElement = computed(() =>
    layout.elements.find((e) => e.id === selectedId.value) || null
  )

  function addElement(element) {
    const id = element.id || nextId()
    layout.elements.push({ ...element, id })
    selectedId.value = id
    return id
  }

  function removeElement(id) {
    const idx = layout.elements.findIndex((e) => e.id === id)
    if (idx >= 0) layout.elements.splice(idx, 1)
    if (selectedId.value === id) selectedId.value = null
  }

  function clearAll() {
    layout.elements = []
    selectedId.value = null
  }

  function setBackground(dataUrl, width, height) {
    layout.background_image_url = dataUrl
    layout.background_image_width = width
    layout.background_image_height = height
  }

  return {
    layout,
    selectedId,
    activeTool,
    selectedElement,
    addElement,
    removeElement,
    clearAll,
    setBackground,
  }
}
