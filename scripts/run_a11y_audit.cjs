const { chromium } = require('playwright');

async function auditPage(url) {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage();
  console.log('\n========================================');
  console.log('AUDITING URL:', url);
  try {
    const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 35000 });
    console.log('HTTP Status:', resp ? resp.status() : 'unknown');
    if (resp && resp.status() >= 400) {
      console.log('Page returned HTTP error, skipping axe evaluation.');
      await browser.close();
      return;
    }
    // Inject axe-core from CDN
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

    console.log('Total Violations:', results.violations.length);
    console.log('Total Passes:', results.passes.length);
    for (const v of results.violations) {
      const tags = v.tags.filter(t => t.startsWith('wcag')).join(', ');
      console.log(`  - [${(v.impact || 'unknown').toUpperCase()}] ${v.id}: ${v.help} (${tags})`);
      console.log(`    Affected elements count: ${v.nodes.length}`);
      for (const node of v.nodes.slice(0, 2)) {
        console.log(`      Snippet: ${node.html.slice(0, 90).replace(/\n/g, ' ')}`);
        console.log(`      Summary: ${node.failureSummary ? node.failureSummary.split('\n')[0] : ''}`);
      }
    }
  } catch (err) {
    console.error('Audit error:', err.message);
  } finally {
    await browser.close();
  }
}

(async () => {
  await auditPage('https://utsav-ai.netlify.app/');
  await auditPage('https://utsav-ai.netlify.app/onboarding');
  await auditPage('https://utsav-ai.netlify.app/dashboard/events/default');
})();
