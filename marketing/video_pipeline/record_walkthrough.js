const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TIMING_FILE = path.join(__dirname, 'timing_manifest.json');
const manifest = JSON.parse(fs.readFileSync(TIMING_FILE, 'utf-8'));
const BEATS = manifest.beats;
const CLIPS_DIR = path.join(__dirname, 'clips');
if (!fs.existsSync(CLIPS_DIR)) {
  fs.mkdirSync(CLIPS_DIR, { recursive: true });
}

const BASE_URL = 'http://localhost:3000';

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function recordBeat(browser, beat, recordLogic) {
  const targetDurationMs = (beat.duration + 0.45) * 1000;
  console.log(`[Recording] ${beat.id} (${beat.title}) - Target: ${(targetDurationMs / 1000).toFixed(2)}s`);
  
  const videoDir = path.join(CLIPS_DIR, `temp_${beat.id}`);
  if (fs.existsSync(videoDir)) {
    fs.rmSync(videoDir, { recursive: true, force: true });
  }
  fs.mkdirSync(videoDir, { recursive: true });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: {
      dir: videoDir,
      size: { width: 1280, height: 720 }
    }
  });

  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.setDefaultNavigationTimeout(15000);

  const startTime = Date.now();

  try {
    await recordLogic(page, targetDurationMs);
  } catch (err) {
    console.error(`Error in beat ${beat.id}:`, err.message);
  }

  // Ensure clip runs for the exact narration beat duration
  const elapsed = Date.now() - startTime;
  if (elapsed < targetDurationMs) {
    await sleep(targetDurationMs - elapsed);
  }

  await page.close();
  await context.close();

  // Find recorded webm and rename
  const files = fs.readdirSync(videoDir).filter(f => f.endsWith('.webm'));
  if (files.length > 0) {
    const origVideo = path.join(videoDir, files[0]);
    const finalVideo = path.join(CLIPS_DIR, `${beat.id}.webm`);
    if (fs.existsSync(finalVideo)) fs.unlinkSync(finalVideo);
    fs.renameSync(origVideo, finalVideo);
    fs.rmSync(videoDir, { recursive: true, force: true });
    console.log(`  -> Saved ${finalVideo} (Elapsed: ${((Date.now() - startTime)/1000).toFixed(2)}s)`);
  }
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--enable-webgl', '--use-gl=angle', '--use-angle=swiftshader']
  });

  // BEAT 1: Chaos to Calm (Hero Landing + Chaos to Composed toggle)
  await recordBeat(browser, BEATS[0], async (page, dur) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'load' });
    await sleep(1500);
    // Smooth scroll down to highlight Chaos to Composed transition
    await page.evaluate(() => {
      window.scrollBy({ top: 380, behavior: 'smooth' });
    });
    await sleep(2500);
    await page.evaluate(() => {
      window.scrollBy({ top: 320, behavior: 'smooth' });
    });
    await sleep(2500);
  });

  // BEAT 2: Guided Onboarding
  await recordBeat(browser, BEATS[1], async (page, dur) => {
    await page.goto(`${BASE_URL}/onboarding`, { waitUntil: 'load' });
    await sleep(1200);
    const weddingOption = page.locator('text=Wedding').first();
    if (await weddingOption.isVisible()) {
      await weddingOption.click();
    }
    await sleep(1500);
    const cityInput = page.locator('input[placeholder*="City"], input[type="text"]').first();
    if (await cityInput.isVisible()) {
      await cityInput.fill('Jaipur, Rajasthan');
    }
    await sleep(2000);
    const budgetInput = page.locator('input[type="number"], input[placeholder*="Budget"]').first();
    if (await budgetInput.isVisible()) {
      await budgetInput.fill('1500000');
    }
    await sleep(2000);
  });

  // BEAT 3: Unified Celebration Hub (Dashboard)
  await recordBeat(browser, BEATS[2], async (page, dur) => {
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'load' });
    await sleep(1500);
    await page.evaluate(() => {
      window.scrollBy({ top: 250, behavior: 'smooth' });
    });
    await sleep(2500);
    const navItem = page.locator('nav a, header a, button').nth(1);
    if (await navItem.isVisible()) {
      await navItem.hover();
    }
    await sleep(2500);
  });

  // BEAT 4: Deterministic Budget Breakdown (Quotes comparison)
  await recordBeat(browser, BEATS[3], async (page, dur) => {
    await page.goto(`${BASE_URL}/dashboard/vendors/quotes`, { waitUntil: 'load' });
    await sleep(1500);
    await page.evaluate(() => {
      window.scrollBy({ top: 200, behavior: 'smooth' });
    });
    await sleep(2500);
    const tableRow = page.locator('table tr, .quote-card, article').first();
    if (await tableRow.isVisible()) {
      await tableRow.hover();
    }
    await sleep(3000);
  });

  // BEAT 5: Nationwide Nearby Venue Map (Leaflet map + OSM pins)
  await recordBeat(browser, BEATS[4], async (page, dur) => {
    await page.goto(`${BASE_URL}/dashboard/events/default/compose`, { waitUntil: 'load' });
    await sleep(1500);
    const map = page.locator('.leaflet-container').first();
    if (await map.isVisible()) {
      const box = await map.boundingBox();
      if (box) {
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await sleep(1000);
        await page.mouse.wheel(0, -100);
      }
    } else {
      await page.evaluate(() => window.scrollBy({ top: 300, behavior: 'smooth' }));
    }
    await sleep(3500);
  });

  // BEAT 6: Auspicious Muhurat Timing (Rituals and timing wisdom)
  await recordBeat(browser, BEATS[5], async (page, dur) => {
    await page.goto(`${BASE_URL}/dashboard/events/default/compose`, { waitUntil: 'load' });
    await sleep(1500);
    await page.evaluate(() => {
      window.scrollTo({ top: 800, behavior: 'smooth' });
    });
    await sleep(2500);
    const muhuratCard = page.locator('text=Muhurat, text=Auspicious, text=Timing').first();
    if (await muhuratCard.isVisible()) {
      await muhuratCard.hover();
    }
    await sleep(2500);
  });

  // BEAT 7: Invitation Cards & Closing CTA
  await recordBeat(browser, BEATS[6], async (page, dur) => {
    await page.goto(`${BASE_URL}/dashboard/events/default/invitations`, { waitUntil: 'load' });
    await sleep(1500);
    const cardPreview = page.locator('img, .invitation-card, article').first();
    if (await cardPreview.isVisible()) {
      await cardPreview.hover();
    }
    await sleep(2000);
    await page.evaluate(() => window.scrollBy({ top: 250, behavior: 'smooth' }));
    await sleep(2500);
  });

  await browser.close();
  console.log('[All Clips Recorded]');
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
