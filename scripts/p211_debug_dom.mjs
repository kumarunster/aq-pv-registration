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

// Check DOM structure
const domCheck = await page.evaluate(() => {
  const form = document.querySelector('form');
  if (!form) return { error: 'no form' };
  
  // Check all attributes
  const attrs = {};
  for (const attr of form.attributes) {
    attrs[attr.name] = attr.value;
  }
  
  // Check event listeners (approximate)
  const hasVue = !!form.__vue_app__ || !!form.__vueParentComponent;
  
  // Check form submission behavior
  return {
    formPresent: true,
    attributes: attrs,
    hasVue: hasVue,
    formAction: form.action,
    formMethod: form.method,
    formTarget: form.target,
    formNoValidate: form.noValidate,
    childCount: form.children.length,
    firstChildTag: form.children[0]?.tagName,
    buttonCount: form.querySelectorAll('button').length,
    submitButtonCount: form.querySelectorAll('button[type="submit"]').length,
  };
});
console.log('DOM check:', JSON.stringify(domCheck, null, 2));

// Test: does form.submit() work?
const submitTest = await page.evaluate(() => {
  const form = document.querySelector('form');
  const originalSubmit = form.submit;
  let called = false;
  form.submit = function() { called = true; };
  
  // Try triggering submit event
  const event = new Event('submit', { bubbles: true, cancelable: true });
  const result = form.dispatchEvent(event);
  
  form.submit = originalSubmit;
  return { submitCalled: called, eventDefaultPrevented: event.defaultPrevented };
});
console.log('Submit test:', JSON.stringify(submitTest));

await browser.close();
