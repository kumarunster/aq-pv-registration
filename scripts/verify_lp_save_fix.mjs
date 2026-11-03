import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
page.on('console', m => { if (m.type() === 'error') pageErrors.push(m.text().slice(0, 200)); });

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));
// ExportTest öffnen
await page.evaluate(() => {
  const inp = document.querySelector('input[type="search"]');
  inp.value = 'ExportTest';
  inp.dispatchEvent(new Event('input', { bubbles: true }));
});
await new Promise(r => setTimeout(r, 2000));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('div.cursor-pointer')].find(r => r.textContent.includes('ExportTest'));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1500));
// Anlagen-Tab
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b && b.click(); });
await new Promise(r => setTimeout(r, 800));
// Erste Anlage öffnen (Wallbox von gestern)
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => /PV|Wallbox/.test(r.textContent));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1000));
// Lageplan-Accordion + Button "Jetzt erstellen"/"Bearbeiten"
const btnState = await page.evaluate(() => {
  const create = document.querySelector('#plant-lageplan-create');
  const edit = document.querySelector('#plant-lageplan-edit');
  return { create: !!create, edit: !!edit, snippet: document.body.innerText.replace(/\s+/g,' ').match(/Lageplan.{0,80}/)?.[0] };
});
console.log('Lageplan-Button:', JSON.stringify(btnState));
const opened = await page.evaluate(() => {
  const b = document.querySelector('#plant-lageplan-edit') || document.querySelector('#plant-lageplan-create');
  if (!b) return 'NO-BUTTON';
  b.click();
  return 'clicked';
});
console.log('Dialog öffnen:', opened);
await new Promise(r => setTimeout(r, 1500));
const dialog = await page.evaluate(() => ({
  dialogOpen: !!document.querySelector('#lageplan-dialog-save'),
  editor: !!document.querySelector('#lp-btn-pdf'),
  metaTitle: !!document.querySelector('#lp-meta-title'),
}));
console.log('Dialog:', JSON.stringify(dialog));
// Lageplan speichern
await page.click('#lageplan-dialog-save');
await new Promise(r => setTimeout(r, 1500));
const after = await page.evaluate(() => ({
  dialogClosed: !document.querySelector('#lageplan-dialog-save'),
  dirty: document.body.innerText.includes('●'),
  snippet: document.body.innerText.replace(/\s+/g,' ').match(/Lageplan.{0,60}/)?.[0],
}));
console.log('nach Save:', JSON.stringify(after));
console.log('PAGE-ERRORS:', JSON.stringify(pageErrors.filter(e => !e.includes('favicon'))));
await browser.close();
