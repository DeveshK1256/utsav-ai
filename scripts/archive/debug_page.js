const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    headless: true
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

  await page.goto('https://utsav-ai.netlify.app/dashboard/events/default', { waitUntil: 'load' });
  await page.waitForTimeout(3000);

  const html = await page.content();
  console.log("HTML length:", html.length);
  console.log("Contains Cultural:", html.includes("Cultural"));
  console.log("Contains Rituals:", html.includes("Rituals"));
  console.log("Buttons found:");
  const buttons = await page.$$eval('button', els => els.map(e => e.innerText));
  console.log(buttons);

  await page.screenshot({ path: 'scripts/initial_page.png' });
  await browser.close();
})();
