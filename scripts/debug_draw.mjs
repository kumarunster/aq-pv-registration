import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', e => console.log('PAGEERROR:', e.message));
page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE:', m.text().slice(0,200)); });

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde')); b.click(); });
await new Promise(r => setTimeout(r, 1000));
const ts = 'DBG' + Date.now().toString(36).slice(-4).toUpperCase();
await page.evaluate((ts) => {
  const set = (sel, v) => { const el = document.querySelector(sel); el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); };
  set('#cust-firstname', 'DBG');
  set('#cust-lastname', ts);
  set('#cust-address-street', 'Testweg 1');
  set('#cust-address-plz', '12345');
  set('#cust-address-city', 'Teststadt');
  const sel = document.querySelector('#cust-company');
  if (sel && sel.options.length > 1) { sel.selectedIndex = 1; sel.dispatchEvent(new Event('change', { bubbles: true })); }
}, ts);
await new Promise(r => setTimeout(r, 400));
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b.click(); });
await new Promise(r => setTimeout(r, 600));
await page.evaluate(() => { const b = document.querySelector('#plant-add'); b.click(); });
await new Promise(r => setTimeout(r, 800));
await page.click('#plant-lageplan-create');
await new Promise(r => setTimeout(r, 1500));

// Rect-Tool
await page.evaluate(() => {
  const tools = [...document.querySelectorAll('button')];
  const rectBtn = tools.find(b => b.textContent.includes('Rechteck'));
  if (rectBtn) rectBtn.click();
});
await new Promise(r => setTimeout(r, 400));

// Ziehen auf der Stage
const stage = await page.$('.stage-container');
const box = await stage.boundingBox();
console.log('Stage-Box:', JSON.stringify(box));
await page.mouse.move(box.x + 150, box.y + 100);
await page.mouse.down();
await page.mouse.move(box.x + 400, box.y + 300, { steps: 15 });
await page.mouse.up();
await new Promise(r => setTimeout(r, 800));

const state = await page.evaluate(() => {
  const canvas = document.querySelector('.stage-container canvas');
  return {
    activeTool: null,
    propsPanel: document.body.innerText.replace(/\s+/g,' ').match(/Eigenschaften: \w+/)?.[0] || 'kein Panel',
    canvasPresent: !!canvas,
    canvasSize: canvas ? canvas.width + 'x' + canvas.height : null,
    bodySnippet: document.body.innerText.replace(/\s+/g,' ').slice(0, 400)
  };
});
console.log('nach Ziehen:', JSON.stringify(state, null, 2));

// Was weiß der Store? (über getLayout via console — nicht möglich) — stattdessen:
// Element in der Vue reaktiv prüfen via window? Nein. Instead check: save and inspect request.
await page.click('#lageplan-dialog-save');
await new Promise(r => setTimeout(r, 1200));
// Kunde speichern
await page.evaluate(() => { const b = document.querySelector('#customer-form-save'); b.click(); });
await new Promise(r => setTimeout(r, 3000));
await browser.close();
