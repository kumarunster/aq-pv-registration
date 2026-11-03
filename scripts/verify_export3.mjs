import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let exportJson = null;
page.on('response', async r => { if (r.url().includes('export-json')) { try { exportJson = await r.json(); } catch {} } });
page.on('pageerror', e => console.log('PAGEERROR:', e.message));

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1500));

// Kunden mit Anlage öffnen
await page.evaluate(() => {
  const rows = [...document.querySelectorAll('div.cursor-pointer')];
  const row = rows.find(r => r.textContent.includes('Anlage'));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1500));
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); if (b) b.click(); });
await new Promise(r => setTimeout(r, 800));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => /PV|Wallbox|Wärmepumpe/.test(r.textContent));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1200));

// Lageplan-Accordion öffnen (falls zu) und Button suchen
const btn = await page.evaluate(() => {
  let b = document.querySelector('#plant-export-json');
  if (b) return { found: true, visible: b.offsetParent !== null };
  // Accordion-Kopf "Lageplan" klicken
  const heads = [...document.querySelectorAll('button')];
  const head = heads.find(h => h.textContent.includes('Lageplan'));
  if (head) { head.click(); return { accordionClicked: true }; }
  return { found: false };
});
console.log('button check:', JSON.stringify(btn));
if (btn.accordionClicked) await new Promise(r => setTimeout(r, 500));
const clicked = await page.evaluate(() => {
  const b = document.querySelector('#plant-export-json');
  if (!b) return 'NO-BUTTON';
  b.click();
  return 'clicked';
});
console.log('Export:', clicked);
await new Promise(r => setTimeout(r, 3500));

if (exportJson) {
  console.log('JSON-Keys:', Object.keys(exportJson).join(', '));
  console.log('customer:', exportJson.customer?.firstname, '|', exportJson.customer?.lastname);
  console.log('plant:', exportJson.plant?.anlagetyp, '| index', exportJson.plant_index);
  console.log('company:', exportJson.company?.name);
  console.log('lageplan_pdf_url:', exportJson.lageplan_pdf_url, '| lageplan inline:', !!exportJson.lageplan);
  console.log('exported_at:', exportJson.exported_at);
} else {
  console.log('kein export-json-Response');
}
console.log('Toasts:', JSON.stringify(await page.evaluate(() => [...document.querySelectorAll('[role="status"]')].map(e => e.textContent.trim()).filter(Boolean))));
await browser.close();
