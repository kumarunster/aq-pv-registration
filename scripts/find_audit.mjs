import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1200));
// Search for P211Test
const ok = await page.evaluate(() => {
  const inp = document.querySelector('input[type="search"]');
  if (!inp) return 'no-input';
  const d = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
  d.set.call(inp, 'P211Test');
  inp.dispatchEvent(new Event('input', { bubbles: true }));
  return 'typed';
});
console.log('search:', ok);
await new Promise(r => setTimeout(r, 2000));
const row = await page.evaluate(() => {
  const rows = [...document.querySelectorAll('tbody tr, tr')];
  const r = rows.find(x => x.textContent.includes('P211Test'));
  return r ? r.textContent.replace(/\s+/g,' ').trim() : 'ROW-NOT-FOUND';
});
console.log('ROW:', row);
await browser.close();
