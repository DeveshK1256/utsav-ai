/**
 * Comprehensive Live E2E & Accessibility Verification on Netlify Production Deployment
 * Target: https://utsav-ai.netlify.app
 * 
 * 1. End-to-End User Intake Wizard Session:
 *    - Steps through Onboarding Wizard (Steps 1 -> 2 -> 3 -> 4)
 *    - Submits live synthesis to Render backend
 *    - Validates owner_token stored in localStorage
 *    - Clicks 'Open Event Workspace' and lands on /dashboard/events/{id}
 *    - Verifies event data renders cleanly with ZERO 403 Forbidden errors
 * 2. WCAG 2.1 AA Accessibility Audit via axe-core against live Netlify pages:
 *    - Landing Page: https://utsav-ai.netlify.app/
 *    - Onboarding: https://utsav-ai.netlify.app/onboarding
 *    - Dashboard: https://utsav-ai.netlify.app/dashboard/events/default
 *    - Compose: https://utsav-ai.netlify.app/dashboard/events/default/compose
 */
const { chromium } = require('playwright');

const BASE_URL = 'https://utsav-ai.netlify.app';

async function runAudit() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  console.log('====================================================');
  console.log('PART 1: LIVE ONBOARDING & AUTHENTICATED DASHBOARD E2E');
  console.log('====================================================');

  console.log(`Navigating to ${BASE_URL}/onboarding...`);
  await page.goto(`${BASE_URL}/onboarding`, { waitUntil: 'networkidle', timeout: 45000 });

  // STEP 1 -> STEP 2
  console.log('On Step 1 (Basics). Advancing to Step 2...');
  const step1Btn = page.locator('button:has-text("Continue to Format & Heritage")');
  await step1Btn.waitFor({ state: 'visible', timeout: 15000 });
  await step1Btn.click();
  await page.waitForTimeout(1000);

  // STEP 2 -> STEP 3
  console.log('On Step 2 (Format & Heritage). Advancing to Step 3...');
  const step2Btn = page.locator('button:has-text("Continue to Scale & Budget")');
  await step2Btn.waitFor({ state: 'visible', timeout: 15000 });
  await step2Btn.click();
  await page.waitForTimeout(1000);

  // STEP 3 -> STEP 4
  console.log('On Step 3 (Scale & Budget). Advancing to Step 4...');
  const step3Btn = page.locator('button:has-text("Review & Compose Plan")');
  await step3Btn.waitFor({ state: 'visible', timeout: 15000 });
  await step3Btn.click();
  await page.waitForTimeout(1000);

  // STEP 4 -> SYNTHESIZE
  console.log('On Step 4 (Review). Submitting synthesis to live Render backend...');
  const synthBtn = page.locator('button:has-text("Synthesize Master Plan")');
  await synthBtn.waitFor({ state: 'visible', timeout: 15000 });
  await synthBtn.click();

  // Wait for Step 5 (Plan Composed)
  console.log('Waiting for plan synthesis completion from live API...');
  const openWorkspaceBtn = page.locator('a:has-text("Open Event Workspace")');
  await openWorkspaceBtn.waitFor({ state: 'visible', timeout: 35000 });
  console.log('Plan synthesis succeeded! Open Event Workspace link visible.');

  // Check localStorage for owner token
  const tokens = await page.evaluate(() => {
    const res = {};
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith('utsav_') || key.includes('token'))) {
        res[key] = localStorage.getItem(key);
      }
    }
    return res;
  });
  console.log('Owner Tokens in localStorage:', JSON.stringify(tokens));

  // Click Open Event Workspace
  console.log('Clicking Open Event Workspace link...');
  await openWorkspaceBtn.click();
  await page.waitForURL(url => url.pathname.includes('/dashboard/events/'), { timeout: 25000 });
  console.log('Navigated to live workspace URL:', page.url());
  await page.waitForTimeout(3000);

  // Check if unauthenticated 403 errors occurred
  const auth403Errors = consoleErrors.filter(e => e.includes('403') || e.includes('Forbidden'));
  console.log('403/Forbidden Console Errors on Workspace:', auth403Errors.length === 0 ? 'ZERO (PASSED)' : auth403Errors);

  // Verify workspace content rendered
  const workspaceText = await page.textContent('body');
  const hasWorkspaceData = workspaceText.includes('Budget') || workspaceText.includes('Itinerary') || workspaceText.includes('Guests');
  console.log('Live workspace content successfully rendered:', hasWorkspaceData);

  console.log('\n====================================================');
  console.log('PART 2: LIVE ACCESSIBILITY AUDIT (AXE-CORE WCAG 2.1 AA)');
  console.log('====================================================');

  const urlsToAudit = [
    `${BASE_URL}/`,
    `${BASE_URL}/onboarding`,
    `${BASE_URL}/dashboard/events/default`,
    `${BASE_URL}/dashboard/events/default/compose`
  ];

  let totalViolationsAcrossPages = 0;

  for (const auditUrl of urlsToAudit) {
    console.log(`\nAuditing URL: ${auditUrl}`);
    await page.goto(auditUrl, { waitUntil: 'domcontentloaded', timeout: 35000 });
    await page.waitForTimeout(2000);

    // Inject axe-core
    await page.addScriptTag({ url: 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js' });
    const results = await page.evaluate(async () => {
      // @ts-ignore
      return await axe.run({
        runOnly: {
          type: 'tag',
          values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
        }
      });
    });

    console.log(`  Total Violations: ${results.violations.length}`);
    console.log(`  Total Passes: ${results.passes.length}`);
    totalViolationsAcrossPages += results.violations.length;

    if (results.violations.length > 0) {
      for (const v of results.violations) {
        console.log(`  [VIOLATION] ${v.id}: ${v.help} (Impact: ${v.impact})`);
      }
    } else {
      console.log('  >>> ZERO WCAG 2.1 AA VIOLATIONS CONFIRMED ON LIVE PAGE! <<<');
    }
  }

  console.log('\n====================================================');
  console.log(`OVERALL AUDIT SUMMARY: Total Violations Across All Live Pages = ${totalViolationsAcrossPages}`);
  console.log('====================================================');

  await browser.close();
}

runAudit().catch(err => {
  console.error('Audit failed with error:', err);
  process.exit(1);
});
