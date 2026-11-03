import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', e => console.log('PAGEERROR:', e.message));
page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE-ERROR:', m.text()); });

await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
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
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); if (b) b.click(); });
await new Promise(r => setTimeout(r, 800));

// Vorher: was ist sichtbar?
const before = await page.evaluate(() => ({
  tabActive: document.querySelector('#customer-tab-anlagen')?.className?.includes('text-white'),
  plantAddVisible: !!document.querySelector('#plant-add'),
  plantSearchVisible: !!document.querySelector('#plant-search'),
  plantEditorVisible: !!document.querySelector('#plant-anlagetyp'),
  plantListVisible: !!document.querySelector('table'),
  emptyMsg: document.body.innerText.includes('Noch keine Anlage')
}));
console.log('vor +Anlage:', JSON.stringify(before));

// +Anlage klicken
const clicked = await page.evaluate(() => {
  const b = document.querySelector('#plant-add');
  if (!b) return 'NO-BUTTON';
  b.click();
  return 'clicked';
});
console.log('+Anlage:', clicked);
await new Promise(r => setTimeout(r, 1000));

const after = await page.evaluate(() => ({
  plantAddVisible: !!document.querySelector('#plant-add'),
  plantEditorVisible: !!document.querySelector('#plant-anlagetyp'),
  plantListRows: document.querySelectorAll('tbody tr').length,
  emptyMsg: document.body.innerText.includes('Noch keine Anlage'),
  snipped: document.body.innerText.replace(/\s+/g, ' ').slice(0, 500)
}));
console.log('nach +Anlage:', JSON.stringify(after, null, 2));
await browser.close();
