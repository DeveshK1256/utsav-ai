const { chromium } = require('playwright');

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

const ROUTES_TO_AUDIT = [
  '/',
  '/onboarding',
  '/dashboard',
  '/dashboard/events/default',
  '/dashboard/events/default/compose',
  '/dashboard/events/default/invitations',
  '/dashboard/events/default/guests',
  '/dashboard/events/default/vibe',
  '/dashboard/events/default/vendors/quotes',
  '/dashboard/events/default/changes/default',
  '/dashboard/vendors/quotes',
  '/privacy',
  '/demo'
];

async function runCspAudit() {
  console.log('=======================================================');
  console.log('RUNNING FULL-ROUTE PLAYWRIGHT CSP VIOLATION AUDIT');
  console.log(`Target: ${BASE_URL}`);
  console.log(`Routes to scan: ${ROUTES_TO_AUDIT.length}`);
  console.log('=======================================================\n');

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  const allCspViolations = [];

  for (const route of ROUTES_TO_AUDIT) {
    const targetUrl = `${BASE_URL}${route}`;
    const routeViolations = [];

    // Capture console messages
    const consoleHandler = (msg) => {
      const text = msg.text();
      const isCspViolation = (
        text.includes('Content Security Policy') ||
        text.includes('violates the following Content Security Policy') ||
        text.includes('Refused to execute inline script') ||
        text.includes('Refused to load') ||
        text.includes('Refused to apply inline style')
      );
      if (isCspViolation) {
        routeViolations.push(`[Console ${msg.type()}] ${text}`);
      }
    };

    // Capture page unhandled errors
    const errorHandler = (err) => {
      const msg = err.message || '';
      if (msg.includes('Content Security Policy') || msg.includes('CSP')) {
        routeViolations.push(`[PageError] ${msg}`);
      }
    };

    page.on('console', consoleHandler);
    page.on('pageerror', errorHandler);

    try {
      console.log(`[Scanning ${route}] Navigating...`);
      const resp = await page.goto(targetUrl, {
        waitUntil: 'domcontentloaded',
        timeout: 15000
      });

      const status = resp ? resp.status() : 'no-response';
      // Wait for client React hydration and any dynamic script execution
      await page.waitForTimeout(1000);

      if (routeViolations.length === 0) {
        console.log(`  ✓ ${route} (HTTP ${status}): 0 CSP violations`);
      } else {
        console.error(`  ✗ ${route} (HTTP ${status}): ${routeViolations.length} CSP violations detected!`);
        for (const v of routeViolations) {
          console.error(`     - ${v}`);
          allCspViolations.push(`${route} -> ${v}`);
        }
      }
    } catch (navErr) {
      console.error(`  ✗ ${route} Failed to load: ${navErr.message}`);
      allCspViolations.push(`${route} -> Navigation error: ${navErr.message}`);
    } finally {
      page.off('console', consoleHandler);
      page.off('pageerror', errorHandler);
    }
  }

  await browser.close();

  console.log('\n=======================================================');
  if (allCspViolations.length === 0) {
    console.log(`AUDIT SUCCESS: All ${ROUTES_TO_AUDIT.length} routes loaded with ZERO CSP violations!`);
    console.log('=======================================================');
    process.exit(0);
  } else {
    console.error(`AUDIT FAILED: ${allCspViolations.length} total CSP violations across routes:`);
    allCspViolations.forEach((v, idx) => console.error(`${idx + 1}. ${v}`));
    console.log('=======================================================');
    process.exit(1);
  }
}

runCspAudit().catch((err) => {
  console.error('Fatal audit runner error:', err);
  process.exit(1);
});
