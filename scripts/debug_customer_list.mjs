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
await new Promise(r => setTimeout(r, 1500));
const info = await page.evaluate(() => {
  const trs = [...document.querySelectorAll('tr')];
  const tbody = document.querySelector('tbody');
  return {
    trCount: trs.length,
    tbodyPresent: !!tbody,
    tbodyRows: tbody ? [...tbody.querySelectorAll('tr')].map(r => r.textContent.replace(/\s+/g,' ').trim().slice(0,120)) : [],
    buttons: [...document.querySelectorAll('button')].map(b => b.textContent.trim()).slice(0, 20),
  };
});
console.log(JSON.stringify(info, null, 2));
await browser.close();
