/** Plant-specific cadastral data and address freshness, independent of UI/network. */
export function plantAddress(plant, customer) {
  const source = plant?.address_from_customer !== false ? customer : plant
  const street = String(source?.address_street || '').trim()
  const postcode = String(source?.address_plz || '').trim()
  const city = String(source?.address_city || '').trim()
  return { complete: Boolean(street && /^\d{5}$/.test(postcode) && city),
    text: [street, [postcode, city].filter(Boolean).join(' ')].filter(Boolean).join(', ') }
}

export const addressKey = (value) => String(value || '').trim().replace(/\s+/g, ' ').toLocaleLowerCase('de')
const field = (value) => String(value ?? '').trim()

export function propertyFound(plant, customer) {
  const k = plant?.kataster
  return Boolean(k?.grundstueck_status === 'ok' && k.gemarkung && k.flurstueck &&
    addressKey(k.adresse) === addressKey(plantAddress(plant, customer).text) &&
    ['gemarkung', 'flur', 'flurstueck'].every((key) => field(k[key]) === field(plant[key])))
}

export function katasterStale(plant, customer) {
  return Boolean(plant?.kataster && addressKey(plant.kataster.adresse) !== addressKey(plantAddress(plant, customer).text))
}

export function backgroundFound(plant, customer) {
  return Boolean(plant?.kataster?.hintergrund_uebernommen && plant?.lageplan?.background_image_url && !katasterStale(plant, customer))
}

export function buildKatasterUpdate(plant, result, background, adresse) {
  // Only one unambiguous, sufficiently identified parcel is eligible for transfer.
  const parcel = result.grundstueck_status === 'ok' && result.grundstuecke?.length === 1 &&
    result.grundstuecke[0].gemarkung && result.grundstuecke[0].flurstueck ? result.grundstuecke[0] : null
  const update = {}
  if (parcel) {
    update.gemarkung = field(parcel.gemarkung)
    update.flur = field(parcel.flur) // Hamburg: null -> empty, never invent a flur.
    update.flurstueck = field(parcel.flurstueck)
  }
  update.kataster = {
    adresse, abgerufen_am: result.abgerufen_am || new Date().toISOString(),
    grundstueck_status: parcel ? 'ok' : (result.grundstueck_status === 'ok' ? 'unvollstaendig' : result.grundstueck_status || 'nicht_verfuegbar'),
    bild_status: background ? result.bild?.status || 'ok' : 'nicht_verfuegbar',
    hintergrund_uebernommen: Boolean(background),
    gemarkung: parcel ? field(parcel.gemarkung) : null,
    flur: parcel ? field(parcel.flur) || null : null,
    flurstueck: parcel ? field(parcel.flurstueck) : null,
    flurstueckskennzeichen: parcel?.flurstueckskennzeichen || null,
    amtliche_flaeche_m2: parcel?.amtliche_flaeche_m2 ?? null,
  }
  if (background || plant.lageplan) {
    const previous = plant.lageplan ? JSON.parse(JSON.stringify(plant.lageplan)) : { title: 'Lageplan', elements: [], metadata: {} }
    update.lageplan = {
      ...previous,
      ...(background ? {
        background_image_url: background.dataUrl,
        background_image_width: background.width,
        background_image_height: background.height,
      } : {}),
      metadata: {
        ...previous.metadata, adresse,
        gemarkung: update.gemarkung ?? plant.gemarkung ?? '',
        flur: update.flur ?? plant.flur ?? '',
        flurstueck: update.flurstueck ?? plant.flurstueck ?? '',
        ...(background ? { kataster: {
          adresse, breite_meter: result.bild?.breite_meter || 60,
          hoehe_meter: result.bild?.hoehe_meter || 45,
          quelle: result.quellenvermerk || [], abgerufen_am: update.kataster.abgerufen_am,
          bild_typ: result.bild?.typ || 'amtlicher_WMS',
        } } : {}),
      },
    }
  }
  return update
}

export function katasterMessage(plant, customer) {
  if (katasterStale(plant, customer)) return 'Adresse geändert – Karte und Grundstücksdaten bitte erneut abrufen.'
  const status = plant?.kataster?.grundstueck_status
  if (status === 'zugang_erforderlich') return 'Für Grundstücksdaten ist in diesem Bundesland ein berechtigter Zugang erforderlich.'
  if (status === 'mehrdeutig' || status === 'grenznah') return 'Die Flurstückszuordnung ist nicht eindeutig. Bitte prüfen; Grundstücksfelder wurden nicht überschrieben.'
  if (status && status !== 'ok') return 'Keine vollständigen Grundstücksinformationen gefunden. Vorhandene Felder bleiben erhalten.'
  if (status === 'ok' && !propertyFound(plant, customer)) return 'Grundstücksdaten wurden nach dem Abruf manuell geändert.'
  return ''
}
