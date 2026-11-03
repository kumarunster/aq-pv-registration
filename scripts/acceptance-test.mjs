// Abnahme-Test: Firmen (Speichern/Bearbeiten/Löschen) + Kunden + Dirty-Data
import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const OUT = 'media/browser/acceptance';
const results = [];
const ok = (name) => { results.push('✅ ' + name); };
const fail = (name, why) => { results.push('❌ ' + name + (why ? ' — ' + why : '')); };
const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };

const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` });

try {
  // ---- Login ----
  await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await page.type('input[type="email"]', 'admin@amelanq.com');
  await page.type('input[type="password"]', 'Admin1234!');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 3000));
  page.url().includes('/admin') ? ok('Login') : fail('Login', page.url());

  const ts = String(Date.now()).slice(-6);
  const firmaName = 'Abnahmefirma ' + ts;

  // ---- 1) Neue Firma speichern ----
  await page.goto(BASE + '/admin/firmen', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));
  await page.evaluate(() => { [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neue Firma'))?.click(); });
  await new Promise(r => setTimeout(r, 600));
  await page.evaluate((firmaName) => {
    const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
    const inputs = [...document.querySelectorAll('form input')];
    set(inputs[0], firmaName); set(inputs[1], 'Abnahmestr. 1'); set(inputs[2], '63263'); set(inputs[3], 'Neu-Isenburg');
  }, firmaName);
  await new Promise(r => setTimeout(r, 300));
  await page.evaluate(() => { [...document.querySelectorAll('button[type="submit"]')].find(b => /Firma anlegen|Speichern/.test(b.textContent))?.click(); });
  await new Promise(r => setTimeout(r, 2500));
  const inList = await page.evaluate((f) => document.body.innerText.includes(f), firmaName);
  const toast = await page.evaluate(() => [...document.querySelectorAll('[role="status"],.fixed')].map(e=>e.textContent).join(' '));
  inList ? ok('Firma gespeichert + in Liste') : fail('Firma in Liste', 'nicht gefunden');
  toast.includes('gespeichert') ? ok('Toast nach Speichern') : fail('Toast', toast.slice(0,60));
  await shot('01-firma-gespeichert');

  // ---- 2) Firma bearbeiten (Vorausfüllen) ----
  const editOk = await page.evaluate((f) => {
    const card = [...document.querySelectorAll('div')].find(d => d.innerText.includes(f) && d.querySelector('button'));
    const btn = card && [...card.querySelectorAll('button')].find(b => b.textContent.includes('Bearbeiten'));
    if (btn) { btn.click(); return true; } return false;
  }, firmaName);
  await new Promise(r => setTimeout(r, 800));
  const prefilled = await page.evaluate((f) => {
    const input = [...document.querySelectorAll('form input')][0];
    return input ? input.value === f : false;
  }, firmaName);
  prefilled ? ok('Firma bearbeiten: Name vorgefüllt') : fail('Vorausfüllen beim Bearbeiten');
  await page.evaluate(() => { [...document.querySelectorAll('button')].find(b => b.textContent.includes('Abbrechen'))?.click(); });
  await new Promise(r => setTimeout(r, 400));

  // ---- 3) Firma löschen (ConfirmDialog) ----
  const dlgOk = await page.evaluate((f) => {
    const card = [...document.querySelectorAll('div')].find(d => d.innerText.includes(f) && d.querySelector('button'));
    const btn = card && [...card.querySelectorAll('button')].find(b => b.textContent.includes('🗑️'));
    if (btn) { btn.click(); return true; } return false;
  }, firmaName);
  await new Promise(r => setTimeout(r, 800));
  const dialogOpen = await page.evaluate(() => !!document.querySelector('[role="dialog"]'));
  dialogOpen ? ok('ConfirmDialog öffnet sich') : fail('ConfirmDialog nicht geöffnet');
  await shot('02-confirm-dialog');
  await page.keyboard.press('Escape');
  await new Promise(r => setTimeout(r, 500));
  const stillInList = await page.evaluate((f) => document.body.innerText.includes(f), firmaName);
  stillInList ? ok('Esc schließt Dialog, Firma bleibt') : fail('Firma nach Esc verschwunden');
  // Dialog erneut öffnen und löschen
  await page.evaluate((f) => {
    const card = [...document.querySelectorAll('div')].find(d => d.innerText.includes(f) && d.querySelector('button'));
    [...card.querySelectorAll('button')].find(b => b.textContent.includes('🗑️'))?.click();
  }, firmaName);
  await new Promise(r => setTimeout(r, 600));
  await page.evaluate(() => { [...document.querySelectorAll('[role="dialog"] button')].find(b => b.textContent.includes('Löschen'))?.click(); });
  await new Promise(r => setTimeout(r, 2500));
  const goneFromList = await page.evaluate((f) => !document.body.innerText.includes(f), firmaName);
  goneFromList ? ok('Firma gelöscht (Confirm-Button)') : fail('Löschen fehlgeschlagen');

  // ---- 4) Kunden: Suche + Dirty-Data-Guard (TASK-001 fehlt noch) ----
  await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 1000));
  const hasSearch = await page.evaluate(() => !!document.querySelector('input[type="search"]'));
  hasSearch ? ok('Kunden-Suche vorhanden') : fail('Suchfeld fehlt');

  // ---- 5) Konsole-Fehler-Check ----
  pageErrors.length === 0 ? ok('Keine JS-Seitenfehler') : fail('JS-Fehler', pageErrors[0].slice(0,80));

  console.log('--- ERGEBNIS ---');
  results.forEach(r => console.log(r));
} catch (e) {
  console.log('FEHLER:', e.message);
} finally {
  await browser.close();
}
