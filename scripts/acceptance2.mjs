// Abnahme-Test Runde 2: robustere Klicklogik, Fokus auf Bearbeiten/Vorausfüllen/Löschen
import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const OUT = 'media/browser/acceptance';
const results = [];
const ok = (name) => { results.push('✅ ' + name); };
const fail = (name, why) => { results.push('❌ ' + name + (why ? ' — ' + why : '')); };
const setVal = `
  const set = (el, v) => {
    const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true }));
  };
`;

const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` }).catch(e => console.log('shot-fehler', e.message));

try {
  await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await page.type('input[type="email"]', 'admin@amelanq.com');
  await page.type('input[type="password"]', 'Admin1234!');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 3000));
  page.url().includes('/admin') ? ok('Login') : fail('Login', page.url());

  const ts = String(Date.now()).slice(-6);
  const firmaName = 'Abnahmefirma ' + ts;

  // Neue Firma speichern
  await page.goto(BASE + '/admin/firmen', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));
  await page.evaluate(() => { [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neue Firma'))?.click(); });
  await new Promise(r => setTimeout(r, 600));
  await page.evaluate((firmaName) => {
    const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
    const inputs = [...document.querySelectorAll('form input')];
    set(inputs[0], firmaName); set(inputs[1], 'Abnahmestr. 1'); set(inputs[2], '63263'); set(inputs[3], 'Neu-Isenburg');
    console.log('FELDER:', JSON.stringify(inputs.map(i => i.value).slice(0, 4)));
  }, firmaName);
  await new Promise(r => setTimeout(r, 300));
  await page.evaluate(() => { [...document.querySelectorAll('button[type="submit"]')].find(b => /Firma anlegen|Speichern/.test(b.textContent))?.click(); });
  await new Promise(r => setTimeout(r, 2500));
  const inList = await page.evaluate((f) => document.body.innerText.includes(f), firmaName);
  const toast = await page.evaluate(() => [...document.querySelectorAll('[role="status"],.fixed')].map(e => e.textContent).join(' '));
  inList ? ok('Firma gespeichert + in Liste') : fail('Firma in Liste');
  toast.includes('gespeichert') ? ok('Toast nach Speichern') : fail('Toast', toast.slice(0, 60));
  await shot('01-firma-gespeichert');

  // Bearbeiten: per Button-Index (2. Button in Karte = Bearbeiten)
  await page.evaluate((f) => {
    const cards = [...document.querySelectorAll('div.bg-slate-900')].filter(d => d.innerText.includes(f));
    if (!cards.length) { console.log('KEINE KARTE'); return; }
    const btns = cards[0].querySelectorAll('button');
    console.log('KARTE-BUTTONS:', [...btns].map(b => b.textContent.trim()));
    btns[1] && btns[1].click();
  }, firmaName);
  await new Promise(r => setTimeout(r, 900));
  const formTitle = await page.evaluate(() => document.querySelector('h2')?.textContent);
  const input0 = await page.evaluate(() => document.querySelector('form input')?.value);
  console.log('FORM-TITEL:', formTitle, '| input0:', input0);
  (formTitle && formTitle.includes('bearbeiten')) ? ok('Bearbeiten-Formular öffnet (Titel)') : fail('Bearbeiten-Titel', formTitle || 'kein h2');
  (input0 === firmaName) ? ok('Name vorgefüllt') : fail('Vorausfüllen', 'input0=' + (input0 || 'leer'));
  await shot('02-firma-bearbeiten');
  await page.evaluate(() => { [...document.querySelectorAll('button')].find(b => b.textContent.includes('Abbrechen'))?.click(); });
  await new Promise(r => setTimeout(r, 500));

  // Löschen: per Button-Index (3. Button = 🗑️)
  await page.evaluate((f) => {
    const cards = [...document.querySelectorAll('div.bg-slate-900')].filter(d => d.innerText.includes(f));
    const btns = cards[0] && cards[0].querySelectorAll('button');
    btns && btns[2] && btns[2].click();
  }, firmaName);
  await new Promise(r => setTimeout(r, 900));
  const dlgOpen = await page.evaluate(() => !!document.querySelector('[role="dialog"]'));
  dlgOpen ? ok('ConfirmDialog öffnet sich') : fail('ConfirmDialog');
  if (dlgOpen) {
    const dlgText = await page.evaluate(() => document.querySelector('[role="dialog"]').textContent);
    dlgText.includes(firmaName) ? ok('Dialog zeigt Firmennamen') : fail('Dialog-Text', dlgText.slice(0, 80));
    await shot('03-confirm-dialog');
    await page.evaluate(() => { [...document.querySelectorAll('[role="dialog"] button')].find(b => b.textContent.includes('Löschen'))?.click(); });
    await new Promise(r => setTimeout(r, 2500));
    const gone = await page.evaluate((f) => !document.body.innerText.includes(f), firmaName);
    gone ? ok('Firma gelöscht (Confirm-Button)') : fail('Löschen fehlgeschlagen');
  }

  // Kunden-Suche
  await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 1000));
  const hasSearch = await page.evaluate(() => !!document.querySelector('input[type="search"]'));
  hasSearch ? ok('Kunden-Suche vorhanden') : fail('Suchfeld fehlt');

  pageErrors.length === 0 ? ok('Keine JS-Seitenfehler') : fail('JS-Fehler', pageErrors[0].slice(0, 80));

  console.log('--- ERGEBNIS ---');
  results.forEach(r => console.log(r));
} catch (e) {
  console.log('FEHLER:', e.message);
} finally {
  await browser.close();
}
