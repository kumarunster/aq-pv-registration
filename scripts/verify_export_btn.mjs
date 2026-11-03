import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let exportJsons = [];
page.on('response', r => { if (r.url().includes('export-json')) { try { exportJsons.push(r.status()); } catch {} } });

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));

// 1) NEUER Kunde: Export-Button darf NICHT sichtbar sein
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde')); b.click(); });
await new Promise(r => setTimeout(r, 1000));
const newForm = await page.evaluate(() => ({
  exportBtn: !!document.querySelector('#customer-export-json'),
  plantExportBtn: !!document.querySelector('#plant-export-json'),
  saveLabel: document.querySelector('#customer-form-save')?.textContent.trim(),
}));
console.log('Neuer Kunde:', JSON.stringify(newForm));

// 2) BESTEHENDER Kunde: Export-Button RECHTS von Speichern
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1200));
await page.evaluate(() => {
  const inp = document.querySelector('input[type="search"]');
  inp.value = 'E2E';
  inp.dispatchEvent(new Event('input', { bubbles: true }));
});
await new Promise(r => setTimeout(r, 2000));
await page.evaluate(() => {
  const rows = [...document.querySelectorAll('div.cursor-pointer')].filter(r => r.textContent.includes('E2E'));
  if (rows.length) rows[rows.length - 1].click();
});
await new Promise(r => setTimeout(r, 1500));
const existing = await page.evaluate(() => {
  const btns = [...document.querySelectorAll('#customer-form button')];
  const ids = btns.map(b => b.id || b.textContent.trim().slice(0,20));
  const exportBtn = document.querySelector('#customer-export-json');
  const saveBtn = document.querySelector('#customer-form-save');
  const order = exportBtn && saveBtn
    ? [...document.querySelectorAll('#customer-form button')].map(b => b.id).filter(Boolean)
    : ids;
  return { order, exportBtnVisible: !!exportBtn, exportLabel: exportBtn?.textContent.trim() };
});
console.log('Bestehender Kunde:', JSON.stringify(existing));

// 3) Export-Button klicken -> Request muss ausgehen
await page.click('#customer-export-json');
await new Promise(r => setTimeout(r, 3500));
console.log('export-json Requests:', JSON.stringify(exportJsons));
console.log('Toasts:', JSON.stringify(await page.evaluate(() => [...document.querySelectorAll('[role="status"]')].map(e => e.textContent.trim()).filter(Boolean))));
const ok = !newForm.exportBtn && existing.exportBtnVisible && exportJsons.length > 0;
console.log(ok ? 'EXPORT-BUTTON: PASS ✅' : 'EXPORT-BUTTON: FAIL ❌');
await browser.close();
process.exit(ok ? 0 : 1);
