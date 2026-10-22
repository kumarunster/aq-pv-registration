import puppeteer from 'puppeteer-core';

const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});
const page = await browser.newPage();

const log = [];
page.on('console', m => log.push('console: ' + m.text()));
page.on('pageerror', e => log.push('pageerror: ' + e.message));
const requests = [];
page.on('request', r => {
  const u = r.url();
  if (u.includes('kratos') || u.includes('api/admin'))
    requests.push(`REQ ${r.method()} ${u}`);
});
page.on('response', async r => {
  const u = r.url();
  if (u.includes('kratos') || u.includes('api/admin'))
    requests.push(`RES ${r.status()} ${r.request().method()} ${u}`);
});

try {
  // 1) Landing
  await page.goto(BASE + '/', { waitUntil: 'networkidle0', timeout: 30000 });
  console.log('LANDING:', page.url());

  // 2) Login-Seite
  await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
  console.log('LOGIN PAGE:', page.url());

  // 3) Formular ausfuellen
  await page.type('input[type="email"]', 'admin@amelanq.com');
  await page.type('input[type="password"]', 'Admin1234!');

  // 4) Absenden
  await Promise.all([
    page.click('button[type="submit"]'),
    page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 30000 }),
  ]);
  console.log('NACH LOGIN:', page.url());

  // 5) Admin-Inhalt
  const h1 = await page.$eval('h1', el => el.textContent).catch(() => 'kein h1');
  console.log('H1:', h1.trim());

  // 6) Admin-API im Browser
  const api = await page.evaluate(async () => {
    const r = await fetch('/api/admin/companies');
    return { status: r.status, body: (await r.text()).slice(0, 200) };
  });
  console.log('API /companies:', JSON.stringify(api));

  console.log('--- requests ---');
  for (const l of requests.slice(-15)) console.log(l);
  console.log('--- console ---');
  for (const l of log.slice(-15)) console.log(l);
} catch (e) {
  console.error('FEHLER:', e.message);
  console.log('URL:', page.url());
  const body = await page.evaluate(() => document.body?.innerText?.slice(0, 500)).catch(() => '');
  console.log('BODY:', body);
  console.log('--- requests ---');
  for (const l of requests.slice(-15)) console.log(l);
  console.log('--- console ---');
  for (const l of log.slice(-15)) console.log(l);
} finally {
  await browser.close();
}
