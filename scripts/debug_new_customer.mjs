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
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));
const neuBtn = await page.evaluate(() => {
  const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde'));
  if (!b) return 'NO-BUTTON';
  b.click();
  return 'clicked';
});
console.log('Neuer Kunde:', neuBtn);
await new Promise(r => setTimeout(r, 1000));
const form = await page.evaluate(() => ({
  url: location.href,
  custIds: [...document.querySelectorAll('[id]')].map(e => e.id).filter(i => i.startsWith('cust')),
  hasPlantAdd: !!document.querySelector('#plant-add'),
  snippet: document.body.innerText.replace(/\s+/g,' ').slice(0,300)
}));
console.log(JSON.stringify(form, null, 2));
await browser.close();
