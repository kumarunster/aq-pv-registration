import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const events = [];
const log = (type, d) => { events.push({type, ...d}); };
page.on('response', r => log('RES', { status: r.status(), url: r.url().replace(BASE,''), method: r.request().method() }));
page.on('pageerror', e => log('PAGEERROR', { text: e.message }));
page.on('console', m => { if (m.type() === 'error' || m.text().startsWith('HOOK')) log('CONSOLE', { text: m.text() }); });

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.evaluateOnNewDocument(() => {
  window.addEventListener('beforeunload', e => console.log('HOOK-BEFOREUNLOAD'));
});
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1000));
const opened = await page.evaluate(() => {
  const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde'));
  if (b) { b.click(); return true; }
  return false;
});
log('INFO', { newCustomerButtonFound: opened });
await new Promise(r => setTimeout(r, 800));
const state = await page.evaluate(() => {
  const form = document.querySelector('form');
  const inputs = [...document.querySelectorAll('form input')];
  const btns = [...document.querySelectorAll('form button')].map(b => b.textContent.trim() + (b.disabled ? ' [DISABLED]' : ''));
  return { formPresent: !!form, inputCount: inputs.length, inputTypes: inputs.map(i => i.type + ':' + (i.required ? 'req' : '')), buttons: btns.slice(0, 15) };
});
log('STATE', state);
const filled = await page.evaluate(() => {
  const inputs = [...document.querySelectorAll('form input')];
  const setVal = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); };
  if (inputs.length < 5) return { filled: false, count: inputs.length };
  setVal(inputs[0], 'DebugKunde'); setVal(inputs[1], 'Test'); setVal(inputs[2], 'Weg 1'); setVal(inputs[3], '12345'); setVal(inputs[4], 'Stadt');
  return { filled: true, count: inputs.length };
});
log('FILL', filled);
await new Promise(r => setTimeout(r, 300));
const saveRes = await page.evaluate(() => {
  const b = [...document.querySelectorAll('form button[type="submit"]')];
  if (!b.length) return { clicked: false, reason: 'no submit button' };
  const btn = b[b.length-1];
  btn.click();
  return { clicked: true, label: btn.textContent.trim(), disabled: btn.disabled };
});
log('SAVE', saveRes);
await new Promise(r => setTimeout(r, 3500));
log('AFTER_URL', { url: page.url() });
const toasts = await page.evaluate(() => [...document.querySelectorAll('[role="status"], [class*="toast"]')].map(e => e.textContent.trim()).filter(Boolean));
log('TOASTS', { toasts });
console.log(JSON.stringify(events, null, 2));
await browser.close();
