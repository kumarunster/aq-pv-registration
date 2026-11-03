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
// Suche: Kunde mit Anlagen + Firma (Langen Baugenossenschaft)
await page.evaluate(() => {
  const inp = document.querySelector('input[type="search"]');
  const d = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
  d.set.call(inp, 'Langen Baugenossenschaft');
  inp.dispatchEvent(new Event('input', { bubbles: true }));
});
await new Promise(r => setTimeout(r, 2000));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('div.cursor-pointer')].find(r => r.textContent.includes('Langen Baugenossenschaft'));
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
  console.log('Keys:', Object.keys(d).join(', '));
  console.log('customer:', d.customer?.firstname, '| plants total:', d.customer?.plants?.length);
  console.log('plant[0]:', d.plant?.anlagetyp, 'company:', d.company?.name);
  console.log('lageplan_pdf_url:', d.lageplan_pdf_url);
} else console.log('KEIN export-json-Request!');
console.log('Toasts:', JSON.stringify(await page.evaluate(() => [...document.querySelectorAll('[role="status"]')].map(e => e.textContent.trim()).filter(Boolean))));
await browser.close();
