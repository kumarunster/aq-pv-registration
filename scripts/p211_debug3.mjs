import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const saveLogs = [];
page.on('response', r => { if (r.url().includes('/api/')) console.log('RES', r.status(), r.request().method(), r.url().replace(BASE,'')); });
page.on('pageerror', e => console.log('PAGEERROR', e.message));
page.on('console', m => { const t = m.text(); if (t.startsWith('[SAVE]')) saveLogs.push(t); });
page.on('request', r => { if (r.method() === 'POST' || r.method() === 'PUT') console.log('MUTATION', r.method(), r.url().replace(BASE,'')); });

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1000));
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde')); b && b.click(); });
await new Promise(r => setTimeout(r, 800));
await page.evaluate(() => {
  const inputs = [...document.querySelectorAll('form input')];
  const setVal = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); };
  setVal(inputs[0], 'DebugKunde'); setVal(inputs[1], 'Test'); setVal(inputs[2], 'Weg 1'); setVal(inputs[3], '12345'); setVal(inputs[4], 'Stadt');
});
await new Promise(r => setTimeout(r, 300));
// Click the actual submit button (last type=submit)
await page.evaluate(() => {
  const btns = [...document.querySelectorAll('form button[type="submit"]')];
  console.log('SUBMIT BUTTONS:', btns.map(b => b.textContent.trim() + '|' + b.disabled));
  btns[btns.length-1].click();
});
await new Promise(r => setTimeout(r, 4000));
console.log('URL:', page.url());
console.log('SAVE LOGS:', JSON.stringify(saveLogs, null, 2));
const toasts = await page.evaluate(() => [...document.querySelectorAll('[role="status"], [class*="toast"]')].map(e => e.textContent.trim()).filter(Boolean));
console.log('TOASTS:', JSON.stringify(toasts));
await browser.close();
