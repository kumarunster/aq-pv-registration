// P2-11-Verifikation (final): Login → neuer Kunde → Save → Toast + API + Audit-Zeile
import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const NAME = 'P211Test ' + String(Date.now()).slice(-6);

const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const results = {};
const apiReqs = [];
page.on('response', r => { if (r.url().includes('/api/')) apiReqs.push({ status: r.status(), method: r.request().method(), url: r.url().replace(BASE,'') }); });
page.on('pageerror', e => results.pageError = e.message);
page.on('dialog', async d => { results.dialog = d.message(); await d.dismiss(); });

// --- Login
await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
results.loginUrl = page.url();

// --- Kundenliste
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1000));

// --- Neuer Kunde
await page.click('button:has-text("Neuer Kunde")').catch(async () => {
  await page.evaluate(() => [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde'))?.click());
});
await new Promise(r => setTimeout(r, 800));
results.formVisible = !!(await page.$('#customer-form'));

// --- Felder via ID (native value-setter + Input-Event)
const setVal = (sel, v) => page.evaluate((sel, v) => {
  const el = document.querySelector(sel);
  if (!el) return false;
  const proto = el.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  const d = Object.getOwnPropertyDescriptor(proto, 'value');
  d.set.call(el, v);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  if (el.tagName === 'SELECT') el.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
}, sel, v);

results.fill = {};
for (const [sel, v] of [
  ['#cust-firstname', NAME],
  ['#cust-lastname', 'Automated'],
  ['#cust-address-street', 'Testweg 1'],
  ['#cust-address-plz', '12345'],
  ['#cust-address-city', 'Teststadt'],
]) {
  results.fill[sel] = await setVal(sel, v);
}
await new Promise(r => setTimeout(r, 300));

// Firma wählen (Admin-Modus, required)
const companyChosen = await page.evaluate(() => {
  const sel = document.querySelector('#cust-company');
  if (!sel) return 'no-select';
  if (sel.options.length < 2) return 'no-options';
  sel.selectedIndex = 1;
  sel.dispatchEvent(new Event('change', { bubbles: true }));
  return sel.value;
});
results.company = companyChosen;
await new Promise(r => setTimeout(r, 300));

// --- Save
await page.click('#customer-form-save');
await new Promise(r => setTimeout(r, 4000));

results.url = page.url();
results.toasts = await page.evaluate(() => [...document.querySelectorAll('[role="status"]')].map(e => e.textContent.trim()).filter(Boolean));
results.postPut = apiReqs.filter(r => r.method === 'POST' || r.method === 'PUT');

// --- Audit-Zeile in der Liste (P2-11): Suche nach dem Namen
await page.evaluate((name) => {
  const inp = document.querySelector('input[type="search"], input[placeholder*="uche"]');
  if (!inp) return;
  const d = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
  d.set.call(inp, name);
  inp.dispatchEvent(new Event('input', { bubbles: true }));
}, NAME);
await new Promise(r => setTimeout(r, 1500));
results.auditLine = await page.evaluate((name) => {
  const rows = [...document.querySelectorAll('tr')];
  const row = rows.find(r => r.textContent.includes(name));
  return row ? row.textContent.replace(/\s+/g, ' ').trim() : 'ROW-NOT-FOUND';
}, NAME);

console.log(JSON.stringify(results, null, 2));
await browser.close();
