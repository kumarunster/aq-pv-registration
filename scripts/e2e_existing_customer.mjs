// E2E: EXISTIERENDEN Kunden öffnen -> PV-Anlage mit Lageplan -> Lageplan speichern -> Kunde speichern -> neu laden -> Lageplan muss da sein
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

// Login
await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));

// Neuen Kunden anlegen (mit Firma, damit PUT mit plants funktioniert)
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde')); b.click(); });
await new Promise(r => setTimeout(r, 1000));
const ts = 'E' + Date.now().toString(36).slice(-5).toUpperCase();
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
// PV-Anlage anlegen
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b.click(); });
await new Promise(r => setTimeout(r, 600));
await page.evaluate(() => { const b = document.querySelector('#plant-add'); b.click(); });
await new Promise(r => setTimeout(r, 800));
// Lageplan-Dialog öffnen, Rechteck zeichnen, speichern
await page.click('#plant-lageplan-create');
await new Promise(r => setTimeout(r, 1500));
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
await page.click('#lageplan-dialog-save');
await new Promise(r => setTimeout(r, 1500));
// Kunde speichern
await page.evaluate(() => { const b = document.querySelector('#customer-form-save'); b.click(); });
await new Promise(r => setTimeout(r, 4000));
const postReq = apiReqLog.find(r => r.m === 'POST');
console.log('POST-Request:', JSON.stringify(postReq));
if (!postReq || !postReq.hasLp) { console.log('E2E: FAIL — POST hat keinen lageplan'); await browser.close(); process.exit(1); }

// JETZT: Kunden neu öffnen (existing) und Lageplan BEARBEITEN
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
const editBtnVisible = await page.evaluate(() => !!document.querySelector('#plant-lageplan-edit'));
console.log('Edit-Button sichtbar (existing Kunde):', editBtnVisible);
if (!editBtnVisible) { console.log('E2E: FAIL — kein Edit-Button'); await browser.close(); process.exit(1); }

// Lageplan BEARBEITEN: Dialog öffnen, neues Element zeichnen, speichern
apiReqLog.length = 0;
await page.click('#plant-lageplan-edit');
await new Promise(r => setTimeout(r, 1500));
await page.evaluate(() => {
  const tools = [...document.querySelectorAll('button')];
  const rectBtn = tools.find(b => b.textContent.includes('Rechteck'));
  if (rectBtn) rectBtn.click();
});
await new Promise(r => setTimeout(r, 400));
const stage2 = await page.$('.stage-container');
const box2 = await stage2.boundingBox();
await page.mouse.move(box2.x + 450, box2.y + 100);
await page.mouse.down();
await page.mouse.move(box2.x + 650, box2.y + 280, { steps: 12 });
await page.mouse.up();
await new Promise(r => setTimeout(r, 600));
await page.click('#lageplan-dialog-save');
await new Promise(r => setTimeout(r, 1500));

// Kunde SPEICHERN (PUT)
await page.evaluate(() => { const b = document.querySelector('#customer-form-save'); b.click(); });
await new Promise(r => setTimeout(r, 4000));
console.log('PUT-Requests:', JSON.stringify(apiReqLog));
const putReq = apiReqLog.find(r => r.m === 'PUT');
if (!putReq) { console.log('E2E: FAIL — kein PUT-Request'); await browser.close(); process.exit(1); }
if (!putReq.hasLp) { console.log('E2E: FAIL — PUT hat keinen lageplan'); await browser.close(); process.exit(1); }
console.log('PUT hat lageplan, elements:', putReq.elems);

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
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => /PV/.test(r.textContent));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1000));
const final = await page.evaluate(() => ({
  warning: document.body.innerText.includes('Lageplan fehlt'),
  editBtn: !!document.querySelector('#plant-lageplan-edit'),
  createBtn: !!document.querySelector('#plant-lageplan-create'),
}));
console.log('Nach Neuladen:', JSON.stringify(final));
console.log('PAGE-ERRORS:', JSON.stringify(pageErrors.filter(e => !/favicon/.test(e))));
const ok = !final.warning && final.editBtn && !final.createBtn;
console.log(ok ? 'E2E: PASS ✅' : 'E2E: FAIL ❌');
await browser.close();
process.exit(ok ? 0 : 1);
