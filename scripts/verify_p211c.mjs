import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const reqs = [];
page.on('request', r => { if (r.url().includes('/api/')) reqs.push({method: r.method(), url: r.url().replace(BASE,''), body: (r.postData()||'').slice(0,300)}); });
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
      const d = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
      if (d && d.set) d.set.call(el, v); else el.value = v;
      el.dispatchEvent(new Event('input', { bubbles: true }));
    };
    if (inputs.length >= 5) { setVal(inputs[0], name); setVal(inputs[1], 'Test'); setVal(inputs[2], 'Weg 1'); setVal(inputs[3], '12345'); setVal(inputs[4], 'Stadt'); }
    console.log('Inputs:', inputs.length);
  }, name);
  await new Promise(r => setTimeout(r, 400));
  const clicked = await page.evaluate(() => {
    const b = [...document.querySelectorAll('button[type="submit"]')].find(b => /speichern|anlegen/i.test(b.textContent));
    console.log('Button:', b ? b.textContent.trim() : null);
    if (b) b.click();
    return b ? true : false;
  });
  await new Promise(r => setTimeout(r, 3000));
  console.log('POST-Requests:', JSON.stringify(reqs.filter(r => r.method === 'POST' || r.method === 'PUT'), null, 2));
} catch (e) {
  console.log('Fehler:', e.message);
} finally {
  await browser.close();
}
