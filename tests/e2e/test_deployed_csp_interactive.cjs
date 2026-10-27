const { chromium } = require('playwright');

const DEPLOY_URL = process.env.DEPLOY_URL || 'https://utsav-ai.netlify.app';

async function testDeployedCsp() {
  console.log('=======================================================');
  console.log('RUNNING DEPLOYED CSP & INTERACTIVITY TEST');
  console.log(`Target URL: ${DEPLOY_URL}`);
  console.log('=======================================================\n');

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  const violations = [];
  const consoleMessages = [];

  page.on('console', msg => {
    const text = msg.text();
    consoleMessages.push(`[${msg.type()}] ${text}`);
    if (
      text.includes('Content Security Policy') ||
      text.includes('violates the following Content Security Policy') ||
      text.includes('Refused to execute inline script') ||
      text.includes('Refused to load') ||
      text.includes('Refused to apply inline style')
    ) {
      violations.push(`[Console ${msg.type()}] ${text}`);
    }
  });

  page.on('pageerror', err => {
    const text = err.message || '';
    if (text.includes('Content Security Policy') || text.includes('CSP')) {
      violations.push(`[PageError] ${text}`);
    }
  });

  console.log(`Navigating to ${DEPLOY_URL}...`);
  const response = await page.goto(DEPLOY_URL, {
    waitUntil: 'networkidle',
    timeout: 30000
  });

  console.log(`HTTP Status: ${response ? response.status() : 'N/A'}`);
  await page.waitForTimeout(2000);

  console.log('\n--- Interactivity Assertion ---');
  // Check for interactive button or link and click it
  const ctaButton = await page.$('a[href*="onboarding"], button, [role="button"]');
  let clickSucceeded = false;
  if (ctaButton) {
    const buttonText = (await ctaButton.innerText()).trim();
    console.log(`Found interactive element: "${buttonText}"`);
    try {
      await ctaButton.click({ timeout: 5000 });
      await page.waitForTimeout(1000);
      console.log(`Clicked "${buttonText}" successfully.`);
      console.log(`Current URL after click: ${page.url()}`);
      clickSucceeded = true;
    } catch (e) {
      console.error(`Failed to click "${buttonText}":`, e.message);
    }
  } else {
    console.error('No interactive CTA element found on the landing page!');
  }

  console.log('\n--- CSP Violation Summary ---');
  console.log(`Total CSP Violations Detected: ${violations.length}`);
  for (const v of violations) {
    console.log(`  ✗ ${v}`);
  }

  await browser.close();

  if (violations.length > 0) {
    console.error('\nFAILURE: CSP Violations detected on deployed URL.');
    process.exit(1);
  } else if (!clickSucceeded) {
    console.error('\nFAILURE: Page was not interactive.');
    process.exit(1);
  } else {
    console.log('\nSUCCESS: 0 CSP violations detected and page is interactive.');
    process.exit(0);
  }
}

testDeployedCsp().catch(err => {
  console.error('Fatal error in test:', err);
  process.exit(1);
});
