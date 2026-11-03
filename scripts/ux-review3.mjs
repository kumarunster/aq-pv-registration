// Vollständiges UX/UI-Review: Screenshots aller Bereiche (1440×900 + mobile 375×812)
import puppeteer from 'puppeteer-core';

const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const OUT = 'media/browser/ux-review3';

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

const errors = [];
page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('response', r => {
  if (r.status() >= 400) errors.push(r.status() + ' ' + r.url());
});

const shot = async (name) => {
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log('SHOT', name);
};

try {
  // ---------- Landing ----------
  await page.goto(BASE + '/', { waitUntil: 'networkidle0', timeout: 30000 });
  await shot('01-landing');

  // ---------- Admin-Login-Seite ----------
  await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await shot('02-admin-login');

  // Login ausfüllen + Fehlermeldung testen (falsches Passwort)
  await page.type('input[type="email"]', 'admin@amelanq.com');
  await page.type('input[type="password"]', 'WrongPass123!');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 2500));
  const errText = await page.$eval('.text-red-400', el => el.textContent).catch(() => null);
  console.log('LOGIN-FEHLER-TEXT:', errText);
  await shot('03-admin-login-fehler');

  // Richtiger Login
  await page.evaluate(() => document.querySelector('input[type="password"]').value = '');
  await page.type('input[type="password"]', 'Admin1234!');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 2500));
  console.log('URL NACH LOGIN:', page.url());
  await shot('04-admin-home');

  // ---------- Firmen ----------
  await page.goto(BASE + '/admin/firmen', { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 800));
  await shot('05-firmen-liste');

  // Firma-Formular öffnen (Neue Firma)
  const newBtn = await page.$('button:has-text("+ Neue Firma")').catch?.(() => null);
  const clicked = await page.evaluate(() => {
    const btns = [...document.querySelectorAll('button')];
    const b = btns.find(b => b.textContent.includes('Neue Firma'));
    if (b) { b.click(); return true; }
    return false;
  });
  if (clicked) { await new Promise(r => setTimeout(r, 500)); await shot('06-firma-formular'); }

  // Zurück zur Liste + Bearbeiten einer Firma
  await page.evaluate(() => {
    const btns = [...document.querySelectorAll('button')];
    const b = btns.find(b => b.textContent.includes('Abbrechen'));
    if (b) b.click();
  });
  await new Promise(r => setTimeout(r, 500));
  await page.evaluate(() => {
    const btns = [...document.querySelectorAll('button')];
    const b = btns.find(b => b.textContent.includes('Bearbeiten'));
    if (b) b.click();
  });
  await new Promise(r => setTimeout(r, 500));
  const firmaBearbeiten = await page.evaluate(() => {
    const h = document.querySelector('h2');
    return h ? h.textContent : null;
  });
  console.log('FIRMA-FORMULAR-TITEL:', firmaBearbeiten);
  if (firmaBearbeiten && firmaBearbeiten.includes('bearbeiten')) await shot('07-firma-bearbeiten');

  // ---------- Kunden-Liste ----------
  await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 1000));
  await shot('08-kunden-liste');

  // Suche testen
  await page.type('input[type="search"]', 'Bau');
  await new Promise(r => setTimeout(r, 1000));
  await shot('09-kunden-suche');
  // Suche zurücksetzen
  await page.evaluate(() => { const i = document.querySelector('input[type="search"]'); i.value = ''; i.dispatchEvent(new Event('input')); });
  await new Promise(r => setTimeout(r, 1000));

  // Kunden-Karte öffnen (Erster Kunde bearbeiten)
  await page.evaluate(() => {
    const cards = [...document.querySelectorAll('div.cursor-pointer')];
    if (cards[0]) cards[0].click();
  });
  await new Promise(r => setTimeout(r, 800));
  await shot('10-kunde-formular');

  // Anlagen-Tab öffnen
  await page.evaluate(() => {
    const btns = [...document.querySelectorAll('button')];
    const b = btns.find(b => b.textContent.includes('Anlagen'));
    if (b) b.click();
  });
  await new Promise(r => setTimeout(r, 500));
  await shot('11-anlagen-tab');

  // Erste Anlage im Editor öffnen
  const AnlageGeöffnet = await page.evaluate(() => {
    const rows = document.querySelectorAll('tbody tr');
    if (rows[0]) { rows[0].click(); return true; }
    return false;
  });
  await new Promise(r => setTimeout(r, 500));
  if (AnlageGeöffnet) {
    await shot('12-anlage-editor-oben');
    // Scrollen in den Editor
    await page.evaluate(() => window.scrollBy(0, 700));
    await new Promise(r => setTimeout(r, 300));
    await shot('13-anlage-editor-mitte');
    await page.evaluate(() => window.scrollBy(0, 700));
    await new Promise(r => setTimeout(r, 300));
    await shot('14-anlage-editor-unten');
  }

  // ---------- Leerzustand (Suche ohne Treffer) ----------
  await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 800));
  await page.type('input[type="search"]', 'zzzz-kein-treffer-999');
  await new Promise(r => setTimeout(r, 1000));
  await shot('15-kunden-leerzustand');

  // ---------- 404 ----------
  await page.goto(BASE + '/does-not-exist', { waitUntil: 'networkidle0', timeout: 30000 });
  await shot('16-notfound');

  // ---------- Installer-Login ----------
  await page.goto(BASE + '/installer/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await shot('17-installer-login');

  // ---------- Lageplan-Editor (standalone, unautentifiziert?) ----------
  await page.goto(BASE + '/lageplan', { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 1500));
  await shot('18-lageplan-editor');

  // ---------- Mobile 375×812 ----------
  const mobile = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await mobile.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await mobile.type('input[type="email"]', 'admin@amelanq.com');
  await mobile.type('input[type="password"]', 'Admin1234!');
  await mobile.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 2500));
  await mobile.screenshot({ path: `${OUT}/19-mobile-admin-home.png` });
  console.log('SHOT 19-mobile-admin-home');
  await mobile.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 1200));
  await mobile.screenshot({ path: `${OUT}/20-mobile-kunden.png` });
  console.log('SHOT 20-mobile-kunden');

  console.log('--- FEHLER/4xx/5xx ---');
  const unique = [...new Set(errors)];
  console.log(unique.length ? unique.slice(0, 30).join('\n') : '(keine)');
} catch (e) {
  console.error('FEHLER:', e.message);
} finally {
  await browser.close();
}
