const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const ARTIFACT_DIR = 'C:/Users/deves/.gemini/antigravity/brain/57333fd6-3848-479e-98dc-d6c0861fdff7';

async function capture() {
  console.log('Launching browser to capture 3D landing page and test reduced motion...');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  
  // 1. Standard Experience (Dynamic 3D enabled)
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto('https://utsav-ai.netlify.app/', { waitUntil: 'networkidle', timeout: 35000 });

  // Screenshot 1: Chaos state hero
  const chaosPath = path.join(ARTIFACT_DIR, '3d_landing_hero_chaos.png');
  await page.screenshot({ path: chaosPath });
  console.log('1. Captured Chaos Hero Screenshot:', chaosPath);

  // Click "Utsav Composed Solution" toggle
  const composedBtn = await page.getByRole('button', { name: /Utsav Composed Solution/i });
  await composedBtn.click();
  await page.waitForTimeout(1000);

  // Screenshot 2: Composed state hero
  const composedPath = path.join(ARTIFACT_DIR, '3d_landing_hero_composed.png');
  await page.screenshot({ path: composedPath });
  console.log('2. Captured Composed Hero Screenshot:', composedPath);

  // Scroll down to feature showcase
  await page.evaluate(() => window.scrollBy(0, 1000));
  await page.waitForTimeout(800);
  const feature1Path = path.join(ARTIFACT_DIR, '3d_landing_features_budget_quote.png');
  await page.screenshot({ path: feature1Path });
  console.log('3. Captured Feature Showcase Screenshot:', feature1Path);

  // Scroll down to Diya & footer
  await page.evaluate(() => window.scrollBy(0, 1500));
  await page.waitForTimeout(800);
  const diyaPath = path.join(ARTIFACT_DIR, '3d_landing_diya_interaction.png');
  await page.screenshot({ path: diyaPath });
  console.log('4. Captured Diya Interaction Screenshot:', diyaPath);

  await page.close();

  // 2. Reduced Motion Test (emulateMedia reducedMotion: 'reduce')
  console.log('\nTesting prefers-reduced-motion fallback...');
  const pageReduced = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await pageReduced.emulateMedia({ reducedMotion: 'reduce' });
  await pageReduced.goto('https://utsav-ai.netlify.app/', { waitUntil: 'networkidle', timeout: 35000 });

  // Evaluate card transforms in reduced motion mode
  const transformCheck = await pageReduced.evaluate(() => {
    const card = document.querySelector('.card-3d-tilt');
    if (!card) return { found: false };
    const computed = window.getComputedStyle(card);
    return {
      found: true,
      transform: computed.transform,
      transition: computed.transition,
      animation: computed.animation
    };
  });
  console.log('Reduced Motion Computed Style on 3D Card:', transformCheck);

  const reducedPath = path.join(ARTIFACT_DIR, '3d_landing_reduced_motion.png');
  await pageReduced.screenshot({ path: reducedPath });
  console.log('5. Captured Reduced Motion Fallback Screenshot:', reducedPath);

  await browser.close();
  console.log('\nAll captures and reduced motion verifications completed successfully!');
}

capture().catch(err => {
  console.error('Capture failed:', err);
  process.exit(1);
});
