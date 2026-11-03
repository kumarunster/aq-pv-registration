// Verifikation: JSON-Export-Button im Footer neben Abbrechen/Speichern
import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let exportJsons = [];
page.on('response', async r => { if (r.url().includes('export-json')) { try { exportJsons.push(await r.json()); } catch {} } });
page.on('pageerror', e => console.log('PAGEERROR:', e.message));

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1500));

// Neuen Kunden öffnen
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde')); b && b.click(); });
await new Promise(r => setTimeout(r, 800));

// Footer-Buttons prüfen (ohne gespeicherten Kunden)
const footer = await page.evaluate(() => {
  const btns = [...document.querySelectorAll('#customer-form button')];
  return btns.map(b => ({ id: b.id, label: b.textContent.trim(), disabled: b.disabled }));
});
console.log('Footer-Buttons (neuer Kunde):', JSON.stringify(footer));

// Kunde speichern (Firma wählen)
await page.evaluate(() => {
  const setVal = (sel, v) => {
    const el = document.querySelector(sel);
    const proto = el.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    if (el.tagName === 'SELECT') el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  setVal('#cust-firstname', 'ExportTest');
  setVal('#cust-lastname', 'Kunde');
  setVal('#cust-address-street', 'Exportweg 1');
  setVal('#cust-address-plz', '12345');
  setVal('#cust-address-city', 'Exportstadt');
  const sel = document.querySelector('#cust-company');
  if (sel.options.length > 1) { sel.selectedIndex = 1; sel.dispatchEvent(new Event('change', { bubbles: true })); }
});
await new Promise(r => setTimeout(r, 300));
// Anlage hinzufügen (Wallbox = kein Lageplan nötig)
await page.evaluate(() => { const b = document.querySelector('#plant-add'); if (b) b.click(); });
await new Promise(r => setTimeout(r, 600));
await page.evaluate(() => {
  const sel = document.querySelector('#plant-anlagetyp');
  if (sel) { const d = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value'); d.set.call(sel, 'wallbox'); sel.dispatchEvent(new Event('change', { bubbles: true })); }
});
await new Promise(r => setTimeout(r, 300));
await page.evaluate(() => { const b = document.querySelector('#customer-form-save'); if (b) b.click(); });
await new Promise(r => setTimeout(r, 3500));
console.log('URL nach Save:', page.url());

// Kunden wieder öffnen (erster in der Liste)
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1200));
await page.evaluate(() => {
  const rows = [...document.querySelectorAll('div.cursor-pointer')];
  const row = rows.find(r => r.textContent.includes('ExportTest'));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1500));

// Footer mit gespeicherten Daten
const footer2 = await page.evaluate(() => {
  const btns = [...document.querySelectorAll('#customer-form button')];
  return btns.map(b => ({ id: b.id, label: b.textContent.trim(), disabled: b.disabled }));
});
console.log('Footer-Buttons (gespeicherter Kunde):', JSON.stringify(footer2));

// Export klicken
const clicked = await page.evaluate(() => {
  const b = document.querySelector('#plant-export-json');
  if (!b) return 'NO-BUTTON';
  b.click();
  return 'clicked';
});
console.log('Export:', clicked);
await new Promise(r => setTimeout(r, 3000));
if (exportJsons.length) {
  const d = exportJsons[0];
  console.log('JSON-Keys:', Object.keys(d).join(', '));
  console.log('customer:', d.customer?.firstname, d.customer?.lastname);
  console.log('plant:', d.plant?.anlagetyp, '| company:', d.company?.name);
  console.log('lageplan_pdf_url:', d.lageplan_pdf_url);
} else console.log('kein export-json-Response');
console.log('Toasts:', JSON.stringify(await page.evaluate(() => [...document.querySelectorAll('[role="status"]')].map(e => e.textContent.trim()).filter(Boolean))));
await browser.close();
