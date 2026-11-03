// Abnahme-Test final: nur die kritischen Pfade, robust verifiziert
import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const OUT = 'media/browser/acceptance';
const results = [];
const ok = (n) => { results.push('✅ ' + n); };
const fail = (n, w) => { results.push('❌ ' + n + (w ? ' — ' + w : '')); };

const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` }).catch(() => {});

try {
  await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await page.type('input[type="email"]', 'admin@amelanq.com');
  await page.type('input[type="password"]', 'Admin1234!');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 3000));
  page.url().includes('/admin') ? ok('Login') : fail('Login', page.url());

  const ts = String(Date.now()).slice(-6);
  const firmaName = 'Finalfirma ' + ts;

  // ---- 1) Neue Firma speichern ----
  await page.goto(BASE + '/admin/firmen', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));
  await page.evaluate(() => { [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neue Firma'))?.click(); });
  await new Promise(r => setTimeout(r, 600));
  await page.evaluate((firmaName) => {
    const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
    const inputs = [...document.querySelectorAll('form input')];
    set(inputs[0], firmaName); set(inputs[1], 'Finalstr. 1'); set(inputs[2], '63263'); set(inputs[3], 'Neu-Isenburg');
  }, firmaName);
  await new Promise(r => setTimeout(r, 300));
  await page.evaluate(() => { [...document.querySelectorAll('button[type="submit"]')].find(b => /Firma anlegen|Speichern/.test(b.textContent))?.click(); });
  await new Promise(r => setTimeout(r, 2500));
  const inList = await page.evaluate((f) => document.body.innerText.includes(f), firmaName);
  const toast = await page.evaluate(() => [...document.querySelectorAll('[role="status"],.fixed')].map(e => e.textContent).join(' '));
  inList ? ok('Firma gespeichert + in Liste') : fail('Firma in Liste');
  toast.includes('gespeichert') ? ok('Toast nach Speichern') : fail('Toast', toast.slice(0, 60));
  await shot('01-firma-gespeichert');

  // ---- 2) Bearbeiten: Vorausfüllen ----
  const editClicked = await page.evaluate((firmaName) => {
    const cards = [...document.querySelectorAll('div.cursor-pointer, div.space-y-3 > div')];
    const card = cards.find(c => c.textContent.includes(firmaName));
    const b = card ? [...card.querySelectorAll('button')].find(b => b.textContent.includes('Bearbeiten'))
                  : [...document.querySelectorAll('button')].find(b => b.textContent.includes('Bearbeiten'));
    if (!b) return false;
    b.click(); return true;
  }, firmaName);
  await new Promise(r => setTimeout(r, 900));
  const formTitle = await page.evaluate(() => document.querySelector('h2')?.textContent);
  const input0 = await page.evaluate(() => document.querySelector('form input')?.value);
  editClicked && formTitle && formTitle.includes('bearbeiten') ? ok('Bearbeiten-Formular öffnet') : fail('Bearbeiten', formTitle || 'kein h2');
  (input0 === firmaName) ? ok('Name vorgefüllt beim Bearbeiten') : fail('Vorausfüllen', 'input0=' + (input0 || 'leer'));
  await shot('02-firma-bearbeiten');
  // TASK-001: Abbrechen bei dirty Formular → Dirty-Dialog öffnen + verwerfen
  await page.evaluate(() => { [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Abbrechen')?.click(); });
  await new Promise(r => setTimeout(r, 600));
  const dirtyDlg = await page.evaluate(() => {
    const d = [...document.querySelectorAll('[role="dialog"]')].find(d => d.textContent.includes('Ungespeicherte Änderungen'));
    return d ? [...d.querySelectorAll('button')].find(b => b.textContent.includes('verwerfen'))?.click() : false;
  });
  await new Promise(r => setTimeout(r, 800));
  dirtyDlg ? ok('TASK-001: Dirty-Dialog bei Abbrechen') : fail('TASK-001: Dirty-Dialog', 'nicht gefunden');

  // ---- 3) Löschen via ConfirmDialog ----
  const delClicked = await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('🗑️'));
    if (!b) return false;
    b.click(); return true;
  });
  await new Promise(r => setTimeout(r, 900));
  const dlgOpen = await page.evaluate(() => !!document.querySelector('[role="dialog"]'));
  delClicked && dlgOpen ? ok('ConfirmDialog öffnet sich') : fail('ConfirmDialog', 'del=' + delClicked + ' dlg=' + dlgOpen);
  if (dlgOpen) {
    const dlgText = await page.evaluate(() => document.querySelector('[role="dialog"]').textContent);
    dlgText.includes(firmaName) ? ok('Dialog zeigt Firmennamen') : fail('Dialog-Text', dlgText.slice(0, 80));
    await shot('03-confirm-dialog');
    await page.evaluate(() => { [...document.querySelectorAll('[role="dialog"] button')].find(b => b.textContent.includes('Löschen'))?.click(); });
    await new Promise(r => setTimeout(r, 2500));
    const gone = await page.evaluate((f) => !document.body.innerText.includes(f), firmaName);
    gone ? ok('Firma gelöscht (Confirm-Button)') : fail('Löschen fehlgeschlagen');
  }

  // ---- 4) Kunden-Liste lädt ----
  await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 1000));
  const hasSearch = await page.evaluate(() => !!document.querySelector('input[type="search"]'));
  const customerCount = await page.evaluate(() => document.body.innerText.match(/Seite \d+ von \d+/)?.[0] || 'keine Pagination');
  hasSearch ? ok('Kunden-Suche vorhanden') : fail('Suchfeld fehlt');
  console.log('Pagination:', customerCount);

  // ---- 5) Installer-Login ----
  await page.goto(BASE + '/installer/login', { waitUntil: 'networkidle0' });
  const hasInstallerForm = await page.evaluate(() => !!document.querySelector('input[type="email"]'));
  hasInstallerForm ? ok('Installer-Login-Formular vorhanden') : fail('Installer-Login fehlt');

  // ---- 6) JS-Fehler ----
  pageErrors.length === 0 ? ok('Keine JS-Seitenfehler') : fail('JS-Fehler', pageErrors[0].slice(0, 80));

  console.log('--- ERGEBNIS ---');
  results.forEach(r => console.log(r));
} catch (e) {
  console.log('FEHLER:', e.message);
} finally {
  await browser.close();
}
