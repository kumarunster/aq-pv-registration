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
  inp.value = 'Kolja E2E2026-10-29T1526';
  inp.dispatchEvent(new Event('input', { bubbles: true }));
});
await new Promise(r => setTimeout(r, 2000));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('div.cursor-pointer')].find(r => r.textContent.includes('Kolja E2E2026'));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1500));
await page.evaluate(() => { const b = document.querySelector('#customer-tab-anlagen'); b && b.click(); });
await new Promise(r => setTimeout(r, 800));
await page.evaluate(() => {
  const row = [...document.querySelectorAll('tbody tr')].find(r => /PV/.test(r.textContent));
  if (row) row.click();
});
await new Promise(r => setTimeout(r, 1000));

// Lageplan-Accordion: Button "Bearbeiten" suchen
const step1 = await page.evaluate(() => {
  const editBtn = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Bearbeiten');
  const accordionHead = [...document.querySelectorAll('div, button')].find(h => h.textContent.includes('📐 Lageplan') && h.textContent.length < 60);
  return { editBtnVisible: !!editBtn, accordionHead: accordionHead ? accordionHead.textContent.replace(/\s+/g,' ').trim() : null };
});
console.log('vor Dialog-Öffnung:', JSON.stringify(step1));

if (!step1.editBtnVisible) {
  // Accordion aufklappen: auf den Header klicken
  await page.evaluate(() => {
    const heads = [...document.querySelectorAll('div')];
    const head = heads.find(h => h.textContent.trim().startsWith('📐 Lageplan'));
    if (head) { const clickTarget = head.querySelector('button') || head; clickTarget.click(); }
  });
  await new Promise(r => setTimeout(r, 800));
}
const step2 = await page.evaluate(() => {
  const editBtn = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Bearbeiten' || b.id === 'plant-lageplan-edit');
  if (editBtn) { editBtn.click(); return 'clicked: ' + editBtn.id; }
  return 'NO-EDIT-BUTTON';
});
console.log('Bearbeiten:', step2);
await new Promise(r => setTimeout(r, 1500));

const step3 = await page.evaluate(() => ({
  dialogOpen: !!document.querySelector('#lageplan-dialog-save'),
  editorPdfBtn: !!document.querySelector('#lp-btn-pdf'),
  overlayCount: document.querySelectorAll('.fixed.inset-0').length,
  overlayHtml: document.querySelector('.fixed.inset-0') ? document.querySelector('.fixed.inset-0').innerHTML.slice(0, 400) : null,
}));
console.log('nach Bearbeiten-Klick:', JSON.stringify(step3, null, 2));
await browser.close();
