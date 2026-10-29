// E2E: Installer-Login -> NEUEN Kunden + PV-Anlage (Adresse/Grundstück) anlegen -> Speichern
// -> Browser schließen -> neu öffnen -> alle Daten müssen da sein.
import puppeteer from 'puppeteer'
import fs from 'fs'

const BASE = 'http://localhost:8092'
const EMAIL = 'installer@amelanq.com'
const PASSWORD = 'Installer1234!'
const TS = new Date().toISOString().replace(/[:.]/g, '').slice(0, 15)
const KUNDE = {
  firstname: 'Kolja',
  lastname: `E2E${TS}`,
  street: 'Testweg 5',
  plz: '63329',
  city: 'Egelsbach',
  phone: '0170 1234567',
  email: 'e2e@test.example',
  iban: 'DE02120300000000202051',
}
const ANLAGE = {
  commission: '15.06.2025',
  kwp: '9.4',
  kwh: '10.5',
  module_manufacturer: `E2E-Modul-${TS}`,
  gemarkung: 'Egelsbach',
  flur: '3',
  flurstueck: '12/1',
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const SHOT = (p, n) => p.screenshot({ path: `/home/moltbot/clawd/projects/amelanq-netz-anmeldung/scripts/e2e-${TS}-${n}.png` })
const results = {}

// Vue reaktiv setzen via label-Text
function makeFill(page) {
  return async (label, value) => {
    const ok = await page.evaluate(({ label, value }) => {
      const labels = [...document.querySelectorAll('label')]
      const el = labels.find(l => l.textContent.trim() === label)
      if (!el) return false
      const input = el.parentElement.querySelector('input')
      if (!input) return false
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
      setter.call(input, value)
      input.dispatchEvent(new Event('input', { bubbles: true }))
      return true
    }, { label, value })
    if (!ok) throw new Error('Label nicht gefunden: ' + label)
  }
}

function makeFillPlaceholder(page) {
  return async (placeholder, value) => {
    const ok = await page.evaluate(({ placeholder, value }) => {
      const inputs = [...document.querySelectorAll('input')]
      const input = inputs.find(i => i.placeholder === placeholder)
      if (!input) return false
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
      setter.call(input, value)
      input.dispatchEvent(new Event('input', { bubbles: true }))
      return true
    }, { placeholder, value })
    if (!ok) throw new Error('Placeholder nicht gefunden: ' + placeholder)
  }
}

function clickButton(page, text) {
  return page.evaluate((t) => {
    const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim().includes(t))
    if (b) { b.click(); return true }
    return false
  }, text)
}

let failed = false

async function stageCreate(browser) {
  const page = await browser.newPage()
  await page.setViewport({ width: 1400, height: 1100 })
  const consoleErrors = []
  page.on('pageerror', (e) => consoleErrors.push(e.message))
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })
  const alerts = []
  page.on('dialog', async (d) => { alerts.push(d.message()); await d.dismiss() })
  const apiLog = []
  page.on('response', async (r) => {
    const u = r.url()
    if (u.includes('/api/')) {
      const req = r.request()
      let body = ''
      try { body = req.postData() || '' } catch {}
      let resp = ''
      try { resp = (await r.text()).slice(0, 300) } catch {}
      if (req.method() !== 'GET') apiLog.push({ m: req.method(), u: u.replace(BASE, ''), s: r.status(), b: body.slice(0, 2000), r: resp })
    }
  })

  // 1) Login
  console.log('STAGE 1: Login')
  await page.goto(`${BASE}/installer/login`, { waitUntil: 'networkidle2', timeout: 30000 })
  await page.waitForSelector('input[type=email]', { timeout: 15000 })
  await page.type('input[type=email]', EMAIL)
  await page.type('input[type=password]', PASSWORD)
  await page.click('button[type=submit]')
  await page.waitForFunction(() => window.location.pathname.startsWith('/installer') && !window.location.pathname.includes('login'), { timeout: 20000 })
  console.log('  LOGIN OK ->', page.url())
  await SHOT(page, '01-login.png')

  // 2) Neuer Kunde
  console.log('STAGE 2: Neuer Kunde')
  await clickButton(page, '+ Neuer Kunde')
  await page.waitForSelector('input[required]', { timeout: 10000 })
  const fill = makeFill(page)
  await fill('Vorname *', KUNDE.firstname)
  await fill('Nachname *', KUNDE.lastname)
  await fill('Straße + Nr *', KUNDE.street)
  await fill('PLZ *', KUNDE.plz)
  await fill('Ort *', KUNDE.city)
  await fill('Telefon', KUNDE.phone)
  await fill('E-Mail', KUNDE.email)
  await fill('IBAN', KUNDE.iban)
  await SHOT(page, '02-kunde.png')

  // 3) Anlage hinzufügen
  console.log('STAGE 3: Anlage + Adresse/Grundstück')
  await clickButton(page, 'Anlage hinzufügen')
  await sleep(600)
  const fillPh = makeFillPlaceholder(page)
  await fillPh('09.12.2024', ANLAGE.commission)
  await fillPh('6,9', ANLAGE.kwp)
  await fillPh('5,1', ANLAGE.kwh)

  // Module (4 inputs ohne Placeholder in der Module-Sektion)
  const modOk = await page.evaluate((mfr) => {
    const h4s = [...document.querySelectorAll('h4')]
    const mh = h4s.find(h => h.textContent.includes('PV-Module'))
    if (!mh) return false
    const inputs = [...mh.parentElement.querySelectorAll('input')]
    const vals = [mfr, 'Hi-MO 6', '28', '9.8']
    inputs.slice(0, 4).forEach((input, i) => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
      setter.call(input, vals[i])
      input.dispatchEvent(new Event('input', { bubbles: true }))
    })
    return inputs.length >= 4
  }, ANLAGE.module_manufacturer)
  if (!modOk) throw new Error('Module-Felder nicht gefunden')

  // Adresse: Häkchen AUS, eigene Adresse
  const cbOk = await page.evaluate(() => {
    const cb = document.querySelector('input[type="checkbox"]')
    if (!cb) return false
    if (cb.checked) { cb.click(); return 'unchecked' }
    return 'already-off'
  })
  console.log('  Adresse-Häkchen:', cbOk)
  await sleep(300)
  // Adressfelder (Labels: Straße + Hausnummer / PLZ / Ort) — PLZ/Ort erscheinen nach Häkchen aus
  await fill('Straße + Hausnummer', KUNDE.street)
  await fill('PLZ', KUNDE.plz)
  await fill('Ort', KUNDE.city)
  // Grundstück
  await fill('Gemarkung', ANLAGE.gemarkung)
  await fill('Flur', ANLAGE.flur)
  await fill('Flurstueck', ANLAGE.flurstueck)
  await SHOT(page, '03-anlage-adresse.png')

  // 4a) Lageplan: Erstellen + minimales Rechteck zeichnen (PV-Pflichtfeld)
  console.log('STAGE 3b: Lageplan (minimales Rechteck)')
  const lpOk = await clickButton(page, 'Erstellen')
  if (!lpOk) throw new Error('Lageplan-Button "Erstellen" nicht gefunden')
  await page.waitForSelector('canvas', { timeout: 15000 })
  await sleep(1000)
  await clickButton(page, 'Rechteck')
  const canvasBox = await page.evaluate(() => {
    const c = document.querySelector('canvas')
    const r = c.getBoundingClientRect()
    return { x: r.x, y: r.y, w: r.width, h: r.height }
  })
  const sx = canvasBox.x + canvasBox.w * 0.3
  const sy = canvasBox.y + canvasBox.h * 0.3
  await page.mouse.move(sx, sy)
  await page.mouse.down()
  await page.mouse.move(sx + 150, sy + 100, { steps: 5 })
  await page.mouse.up()
  await sleep(500)
  await clickButton(page, 'Lageplan speichern')
  await sleep(500)
  const lpStatus = await page.evaluate(() => document.body.innerText.includes('✓ erfasst'))
  console.log('  Lageplan erfasst:', lpStatus)
  if (!lpStatus) throw new Error('Lageplan-Status nicht "✓ erfasst"')
  await SHOT(page, '03b-lageplan.png')

  // 4) Speichern
  console.log('STAGE 4: Speichern')
  await page.evaluate(() => {
    const b = document.querySelector('form button[type=submit]')
    if (b) b.click()
  })
  await sleep(4000)
  if (alerts.length) console.log('  ALERTS:', alerts)
  // Kunde in der Liste?
  const inList = await page.evaluate((n) => document.body.innerText.includes(n), KUNDE.lastname)
  const plantInList = await page.evaluate((n) => document.body.innerText.includes(n), ANLAGE.module_manufacturer)
  console.log('  Kunde in Liste:', inList, '| Modul in Liste:', plantInList)
  results.apiLog = apiLog
  await SHOT(page, '04-gespeichert.png')
  console.log('  Console-Errors:', consoleErrors.length ? consoleErrors : 'keine')
  if (!inList) throw new Error('Kunde nach Speichern NICHT in der Liste')
  await page.close()
}

async function stageVerify(browser) {
  const page = await browser.newPage()
  await page.setViewport({ width: 1400, height: 1100 })
  const consoleErrors = []
  page.on('pageerror', (e) => consoleErrors.push(e.message))

  // 1) Login (neue Session — Browser war 'zu')
  console.log('STAGE 5: Neu Login (Browser neu geöffnet)')
  await page.goto(`${BASE}/installer/login`, { waitUntil: 'networkidle2', timeout: 30000 })
  await page.waitForSelector('input[type=email]', { timeout: 15000 })
  await page.type('input[type=email]', EMAIL)
  await page.type('input[type=password]', PASSWORD)
  await page.click('button[type=submit]')
  await page.waitForFunction(() => window.location.pathname.startsWith('/installer') && !window.location.pathname.includes('login'), { timeout: 20000 })
  await SHOT(page, '05-relogin.png')

  // 2) Kunde muss in der Liste sein
  await sleep(1500)
  const inList = await page.evaluate((n) => document.body.innerText.includes(n), KUNDE.lastname)
  console.log('  Kunde nach Neuladen in Liste:', inList)
  if (!inList) {
    // suchen
    await page.type('input[placeholder*="Kunde suchen"]', KUNDE.lastname)
    await sleep(1000)
    const inList2 = await page.evaluate((n) => document.body.innerText.includes(n), KUNDE.lastname)
    console.log('  (nach Suche) Kunde in Liste:', inList2)
  }

  // 3) Bearbeiten öffnen: alle Daten müssen vorgefüllt sein
  console.log('STAGE 6: Bearbeiten — Daten prüfen')
  await page.evaluate((n) => {
    const cards = [...document.querySelectorAll('h3')]
    const card = cards.find(c => c.textContent.includes(n))
    if (card) {
      const b = card.closest('div')?.querySelectorAll('button')
      const editBtn = [...(b || [])].find(x => x.textContent.includes('Bearbeiten'))
      if (editBtn) editBtn.click()
    }
  }, KUNDE.lastname)
  await page.waitForSelector('input[required]', { timeout: 10000 })
  await sleep(500)

  const getVal = (label) => page.evaluate((l) => {
    const labels = [...document.querySelectorAll('label')]
    const el = labels.find(x => x.textContent.trim() === l)
    const input = el?.parentElement?.querySelector('input')
    return input ? input.value : null
  }, label)

  results.verify = {
    firstname: await getVal('Vorname *'),
    lastname: await getVal('Nachname *'),
    street: await getVal('Straße + Nr *'),
    plz: await getVal('PLZ *'),
    city: await getVal('Ort *'),
    email: await getVal('E-Mail'),
    commission: await getVal('Inbetriebnahme (TT.MM.JJJJ)'),
    kwp: await getVal('kWp (Nennleistung)'),
    gemarkung: await getVal('Gemarkung'),
    flur: await getVal('Flur'),
    flurstueck: await getVal('Flurstueck'),
    // Adresse-Häkchen: muss AKTIV sein (wenn address_from_customer=true)? Wir haben es AUSgemacht -> eigene Adresse -> Häkchen aus
    // Modul-Hersteller per section
  }
  results.verify.module = await page.evaluate((n) => {
    const h4s = [...document.querySelectorAll('h4')]
    const mh = h4s.find(h => h.textContent.includes('PV-Module'))
    const inputs = [...(mh?.parentElement?.querySelectorAll('input') || [])]
    return inputs[0]?.value || null
  }, ANLAGE.module_manufacturer)
  await SHOT(page, '06-bearbeiten-daten.png')

  console.log('  VORGEFÜLLT:')
  for (const [k, v] of Object.entries(results.verify)) {
    if (typeof v === 'object') continue
    console.log(`   ${k}: ${JSON.stringify(v)}`)
  }
  console.log('   module:', JSON.stringify(results.verify.module))
  console.log('  Console-Errors:', consoleErrors.length ? consoleErrors : 'keine')
  await page.close()
}

// ===========================
const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] })
try {
  await stageCreate(browser)
  console.log('STAGE-4 ERLEDIGT')
  await browser.close()
} catch (e) {
  failed = true
  console.error('CREATE-ERROR:', e.message)
  try { await browser.close() } catch {}
}

if (!failed) {
  const browser2 = await puppeteer.launch({ headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] })
  try {
    await stageVerify(browser2)
    console.log('STAGE-6 ERLEDIGT')
    await browser2.close()
  } catch (e) {
    failed = true
    console.error('VERIFY-ERROR:', e.message)
    try { await browser2.close() } catch {}
  }
}

// Ergebnis-Auswertung
console.log('\n================ ERGEBNIS ================')
const v = results.verify || {}
const checks = [
  ['Kunde nach Neuladen sichtbar', v.lastname === KUNDE.lastname],
  ['Vorname', v.firstname === KUNDE.firstname],
  ['Straße', v.street === KUNDE.street],
  ['PLZ', v.plz === KUNDE.plz],
  ['Ort', v.city === KUNDE.city],
  ['E-Mail', v.email === KUNDE.email],
  ['Inbetriebnahme', v.commission === ANLAGE.commission],
  ['kWp', v.kwp === ANLAGE.kwp],
  ['Gemarkung', v.gemarkung === ANLAGE.gemarkung],
  ['Flur', v.flur === ANLAGE.flur],
  ['Flurstueck', v.flurstueck === ANLAGE.flurstueck],
  ['Modul-Hersteller', v.module === ANLAGE.module_manufacturer],
]
let allOk = true
for (const [name, ok] of checks) {
  console.log(`${ok ? '✅' : '❌'} ${name}`)
  if (!ok) allOk = false
}
console.log('==========================================')
console.log(failed || !allOk ? 'ERGEBNIS: FEHLGESCHLAGEN' : 'ERGEBNIS: ERFOLGREICH — alle Daten überleben Browser-Neustart')
fs.writeFileSync(`/home/moltbot/clawd/projects/amelanq-netz-anmeldung/scripts/e2e-${TS}-result.json`, JSON.stringify({ results, checks }, null, 2))
process.exit(failed || !allOk ? 1 : 0)
