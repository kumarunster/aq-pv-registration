import client from './client'
const TIMEOUT = 330000

export function katasterError(error) {
  const detail = error?.response?.data?.detail
  const code = detail?.code
  if (error?.response?.status === 401) return 'Bitte erneut anmelden.'
  if (error?.response?.status === 429) return 'Der Katasterdienst bearbeitet bereits eine Anfrage. Bitte kurz warten und erneut versuchen.'
  if (code === 'ADDRESS_AMBIGUOUS' || code === 'ADDRESS_NOT_EXACT') return 'Die Anlagenadresse konnte nicht eindeutig zugeordnet werden. Bitte Straße, Hausnummer, PLZ und Ort prüfen.'
  if (error?.response?.status === 504 || error?.code === 'ECONNABORTED') return 'Die Katasterabfrage dauert zu lange. Bitte erneut versuchen.'
  if (typeof detail === 'string') return detail
  if (detail?.meldung) return detail.meldung
  return 'Katasterdaten konnten nicht geladen werden. Bitte später erneut versuchen.'
}

function imageData(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('Bild konnte nicht gelesen werden.'))
    reader.onload = () => {
      const img = new Image()
      img.onerror = () => reject(new Error('Ungültiges Kartenbild.'))
      img.onload = () => resolve({ dataUrl: reader.result, width: img.naturalWidth || img.width, height: img.naturalHeight || img.height })
      img.src = reader.result
    }
    reader.readAsDataURL(blob)
  })
}

export async function loadKataster(adresse, { installer = false, signal } = {}) {
  const prefix = `/${installer ? 'installer' : 'admin'}/liegenschaftskarte`
  const { data: result } = await client.post(`${prefix}/auszug`, {
    adresse, breite_meter: 60, nur_amtlich: true,
  }, { timeout: TIMEOUT, signal })
  let background = null
  let imageError = ''
  if (result.dateien?.bild) {
    // Only download from our own authenticated backend namespace. Axios already
    // uses /api as its baseURL; avoid producing /api/api/... .
    const expected = `/api${prefix}/ergebnisse/`
    const path = result.dateien.bild
    if (!path.startsWith(expected) || !/^[0-9a-f]{32}\/karte\.png$/.test(path.slice(expected.length))) {
      imageError = 'Der Kartenlink ist ungültig.'
    } else {
      try {
        const { data: blob } = await client.get(path.slice(4), { responseType: 'blob', timeout: TIMEOUT, signal })
        background = await imageData(blob)
      } catch (error) {
        if (signal?.aborted) throw error
        imageError = 'Grundstücksabfrage abgeschlossen; das Kartenbild konnte nicht geladen werden. Bitte erneut versuchen.'
      }
    }
  }
  return { result, background, imageError }
}
