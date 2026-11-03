import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const consoleLogs = [];
page.on('response', r => { if (r.url().includes('/api/')) console.log('API:', r.status(), r.request().method(), r.url().replace(BASE,'')); });
page.on('pageerror', e => console.log('PAGEERROR:', e.message));
page.on('console', m => { 
  const t = m.text(); 
  consoleLogs.push(t);
  if (t.startsWith('[SAVE') || t.startsWith('SAVE-ENTER') || t.startsWith('SAVE-REQUEST')) console.log('CONSOLE:', t);
});
page.on('dialog', async d => { console.log('DIALOG:', d.message()); await d.dismiss(); });

// Login
await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));

// Navigate to customers
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1500));

// Open NEW customer form
await page.evaluate(() => { 
  const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde')); 
  if (b) b.click(); 
});
await new Promise(r => setTimeout(r, 800));

// Fill form
const filled = await page.evaluate(() => {
  const inputs = [...document.querySelectorAll('form input')];
  const setVal = (el, v) => {
    const d = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
    if (d && d.set) d.set.call(el, v); else el.value = v;
    el.dispatchEvent(new Event('input', { bubbles: true }));
  };
  if (inputs.length >= 5) {
    setVal(inputs[0], 'P211Verify');
    setVal(inputs[1], 'Test');
    setVal(inputs[2], 'Testweg 1');
    setVal(inputs[3], '12345');
    setVal(inputs[4], 'Teststadt');
    return { ok: true, count: inputs.length };
  }
  return { ok: false, count: inputs.length };
});
console.log('Filled:', JSON.stringify(filled));
await new Promise(r => setTimeout(r, 300));

// Click save
const saveClicked = await page.evaluate(() => {
  const btns = [...document.querySelectorAll('form button[type="submit"]')];
  if (btns.length === 0) return { clicked: false, reason: 'no submit buttons' };
  const btn = btns[btns.length - 1];
  const info = { label: btn.textContent.trim(), disabled: btn.disabled };
  btn.click();
  return { clicked: true, ...info };
});
console.log('Save clicked:', JSON.stringify(saveClicked));
await new Promise(r => setTimeout(r, 4000));

// Check results
const toasts = await page.evaluate(() => [...document.querySelectorAll('[role="status"], [class*="toast"]')].map(e => e.textContent.trim()).filter(Boolean));
console.log('Toasts:', JSON.stringify(toasts));
console.log('URL:', page.url());
console.log('All console logs:', JSON.stringify(consoleLogs.slice(-20), null, 2));

await browser.close();
