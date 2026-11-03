import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const apiReqs = [];
let exportJson = null;
page.on('response', async r => {
  if (r.url().includes('/api/')) {
    apiReqs.push({ status: r.status(), method: r.request().method(), url: r.url().replace(BASE,'') });
    if (r.url().includes('export-json')) { try { exportJson = await r.json(); } catch {} }
  }
});
page.on('pageerror', e => console.log('PAGEERROR:', e.message));

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1500));

// Ersten Kunden mit Anlagen öffnen ("Test0 Customer0" hat 1 Anlage)
const opened = await page.evaluate(() => {
  const rows = [...document.querySelectorAll('div.cursor-pointer')];
  const row = rows.find(r => r.textContent.includes('Anlage'));
  if (!row) return 'no-row';
  row.click();
  return 'clicked: ' + row.textContent.replace(/\s+/g,' ').slice(0,60);
});
console.log('Opened:', opened);
await new Promise(r => setTimeout(r, 1500));

// Anlagen-Tab
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); if (b) b.click(); });
await new Promise(r => setTimeout(r, 800));

// Erste Anlage in der Liste öffnen
const plantOpened = await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => /PV|Wallbox|Wärmepumpe/.test(r.textContent));
  if (!row) return 'no-plant-row';
  row.click();
  return 'opened: ' + row.textContent.replace(/\s+/g,' ').slice(0,60);
});
console.log('Plant:', plantOpened);
await new Promise(r => setTimeout(r, 1000));

// JSON-Export
const clicked = await page.evaluate(() => {
  const b = document.querySelector('#plant-export-json');
  if (!b) return 'NO-BUTTON';
  b.click();
  return 'clicked';
});
console.log('Export:', clicked);
await new Promise(r => setTimeout(r, 3500));

console.log('Export-Requests:', JSON.stringify(apiReqs.filter(r => r.url.includes('export-json'))));
if (exportJson) {
  console.log('JSON-Keys:', Object.keys(exportJson));
  console.log('customer:', exportJson.customer?.firstname, exportJson.customer?.lastname);
  console.log('plant.anlagetyp:', exportJson.plant?.anlagetyp, '| company_id:', exportJson.plant?.company_id);
  console.log('company:', exportJson.company?.name);
  console.log('lageplan_pdf_url:', exportJson.lageplan_pdf_url);
  console.log('lageplan-present:', !!exportJson.lageplan);
  console.log('exported_at:', exportJson.exported_at);
}
console.log('Toasts:', JSON.stringify(await page.evaluate(() => [...document.querySelectorAll('[role="status"]')].map(e => e.textContent.trim()).filter(Boolean))));
await browser.close();
