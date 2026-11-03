// Definitiv-Test: Firma anlegen, Toast prüfen, Liste prüfen
import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('console', m => console.log('CONSOLE[' + m.type() + ']:', m.text().slice(0,150)));
page.on('pageerror', e => console.log('PAGEERROR:', e.message));

const set = (el, v) => {
  const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  s.call(el, v);
  el.dispatchEvent(new Event('input', { bubbles: true }));
};

try {
  await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await page.type('input[type="email"]', 'admin@amelanq.com');
  await page.type('input[type="password"]', 'Admin1234!');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 3000));
  console.log('URL nach Login:', page.url());

  await page.goto(BASE + '/admin/firmen', { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 1000));

  const ts = 'T' + String(Date.now()).slice(-6);
  await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neue Firma')); b && b.click(); });
  await new Promise(r => setTimeout(r, 800));

  await page.evaluate((ts) => {
    const inputs = [...document.querySelectorAll('form input')];
    const set = (el, v) => { const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
    set(inputs[0], 'Testfirma ' + ts);
    set(inputs[1], 'Teststr. 1');
    set(inputs[2], '63263');
    set(inputs[3], 'Neu-Isenburg');
    console.log('FELDER:', JSON.stringify(inputs.map(i => i.value).slice(0,4)));
  }, ts);
  await new Promise(r => setTimeout(r, 300));

  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('button[type="submit"]')].find(b => /Firma anlegen|Speichern/.test(b.textContent));
    console.log('Klicke auf:', btn && btn.textContent.trim(), '| disabled:', btn && btn.disabled);
    btn && btn.click();
  });
  await new Promise(r => setTimeout(r, 3000));

  const toast = await page.evaluate(() => {
    const els = [...document.querySelectorAll('[role="status"], [role="alert"], .fixed')];
    return els.map(e => e.textContent.trim()).filter(Boolean).join(' | ') || 'KEIN TOAST';
  });
  console.log('TOAST:', toast);

  const listHas = await page.evaluate((ts) => {
    const body = document.body.innerText;
    return body.includes('Testfirma ' + ts);
  }, ts);
  console.log('IN LISTE:', listHas);
  await page.screenshot({ path: 'media/browser/ux-review3/save-definitiv.png' });
  console.log('URL am Ende:', page.url());
} catch (e) {
  console.log('FEHLER:', e.message);
} finally {
  await browser.close();
}
