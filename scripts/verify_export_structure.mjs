import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let exported = null;
page.on('response', async r => {
  if (r.url().includes('/export-json')) {
    try { exported = await r.json(); } catch {}
  }
});

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'domcontentloaded' });
await new Promise(r => setTimeout(r, 1500));
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
await page.click('#customer-export-json');
await new Promise(r => setTimeout(r, 4000));
if (!exported) { console.log('FAIL: keine Antwort'); process.exit(1); }

const checks = {
  top_level: Object.keys(exported).sort(),
  customer_no_plants: !('plants' in exported.customer),
  plants_count: (exported.plants||[]).length,
  no_raw_lageplan: !(exported.plants||[]).some(p => 'lageplan' in p),
  lageplan_urls: (exported.plants||[]).map(p => p.lageplan_url),
  licensedCompany: exported.licensedCompany,
  exported_at: !!exported.exported_at,
};
console.log(JSON.stringify(checks, null, 2));

// E2E-Test hatte Firma gesetzt → licensedCompany sollte Objekt sein
const ok = JSON.stringify(Object.keys(exported).sort()) === JSON.stringify(['customer','exported_at','licensedCompany','plants'])
  && checks.customer_no_plants
  && checks.plants_count > 0
  && checks.no_raw_lageplan
  && checks.exported_at
  && (exported.licensedCompany === null || typeof exported.licensedCompany === 'object');
console.log(ok ? 'PASS ✅' : 'FAIL ❌');
process.exit(ok ? 0 : 1);
