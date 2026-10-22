import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage'] });
const page = await browser.newPage();

// 1) Login
await page.goto(BASE + '/', { waitUntil: 'networkidle0' });
await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await Promise.all([page.click('button[type="submit"]'), page.waitForNavigation({ waitUntil: 'networkidle0' })]);
console.log('nach Login:', page.url());

// 2) Kunden-Ansicht
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });

// 3) Ersten Kunden bearbeiten (via evaluate, da :has-text nicht gültig ist)
const found = await page.evaluate(() => {
  const btns = [...document.querySelectorAll('button')];
  const btn = btns.find(b => b.textContent.includes('Bearbeiten'));
  if (btn) { btn.click(); return true; }
  return false;
});
if (!found) { console.log('KEIN BEARBEITEN-BUTTON'); await browser.close(); process.exit(0); }
await new Promise(r => setTimeout(r, 1000));

// 4) Formular prüfen
const h2 = await page.$eval('h2', el => el.textContent).catch(() => 'kein h2');
console.log('Überschrift:', h2.trim());
const vals = await page.$$eval('.input', els => els.slice(0, 4).map(e => ({ placeholder: e.placeholder || e.type, value: e.value })));
console.log('erste Felder:', JSON.stringify(vals));
const anyFilled = vals.some(v => v.value && v.value.trim());
console.log(anyFilled ? '✅ FELDER GEFÜLLT' : '❌ FELDER LEER');

await browser.close();
