import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const logs = [];
const log = (t) => { logs.push(t); console.log(t); };
page.on('pageerror', e => log('PAGEERROR: ' + e.message));
page.on('console', m => { const t = m.text(); if (t.startsWith('[SAVE]') || t.startsWith('HOOK')) log('CONSOLE: ' + t); });
page.on('request', r => { if (r.method() === 'POST' || r.method() === 'PUT') log('MUTATION ' + r.method() + ' ' + r.url().replace(BASE,'')); });

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1000));

// HOOKS FIRST (before any navigation)
await page.evaluateOnNewDocument(() => {
  const orig = window.location.assign.bind(window.location);
  window.location.assign = u => { console.log('HOOK-ASSIGN ' + u); return orig(u); };
  const origR = window.location.replace.bind(window.location);
  window.location.replace = u => { console.log('HOOK-REPLACE ' + u); return origR(u); };
  window.addEventListener('beforeunload', e => console.log('HOOK-BEFOREUNLOAD'));
});

await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde')); b && b.click(); });
await new Promise(r => setTimeout(r, 800));
await page.evaluate(() => {
  const inputs = [...document.querySelectorAll('form input')];
  const setVal = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); };
  setVal(inputs[0], 'DebugKunde'); setVal(inputs[1], 'Test'); setVal(inputs[2], 'Weg 1'); setVal(inputs[3], '12345'); setVal(inputs[4], 'Stadt');
});
await new Promise(r => setTimeout(r, 300));

// Test: button.click() vs requestSubmit()
await page.evaluate(() => {
  const btns = [...document.querySelectorAll('form button[type="submit"]')];
  const btn = btns[btns.length - 1];
  console.log('CLICKING: ' + btn.textContent.trim());
  btn.click();
});
await new Promise(r => setTimeout(r, 2000));
log('URL after click: ' + page.url());
log('Save logs: ' + JSON.stringify(logs.filter(l => l.startsWith('CONSOLE: [SAVE]'))));

// Try requestSubmit
await page.evaluate(() => {
  const form = document.querySelector('form');
  console.log('REQUESTSUBMIT: form exists = ' + !!form);
  form.requestSubmit();
});
await new Promise(r => setTimeout(r, 2000));
log('URL after requestSubmit: ' + page.url());
log('Save logs: ' + JSON.stringify(logs.filter(l => l.startsWith('CONSOLE: [SAVE]'))));

// Check if form has Vue's submit handler
const formInfo = await page.evaluate(() => {
  const form = document.querySelector('form');
  return {
    form: !!form,
    vue: !!form.__vueParentComponent,
    app: !!form.__vue_app__,
    formId: form.id,
    formAction: form.action,
    formMethod: form.method,
    formNoValidate: form.noValidate
  };
});
log('FORM INFO: ' + JSON.stringify(formInfo));

await browser.close();
