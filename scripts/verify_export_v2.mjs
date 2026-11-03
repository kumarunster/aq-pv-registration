import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let exportJsons = [];
page.on('response', async r => { if (r.url().includes('export-json')) { try { exportJsons.push(await r.json()); } catch {} } });
page.on('pageerror', e => console.log('PAGEERROR:', e.message));

// Login
await page.goto(BASE + '/admin/login', { waitUntil: 'domcontentloaded', timeout: 15000 });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded', timeout: 15000 });
await new Promise(r => setTimeout(r, 1500));

// Suche + öffnen
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
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); if (b) b.click(); });
await new Promise(r => setTimeout(r, 800));

// +Anlage (default PV)
await page.evaluate(() => { const b = document.querySelector('#plant-add'); if (b) b.click(); });
await new Promise(r => setTimeout(r, 1000));

// Anlagetyp → wallbox (kein Lageplan-Pflicht)
await page.evaluate(() => {
  const sel = document.querySelector('#plant-anlagetyp');
  if (!sel) return 'NO-SELECT';
  sel.value = 'wallbox';
  sel.dispatchEvent(new Event('change', { bubbles: true }));
  return 'ok';
});
await new Promise(r => setTimeout(r, 500));

// Zurück zum Kunden-Tab und Speichern
await page.evaluate(() => { const b = document.querySelector('#customer-tab-kunde'); if (b) b.click(); });
await new Promise(r => setTimeout(r, 500));
await page.evaluate(() => { const b = document.querySelector('#customer-form-save'); if (b) b.click(); });
await new Promise(r => setTimeout(r, 3500));
console.log('URL nach Save:', page.url());

// Kunden erneut öffnen
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded', timeout: 15000 });
await new Promise(r => setTimeout(r, 1200));
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

const footer = await page.evaluate(() => [...document.querySelectorAll('#customer-form button')].map(b => ({ id: b.id, label: b.textContent.trim() })));
console.log('Footer:', JSON.stringify(footer));

const clicked = await page.evaluate(() => { const b = document.querySelector('#plant-export-json'); if (!b) return 'NO-BUTTON'; b.click(); return 'clicked'; });
console.log('Export:', clicked);
await new Promise(r => setTimeout(r, 4000));

if (exportJsons.length) {
  const d = exportJsons[0];
  console.log('JSON-Keys:', Object.keys(d).join(', '));
  console.log('customer:', d.customer?.firstname, d.customer?.lastname);
  console.log('plants total:', d.customer?.plants?.length);
  console.log('plant[0]:', d.plant?.anlagetyp, '| company:', d.company?.name);
  console.log('lageplan_pdf_url:', d.lageplan_pdf_url);
  console.log('lageplan inline:', !!d.lageplan);
  console.log('exported_at:', d.exported_at);
} else {
  console.log('KEIN export-json-Request!');
}
console.log('Toasts:', JSON.stringify(await page.evaluate(() => [...document.querySelectorAll('[role="status"]')].map(e => e.textContent.trim()).filter(Boolean))));
await browser.close();
