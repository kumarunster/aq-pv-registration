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

// Intercept submit event to check if handler is called
const handlerCheck = await page.evaluate(() => {
  const form = document.querySelector('form');
  
  // Add a capture-phase listener to detect if ANY submit handler runs
  let handlerCalled = false;
  let handlerInfo = [];
  
  form.addEventListener('submit', (e) => {
    handlerCalled = true;
    handlerInfo.push('capture-phase-listener-fired');
    console.log('SUBMIT-CAPTURE: ' + e.type + ' defaultPrevented=' + e.defaultPrevented);
  }, true);
  
  // Also check bubbling phase
  form.addEventListener('submit', (e) => {
    handlerInfo.push('bubble-phase-listener-fired');
  }, false);
  
  // Now trigger the submit
  const event = new Event('submit', { bubbles: true, cancelable: true });
  form.dispatchEvent(event);
  
  // Check what Vue did
  return {
    handlerCalled: handlerCalled,
    handlerInfo: handlerInfo,
    eventDefaultPrevented: event.defaultPrevented,
    // Check if there are any __vue__ props
    hasOnsubmit: !!form.onsubmit,
  };
});
console.log('Handler check:', JSON.stringify(handlerCheck, null, 2));

// Try to find Vue component tree
const vueTree = await page.evaluate(() => {
  const form = document.querySelector('form');
  if (!form) return { error: 'no form' };
  
  // Walk up the DOM tree looking for Vue instances
  let el = form;
  const found = [];
  while (el && found.length < 5) {
    if (el.__vue_app__ || el.__vueParentComponent || el.__vueParentApp) {
      found.push({
        tag: el.tagName,
        id: el.id,
        class: el.className?.toString().slice(0, 50),
        hasVueApp: !!el.__vue_app__,
        hasVueComponent: !!el.__vueParentComponent,
      });
    }
    el = el.parentElement;
  }
  
  // Check root app
  const root = document.querySelector('#app');
  return {
    rootHasVue: !!root?.__vue_app__,
    rootHasComponent: !!root?.__vueParentComponent,
    found: found,
  };
});
console.log('Vue tree:', JSON.stringify(vueTree, null, 2));

await browser.close();
