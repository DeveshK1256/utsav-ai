const { chromium } = require('playwright');
const { AxeBuilder } = require('@axe-core/playwright');

const BASE_URL = process.env.AUDIT_URL || 'https://utsav-ai.netlify.app';

const ROUTES = [
  '/',
  '/onboarding',
  '/dashboard/events/default',
  '/dashboard/events/default/compose'
];

async function runAxeAudit() {
  console.log(`=== AXE-CORE ACCESSIBILITY AUDIT AGAINST ${BASE_URL} ===\n`);
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  let totalViolations = 0;

  for (const route of ROUTES) {
    const page = await context.newPage();
    const url = `${BASE_URL}${route}`;
    console.log(`Scanning: ${url}...`);
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(2000); // Allow React hydration and Leaflet/canvas to settle

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
        .analyze();

      const violations = accessibilityScanResults.violations;
      console.log(`  -> Violations found: ${violations.length}`);
      if (violations.length > 0) {
        totalViolations += violations.length;
        violations.forEach(v => {
          console.log(`     [${v.impact?.toUpperCase()}] ${v.id}: ${v.help} (${v.nodes.length} nodes)`);
          v.nodes.slice(0, 3).forEach(n => console.log(`       - Target: ${n.target.join(' ')}`));
        });
      }
    } catch (e) {
      console.error(`  Error scanning ${url}:`, e.message);
      totalViolations++;
    } finally {
      await page.close();
    }
  }

  await browser.close();
  console.log(`\nTotal Axe Violations across ${ROUTES.length} routes: ${totalViolations}`);
  process.exit(totalViolations > 0 ? 1 : 0);
}

runAxeAudit();
