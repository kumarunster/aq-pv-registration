// PUT-only test: gespeicherten E2E-Kunden neu laden, Lageplan per API-Flow speichern, PUT pruefen
import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
const puts = [];
page.on('request', r => {
  if (r.method() === 'PUT' && /customer/.test(r.url())) {
    const b = r.postData() || '';
    puts.push({ url: r.url().replace(BASE,''), hasLp: /"lageplan":\{/.test(b), elements: (b.match(/"elements":\[(.{0,80})/)||[])[1]||null, companyField: /"company_id":null/.test(b) ? 'null' : 'set' });
  }
});
const lastLp = process.env.E2E_LAST || '6ae97f0ba2b359d0e43a7e05';

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));

// Kunden per ID öffnen: Liste durchsuchen nach E2E (letzter)
await page.evaluate(() => {
  const inp = document.querySelector('input[type="search"]');
  inp.value = 'E2E';
  inp.dispatchEvent(new Event('input', { bubbles: true }));
});
await new Promise(r => setTimeout(r, 2000));
// Letzten E2E-Kunden öffnen
await page.evaluate((lastLp) => {
  const rows = [...document.querySelectorAll('div.cursor-pointer')].filter(r => r.textContent.includes('E2E'));
  if (rows.length) rows[rows.length - 1].click();
}, lastLp);
await new Promise(r => setTimeout(r, 1500));
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b.click(); });
await new Promise(r => setTimeout(r, 800));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => /PV/.test(r.textContent));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1000));
const editVisible = await page.evaluate(() => !!document.querySelector('#plant-lageplan-edit'));
console.log('Edit-Button (existing):', editVisible);
if (!editVisible) { console.log('FAIL: kein Edit-Button'); await browser.close(); process.exit(1); }

// Dialog öffnen
await page.click('#plant-lageplan-edit');
await new Promise(r => setTimeout(r, 1500));
// Rechteck zeichnen
await page.evaluate(() => {
  const tools = [...document.querySelectorAll('button')];
  const rectBtn = tools.find(b => b.textContent.includes('Rechteck'));
  if (rectBtn) rectBtn.click();
});
await new Promise(r => setTimeout(r, 400));
const stage = await page.$('.stage-container');
const box = await stage.boundingBox();
await page.mouse.move(box.x + 450, box.y + 100);
await page.mouse.down();
await page.mouse.move(box.x + 650, box.y + 280, { steps: 12 });
await page.mouse.up();
await new Promise(r => setTimeout(r, 600));
// Dialog speichern
await page.click('#lageplan-dialog-save');
await new Promise(r => setTimeout(r, 1500));
// Kunde speichern
await page.evaluate(() => { const b = document.querySelector('#customer-form-save'); b.click(); });
await new Promise(r => setTimeout(r, 4000));
console.log('PUTs:', JSON.stringify(puts, null, 2));
const okPut = puts.find(p => p.hasLp);
console.log(pageErrors.length ? 'PAGE-ERRORS: ' + JSON.stringify(pageErrors) : 'no page errors');
console.log(okPut ? 'PUT mit lageplan: PASS ✅' : 'PUT ohne lageplan: FAIL ❌');
await browser.close();
process.exit(okPut ? 0 : 1);
