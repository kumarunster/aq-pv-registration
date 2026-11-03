import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const reqs = [];
page.on('response', r => { if (r.url().includes('/api/')) reqs.push({ status: r.status(), method: r.request().method(), url: r.url().replace(BASE,'') }); });
page.on('console', m => { const t = m.text(); if (t.startsWith('[SAVE')) console.log('CONSOLE: ' + t); });

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
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde')); b && b.click(); });
await new Promise(r => setTimeout(r, 800));

// Fill form using native input value setter + input event
const filled = await page.evaluate(() => {
  const inputs = [...document.querySelectorAll('form input')];
  const setVal = (el, v) => {
    const d = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
    if (d && d.set) d.set.call(el, v); else el.value = v;
    el.dispatchEvent(new Event('input', { bubbles: true }));
  };
  if (inputs.length >= 5) {
    setVal(inputs[0], 'P211Test');
    setVal(inputs[1], 'Customer');
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
await page.evaluate(() => {
  const btns = [...document.querySelectorAll('form button[type="submit"]')];
  const btn = btns[btns.length - 1];
  console.log('Clicking: ' + btn.textContent.trim() + ' disabled=' + btn.disabled);
  btn.click();
});
await new Promise(r => setTimeout(r, 4000));

// Check results
const toasts = await page.evaluate(() => [...document.querySelectorAll('[role="status"], [class*="toast"]')].map(e => e.textContent.trim()).filter(Boolean));
console.log('Toasts:', JSON.stringify(toasts));
console.log('URL:', page.url());
console.log('API Requests:', JSON.stringify(reqs.filter(r => r.method === 'POST' || r.method === 'PUT'), null, 2));

await browser.close();
