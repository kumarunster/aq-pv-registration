import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const requests = [];
page.on('response', async r => { 
  if (r.url().includes('stats')) {
    const body = await r.text().catch(() => 'fehler');
    requests.push({url: r.url(), status: r.status(), text: body.slice(0,200)});
  }
});
try {
  await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await page.type('input[type="email"]', 'admin@amelanq.com');
  await page.type('input[type="password"]', 'Admin1234!');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 3000));
  await page.goto(BASE + '/admin/firmen', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 2000));
  console.log('Stats-Requests:', JSON.stringify(requests, null, 2));
  const statsText = await page.evaluate(() => document.body.innerText);
  const hasStats = /👥 \d+ Kunde\w* · 🔌 \d+ Anlag\w+/.test(statsText);
  const match = statsText.match(/[👥🔌][^\n]*/g);
  console.log('P2-10 Stats sichtbar:', hasStats);
  console.log('Stats-Text:', match ? match.slice(0,5) : 'keine');
  hasStats ? console.log('✅ P2-10 OK') : console.log('❌ P2-10 Fehlschlag');
} catch (e) {
  console.log('Fehler:', e.message);
} finally {
  await browser.close();
}
