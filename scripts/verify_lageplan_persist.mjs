import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
page.on('console', m => { if (m.type() === 'error') pageErrors.push(m.text().slice(0, 300)); });

// Login
await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));

// ExportTest öffnen
await page.evaluate(() => {
  const inp = document.querySelector('input[type="search"]');
  inp.value = 'ExportTest';
  inp.dispatchEvent(new Event('input', { bubbles: true }));
});
await new Promise(r => setTimeout(r, 2000));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('div.cursor-pointer')].find(r => r.textContent.includes('ExportTest'));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1500));

// Anlagen-Tab
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b && b.click(); });
await new Promise(r => setTimeout(r, 800));

// Erste Anlage öffnen (Wallbox)
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => /Wallbox/.test(r.textContent));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1000));

// Lageplan-Accordion: Button "Erstellen"/"Bearbeiten" finden und klicken
const opened = await page.evaluate(() => {
  const btn = document.querySelector('#plant-lageplan-create') || document.querySelector('#plant-lageplan-edit');
  if (!btn) return 'NO-BUTTON';
  btn.click();
  return 'clicked: ' + btn.id;
});
console.log('Lageplan-Dialog öffnen:', opened);
await new Promise(r => setTimeout(r, 1500));

// Dialog prüfen
const dialog = await page.evaluate(() => ({
  open: !!document.querySelector('#lageplan-dialog-save'),
  editor: !!document.querySelector('#lp-btn-pdf'),
}));
console.log('Dialog:', JSON.stringify(dialog));

// Ein Element zeichnen: Rechteck-Tool wählen und ziehen
await page.evaluate(() => {
  // Rect-Button im Toolbar klicken
  const tools = [...document.querySelectorAll('button')];
  const rectBtn = tools.find(b => b.textContent.includes('Rechteck'));
  if (rectBtn) rectBtn.click();
});
await new Promise(r => setTimeout(r, 300));

// Auf der Stage ziehen (Canvas-Mausereignisse simulieren)
const stage = await page.$('.stage-container');
if (stage) {
  const box = await stage.boundingBox();
  const startX = box.x + 100, startY = box.y + 100;
  const endX = box.x + 300, endY = box.y + 250;
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(endX, endY, { steps: 10 });
  await page.mouse.up();
  await new Promise(r => setTimeout(r, 500));
}

// Lageplan speichern
await page.click('#lageplan-dialog-save');
await new Promise(r => setTimeout(r, 1500));
console.log('Lageplan gespeichert.');

// Prüfen: Ist der Lageplan jetzt "erfasst"?
const afterSave = await page.evaluate(() => {
  const badge = document.body.innerText.match(/Lageplan.{0,30}/)?.[0];
  const warning = document.body.innerText.includes('Lageplan fehlt');
  return { badge, warning };
});
console.log('Nach Lageplan-Speichern:', JSON.stringify(afterSave));

// Kunde speichern
await page.evaluate(() => { const b = document.querySelector('#customer-form-save'); b && b.click(); });
await new Promise(r => setTimeout(r, 3500));

// Kunde schließen (Zurück)
await page.evaluate(() => { const b = document.querySelector('#customer-form-back'); b && b.click(); });
await new Promise(r => setTimeout(r, 1500));

// Kunde erneut öffnen
await page.evaluate(() => {
  const inp = document.querySelector('input[type="search"]');
  inp.value = 'ExportTest';
  inp.dispatchEvent(new Event('input', { bubbles: true }));
});
await new Promise(r => setTimeout(r, 2000));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('div.cursor-pointer')].find(r => r.textContent.includes('ExportTest'));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1500));

// Anlagen-Tab
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b && b.click(); });
await new Promise(r => setTimeout(r, 800));

// Prüfen: Ist der Lageplan nach dem Neuladen noch da?
const final = await page.evaluate(() => {
  const badge = document.body.innerText.match(/Lageplan.{0,30}/)?.[0];
  const warning = document.body.innerText.includes('Lageplan fehlt');
  const lageplanBtn = document.querySelector('#plant-lageplan-edit') ? 'edit' : (document.querySelector('#plant-lageplan-create') ? 'create' : 'none');
  return { badge, warning, lageplanBtn };
});
console.log('Nach Neuladen:', JSON.stringify(final));
console.log('PAGE-ERRORS:', JSON.stringify(pageErrors.filter(e => !e.includes('favicon'))));

await browser.close();
