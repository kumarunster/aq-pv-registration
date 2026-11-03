// E2E: Firma auf Kunden-Ebene speichern -> erneut oeffnen -> Firma muss gesetzt sein
import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let saveBody = null, saveMethod = null;
page.on('request', r => {
  if ((r.method() === 'PUT' || r.method() === 'POST') && /api\/(admin|installer)\/customers/.test(r.url()) && !r.url().includes('export-json')) {
    saveMethod = r.method();
    saveBody = r.postData() || null;
  }
});

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });

// NEUEN Kunden anlegen
const ts = 'C' + Date.now().toString(36).slice(-5).toUpperCase();
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde')); b.click(); });
await page.waitForSelector('#cust-firstname', { timeout: 5000 });
await page.evaluate((ts) => {
  const set = (sel, v) => { const el = document.querySelector(sel); el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); };
  set('#cust-firstname', 'Firma');
  set('#cust-lastname', ts);
  set('#cust-address-street', 'Testweg 1');
  set('#cust-address-plz', '12345');
  set('#cust-address-city', 'Teststadt');
  const sel = document.querySelector('#cust-company');
  if (sel && sel.options.length > 1) { sel.selectedIndex = 2; sel.dispatchEvent(new Event('change', { bubbles: true })); }
}, ts);
await new Promise(r => setTimeout(r, 300));
const chosen = await page.evaluate(() => {
  const sel = document.querySelector('#cust-company');
  return sel && sel.selectedIndex > 0 ? sel.options[sel.selectedIndex].textContent.trim() : '(keine)';
});
console.log('gewählte Firma:', chosen);

// Speichern
await page.click('#customer-form-save');
await new Promise(r => setTimeout(r, 3500));
console.log('Save-Request:', saveMethod, saveBody ? saveBody.slice(0, 400) : null);
const hasCompany = saveBody && /"company_id":"[^"]+"/.test(saveBody);
if (!hasCompany) { console.log('FAIL: Save-Request ohne company_id'); process.exit(1); }

// Kunde erneut öffnen
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await page.evaluate((ts) => {
  const inp = document.querySelector('input[type="search"]');
  inp.value = ts;
  inp.dispatchEvent(new Event('input', { bubbles: true }));
}, ts);
await new Promise(r => setTimeout(r, 2000));
await page.evaluate((ts) => {
  const rows = [...document.querySelectorAll('div.cursor-pointer')].filter(r => r.textContent.includes(ts));
  if (rows.length) rows[0].click();
}, ts);
await new Promise(r => setTimeout(r, 1500));
await page.waitForSelector('#cust-company', { timeout: 5000 });
const reopened = await page.evaluate(() => {
  const sel = document.querySelector('#cust-company');
  return { value: sel ? sel.value : null, label: sel && sel.selectedIndex > 0 ? sel.options[sel.selectedIndex].textContent.trim() : '(leer)' };
});
console.log('nach Neuöfnen:', JSON.stringify(reopened));
const ok = reopened.value && reopened.value !== '' && reopened.label !== '(leer)';
console.log(ok ? 'FIRMEN-REFERENZ: PASS ✅' : 'FIRMEN-REFERENZ: FAIL ❌');
await browser.close();
process.exit(ok ? 0 : 1);
