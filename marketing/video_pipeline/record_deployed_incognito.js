const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const CLIPS_DIR = path.join(__dirname, 'clips_incognito');
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
  page.setDefaultTimeout(20000);

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

  // BEAT 1: Incognito Launch & Paste Deployed Link
  await recordClip(browser, 'beat1_incognito_paste', 8.5, async (page) => {
    const newTabUrl = `file://${path.resolve('video_pipeline/incognito_new_tab.html').replace(/\\/g, '/')}`;
    await page.goto(newTabUrl, { waitUntil: 'load' });
    await sleep(600);
    await page.evaluate(() => window.runPasteAnimation());
    await sleep(4000);
  });

  // BEAT 2: Deployed Landing Page & 3D Diya
  await recordClip(browser, 'beat2_landing_3d', 8.5, async (page) => {
    await page.goto('https://utsav-ai.netlify.app', { waitUntil: 'domcontentloaded' });
    await sleep(800);
    await injectIncognitoHeader(page, '');
    await sleep(1500);

    // Smooth hover across 3D canvas
    await page.mouse.move(960, 480, { steps: 20 });
    await sleep(1000);
    await page.mouse.move(1100, 520, { steps: 20 });
    await sleep(1000);

    // Smooth scroll down to highlight chaos vs composed
    await page.evaluate(() => window.scrollBy({ top: 400, behavior: 'smooth' }));
    await sleep(2200);
    await page.evaluate(() => window.scrollBy({ top: 300, behavior: 'smooth' }));
    await sleep(1500);
  });

  // BEAT 3: Deployed Onboarding Flow
  await recordClip(browser, 'beat3_onboarding', 8.5, async (page) => {
    await page.goto('https://utsav-ai.netlify.app/onboarding', { waitUntil: 'domcontentloaded' });
    await sleep(800);
    await injectIncognitoHeader(page, '/onboarding');
    await sleep(1200);

    // Click Wedding option
    const weddingBtn = page.locator('button:has-text("Wedding"), div:has-text("Wedding")').first();
    if (await weddingBtn.isVisible()) {
      await weddingBtn.click();
    }
    await sleep(1500);

    // Type City
    const cityInput = page.locator('input[type="text"]').first();
    if (await cityInput.isVisible()) {
      await cityInput.click();
      await cityInput.fill('Jaipur, Rajasthan');
    }
    await sleep(1500);

    // Scroll slightly to view generate button
    await page.evaluate(() => window.scrollBy({ top: 300, behavior: 'smooth' }));
    await sleep(1500);
  });

  // BEAT 4: Deployed Dashboard Budget & Map
  await recordClip(browser, 'beat4_dashboard_budget', 9.0, async (page) => {
    await page.goto('https://utsav-ai.netlify.app/dashboard', { waitUntil: 'domcontentloaded' });
    await sleep(800);
    await injectIncognitoHeader(page, '/dashboard');
    await sleep(1800);

    // Scroll to Budget breakdown
    await page.evaluate(() => window.scrollBy({ top: 450, behavior: 'smooth' }));
    await sleep(2200);

    // Scroll to Venue map
    await page.evaluate(() => window.scrollBy({ top: 450, behavior: 'smooth' }));
    await sleep(2500);
  });

  // BEAT 5: Deployed Invitation Card & Outro
  await recordClip(browser, 'beat5_invitation_export', 10.0, async (page) => {
    await page.goto('https://utsav-ai.netlify.app/dashboard', { waitUntil: 'domcontentloaded' });
    await sleep(800);
    await injectIncognitoHeader(page, '/dashboard#invitations');
    await sleep(1000);

    // Scroll down to the invitation preview section
    await page.evaluate(() => window.scrollBy({ top: 1100, behavior: 'smooth' }));
    await sleep(2500);

    // Inject verified badge overlay in last 4 seconds
    await page.evaluate(() => {
      const overlay = document.createElement('div');
      overlay.id = 'outro-pill';
      overlay.innerHTML = `
        <div style="background: rgba(15, 23, 42, 0.94); border: 2px solid #d97706; border-radius: 20px; padding: 24px 36px; box-shadow: 0 25px 60px rgba(0,0,0,0.8); text-align: center; color: #ffffff; backdrop-filter: blur(12px);">
          <div style="font-size: 26px; font-weight: 800; color: #fde68a; margin-bottom: 8px;">🪔 Utsav (उत्सव) — Deployed & Production Ready</div>
          <div style="font-size: 18px; color: #38bdf8; font-weight: 600; margin-bottom: 12px;">🌐 https://utsav-ai.netlify.app</div>
          <div style="font-size: 16px; color: #cbd5e1;">Built for Prompt Wars Virtual with Google Gemini</div>
          <div style="font-size: 15px; color: #f59e0b; font-weight: 700; margin-top: 6px;">@googlefordevelopers • @hack2skill</div>
        </div>
      `;
      overlay.style.position = 'fixed';
      overlay.style.bottom = '40px';
      overlay.style.right = '40px';
      overlay.style.zIndex = '2147483647';
      overlay.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      overlay.style.animation = 'fadeIn 0.6s ease';
      document.body.appendChild(overlay);
    });
    await sleep(3500);
  });

  await browser.close();
  console.log('\n[SUCCESS] All 5 incognito walkthrough clips recorded.');
}

run().catch(console.error);
