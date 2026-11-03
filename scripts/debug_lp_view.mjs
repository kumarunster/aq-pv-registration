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
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b && b.click(); });
await new Promise(r => setTimeout(r, 800));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => /PV|Wallbox/.test(r.textContent));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1000));

// Was ist im DOM? Alle IDs mit "lageplan"/"plant"
const ids = await page.evaluate(() => {
  const all = [...document.querySelectorAll('[id]')].map(e => e.id);
  return {
    lageplanIds: all.filter(i => i.includes('lageplan') || i.includes('Lageplan')),
    plantIds: all.filter(i => i.includes('plant')).slice(0, 20),
    url: location.href,
    // Was ist im Anlage-Editor sichtbar?
    editorSnippet: document.body.innerText.replace(/\s+/g, ' ').slice(0, 800)
  };
});
console.log(JSON.stringify(ids, null, 2));
await browser.close();
