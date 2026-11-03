// E2E: Kunde mit PV-Anlage + Lageplan anlegen -> Lageplan speichern -> Kunde speichern -> neu laden -> Lageplan muss da sein
import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
const apiReqLog = [];
page.on('request', r => {
  const m = r.method();
  if ((m === 'PUT' || m === 'POST') && /customer/.test(r.url()) && !r.url().includes('export-json')) {
    const b = r.postData() || '';
    apiReqLog.push({ m, url: r.url().replace(BASE,''), hasLp: /"lageplan":\{/.test(b), elems: (b.match(/"elements":\[(.{0,60})/)||[])[1]||null });
  }
});
const ts = 'E' + Date.now().toString(36).slice(-5).toUpperCase();

// Login
await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));

// Neuen Kunden anlegen
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde')); b.click(); });
await new Promise(r => setTimeout(r, 1000));
await page.evaluate((ts) => {
  const set = (sel, v) => { const el = document.querySelector(sel); el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); };
  set('#cust-firstname', 'E2E');
  set('#cust-lastname', ts);
  set('#cust-address-street', 'Testweg 1');
  set('#cust-address-plz', '12345');
  set('#cust-address-city', 'Teststadt');
  const sel = document.querySelector('#cust-company');
  if (sel && sel.options.length > 1) { sel.selectedIndex = 1; sel.dispatchEvent(new Event('change', { bubbles: true })); }
}, ts);
await new Promise(r => setTimeout(r, 400));
// Zum Anlagen-Tab
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b.click(); });
await new Promise(r => setTimeout(r, 600));
// PV-Anlage anlegen
await page.evaluate(() => { const b = document.querySelector('#plant-add'); b.click(); });
await new Promise(r => setTimeout(r, 800));
const afterAdd = await page.evaluate(() => ({
  warning: document.body.innerText.includes('Lageplan fehlt'),
  createBtn: !!document.querySelector('#plant-lageplan-create'),
}));
console.log('1) nach +Anlage:', JSON.stringify(afterAdd));
if (!afterAdd.createBtn) { console.log('FEHLER: kein Lageplan-Create-Button'); process.exit(1); }

// Lageplan-Dialog öffnen
await page.click('#plant-lageplan-create');
await new Promise(r => setTimeout(r, 1500));
const dialog = await page.evaluate(() => ({
  open: !!document.querySelector('#lageplan-dialog-save'),
  editor: !!document.querySelector('#lp-btn-pdf'),
}));
console.log('2) Dialog offen:', JSON.stringify(dialog));

// Rechteck zeichnen (Konva-Stage)
await page.evaluate(() => {
  const tools = [...document.querySelectorAll('button')];
  const rectBtn = tools.find(b => b.textContent.includes('Rechteck'));
  if (rectBtn) rectBtn.click();
});
await new Promise(r => setTimeout(r, 400));
const stage = await page.$('.stage-container');
const box = await stage.boundingBox();
await page.mouse.move(box.x + 100, box.y + 80);
await page.mouse.down();
await page.mouse.move(box.x + 350, box.y + 250, { steps: 12 });
await page.mouse.up();
await new Promise(r => setTimeout(r, 600));

// Lageplan speichern
await page.click('#lageplan-dialog-save');
await new Promise(r => setTimeout(r, 1500));
const afterLpSave = await page.evaluate(() => ({
  dialogClosed: !document.querySelector('#lageplan-dialog-save'),
  warningGone: !document.body.innerText.includes('Lageplan fehlt'),
}));
console.log('3) nach Lageplan-Speichern:', JSON.stringify(afterLpSave));

// Kunde speichern
await page.evaluate(() => { const b = document.querySelector('#customer-form-save'); b.click(); });
await new Promise(r => setTimeout(r, 4000));
console.log('4) API-Requests:', JSON.stringify(apiReqLog));
const saved = await page.evaluate(() => ({ toasts: [...document.querySelectorAll('[role="status"]')].map(e => e.textContent.trim()) }));
console.log('5) nach Kunde-Speichern:', JSON.stringify(saved));
const saveReq = apiReqLog.find(r => r.m === 'POST' || r.m === 'PUT');
if (!saveReq) { console.log('E2E: FAIL — kein Save-Request'); await browser.close(); process.exit(1); }
if (!saveReq.hasLp) { console.log('E2E: FAIL — Save-Request hat KEINEN lageplan'); await browser.close(); process.exit(1); }
console.log('6) Save-Request hat lageplan mit elements:', saveReq.elems);

// Neuladen und prüfen
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));
await page.evaluate((ts) => {
  const inp = document.querySelector('input[type="search"]');
  inp.value = ts;
  inp.dispatchEvent(new Event('input', { bubbles: true }));
}, ts);
await new Promise(r => setTimeout(r, 2000));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('div.cursor-pointer')].find(r => r.textContent.includes('E2E'));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1500));
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b.click(); });
await new Promise(r => setTimeout(r, 800));
// Anlage öffnen
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => /PV/.test(r.textContent));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1000));
const final = await page.evaluate(() => ({
  warning: document.body.innerText.includes('Lageplan fehlt'),
  badge: document.body.innerText.match(/📐 Lageplan.{0,20}/)?.[0],
  editBtn: !!document.querySelector('#plant-lageplan-edit'),
  createBtn: !!document.querySelector('#plant-lageplan-create'),
}));
console.log('7) nach Neuladen:', JSON.stringify(final));
console.log('PAGE-ERRORS:', JSON.stringify(pageErrors.filter(e => !/favicon/.test(e))));
const ok = !final.warning && final.editBtn && !final.createBtn;
console.log(ok ? 'E2E: PASS ✅' : 'E2E: FAIL ❌');
await browser.close();
process.exit(ok ? 0 : 1);
