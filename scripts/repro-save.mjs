// Save-Bug-Reproduktion: Firma anlegen + komplettes Request-Log
import puppeteer from 'puppeteer-core';

const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

const trace = [];
const log = (t) => { trace.push({ t: Date.now(), ...t }); console.log(t.type, t.method || '', t.url || t.text || ''); };

page.on('request', r => log({ type: 'REQ', method: r.method(), url: r.url() }));
page.on('requestfailed', r => log({ type: 'REQFAIL', method: r.method(), url: r.url(), err: r.failure()?.errorText }));
page.on('response', r => log({ type: 'RES', status: r.status(), method: r.request().method(), url: r.url() }));
page.on('dialog', async d => { log({ type: 'DIALOG', text: d.message() }); await d.dismiss().catch(() => {}); });
page.on('framenavigated', f => log({ type: 'NAV', url: f.url() }));
page.on('pageerror', e => log({ type: 'PAGEERROR', text: e.message }));
page.on('console', m => log({ type: 'CONSOLE', text: m.text() }));

// Hooks vor jeder Navigation einbauen
const HOOK = `
(() => {
  if (window.__hooked) return;
  window.__hooked = true;
  const t = () => Date.now();
  const desc = (name) => {
    const orig = window[name];
    Object.defineProperty(window, name, {
      configurable: true,
      set: (v) => { console.log('HOOK-SET ' + name + ' = ' + v + ' @ ' + t()); orig && orig(v); },
      get: () => (orig && typeof orig === 'function' ? orig.call(window) : undefined),
    });
  };
  ['location', 'location.href', 'location.assign', 'location.replace'].forEach(() => {});
  const origAssign = window.location.assign.bind(window.location);
  const origReplace = window.location.replace.bind(window.location);
  window.location.assign = (u) => { console.log('HOOK-ASSIGN ' + u + ' @ ' + t()); return origAssign(u); };
  window.location.replace = (u) => { console.log('HOOK-REPLACE ' + u + ' @ ' + t()); return origReplace(u); };
  window.addEventListener('beforeunload', (e) => console.log('HOOK-BEFOREUNLOAD fired, dirty? @ ' + t()));
  console.log('HOOKS installed @ ' + t());
})();
`;

try {
  await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0', timeout: 30000 });
  await page.evaluateOnNewDocument(HOOK);
  await page.reload({ waitUntil: 'networkidle0' });
  await page.type('input[type="email"]', 'admin@amelanq.com');
  await page.type('input[type="password"]', 'Admin1234!');

  log({ type: 'MARK', text: '--- LOGIN-CLICK ---' });
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 3000));
  log({ type: 'INFO', text: 'URL nach Login: ' + page.url() });

  await page.goto(BASE + '/admin/firmen', { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 1000));

  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neue Firma'));
    b && b.click();
  });
  await new Promise(r => setTimeout(r, 800));

  const ts = String(Date.now()).slice(-6);
  await page.type('input[required]', 'Testfirma ' + ts);
  await page.evaluate(() => {
    const inputs = [...document.querySelectorAll('form input[required]')];
    // Straße, PLZ, Ort nach dem Namen
    inputs[1] && (inputs[1].value = 'Teststr. 1', inputs[1].dispatchEvent(new Event('input', { bubbles: true })));
  });
  await new Promise(r => setTimeout(r, 300));

  log({ type: 'MARK', text: '--- SAVE-CLICK ---' });
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('button[type="submit"]')].find(b => b.textContent.includes('Firma anlegen'));
    b && b.click();
  });
  await new Promise(r => setTimeout(r, 4000));
  log({ type: 'INFO', text: 'URL nach Save: ' + page.url() });

  // Whoami-Check
  const whoami = await page.evaluate(async () => {
    const r = await fetch('/kratos/sessions/whoami', { headers: { Accept: 'application/json' } });
    return r.status;
  }).catch(e => 'ERR ' + e.message);
  log({ type: 'INFO', text: 'whoami-Status: ' + whoami });

} catch (e) {
  log({ type: 'ERROR', text: e.message });
} finally {
  await browser.close();
  const fs = await import('fs');
  fs.writeFileSync('media/browser/ux-review3/save-trace-final.json', JSON.stringify(trace, null, 2));
  console.log('TRACE-GESPEICHERT:', trace.length, 'Einträge');
}
