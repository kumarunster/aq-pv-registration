import { describe, expect, it } from 'vitest'
import { plantAddress, propertyFound, katasterStale, buildKatasterUpdate, backgroundFound } from '../src/lib/kataster'
const customer = { address_street: 'Im Schönenfelde 14', address_plz: '21109', address_city: 'Hamburg' }
const address = 'Im Schönenfelde 14, 21109 Hamburg'
const result = { status: 'ok', grundstueck_status: 'ok', grundstuecke: [{ gemarkung: 'Wilhelmsburg', flur: null, flurstueck: '2798' }], bild: { status: 'ok', breite_meter: 60 }, quellenvermerk: ['Amtlicher Dienst'] }
const image = { dataUrl: 'data:image/png;base64,aGVsbG8=', width: 1600, height: 1340 }
describe('Katasteruebernahme', () => {
 it('uses customer or independent plant address', () => {
  expect(plantAddress({ address_from_customer: true }, customer).text).toBe(address)
  expect(plantAddress({ ...customer, address_from_customer: false }, {}).text).toBe(address)
  expect(plantAddress({ ...customer, address_from_customer: false, address_plz: '2110' }, {}).complete).toBe(false)
 })
 it('clears stale flur, transfers data and creates self-contained background', () => {
  const plant = buildKatasterUpdate({ flur: '16' }, result, image, address)
  expect(plant.flur).toBe(''); expect(plant.gemarkung).toBe('Wilhelmsburg')
  expect(plant.lageplan.background_image_url).toBe(image.dataUrl)
  expect(plant.lageplan.metadata.kataster.quelle).toEqual(['Amtlicher Dienst'])
  expect(propertyFound(plant, customer)).toBe(true); expect(backgroundFound(plant, customer)).toBe(true)
 })
 it('preserves drawings and metadata without mutating the prior plan', () => {
  const plant = { lageplan: { title: 'Mein Plan', elements: [{ id: 'panel', x: 45 }], metadata: { custom: 'keep' } } }
  const next = buildKatasterUpdate(plant, result, image, address)
  expect(next.lageplan.elements).toEqual(plant.lageplan.elements)
  expect(next.lageplan.metadata.custom).toBe('keep')
  expect(plant.lageplan.background_image_url).toBeUndefined()
 })
 it('does not create an empty mandatory plan for property-only results', () => expect(buildKatasterUpdate({}, result, null, address).lageplan).toBeUndefined())
 it('does not transfer ambiguous or missing property data', () => {
  for (const status of ['mehrdeutig', 'grenznah', 'zugang_erforderlich', 'nicht_verfuegbar']) expect(buildKatasterUpdate({}, { ...result, grundstueck_status: status }, image, address).gemarkung).toBeUndefined()
  expect(buildKatasterUpdate({}, { ...result, grundstuecke: [...result.grundstuecke, ...result.grundstuecke] }, image, address).kataster.grundstueck_status).toBe('unvollstaendig')
 })
 it('invalidates verification after address or property changes', () => {
  const plant = buildKatasterUpdate({}, result, image, address)
  expect(katasterStale(plant, { ...customer, address_street: 'Andere Straße 1' })).toBe(true)
  expect(propertyFound(plant, { ...customer, address_street: 'Andere Straße 1' })).toBe(false)
  plant.flurstueck = '999'; expect(propertyFound(plant, customer)).toBe(false)
 })
})
