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

// Kunde mit Anlagen (ExportTest) öffnen
const opened = await page.evaluate(() => {
  const rows = [...document.querySelectorAll('div.cursor-pointer')];
  const row = rows.find(r => r.textContent.includes('ExportTest'));
  if (!row) return 'ROW-NOT-FOUND';
  row.click();
  return 'opened';
});
console.log('Kunde:', opened);
await new Promise(r => setTimeout(r, 1500));

const footer = await page.evaluate(() => [...document.querySelectorAll('#customer-form button')].map(b => ({ id: b.id, label: b.textContent.trim() })));
console.log('Footer:', JSON.stringify(footer));

const clicked = await page.evaluate(() => { const b = document.querySelector('#plant-export-json'); if (!b) return 'NO-BUTTON'; b.click(); return 'clicked'; });
console.log('Export:', clicked);
await new Promise(r => setTimeout(r, 3500));
if (exportJsons.length) {
  const d = exportJsons[0];
  console.log('Keys:', Object.keys(d).join(', '));
  console.log('customer:', d.customer?.firstname, d.customer?.lastname, '| plants:', d.customer?.plants?.length);
} else console.log('KEIN export-json-Request!');
console.log('Toasts:', JSON.stringify(await page.evaluate(() => [...document.querySelectorAll('[role="status"]')].map(e => e.textContent.trim()).filter(Boolean))));
await browser.close();
