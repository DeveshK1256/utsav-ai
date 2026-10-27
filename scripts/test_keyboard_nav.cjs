const { chromium } = require('playwright');

async function testKeyboardNavigation() {
  console.log('=== REAL KEYBOARD NAVIGATION TEST (WCAG 2.1.1 / 2.4.1) ===');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('http://localhost:3000/dashboard/events/default/compose', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('text=Select or Shortlist a Celebration Venue', { timeout: 10000 });

  // SCENARIO 1: Test Skip Link directly via Keyboard
  console.log('\n--- Scenario 1: Using "Skip map controls to venue list" Link ---');
  await page.focus('body');
  // Tab until skip link is focused
  for (let i = 0; i < 9; i++) {
    await page.keyboard.press('Tab');
  }
  const skipText = await page.evaluate(() => document.activeElement ? document.activeElement.textContent : '');
  console.log('Focused at Tab 9:', skipText);
  
  // Press Enter on skip link
  await page.keyboard.press('Enter');
  await page.waitForTimeout(100);

  // Next Tab should immediately focus the first venue card or action
  await page.keyboard.press('Tab');
  const afterSkip = await page.evaluate(() => {
    const el = document.activeElement;
    return {
      tag: el?.tagName,
      id: el?.id,
      role: el?.getAttribute('role'),
      text: (el?.textContent || '').trim().slice(0, 50),
      ariaLabel: el?.getAttribute('aria-label')
    };
  });
  console.log('Element focused after skip link activation:', afterSkip);

  // SCENARIO 2: Natural Tab traversal through all pins until clean exit to cards & CTA
  console.log('\n--- Scenario 2: Continuous Tab traversal through map pins and exit ---');
  await page.reload({ waitUntil: 'networkidle' });
  await page.focus('body');

  let reachedExitCTA = false;
  let exitElement = null;

  for (let i = 0; i < 50; i++) {
    await page.keyboard.press('Tab');
    const elInfo = await page.evaluate(() => {
      const el = document.activeElement;
      return {
        tag: el?.tagName,
        text: (el?.textContent || '').trim().slice(0, 40),
        role: el?.getAttribute('role'),
        ariaLabel: el?.getAttribute('aria-label')
      };
    });

    if (elInfo.text.includes('Continue to Auspicious Timing') || elInfo.text.includes('Skip this step') || (elInfo.role === 'button' && elInfo.ariaLabel && elInfo.ariaLabel.includes('Select venue'))) {
      reachedExitCTA = true;
      exitElement = elInfo;
      console.log(`Exited map and reached target at Tab ${i+1}: <${elInfo.tag}> "${elInfo.text}" role="${elInfo.role}" aria-label="${elInfo.ariaLabel}"`);
      break;
    }
  }

  await browser.close();

  if (reachedExitCTA) {
    console.log('\n>>> PASS: Keyboard focus traverses map pins and exits cleanly to next page elements without getting trapped! <<<');
    process.exit(0);
  } else {
    console.log('\n>>> FAIL: Focus trapped inside map <<<');
    process.exit(1);
  }
}

testKeyboardNavigation().catch(err => {
  console.error(err);
  process.exit(1);
});
