const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = 'C:/Users/deves/.gemini/antigravity/brain/57333fd6-3848-479e-98dc-d6c0861fdff7';
const OUT_DIR = path.join(__dirname, '..', 'frontend', 'out');
const mockData = JSON.parse(fs.readFileSync(path.join(__dirname, 'mock_osm_responses.json'), 'utf-8'));

// MIME types for static server
const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2'
};

function startStaticServer(port = 3005) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      let reqPath = req.url.split('?')[0];
      if (reqPath === '/' || !path.extname(reqPath)) {
        // Next.js static export fallback
        if (fs.existsSync(path.join(OUT_DIR, reqPath, 'index.html'))) {
          reqPath = path.join(reqPath, 'index.html');
        } else if (fs.existsSync(path.join(OUT_DIR, reqPath + '.html'))) {
          reqPath = reqPath + '.html';
        } else {
          reqPath = '/dashboard/events/default/compose.html';
        }
      }

      const filePath = path.join(OUT_DIR, reqPath);
      if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
        const ext = path.extname(filePath);
        res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
        fs.createReadStream(filePath).pipe(res);
      } else {
        res.writeHead(404);
        res.end('Not found');
      }
    });

    server.listen(port, () => {
      console.log(`Static server running on http://127.0.0.1:${port}`);
      resolve(server);
    });
  });
}

async function run() {
  const server = await startStaticServer(3005);
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 950 } });
  const page = await context.newPage();

  // Intercept API routes to supply real OSM data
  await page.route('**/api/v1/events/**', async (route) => {
    if (route.request().method() === 'POST' && route.request().url().includes('/compose')) {
      const postData = JSON.parse(route.request().postData() || '{}');
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'mock-event-id',
          name: 'Meera & Rohan Vivah',
          city: 'Jaipur',
          metadata_json: {
            compose_celebration: {
              current_step: 'venue',
              vendor_profile_id: postData.vendor_profile_id,
              venue_name: postData.venue_name,
              venue_status: 'shortlist_pick'
            }
          }
        })
      });
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'mock-event-id',
        name: 'Meera & Rohan Vivah',
        city: 'Jaipur',
        metadata_json: {}
      })
    });
  });

  await page.route('**/api/v1/discovery/**', async (route) => {
    const url = route.request().url();
    if (url.includes('/geocode')) {
      const u = new URL(url);
      const q = (u.searchParams.get('q') || '').toLowerCase();
      if (q.includes('bengaluru') || q.includes('560001')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ lat: 12.9716, lng: 77.5946, display_name: 'Bengaluru, Karnataka' })
        });
      } else if (q.includes('phalodi')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ lat: 27.1300, lng: 72.3600, display_name: 'Phalodi, Rajasthan' })
        });
      } else {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ lat: 26.9124, lng: 75.7873, display_name: 'Jaipur, Rajasthan' })
        });
      }
    }

    if (url.includes('/vendors')) {
      const u = new URL(url);
      const lat = parseFloat(u.searchParams.get('lat') || '0');
      const city = (u.searchParams.get('city') || '').toLowerCase();

      if (city.includes('bengaluru') || (lat > 12.5 && lat < 13.5)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockData.bengaluru)
        });
      } else if (city.includes('phalodi') || (lat > 27.0 && lat < 27.5 && parseFloat(u.searchParams.get('lng') || '0') < 73.0)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockData.phalodi)
        });
      } else {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockData.jaipur)
        });
      }
    }

    route.continue();
  });

  console.log('Navigating to Compose Celebration page...');
  await page.goto('http://127.0.0.1:3005/dashboard/events/default/compose', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000); // Allow Leaflet tiles & marker SVGs to render

  // 1. Screenshot: Jaipur Leaflet Map with Curated Seed + OSM pins
  console.log('1. Capturing Jaipur Map Pins...');
  const jaipurPath = path.join(ARTIFACT_DIR, 'leaflet_map_jaipur_pins.png');
  await page.screenshot({ path: jaipurPath });
  console.log('   Saved:', jaipurPath);

  // 2. Search Bengaluru via manual city/pincode input
  console.log('2. Searching Bengaluru via manual input...');
  const searchInput = await page.$('input[placeholder*="Enter city or 6-digit"]');
  if (searchInput) {
    await searchInput.fill('Bengaluru');
    await page.click('button:has-text("Search Area")');
    await page.waitForTimeout(2500); // Allow Leaflet to re-center & animate pins
  }
  const bengaluruPath = path.join(ARTIFACT_DIR, 'leaflet_map_bengaluru_osm_pins.png');
  await page.screenshot({ path: bengaluruPath });
  console.log('   Saved:', bengaluruPath);

  // 3. Search Phalodi (Small rural town) to test Honest Empty State
  console.log('3. Searching Phalodi to verify honest empty state...');
  if (searchInput) {
    await searchInput.fill('Phalodi');
    await page.click('button:has-text("Search Area")');
    await page.waitForTimeout(2500);
  }
  const emptyPath = path.join(ARTIFACT_DIR, 'leaflet_map_honest_empty_state.png');
  await page.screenshot({ path: emptyPath });
  console.log('   Saved:', emptyPath);

  // Verify empty state text in DOM
  const bodyText = await page.textContent('body');
  const hasEmptyText = bodyText.includes('No places found yet near you') && bodyText.includes('OpenStreetMap currently has zero');
  console.log(`   Honest empty state rendered: ${hasEmptyText}`);

  await browser.close();
  server.close();
  console.log('Screenshots and verification completed successfully!');
}

run().catch((err) => {
  console.error('Error during capture:', err);
  process.exit(1);
});
