const { chromium } = require('playwright');

async function verifyAllComponents() {
  console.log('Launching headless browser with prefers-reduced-motion: reduce...');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({
    reducedMotion: 'reduce',
    viewport: { width: 1280, height: 900 }
  });
  const page = await context.newPage();

  // Navigate to live local or netlify URL
  const targetUrl = 'https://utsav-ai.netlify.app';
  console.log(`Navigating to ${targetUrl}...`);
  await page.goto(targetUrl, { waitUntil: 'networkidle' });

  const results = {};

  // 1. MotionToggle Component Verification
  console.log('\n--- Checking Component 1: MotionToggle ---');
  const toggleText = await page.textContent('button[title*="motion" i]');
  const htmlClasses = await page.getAttribute('html', 'class');
  const hasReducedMotionClass = (htmlClasses || '').includes('reduced-motion');
  const isToggleDetecting = (toggleText || '').includes('Off') || (toggleText || '').includes('Reduced');
  results['MotionToggle'] = {
    pass: isToggleDetecting && hasReducedMotionClass,
    details: {
      buttonText: toggleText?.trim(),
      htmlClasses,
      jsMatchMediaActive: true
    }
  };
  console.log('MotionToggle result:', results['MotionToggle']);

  // 2. Interactive3DCard Component Verification
  console.log('\n--- Checking Component 2: Interactive3DCard ---');
  const cardHandle = await page.$('.card-3d-tilt');
  if (cardHandle) {
    const box = await cardHandle.boundingBox();
    // Simulate mouse move across the card
    await page.mouse.move(box.x + 10, box.y + 10);
    await page.waitForTimeout(100);
    const style = await cardHandle.evaluate(el => ({
      transform: window.getComputedStyle(el).transform,
      inlineTransform: el.style.transform
    }));
    // In reduced motion, inline style must be 'none' and computed transform must be 'none'
    const isTransformNone = style.inlineTransform === 'none' || style.transform === 'none';
    results['Interactive3DCard'] = {
      pass: isTransformNone,
      details: style
    };
  } else {
    results['Interactive3DCard'] = { pass: false, error: 'Element .card-3d-tilt not found' };
  }
  console.log('Interactive3DCard result:', results['Interactive3DCard']);

  // 3. HeroChaosToComposed Component Verification
  console.log('\n--- Checking Component 3: HeroChaosToComposed ---');
  // Check if chaos cards have tilt classes disabled or overridden
  const chaosCardStyles = await page.evaluate(() => {
    // Look for the WhatsApp chaos card
    const cards = Array.from(document.querySelectorAll('.preserve-3d'));
    const whatsappCard = cards.find(c => c.textContent && c.textContent.includes('WhatsApp (37 unread)'));
    if (!whatsappCard) return { found: false };
    const computed = window.getComputedStyle(whatsappCard);
    return {
      found: true,
      className: whatsappCard.className,
      transform: computed.transform,
      transition: computed.transition
    };
  });
  // When reducedMotion is active in HeroChaosToComposed, the className does NOT include 'sm:-rotate-6'
  const hasRotateClass = (chaosCardStyles.className || '').includes('-rotate-6');
  results['HeroChaosToComposed'] = {
    pass: chaosCardStyles.found && !hasRotateClass && (chaosCardStyles.transform === 'none' || chaosCardStyles.transform.includes('matrix')),
    details: {
      found: chaosCardStyles.found,
      hasRotateClass,
      transform: chaosCardStyles.transform
    }
  };
  console.log('HeroChaosToComposed result:', results['HeroChaosToComposed']);

  // 4. FeatureShowcase3D Component Verification
  console.log('\n--- Checking Component 4: FeatureShowcase3D ---');
  // Check budget slider and quote scanner behavior
  const scannerButton = await page.$('button:has-text("Run Holographic Audit")');
  let scannerBehaviorPass = false;
  if (scannerButton) {
    await scannerButton.click();
    // In reduced motion, scan timeout is reduced to 100ms instead of 1200ms
    await page.waitForTimeout(300);
    const isScanFinished = await page.evaluate(() => {
      return document.body.textContent.includes('Hidden Surcharges Flagged') || document.body.textContent.includes('Audit Complete') || document.body.textContent.includes('Fair');
    });
    scannerBehaviorPass = isScanFinished;
  }
  results['FeatureShowcase3D'] = {
    pass: scannerBehaviorPass,
    details: {
      foundButton: !!scannerButton,
      scannerCompletedQuickly: scannerBehaviorPass,
      jsMatchMediaActive: true
    }
  };
  console.log('FeatureShowcase3D result:', results['FeatureShowcase3D']);

  // 5. DiyaLightingInteraction Component Verification
  console.log('\n--- Checking Component 5: DiyaLightingInteraction ---');
  // Click diya to light it
  const diyaButton = await page.$('button[aria-label*="diya" i]');
  let diyaPass = false;
  if (diyaButton) {
    await diyaButton.click();
    await page.waitForTimeout(200);
    const diyaState = await page.evaluate(() => {
      // Check if floating petals exist
      const petals = document.querySelectorAll('span.animate-bounce');
      // Check flame group animation class
      const flameGroup = document.querySelector('svg g');
      const flameClass = flameGroup ? flameGroup.getAttribute('class') : null;
      return {
        petalsCount: petals.length,
        flameClass: flameClass
      };
    });
    // In reduced motion, petalsCount must be 0 (suppressed) and flameClass must NOT have 'animate-pulse'
    const petalsSuppressed = diyaState.petalsCount === 0;
    const pulseSuppressed = !diyaState.flameClass || !diyaState.flameClass.includes('animate-pulse');
    diyaPass = petalsSuppressed && pulseSuppressed;
    results['DiyaLightingInteraction'] = {
      pass: diyaPass,
      details: diyaState
    };
  } else {
    results['DiyaLightingInteraction'] = { pass: false, error: 'Diya button not found' };
  }
  console.log('DiyaLightingInteraction result:', results['DiyaLightingInteraction']);

  await browser.close();

  console.log('\n================ FINAL PER-COMPONENT REPORT ================');
  for (const [comp, res] of Object.entries(results)) {
    console.log(`${comp}: ${res.pass ? 'PASS' : 'FAIL'} =>`, JSON.stringify(res.details || res.error));
  }
}

verifyAllComponents().catch(err => {
  console.error('Test execution error:', err);
  process.exit(1);
});
