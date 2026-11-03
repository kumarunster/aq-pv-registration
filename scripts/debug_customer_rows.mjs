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
  const rows = [...document.querySelectorAll('div[class*="cursor"], [role="row"]')];
  const first = rows[0];
  const rowTexts = rows.slice(0, 3).map(r => r.textContent.replace(/\s+/g,' ').trim().slice(0, 150));
  return {
    rowCount: rows.length,
    rowTexts: rowTexts,
    firstRowClass: first ? first.className : 'none',
    bodySnippet: document.body.innerText.slice(0, 600)
  };
});
console.log(JSON.stringify(info, null, 2));
await browser.close();
