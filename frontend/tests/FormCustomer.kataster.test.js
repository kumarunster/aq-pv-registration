import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import FormCustomer from '@/components/admin/FormCustomer.vue'
import { loadKataster } from '@/api/kataster'
import client from '@/api/client'
vi.mock('@/api/client', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, zerezSearch: vi.fn() }))
vi.mock('@/api/kataster', () => ({ loadKataster: vi.fn(), katasterError: () => 'Dienst nicht erreichbar.' }))
vi.mock('@/api/toast', () => ({ default: { success: vi.fn(), info: vi.fn(), error: vi.fn() } }))
vi.mock('@/components/lageplan/LageplanEditor.vue', async () => {
 const { h } = await import('vue')
 return { default: { name: 'LageplanEditor', props: ['initialLayout'], setup(props, { expose }) { expose({ getLayout: () => props.initialLayout }); return () => h('div') } } }
})
const address = 'Im Schönenfelde 14, 21109 Hamburg'
const fetched = () => ({ result: { status: 'ok', grundstueck_status: 'ok', grundstuecke: [{ gemarkung: 'Wilhelmsburg', flur: null, flurstueck: '2798' }], bild: { status: 'ok', breite_meter: 60 } }, background: { dataUrl: 'data:image/png;base64,aGVsbG8=', width: 1600, height: 1340 }, imageError: '' })
let wrappers = []
async function form(mode = 'admin', plants = [{}]) {
 const w = mount(FormCustomer, { props: { mode, companies: [{ _id: 'company1', name: 'Firma' }], initial: { _id: 'customer1', firstname: 'Max', lastname: 'Mustermann', company_id: 'company1', address_street: 'Im Schönenfelde 14', address_plz: '21109', address_city: 'Hamburg', plants: plants.map(p => ({ anlagetyp: 'pv', ...p })) } }, global: { stubs: { teleport: true } } })
 wrappers.push(w); await w.get('#customer-tab-anlagen').trigger('click'); await w.get('tbody tr').trigger('click'); return w
}
beforeEach(() => { loadKataster.mockReset(); loadKataster.mockResolvedValue(fetched()); client.put.mockReset(); client.put.mockImplementation(async (_url, payload) => ({ data: { _id: 'customer1', ...payload } })) })
afterEach(() => { wrappers.forEach(w => w.unmount()); wrappers = [] })
describe('Anlagenformular Kataster', () => {
 it.each(['admin', 'installer'])('transfers and persists fields and background for %s', async (mode) => {
  const w = await form(mode); await w.get('[data-testid=kataster-load]').trigger('click'); await flushPromises()
  expect(loadKataster).toHaveBeenCalledWith(address, expect.objectContaining({ installer: mode === 'installer' }))
  expect(w.text()).toContain('✓ Grundstücksinfos gefunden'); expect(w.text()).toContain('✓ Hintergrundbild geladen'); expect(w.text()).toContain('✓ erfasst')
  await w.get('#plant-lageplan-edit').trigger('click')
  const editor = w.findComponent({ name: 'LageplanEditor' }); expect(editor.props('initialLayout').background_image_url).toBe(fetched().background.dataUrl)
  expect(editor.props('initialLayout').metadata.gemarkung).toBe('Wilhelmsburg')
  await w.get('#lageplan-dialog-close').trigger('click'); await w.get('#customer-form').trigger('submit'); await flushPromises()
  const [url, payload] = client.put.mock.calls[0]; expect(url).toBe(`/${mode}/customers/customer1`)
  expect(payload.plants[0]).toMatchObject({ gemarkung: 'Wilhelmsburg', flur: null, flurstueck: '2798', kataster: { hintergrund_uebernommen: true } })
  expect(payload.plants[0].lageplan.background_image_url).toBe(fetched().background.dataUrl)
 })
 it('uses a separate plant address', async () => {
  const w = await form('admin', [{ address_from_customer: false, address_street: 'Im Kreutzchen 32', address_plz: '56070', address_city: 'Koblenz' }]); await w.get('[data-testid=kataster-load]').trigger('click'); await flushPromises()
  expect(loadKataster).toHaveBeenCalledWith('Im Kreutzchen 32, 56070 Koblenz', expect.anything())
 })
 it('shows loading, prevents duplicate requests and blocks save until completion', async () => {
  let resolve; loadKataster.mockImplementation(() => new Promise(r => { resolve = r }))
  const w = await form(); await w.get('[data-testid=kataster-load]').trigger('click')
  expect(w.get('[data-testid=kataster-load]').attributes('disabled')).toBeDefined(); expect(w.get('#customer-form-save').attributes('disabled')).toBeDefined()
  expect(w.text()).toContain('Katasterdaten werden geladen'); await w.get('#customer-form').trigger('submit'); expect(client.put).not.toHaveBeenCalled()
  resolve(fetched()); await flushPromises(); expect(w.get('#customer-form-save').attributes('disabled')).toBeUndefined()
 })
 it('discards a response after changing the address in flight', async () => {
  let resolve; loadKataster.mockImplementation(() => new Promise(r => { resolve = r }))
  const w = await form(); await w.get('[data-testid=kataster-load]').trigger('click'); await w.get('#customer-tab-kunde').trigger('click'); await w.get('#cust-address-street').setValue('Andere Straße 1')
  resolve(fetched()); await flushPromises(); await w.get('#customer-tab-anlagen').trigger('click')
  expect(w.text()).toContain('während der Abfrage geändert'); expect(w.text()).not.toContain('✓ Grundstücksinfos gefunden'); expect(w.find('#plant-lageplan-edit').exists()).toBe(false)
 })
 it('shows a retryable error and preserves existing drawings', async () => {
  loadKataster.mockRejectedValue(new Error('offline')); const original = { title: 'Bestehend', elements: [{ id: 'panel1', type: 'rect', x: 3 }], metadata: {} }
  const w = await form('admin', [{ lageplan: original }]); await w.get('[data-testid=kataster-load]').trigger('click'); await flushPromises(); expect(w.get('[role=alert]').text()).toBe('Dienst nicht erreichbar.')
  await w.get('#plant-lageplan-edit').trigger('click'); expect(w.findComponent({ name: 'LageplanEditor' }).props('initialLayout').elements).toEqual(original.elements)
 })
 it('does not claim a mandatory plan for property-only results', async () => {
  loadKataster.mockResolvedValue({ ...fetched(), background: null, imageError: 'Bild nicht verfügbar.' }); const w = await form(); await w.get('[data-testid=kataster-load]').trigger('click'); await flushPromises()
  expect(w.text()).toContain('✓ Grundstücksinfos gefunden'); expect(w.text()).toContain('Lageplan fehlt'); expect(w.text()).not.toContain('✓ Hintergrundbild geladen')
 })
 it('retains verification after saving and reopening', async () => {
  const w = await form(); await w.get('[data-testid=kataster-load]').trigger('click'); await flushPromises(); await w.get('#customer-form').trigger('submit'); await flushPromises()
  const saved = client.put.mock.calls[0][1].plants[0]; w.unmount(); wrappers = []
  const reopened = await form('admin', [saved]); expect(reopened.text()).toContain('✓ Grundstücksinfos gefunden'); expect(reopened.text()).toContain('✓ Hintergrundbild geladen')
 })
 it('clears only the background confirmation when replacing the image in the editor', async () => {
  const w = await form(); await w.get('[data-testid=kataster-load]').trigger('click'); await flushPromises()
  await w.get('#plant-lageplan-edit').trigger('click')
  w.findComponent({ name: 'LageplanEditor' }).props('initialLayout').background_image_url = 'data:image/png;base64,bWFudWFs'
  await w.get('#lageplan-dialog-save').trigger('click')
  expect(w.text()).not.toContain('✓ Hintergrundbild geladen'); expect(w.text()).toContain('✓ Grundstücksinfos gefunden')
  await w.get('#customer-form').trigger('submit'); await flushPromises()
  expect(client.put.mock.calls[0][1].plants[0].kataster.hintergrund_uebernommen).toBe(false)
 })
 it('does not permit a request with an incomplete independent plant address', async () => {
  const w = await form('admin', [{ address_from_customer: false, address_street: 'Straße 1', address_plz: '', address_city: '' }])
  expect(w.get('[data-testid=kataster-load]').attributes('disabled')).toBeDefined()
  expect(w.text()).toContain('fünfstellige PLZ')
  expect(loadKataster).not.toHaveBeenCalled()
 })

})
