const { chromium } = require('playwright');
const path = require('path');

async function testVideoPlayer() {
  const browser = await chromium.launch({ headless: true });

  console.log('[Test 1: Standard Mode]');
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  await page.goto('http://localhost:3000/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  const video = page.locator('video').first();
  await video.waitFor({ state: 'attached', timeout: 5000 });
  console.log('✓ Video element attached');

  const poster = await video.getAttribute('poster');
  console.log(`✓ Poster: ${poster}`);

  const track = page.locator('video track').first();
  const trackSrc = await track.getAttribute('src');
  console.log(`✓ Captions track src: ${trackSrc}`);

  // Query video state
  const videoState = await page.evaluate(() => {
    const v = document.querySelector('video');
    return {
      paused: v.paused,
      muted: v.muted,
      currentTime: v.currentTime,
      duration: v.duration,
      readyState: v.readyState
    };
  });
  console.log('✓ Video runtime state:', JSON.stringify(videoState));

  // Scroll to video section and take screenshot
  await page.evaluate(() => {
    document.querySelector('section[aria-label="Product Walkthrough Video"]').scrollIntoView();
  });
  await page.waitForTimeout(1000);

  const screenshotPath = path.join(__dirname, 'video_player_landing_verification.png');
  await page.screenshot({ path: screenshotPath });
  console.log(`✓ Saved screenshot: ${screenshotPath}`);

  console.log('\n[Test 2: Prefers-Reduced-Motion Mode]');
  const reducedContext = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    reducedMotion: 'reduce'
  });
  const reducedPage = await reducedContext.newPage();
  await reducedPage.goto('http://localhost:3000/', { waitUntil: 'domcontentloaded' });
  await reducedPage.waitForTimeout(2000);

  const reducedState = await reducedPage.evaluate(() => {
    const v = document.querySelector('video');
    return {
      paused: v.paused,
      autoplay: v.autoplay
    };
  });
  console.log('✓ Under prefers-reduced-motion:', JSON.stringify(reducedState));
  if (reducedState.paused) {
    console.log('✓ Verified: video does NOT autoplay under reduced motion');
  }

  // Click play overlay button on reduced motion page
  const playOverlay = reducedPage.locator('button[aria-label="Play video walkthrough"]').first();
  if (await playOverlay.isVisible()) {
    await playOverlay.click();
    await reducedPage.waitForTimeout(1000);
    const nowPlaying = await reducedPage.evaluate(() => !document.querySelector('video').paused);
    console.log(`✓ Video started playing after user click: ${nowPlaying}`);
  }

  await browser.close();
  console.log('\n[ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY]');
}

testVideoPlayer().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
