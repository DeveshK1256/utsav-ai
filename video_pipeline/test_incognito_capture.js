const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function testCapture() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--enable-webgl', '--use-gl=angle', '--use-angle=d3d11']
  });

  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  
  // Go to deployed site
  console.log('Loading deployed site...');
  await page.goto('https://utsav-ai.netlify.app', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);

  // Inject Incognito Chrome Bar
  await page.evaluate(() => {
    const bar = document.createElement('div');
    bar.id = 'incognito-chrome-bar';
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
          <span style="color: #9aa0a6; font-size: 20px; cursor: pointer;">⋮</span>
        </div>
      </div>
      <div style="height: 48px; background: #2b2b30; display: flex; align-items: center; padding: 0 18px; gap: 16px; border-bottom: 1px solid #3c4043;">
        <div style="display: flex; gap: 14px; color: #9aa0a6; font-size: 18px;">
          <span style="cursor: pointer;">←</span>
          <span style="cursor: pointer;">→</span>
          <span style="cursor: pointer;">↻</span>
        </div>
        <div style="flex: 1; background: #1f1f23; height: 36px; border-radius: 18px; display: flex; align-items: center; padding: 0 18px; color: #ffffff; font-size: 15px; gap: 10px; border: 1px solid #3c4043; box-shadow: inset 0 1px 3px rgba(0,0,0,0.4);">
          <span style="color: #81c995; font-size: 15px;">🔒</span>
          <span style="color: #8ab4f8; font-weight: 500;">https://</span><span style="color: #e8eaed; font-weight: 500;">utsav-ai.netlify.app</span>
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
  });

  await page.screenshot({ path: 'test_incognito_deployed.png' });
  console.log('Screenshot captured: test_incognito_deployed.png');
  await browser.close();
}

testCapture().catch(console.error);
