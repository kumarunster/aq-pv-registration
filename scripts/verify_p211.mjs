import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
try {
  await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await page.type('input[type="email"]', 'admin@amelanq.com');
  await page.type('input[type="password"]', 'Admin1234!');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 3000));
  const name = 'VerifKunde ' + String(Date.now()).slice(-6);
  await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 1000));
  // Formular öffnen
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde'));
    if (b) b.click();
  });
  await new Promise(r => setTimeout(r, 800));
  // Formular ausfüllen (sicher per native-setter)
  await page.evaluate((name) => {
    const inputs = [...document.querySelectorAll('form input')];
    const setVal = (el, v) => {
      const proto = Object.getPrototypeOf(el);
      const desc = Object.getOwnPropertyDescriptor(proto, 'value');
      if (desc && desc.set) { desc.set.call(el, v); } else { el.value = v; }
      el.dispatchEvent(new Event('input', { bubbles: true }));
    };
    if (inputs.length >= 5) {
      setVal(inputs[0], name);
      setVal(inputs[1], 'Test');
      setVal(inputs[2], 'Weg 1');
      setVal(inputs[3], '12345');
      setVal(inputs[4], 'Stadt');
    }
  }, name);
  await new Promise(r => setTimeout(r, 400));
  // Speichern
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button[type="submit"]')].find(b => /Speichern|anlegen|Speichern/.test(b.textContent));
    if (b) b.click();
  });
  await new Promise(r => setTimeout(r, 3000));
  // Suche setzen
  await page.evaluate((name) => {
    const inp = document.querySelector('input[type="search"]');
    if (!inp) return;
    const proto = Object.getPrototypeOf(inp);
    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
    if (desc && desc.set) { desc.set.call(inp, name); } else { inp.value = name; }
    inp.dispatchEvent(new Event('input', { bubbles: true }));
  }, name);
  await new Promise(r => setTimeout(r, 2000));
  const text = await page.evaluate(() => document.body.innerText);
  const found = text.includes(name);
  const audit = text.match(/Zuletzt geändert:[^\n]*|Erstellt:[^\n]*/g);
  console.log('Kunde gefunden:', found);
  console.log('Audit-Texte:', audit ? audit.slice(0,3) : 'keine');
  const ok11 = found && audit && audit.length > 0;
  console.log(ok11 ? '✅ P2-11 OK' : '❌ P2-11 Fehlschlag');
  await page.screenshot({ path: 'media/browser/p211_verify.png' });
} catch (e) {
  console.log('Fehler:', e.message, e.stack?.slice(0,500));
} finally {
  await browser.close();
}
