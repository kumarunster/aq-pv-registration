import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const events = [];
const log = (type, d) => events.push({type, ...d});
page.on('response', r => log('RES', { status: r.status(), url: r.url().replace(BASE,''), method: r.request().method() }));
page.on('pageerror', e => log('PAGEERROR', { text: e.message }));
page.on('console', m => log('CONSOLE', { text: m.text().slice(0,200) }));
page.on('dialog', d => log('DIALOG', { text: d.message() }));

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.evaluateOnNewDocument(() => {
  const orig = window.location.assign.bind(window.location);
  window.location.assign = u => { console.log('HOOK-ASSIGN ' + u); return orig(u); };
  const origR = window.location.replace.bind(window.location);
  window.location.replace = u => { console.log('HOOK-REPLACE ' + u); return origR(u); };
});
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
await page.evaluate(() => { const b = [...document.querySelectorAll('form button[type="submit"]')]; b[b.length-1].click(); });
await new Promise(r => setTimeout(r, 4000));
log('AFTER_URL', { url: page.url() });
console.log(JSON.stringify(events.filter(e => e.type !== 'CONSOLE' || e.text.startsWith('HOOK')), null, 2));
await browser.close();
