import puppeteer from 'puppeteer-core';
const CHROME = '/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome';
const BASE = 'http://localhost:8092';
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

// Login
await page.goto(BASE + '/admin/login', { waitUntil: 'networkidle0' });
await page.type('input[type="email"]', 'admin@amelanq.com');
await page.type('input[type="password"]', 'Admin1234!');
await page.click('button[type="submit"]');
await new Promise(r => setTimeout(r, 3000));

// Navigate to customers
await page.goto(BASE + '/admin/kunden', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1500));

// Open NEW customer form
await page.evaluate(() => { 
  const b = [...document.querySelectorAll('button')].find(b => b.textContent.includes('Neuer Kunde')); 
  if (b) b.click(); 
});
await new Promise(r => setTimeout(r, 800));

// Check Vue instance on form
const vueCheck = await page.evaluate(() => {
  const form = document.querySelector('form');
  if (!form) return { form: false };
  
  // Vue 3 stores component instance on DOM element
  const vueInstance = form.__vueParentComponent;
  if (!vueInstance) return { form: true, vue: false, formId: form.id };
  
  const setupState = vueInstance.setupState || {};
  const props = vueInstance.props || {};
  const emits = vueInstance.emits || {};
  
  return {
    form: true,
    vue: true,
    hasSave: typeof setupState.save === 'function',
    saveType: typeof setupState.save,
    props: Object.keys(props),
    emits: Object.keys(emits),
    formDirty: setupState.formDirty,
    saving: setupState.saving,
    formKeys: Object.keys(setupState.form || {})
  };
});
console.log('Vue check:', JSON.stringify(vueCheck, null, 2));

// Try calling save directly via Vue
const saveResult = await page.evaluate(() => {
  const form = document.querySelector('form');
  const vueInstance = form?.__vueParentComponent;
  if (!vueInstance) return { error: 'no vue instance' };
  
  const setupState = vueInstance.setupState;
  if (typeof setupState.save !== 'function') return { error: 'save not found', keys: Object.keys(setupState).slice(0, 20) };
  
  try {
    setupState.save();
    return { called: true };
  } catch (e) {
    return { error: e.message };
  }
});
console.log('Save call result:', JSON.stringify(saveResult));

await new Promise(r => setTimeout(r, 3000));
console.log('URL:', page.url());

await browser.close();
