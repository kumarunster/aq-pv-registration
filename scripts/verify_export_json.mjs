// JSON-Export verifizieren: API direkt + UI-Button
import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const apiReqs = [];
page.on('response', r => { if (r.url().includes('/api/')) apiReqs.push({ status: r.status(), method: r.request().method(), url: r.url().replace(BASE,'') }); });
page.on('pageerror', e => console.log('PAGEERROR:', e.message));
page.on('dialog', async d => { console.log('DIALOG:', d.message()); await d.dismiss(); });

// Login
await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1200));

// Ersten Kunden mit Anlage öffnen (Reihe suchen)
const found = await page.evaluate(() => {
  const rows = [...document.querySelectorAll('tbody tr, tr')].filter(r => r.textContent.includes('Bearbeiten'));
  return rows.length;
});
console.log('Kunden mit Bearbeiten:', found);

// Ersten Kunden öffnen (Klick auf Zeile)
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr, tr')].find(r => r.textContent.includes('Bearbeiten'));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1500));
console.log('URL:', page.url());

// Zu Anlagen-Tab
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); if (b) b.click(); });
await new Promise(r => setTimeout(r, 800));

// Erste Anlage öffnen
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => r.textContent.match(/Anlage|PV|Wallbox|Wärmepumpe/i));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1000));

// JSON-Export-Button suchen und klicken
const exportClicked = await page.evaluate(() => {
  const b = document.querySelector('#plant-export-json');
  if (!b) return 'NO-BUTTON';
  b.click();
  return 'clicked';
});
console.log('Export-Button:', exportClicked);
await new Promise(r => setTimeout(r, 3000));

const exportReq = apiReqs.filter(r => r.url.includes('export-json'));
console.log('Export-Requests:', JSON.stringify(exportReq, null, 2));
console.log('Toasts:', JSON.stringify(await page.evaluate(() => [...document.querySelectorAll('[role="status"]')].map(e => e.textContent.trim()).filter(Boolean))));

await browser.close();
