import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const trace = [];
const log = (o) => { trace.push({ t: Date.now(), ...o }); };
page.on('request', r => log({ type: 'REQ', method: r.method(), url: r.url() }));
page.on('response', r => log({ type: 'RES', status: r.status(), method: r.request().method(), url: r.url() }));
page.on('framenavigated', f => log({ type: 'NAV', url: f.url() }));
page.on('dialog', async d => { log({ type: 'DIALOG', text: d.message() }); });

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
log({ type: 'MARK', text: 'LOGIN-CLICK' });
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
log({ type: 'INFO', text: 'URL: ' + page.url() });

await page.goto(BASE + '/admin/firmen', { waitUntil: 'networkidle0', timeout: 30000 });
await new Promise(r => setTimeout(r, 1000));
log({ type: 'MARK', text: 'NEUE-FIRMA-CLICK' });
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neue Firma')); b && b.click(); });
await new Promise(r => setTimeout(r, 800));

const ts = String(Date.now()).slice(-6);
log({ type: 'MARK', text: 'FORMULAR-AUSFUELLEN ' + ts });
await page.evaluate((ts) => {
  const form = document.querySelector('form');
  const inputs = [...form.querySelectorAll('input')];
  const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
  set(inputs[0], 'Testfirma ' + ts);
  set(inputs[1], 'Teststr. 1');
  set(inputs[2], '63263');
  set(inputs[3], 'Neu-Isenburg');
  const v = inputs.map(i => i.value);
  console.log('FORM-WERTE: ' + JSON.stringify(v));
}, ts);
await new Promise(r => setTimeout(r, 500));

log({ type: 'MARK', text: 'SAVE-CLICK' });
await page.evaluate(() => {
  const btn = [...document.querySelectorAll('button[type="submit"]')].find(b => /Firma anlegen|Speichern/.test(b.textContent));
  if (!btn) { console.log('SAVE-BUTTON NICHT GEFUNDEN'); return; }
  console.log('SAVE-BUTTON: ' + btn.textContent.trim() + ' disabled=' + btn.disabled);
  btn.click();
});
await new Promise(r => setTimeout(r, 5000));
log({ type: 'INFO', text: 'URL nach Save: ' + page.url() });
const toast = await page.evaluate(() => [...document.querySelectorAll('[role="status"], [role="alert"]')].map(e => e.textContent).join(' | ') || 'kein Toast-Element');
log({ type: 'INFO', text: 'Toast: ' + toast });
await page.screenshot({ path: 'media/browser/ux-review3/save-test-final.png' });
log({ type: 'MARK', text: 'END' });
await browser.close();
const fs = await import('fs');
fs.writeFileSync('media/browser/ux-review3/save-trace2.json', JSON.stringify(trace, null, 2));
console.log('EINTRAEGE:', trace.length);
