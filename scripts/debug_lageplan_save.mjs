import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', e => console.log('PAGEERROR:', e.message));
page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE-ERROR:', m.text().slice(0,300)); });

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));
// Kunde mit PV-Anlage + Lageplan: "Kolja E2E2026-10-29T1526"
await page.evaluate(() => {
  const inp = document.querySelector('input[type="search"]');
  inp.value = 'Kolja E2E2026-10-29T1526';
  inp.dispatchEvent(new Event('input', { bubbles: true }));
});
await new Promise(r => setTimeout(r, 2000));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('div.cursor-pointer')].find(r => r.textContent.includes('Kolja E2E2026'));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1500));
// Anlagen-Tab
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b && b.click(); });
await new Promise(r => setTimeout(r, 800));
// Anlage öffnen
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => /PV/.test(r.textContent));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1000));
// Lageplan-Accordion öffnen
await page.evaluate(() => {
  const heads = [...document.querySelectorAll('button, div')];
  const head = heads.find(h => h.textContent.trim().startsWith('📐 Lageplan'));
  if (head) head.click();
});
await new Promise(r => setTimeout(r, 600));
// Dialog öffnen
await page.evaluate(() => { const b = document.querySelector('#plant-lageplan-edit'); if (b) b.click(); else { const b2=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('Bearbeiten')); b2 && b2.click(); } });
await new Promise(r => setTimeout(r, 1200));

const dialogState = await page.evaluate(() => ({
  dialogOpen: !!document.querySelector('#lageplan-dialog-save'),
  editorVisible: !!document.querySelector('#lp-btn-pdf'),
  saveBtn: !!document.querySelector('#lageplan-dialog-save'),
}));
console.log('Dialog:', JSON.stringify(dialogState));

// Save klicken
await page.click('#lageplan-dialog-save');
await new Promise(r => setTimeout(r, 1500));

const after = await page.evaluate(() => {
  // ist der Dialog zu?
  const dialogClosed = !document.querySelector('#lageplan-dialog-save');
  // Form ist dirty?
  const dirtyDot = document.body.innerText.includes('●');
  // Badge im Accordion "erfasst"?
  const badge = document.body.innerText.match(/📐 Lageplan.{0,30}/);
  // Form-plant: was steht im Vue-Form? (via DOM: Lageplan-Accordion badge)
  return { dialogClosed, dirtyDot, badge: badge ? badge[0] : null, url: location.href };
});
console.log('nach Save:', JSON.stringify(after));
await browser.close();
