const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const CLIPS_DIR = path.join(__dirname, 'clips_detailed');
if (!fs.existsSync(CLIPS_DIR)) {
  fs.mkdirSync(CLIPS_DIR, { recursive: true });
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function injectIncognitoHeader(page, routePath = '') {
  return page.evaluate((subpath) => {
    if (document.getElementById('incognito-chrome-bar')) return;
    const bar = document.createElement('div');
    bar.id = 'incognito-chrome-bar';
    const displayUrl = subpath ? `https://utsav-ai.netlify.app${subpath}` : 'https://utsav-ai.netlify.app';
    bar.innerHTML = `
      <div style="height: 42px; background: #1f1f23; display: flex; align-items: center; padding: 0 18px; justify-content: space-between; border-bottom: 1px solid #2b2b30;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="width: 14px; height: 14px; border-radius: 50%; background: #ed6a5e;"></div>
          <div style="width: 14px; height: 14px; border-radius: 50%; background: #f5bf4f;"></div>
          <div style="width: 14px; height: 14px; border-radius: 50%; background: #62c554;"></div>
          <div style="margin-left: 18px; background: #2b2b30; color: #f1f3f4; padding: 8px 20px; border-radius: 10px 10px 0 0; font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 10px; border-top: 2px solid #8ab4f8;">
            <span style="font-size: 16px;">🕶️</span>
            <span>Utsav (उत्सव) — Celebrations, Composed</span>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <div style="color: #e8eaed; font-size: 14px; font-weight: 600; background: #2b2b30; padding: 6px 14px; border-radius: 6px; display: flex; align-items: center; gap: 8px; border: 1px solid #3c4043;">
            <span>🕶️</span>
            <span>Incognito</span>
          </div>
          <span style="color: #9aa0a6; font-size: 20px;">⋮</span>
        </div>
      </div>
      <div style="height: 48px; background: #2b2b30; display: flex; align-items: center; padding: 0 18px; gap: 16px; border-bottom: 1px solid #3c4043;">
        <div style="display: flex; gap: 14px; color: #9aa0a6; font-size: 18px;">
          <span>←</span>
          <span>→</span>
          <span>↻</span>
        </div>
        <div style="flex: 1; background: #1f1f23; height: 36px; border-radius: 18px; display: flex; align-items: center; padding: 0 18px; color: #ffffff; font-size: 15px; gap: 10px; border: 1px solid #3c4043; box-shadow: inset 0 1px 3px rgba(0,0,0,0.4);">
          <span style="color: #81c995; font-size: 15px;">🔒</span>
          <span style="color: #8ab4f8; font-weight: 500;">https://</span><span style="color: #e8eaed; font-weight: 500;">${displayUrl.replace('https://', '')}</span>
        </div>
        <div style="color: #9aa0a6; font-size: 18px;">★</div>
      </div>
    `;
    bar.style.position = 'fixed';
    bar.style.top = '0';
    bar.style.left = '0';
    bar.style.width = '100%';
    bar.style.zIndex = '2147483647';
    bar.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    document.body.prepend(bar);
    document.body.style.paddingTop = '90px';
  }, routePath);
}

async function recordClip(browser, clipId, durationSec, recordAction) {
  console.log(`\n=== Recording Clip: ${clipId} (${durationSec}s) ===`);
  const tempDir = path.join(CLIPS_DIR, `temp_${clipId}`);
  if (fs.existsSync(tempDir)) fs.rmSync(tempDir, { recursive: true, force: true });
  fs.mkdirSync(tempDir, { recursive: true });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: {
      dir: tempDir,
      size: { width: 1920, height: 1080 }
    }
  });

  const page = await context.newPage();
  page.setDefaultTimeout(25000);

  const startMs = Date.now();
  try {
    await recordAction(page);
  } catch (err) {
    console.error(`Error in ${clipId}:`, err);
  }

  const elapsed = (Date.now() - startMs) / 1000;
  if (elapsed < durationSec) {
    await sleep((durationSec - elapsed) * 1000);
  }

  await page.close();
  await context.close();

  // Rename recorded file
  const files = fs.readdirSync(tempDir).filter(f => f.endsWith('.webm'));
  if (files.length > 0) {
    const orig = path.join(tempDir, files[0]);
    const finalOut = path.join(CLIPS_DIR, `${clipId}.webm`);
    if (fs.existsSync(finalOut)) fs.unlinkSync(finalOut);
    fs.renameSync(orig, finalOut);
    fs.rmSync(tempDir, { recursive: true, force: true });
    console.log(`[SAVED] ${finalOut} (${((Date.now() - startMs) / 1000).toFixed(2)}s)`);
  }
}

async function run() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--enable-webgl', '--use-gl=angle', '--use-angle=d3d11']
  });

  // BEAT 1: Incognito Launch & Paste Deployed Link (12s)
  await recordClip(browser, 'd1_incognito', 12.0, async (page) => {
    const newTabUrl = `file://${path.resolve('video_pipeline/incognito_new_tab.html').replace(/\\/g, '/')}`;
    await page.goto(newTabUrl, { waitUntil: 'load' });
    await sleep(800);
    await page.evaluate(() => window.runPasteAnimation());
    await sleep(5500);
  });

  // BEAT 2: Deployed Landing Page, 3D Diya & Chaos to Composed (12.5s)
  await recordClip(browser, 'd2_landing', 12.5, async (page) => {
    await page.goto('https://utsav-ai.netlify.app', { waitUntil: 'domcontentloaded' });
    await sleep(800);
    await injectIncognitoHeader(page, '');
    await sleep(1500);

    // Smooth hover across 3D canvas
    await page.mouse.move(960, 480, { steps: 25 });
    await sleep(1500);
    await page.mouse.move(1120, 530, { steps: 25 });
    await sleep(1500);

    // Smooth scroll down to highlight chaos vs composed
    await page.evaluate(() => window.scrollBy({ top: 420, behavior: 'smooth' }));
    await sleep(2500);
    await page.evaluate(() => window.scrollBy({ top: 350, behavior: 'smooth' }));
    await sleep(2000);
  });

  // BEAT 3: Deployed Guided Onboarding (13.5s)
  await recordClip(browser, 'd3_onboarding', 13.5, async (page) => {
    await page.goto('https://utsav-ai.netlify.app/onboarding', { waitUntil: 'domcontentloaded' });
    await sleep(800);
    await injectIncognitoHeader(page, '/onboarding');
    await sleep(1500);

    // Click Wedding option
    const weddingBtn = page.locator('button:has-text("Wedding"), div:has-text("Wedding")').first();
    if (await weddingBtn.isVisible()) {
      await weddingBtn.click();
    }
    await sleep(2000);

    // Type City
    const cityInput = page.locator('input[type="text"]').first();
    if (await cityInput.isVisible()) {
      await cityInput.click();
      await cityInput.fill('Jaipur, Rajasthan');
    }
    await sleep(2000);

    // Scroll slightly to view guest & budget inputs
    await page.evaluate(() => window.scrollBy({ top: 320, behavior: 'smooth' }));
    await sleep(2500);
  });

  // BEAT 4: Unified Celebration Hub Dashboard (11.5s)
  await recordClip(browser, 'd4_dashboard', 11.5, async (page) => {
    await page.goto('https://utsav-ai.netlify.app/dashboard', { waitUntil: 'domcontentloaded' });
    await sleep(800);
    await injectIncognitoHeader(page, '/dashboard');
    await sleep(2000);

    // Scroll slightly to view celebration metrics
    await page.evaluate(() => window.scrollBy({ top: 300, behavior: 'smooth' }));
    await sleep(2500);

    // Hover nav tab
    const navItem = page.locator('nav a, header a, button').nth(2);
    if (await navItem.isVisible()) {
      await navItem.hover();
    }
    await sleep(2500);
  });

  // BEAT 5: Deterministic Budget Math & Quote Auditing (14.5s)
  await recordClip(browser, 'd5_quotes', 14.5, async (page) => {
    await page.goto('https://utsav-ai.netlify.app/dashboard/vendors/quotes', { waitUntil: 'domcontentloaded' });
    await sleep(800);
    await injectIncognitoHeader(page, '/dashboard/vendors/quotes');
    await sleep(2000);

    // Scroll to examine quotes table
    await page.evaluate(() => window.scrollBy({ top: 280, behavior: 'smooth' }));
    await sleep(3000);

    // Hover row / quote
    const row = page.locator('table tr, .quote-card, article').first();
    if (await row.isVisible()) {
      await row.hover();
    }
    await sleep(3500);
  });

  // BEAT 6: Nationwide Venue Map & Auspicious Muhurats (14.0s)
  await recordClip(browser, 'd6_map_muhurat', 14.0, async (page) => {
    await page.goto('https://utsav-ai.netlify.app/dashboard/events/default/compose', { waitUntil: 'domcontentloaded' });
    await sleep(800);
    await injectIncognitoHeader(page, '/dashboard/events/default/compose');
    await sleep(2000);

    // Leaflet map interaction
    const map = page.locator('.leaflet-container').first();
    if (await map.isVisible()) {
      const box = await map.boundingBox();
      if (box) {
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await sleep(1000);
        await page.mouse.wheel(0, -80);
      }
    }
    await sleep(2500);

    // Scroll to Muhurat timings
    await page.evaluate(() => window.scrollBy({ top: 400, behavior: 'smooth' }));
    await sleep(3000);
  });

  // BEAT 7: Live Devanagari Invitation Studio & Outro (15.0s)
  await recordClip(browser, 'd7_invitations_outro', 15.0, async (page) => {
    await page.goto('https://utsav-ai.netlify.app/dashboard/events/default/invitations', { waitUntil: 'domcontentloaded' });
    await sleep(800);
    await injectIncognitoHeader(page, '/dashboard/events/default/invitations');
    await sleep(2000);

    // Hover over rendered card preview
    const card = page.locator('img, .invitation-card, article').first();
    if (await card.isVisible()) {
      await card.hover();
    }
    await sleep(3000);

    // Inject verified outro badge
    await page.evaluate(() => {
      const overlay = document.createElement('div');
      overlay.id = 'outro-pill';
      overlay.innerHTML = `
        <div style="background: rgba(15, 23, 42, 0.95); border: 2px solid #d97706; border-radius: 24px; padding: 28px 44px; box-shadow: 0 30px 70px rgba(0,0,0,0.85); text-align: center; color: #ffffff; backdrop-filter: blur(14px);">
          <div style="font-size: 28px; font-weight: 800; color: #fde68a; margin-bottom: 8px;">🪔 Utsav (उत्सव) — Live at utsav-ai.netlify.app</div>
          <div style="font-size: 20px; color: #38bdf8; font-weight: 600; margin-bottom: 12px;">🌐 https://utsav-ai.netlify.app &nbsp;|&nbsp; 💻 github.com/DeveshK1256/utsav-ai</div>
          <div style="font-size: 17px; color: #cbd5e1;">Culture-Native GenAI Event Orchestration with Google Gemini</div>
          <div style="font-size: 16px; color: #f59e0b; font-weight: 700; margin-top: 8px;">@googlefordevelopers • @hack2skill • #PromptWarsVirtual</div>
        </div>
      `;
      overlay.style.position = 'fixed';
      overlay.style.bottom = '40px';
      overlay.style.right = '40px';
      overlay.style.zIndex = '2147483647';
      overlay.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      document.body.appendChild(overlay);
    });
    await sleep(4000);
  });

  await browser.close();
  console.log('\n[SUCCESS] All 7 in-depth incognito walkthrough clips recorded.');
}

run().catch(console.error);
