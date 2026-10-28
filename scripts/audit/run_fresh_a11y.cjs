const { chromium } = require('playwright');

async function auditPage(url) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  console.log('\n========================================');
  console.log('AUDITING URL:', url);
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 35000 });
    console.log('HTTP Status:', resp ? resp.status() : 'unknown');
    if (resp && resp.status() >= 400) {
      console.log('Page returned HTTP error, skipping axe evaluation.');
      await browser.close();
      return;
    }
    await page.waitForTimeout(2000);
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

    // Inspect video caption tracks if present
    const videoDetails = await page.evaluate(() => {
      const v = document.querySelector('video');
      if (!v) return null;
      const tracks = Array.from(v.querySelectorAll('track')).map(t => ({
        kind: t.getAttribute('kind'),
        srclang: t.getAttribute('srclang'),
        src: t.getAttribute('src'),
        default: t.hasAttribute('default')
      }));
      return { hasVideo: true, tracks };
    });
    if (videoDetails) {
      console.log('Video Element Audit:', JSON.stringify(videoDetails));
    }

    // Inspect Leaflet map keyboard operability if present
    const mapDetails = await page.evaluate(() => {
      const map = document.querySelector('.leaflet-container');
      if (!map) return null;
      const markers = map.querySelectorAll('.leaflet-marker-icon');
      const tabIndexes = Array.from(markers).map(m => m.getAttribute('tabindex') || m.tabIndex);
      return { markerCount: markers.length, tabIndexes };
    });
    if (mapDetails) {
      console.log('Leaflet Map Keyboard Operability:', JSON.stringify(mapDetails));
    }

  } catch (err) {
    console.error('Audit error:', err.message);
  } finally {
    await browser.close();
  }
}

(async () => {
  await auditPage('http://localhost:3000/');
  await auditPage('http://localhost:3000/onboarding');
  await auditPage('http://localhost:3000/dashboard/events/default');
  await auditPage('http://localhost:3000/dashboard/events/default/compose');
})();
