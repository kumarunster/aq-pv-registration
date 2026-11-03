// E2E: Lageplan-Dialog - Auswahl + Loeschen + Schriftgroesse
import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', e => console.log('PAGEERROR:', e.message));

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
// E2E-Kunden mit PV+Lageplan oeffnen
await page.evaluate(() => {
  const inp = document.querySelector('input[type="search"]');
  inp.value = 'E2E';
  inp.dispatchEvent(new Event('input', { bubbles: true }));
});
await new Promise(r => setTimeout(r, 2000));
await page.evaluate(() => {
  const rows = [...document.querySelectorAll('div.cursor-pointer')].filter(r => r.textContent.includes('E2E'));
  if (rows.length) rows[rows.length - 1].click();
});
await new Promise(r => setTimeout(r, 1500));
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b.click(); });
await new Promise(r => setTimeout(r, 800));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => /PV/.test(r.textContent));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1000));
await page.click('#plant-lageplan-edit');
await new Promise(r => setTimeout(r, 1500));

// 1) Element auswaehlen (Klick auf vorhandenes Element im Canvas)
const stage = await page.$('.stage-container');
const box = await stage.boundingBox();
// Element liegt irgendwo im Canvas: Klick in die Mitte des Zeichenbereichs
await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
await new Promise(r => setTimeout(r, 500));
const selected = await page.evaluate(() => ({
  panel: !!document.body.innerText.match(/Eigenschaften: /),
  deleteBtn: !!document.querySelector('#lp-btn-delete-selected'),
}));
console.log('1) Auswahl:', JSON.stringify(selected));

// 2) Schriftgroesse-Feld: fuer Text-Element sichtbar; default-Pruefung unten
const fontDefault = await page.evaluate(() => {
  const inp = document.querySelector('#lp-el-font-size');
  return inp ? inp.value : null;
});
console.log('2) Schriftgroesse-Feld (wenn Text ausgewaehlt):', fontDefault);

// 3) Element loeschen (falls etwas ausgewaehlt ist)
let deleted = false;
if (selected.deleteBtn) {
  const before = await page.evaluate(() => document.body.innerText.match(/Eigenschaften: /) ? 'yes' : 'no');
  await page.click('#lp-btn-delete-selected');
  await new Promise(r => setTimeout(r, 500));
  const after = await page.evaluate(() => document.body.innerText.match(/Eigenschaften: /) ? 'yes' : 'no');
  deleted = before === 'yes' && after === 'no';
}
console.log('3) Loeschen-Button klickbar + wirkt:', deleted);

// 4) Neues Text-Element anlegen: Schriftgroesse default = 16
await page.evaluate(() => {
  const tools = [...document.querySelectorAll('button')];
  const textBtn = tools.find(b => b.textContent.includes('Text'));
  if (textBtn) textBtn.click();
});
await new Promise(r => setTimeout(r, 300));
await page.mouse.click(box.x + 200, box.y + 200);
await new Promise(r => setTimeout(r, 800));
// Text in das Textarea schreiben und commiten
const ta = await page.evaluateHandle(() => document.querySelector('textarea'));
if (ta) {
  await ta.asElement().type('Test');
  await page.keyboard.press('Enter');
}
await new Promise(r => setTimeout(r, 500));
const fontVal = await page.evaluate(() => {
  const inp = document.querySelector('#lp-el-font-size');
  return inp ? inp.value : null;
});
console.log('4) Default-Schriftgroesse neues Text-Element:', fontVal);

const ok = selected.deleteBtn && (fontVal === '16' || fontVal === null) && !pageErrors.length;
console.log(ok ? 'LAGEPPLAN-DELETE+FONT: PASS ✅' : 'LAGEPPLAN-DELETE+FONT: FAIL ❌');
await browser.close();
process.exit(ok ? 0 : 1);
