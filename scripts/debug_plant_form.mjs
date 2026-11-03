import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', e => console.log('PAGEERROR:', e.message));
page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE-ERROR:', m.text().slice(0,200)); });

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));
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
// + Anlage klicken
await page.evaluate(() => { const b = document.querySelector('#plant-add'); b && b.click(); });
await new Promise(r => setTimeout(r, 1000));
// Was ist jetzt sichtbar?
const state = await page.evaluate(() => ({
  url: location.href,
  plantIds: [...document.querySelectorAll('[id]')].map(e => e.id).filter(i => i.includes('plant') || i.includes('lageplan')),
  anlagetypSelect: !!document.querySelector('#plant-anlagetyp'),
  snippet: document.body.innerText.replace(/\s+/g,' ').slice(0, 400)
}));
console.log('nach +Anlage:', JSON.stringify(state, null, 2));
// Anlagetyp PV wählen
await page.evaluate(() => {
  const sel = document.querySelector('#plant-anlagetyp');
  if (sel) { sel.value = 'pv'; sel.dispatchEvent(new Event('change', { bubbles: true })); }
});
await new Promise(r => setTimeout(r, 500));
const state2 = await page.evaluate(() => ({
  anlagetyp: document.querySelector('#plant-anlagetyp')?.value,
  lageplanIds: [...document.querySelectorAll('[id]')].map(e => e.id).filter(i => i.includes('lageplan')),
  warning: document.body.innerText.includes('Lageplan fehlt')
}));
console.log('nach PV wählen:', JSON.stringify(state2));
await browser.close();
