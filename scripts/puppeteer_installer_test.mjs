import puppeteer from 'puppeteer';

const BASE = 'http://localhost:8092';

const browser = await puppeteer.launch({
  headless: 'new',
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

const page = await browser.newPage();
page.on('console', msg => console.log('[browser]', msg.type(), msg.text()));
page.on('dialog', async d => { console.log('[dialog]', d.message()); await d.accept(); });

function log(...a) { console.log(...a); }

try {
  // 1) Login-Seite
  log('1) Navigiere zu /installer/login');
  await page.goto(BASE + '/installer/login', { waitUntil: 'networkidle2', timeout: 30000 });
  log('   URL:', page.url());
  const h1 = await page.$eval('h1', el => el.textContent).catch(() => '(kein h1)');
  log('   H1:', h1.trim());

  // 2) Login ausfüllen + absenden
  log('2) Login: installer@amelanq.com');
  await page.type('input[type="email"]', 'installer@amelanq.com');
  await page.type('input[type="password"]', 'Installer1234!');
  await Promise.all([
    page.click('button[type="submit"]'),
    page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 30000 }),
  ]);
  log('   URL nach Login:', page.url());
  if (!page.url().startsWith(BASE + '/installer/')) {
    throw new Error('Login nicht erfolgreich, URL: ' + page.url());
  }

  // 3) "+ Neuer Kunde"
  log('3) Öffne Formular "+ Neuer Kunde"');
  await page.click('button:has-text("+ Neuer Kunde")');
  await page.waitForSelector('form', { timeout: 10000 });

  // 4) Kunden-Stammdaten
  log('4) Kunden-Stammdaten ausfüllen');
  async function fillInput(placeholder, value) {
    // inputs werden über label-Text gefunden
    const el = await page.evaluateHandle((labelText) => {
      const labels = [...document.querySelectorAll('label')];
      const label = labels.find(l => l.textContent.includes(labelText));
      return label ? label.nextElementSibling : null;
    }, placeholder);
    if (el) await el.asElement().type(value);
  }
  await fillInput('Vorname', 'Erika');
  await fillInput('Nachname', 'Testmüller');
  await fillInput('Straße', 'Sonnweg 7');
  await fillInput('PLZ', '65428');
  await fillInput('Ort', 'Rüsselsheim');
  await fillInput('Telefon', '06142 998877');
  await fillInput('E-Mail', 'erika.testmueller@example.com');
  await fillInput('IBAN', 'DE44 5001 0517 0400 4242 40');

  // 5) Anlage hinzufügen + ausfüllen
  log('5) Anlage hinzufügen und ausfüllen');
  await page.click('button:has-text("+ Anlage hinzufügen")');
  await page.waitForTimeout(500);

  // Anlagetyp PV ist default. Inbetriebnahme, kWp, Speicher
  const inputs = await page.$$('input');
  // Über Placeholder ausfüllen wo möglich
  await page.evaluate(() => {
    function setVal(sel, val) {
      const el = document.querySelector(sel);
      if (el) { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); }
    }
  });
  // Placeholder-basiert:
  async function byPlaceholder(placeholder, value) {
    const ok = await page.evaluate((ph, v) => {
      const el = [...document.querySelectorAll('input')].find(i => (i.placeholder || '') === ph);
      if (!el) return false;
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(el, v);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      return true;
    }, placeholder, value);
    if (!ok) log('   (Placeholder nicht gefunden:', placeholder + ')');
    return ok;
  }
  await byPlaceholder('09.12.2024', '15.06.2026');      // Inbetriebnahme
  await byPlaceholder('6', '7.2');                        // kW
  await byPlaceholder('6,9', '7.2');                      // kWp
  await byPlaceholder('5,1', '10');                       // Speicher kWh
  // Module
  await byPlaceholder('Hersteller', 'LONGi');
  await byPlaceholder('Typ', 'HI-MO 7');
  await byPlaceholder('Anzahl', '12');
  // MStR
  await byPlaceholder('SEE Anlage', 'DE-SEE-2026-000123');
  await byPlaceholder('EEG-Anlage', 'DE-EEG-2026-000123');
  await byPlaceholder('SEE Speicher', 'DE-SEE-2026-000124');

  // 6) Speichern
  log('6) Kunde anlegen (Speichern)');
  await page.click('button:has-text("Kunde anlegen")');
  await page.waitForTimeout(3000);

  // 7) Kunde in der Liste suchen
  log('7) Prüfe Liste auf "Erika Testmüller"');
  const found = await page.evaluate(() => document.body.innerText.includes('Erika Testmüller'));
  if (!found) {
    const bodyText = await page.evaluate(() => document.body.innerText);
    log('   NICHT GEFUNDEN. Seite-Auszug:', bodyText.slice(0, 800));
  } else {
    log('   GEFUNDEN: Kunde "Erika Testmüller" mit PV-Anlage in der Liste');
    const plant = await page.evaluate(() => {
      const cards = [...document.querySelectorAll('h3')].filter(h => h.textContent.includes('Erika Testmüller'));
      if (!cards.length) return null;
      return cards[0].closest('.bg-slate-900')?.innerText || '';
    });
    log('   Kartendetails:', plant);
  }
} catch (e) {
  console.error('FEHLER:', e.message);
  const bodyText = await page.evaluate(() => document.body.innerText).catch(() => '');
  console.error('Seite-Auszug:', bodyText.slice(0, 800));
  const shot = '/home/moltbot/clawd/projects/amelanq-netz-anmeldung/memory/puppeteer_fail.png';
  await page.screenshot({ path: shot });
  console.error('Screenshot:', shot);
  process.exitCode = 1;
} finally {
  await browser.close();
}
