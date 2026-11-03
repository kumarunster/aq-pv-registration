import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const logs = [];
page.on('console', m => logs.push('CONSOLE: ' + m.text()));
page.on('response', async r => { if (r.url().includes('/api/')) { const b = await r.text().catch(()=> ''); logs.push('RESP ' + r.status() + ' ' + r.url().replace(BASE,'') + (b.slice(0,120))); } });
try {
  await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await page.type('input[type="email"]', 'admin@amelanq.com');
  await page.type('input[type="password"]', 'Admin1234!');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 3000));
  const name = 'VerifKunde ' + String(Date.now()).slice(-6);
  await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 1000));
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde'));
    if (b) b.click();
  });
  await new Promise(r => setTimeout(r, 800));
  await page.evaluate((name) => {
    const inputs = [...document.querySelectorAll('form input')];
    const setVal = (el, v) => {
      const desc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
      if (desc && desc.set) desc.set.call(el, v); else el.value = v;
      el.dispatchEvent(new Event('input', { bubbles: true }));
    };
    // FormCustomer: 0=Vorname 1=Nachname 2=Straße 3=PLZ 4=Ort (5)
    if (inputs.length >= 5) { setVal(inputs[0], name); setVal(inputs[1], 'Test'); setVal(inputs[2], 'Weg 1'); setVal(inputs[3], '12345'); setVal(inputs[4], 'Stadt'); }
    else console.log('nur', inputs.length, 'Form-Inputs');
  }, name);
  await new Promise(r => setTimeout(r, 400));
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button[type="submit"]')].find(b => /Speichern|anlegen/i.test(b.textContent));
    console.log('Submit-Button:', b ? b.textContent.trim() : 'NICHT GEFUNDEN');
    if (b) b.click();
  });
  await new Promise(r => setTimeout(r, 3000));
  // Kunde in DB?
  const dbHas = await page.evaluate(async (name) => {
    const r = await fetch('/api/admin/customers/search?q=' + encodeURIComponent(name), { headers: { 'Accept': 'application/json' } });
    const d = await r.json();
    return (Array.isArray(d) ? d : []).length;
  }, name);
  console.log('Kunden via API:', dbHas);
  // Liste neu laden
  await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 1500));
  await page.evaluate((name) => {
    const inp = document.querySelector('input[type="search"]');
    const desc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(inp), 'value');
    if (desc && desc.set) desc.set.call(inp, name); else inp.value = name;
    inp.dispatchEvent(new Event('input', { bubbles: true }));
  }, name);
  await new Promise(r => setTimeout(r, 2500));
  const text = await page.evaluate(() => document.body.innerText);
  console.log('Kunde in UI:', text.includes(name));
  console.log('Audit-Texte:', (text.match(/Zuletzt geändert:[^\n]*|Erstellt:[^\n]*/g) || 'keine').slice(0,3));
  const last = logs.filter(l => l.startsWith('RESP') && (l.includes('customer') || l.includes('Customer'))).slice(-6);
  console.log('API-Log:', last);
} catch (e) {
  console.log('Fehler:', e.message);
} finally {
  await browser.close();
}
