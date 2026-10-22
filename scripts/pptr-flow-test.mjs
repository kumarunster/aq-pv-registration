// Puppeteer-End2End: Installer-Login -> Kunde + PV-Anlage anlegen -> Liste prüfen
import puppeteer from 'puppeteer'

const BASE = 'http://localhost:8092'
const EMAIL = 'installer@amelanq.com'
const PASSWORD = 'Installer1234!'
const KUNDE = {
  firstname: 'Friedhelm',
  lastname: 'Testmuster',
  street: 'Sonnwendweg 7',
  plz: '63110',
  city: 'Rodenbach',
  phone: '06074 982301',
  email: 'friedhelm.testmuster@example.de',
  iban: 'DE02120300000000202051',
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const SHOT = (p, n) => p.screenshot({ path: `/home/moltbot/clawd/projects/amelanq-netz-anmeldung/scripts/flow-${n}.png` })

const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] })
const page = await browser.newPage()
await page.setViewport({ width: 1400, height: 1000 })
const consoleErrors = []
page.on('pageerror', (e) => consoleErrors.push(e.message))
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })

let failed = false
try {
  // 1) Login
  console.log('STAGE 1: Login')
  await page.goto(`${BASE}/installer/login`, { waitUntil: 'networkidle2', timeout: 30000 })
  await page.waitForSelector('input[type=email]', { timeout: 15000 })
  await page.type('input[type=email]', EMAIL)
  await page.type('input[type=password]', PASSWORD)
  await page.click('button[type=submit]')
  await page.waitForFunction(() => window.location.pathname.startsWith('/installer') && !window.location.pathname.includes('/login'), { timeout: 20000 })
  console.log('LOGIN OK ->', page.url())
  await SHOT(page, '01-logged-in.png')

  // 2) Formular öffnen
  console.log('STAGE 2: Formular öffnen')
  await page.waitForSelector('button', { timeout: 10000 })
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(x => x.textContent.includes('Neuer Kunde'))
    if (b) b.click()
  })
  await page.waitForSelector('input[required]', { timeout: 10000 })
  await SHOT(page, '02-form-open.png')

  // Helper: Vue reaktiv setzen via label-Text
  const fill = async (label, value) => {
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

  // Kunden-Stammdaten
  await fill('Vorname *', KUNDE.firstname)
  await fill('Nachname *', KUNDE.lastname)
  await fill('Straße + Nr *', KUNDE.street)
  await fill('PLZ *', KUNDE.plz)
  await fill('Ort *', KUNDE.city)
  await fill('Telefon', KUNDE.phone)
  await fill('E-Mail', KUNDE.email)
  await fill('IBAN', KUNDE.iban)
  await SHOT(page, '03-kunde-gefuellt.png')

  // 3) Anlage hinzufügen + PV ausfüllen
  console.log('STAGE 3: Anlage hinzufügen')
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(x => x.textContent.includes('Anlage hinzufügen'))
    if (b) b.click()
  })
  await sleep(500)

  // Anlage-Felder per placeholder
  const fillByPlaceholder = async (placeholder, value) => {
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

  await fillByPlaceholder('09.12.2024', '15.06.2025')  // Inbetriebnahme
  await fillByPlaceholder('6,9', '9.4')                   // kWp
  await fillByPlaceholder('5,1', '10.5')                 // Speicher kWh

  // Module (4 inputs ohne placeholder in der Module-Sektion)
  await page.evaluate(() => {
    const sections = [...document.querySelectorAll('section')]
    const modSection = sections.find(s => s.querySelector('h4')?.textContent.includes('Module'))
    if (!modSection) throw new Error('Module-Sektion nicht gefunden')
    const inputs = [...modSection.querySelectorAll('input')]
    const vals = ['Longi', 'Hi-MO 6', '28', '9.8']
    inputs.slice(0, 4).forEach((input, i) => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
      setter.call(input, vals[i])
      input.dispatchEvent(new Event('input', { bubbles: true }))
    })
  })
  await SHOT(page, '04-anlage-gefuellt.png')

  // 4) Speichern
  console.log('STAGE 4: Speichern')
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('form button[type=submit]')]
    if (b.length) b[b.length - 1].click()
  })
  await sleep(3000)
  await page.waitForFunction((name) => document.body.innerText.includes(name), { timeout: 10000 }, KUNDE.lastname)
  console.log('KUNDE SPEICHERT')
  await SHOT(page, '05-speichert.png')

  // Prüfen: Kunde + Anlage in Liste
  const customerVisible = await page.evaluate((n) => document.body.innerText.includes(n), KUNDE.lastname)
  const plantVisible = await page.evaluate(() => document.body.innerText.includes('Hi-MO 6'))
  console.log('Kunde in Liste:', customerVisible, '| Anlage in Liste:', plantVisible)
  if (!customerVisible) throw new Error('Kunde nach Speichern nicht sichtbar')
  if (!plantVisible) throw new Error('Anlage (Hi-MO 6) nach Speichern nicht sichtbar')

  // 5) Logout
  console.log('STAGE 5: Logout')
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(x => x.textContent.includes('Abmelden'))
    if (b) b.click()
  })
  await page.waitForFunction(() => window.location.pathname.includes('/login'), { timeout: 10000 })
  console.log('LOGOUT OK ->', page.url())
  await SHOT(page, '06-logout.png')
} catch (e) {
  failed = true
  console.error('FLOW-ERROR:', e.message)
  try { await SHOT(page, '99-error.png') } catch {}
}

if (consoleErrors.length) console.log('Console-Errors:', consoleErrors)
await browser.close()
console.log(failed ? 'ERGEBNIS: FEHLGESCHLAGEN' : 'ERGEBNIS: ERFOLGREICH')
process.exit(failed ? 1 : 0)
