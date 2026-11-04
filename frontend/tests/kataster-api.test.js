import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import client from '@/api/client'
import { loadKataster } from '@/api/kataster'
vi.mock('@/api/client', () => ({ default: { get: vi.fn(), post: vi.fn() } }))
const id = 'a'.repeat(32)
beforeEach(() => {
 client.post.mockReset(); client.get.mockReset()
 vi.stubGlobal('Image', class { naturalWidth = 1600; naturalHeight = 1340; set src(value) { this.url = value; queueMicrotask(() => this.onload()) } })
})
afterEach(() => vi.unstubAllGlobals())
it.each(['admin', 'installer'])('uses only the authenticated %s relay and a long timeout', async (role) => {
 const path = `/api/${role}/liegenschaftskarte/ergebnisse/${id}/karte.png`
 client.post.mockResolvedValue({ data: { dateien: { bild: path } } })
 client.get.mockResolvedValue({ data: new Blob(['PNG'], { type: 'image/png' }) })
 const { background } = await loadKataster('Beispielstraße 1, 12345 Ort', { installer: role === 'installer' })
 expect(client.post).toHaveBeenCalledWith(`/${role}/liegenschaftskarte/auszug`, { adresse: 'Beispielstraße 1, 12345 Ort', breite_meter: 60, nur_amtlich: true }, expect.objectContaining({ timeout: 330000 }))
 expect(client.get).toHaveBeenCalledWith(path.slice(4), expect.objectContaining({ responseType: 'blob' }))
 expect(background.dataUrl).toMatch(/^data:image\/png;base64,/)
 expect(background.width).toBe(1600)
})
it.each([`https://evil/ergebnisse/${id}/karte.png`, `/api/installer/liegenschaftskarte/ergebnisse/${id}/karte.png`, '/api/admin/liegenschaftskarte/ergebnisse/../../file'])('does not download an untrusted or wrong-role URL: %s', async (path) => {
 client.post.mockResolvedValue({ data: { dateien: { bild: path } } })
 const r = await loadKataster('Beispielstraße 1, 12345 Ort')
 expect(client.get).not.toHaveBeenCalled(); expect(r.background).toBeNull(); expect(r.imageError).toBeTruthy()
})
it('retains property results if the image download fails', async () => {
 const result = { grundstuecke: [{ gemarkung: 'Beispiel' }], dateien: { bild: `/api/admin/liegenschaftskarte/ergebnisse/${id}/karte.png` } }
 client.post.mockResolvedValue({ data: result }); client.get.mockRejectedValue(new Error('offline'))
 const r = await loadKataster('Beispielstraße 1, 12345 Ort')
 expect(r.result).toEqual(result); expect(r.background).toBeNull(); expect(r.imageError).toBeTruthy()
})
it('preserves aborts instead of applying partial stale results', async () => {
 const controller = new AbortController()
 client.post.mockResolvedValue({ data: { dateien: { bild: `/api/admin/liegenschaftskarte/ergebnisse/${id}/karte.png` } } })
 client.get.mockImplementation(() => { controller.abort(); throw new Error('cancelled') })
 await expect(loadKataster('Beispielstraße 1, 12345 Ort', { signal: controller.signal })).rejects.toThrow('cancelled')
})
