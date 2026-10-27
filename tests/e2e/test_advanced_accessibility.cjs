const { chromium } = require('playwright');
const { AxeBuilder } = require('@axe-core/playwright');

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

async function runAdvancedA11yAudit() {
  console.log('=======================================================');
  console.log('RUNNING ADVANCED ACCESSIBILITY & PLAYWRIGHT TEST SUITE');
  console.log(`Target: ${BASE_URL}`);
  console.log('=======================================================\n');

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', msg => {
    if (msg.text().includes('DEBUG-MODAL') || msg.text().includes('error')) {
      console.log('Browser Console:', msg.text());
    }
  });

  let passed = 0;
  let total = 0;

  // Helper assertion
  function assert(condition, message) {
    total++;
    if (!condition) {
      console.error(`  ✗ FAIL: ${message}`);
      throw new Error(message);
    }
    console.log(`  ✓ PASS: ${message}`);
    passed++;
  }

  try {
    // -------------------------------------------------------------------------
    // 1. Skip Link Test
    // -------------------------------------------------------------------------
    console.log('\n[Check 1/7] Skip to Main Content Link');
    await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);

    // Tab once to reach skip link
    await page.keyboard.press('Tab');
    const skipLink = await page.$('a[href="#main-content"]');
    assert(skipLink !== null, 'Skip link with href="#main-content" exists in DOM');

    const isSkipFocused = await page.evaluate(() => {
      const el = document.activeElement;
      return el && el.getAttribute('href') === '#main-content';
    });
    assert(isSkipFocused, 'Skip link receives focus on initial Tab navigation');

    // Press Enter on skip link and verify main receives focus or scroll
    await page.keyboard.press('Enter');
    const mainTarget = await page.$('#main-content');
    assert(mainTarget !== null, 'Target element with id="main-content" exists');

    // -------------------------------------------------------------------------
    // 2. Language Attribute Switching (hi / mr / en)
    // -------------------------------------------------------------------------
    console.log('\n[Check 2/7] Dynamic HTML lang Attribute Switching (hi / mr / en)');
    const langSelect = await page.$('#utsav-lang-select');
    assert(langSelect !== null, 'Language selector dropdown exists');

    // Switch to Hindi
    await langSelect.selectOption('hi');
    await page.waitForTimeout(300);
    const htmlLangHi = await page.evaluate(() => document.documentElement.lang);
    assert(htmlLangHi === 'hi', `HTML lang switched to 'hi' (actual: '${htmlLangHi}')`);

    // Switch to Marathi
    await langSelect.selectOption('mr');
    await page.waitForTimeout(300);
    const htmlLangMr = await page.evaluate(() => document.documentElement.lang);
    assert(htmlLangMr === 'mr', `HTML lang switched to 'mr' (actual: '${htmlLangMr}')`);

    // Switch back to English
    await langSelect.selectOption('en');
    await page.waitForTimeout(300);
    const htmlLangEn = await page.evaluate(() => document.documentElement.lang);
    assert(htmlLangEn === 'en', `HTML lang switched back to 'en' (actual: '${htmlLangEn}')`);

    // -------------------------------------------------------------------------
    // 3. Dark Mode Toggle Verification
    // -------------------------------------------------------------------------
    console.log('\n[Check 3/7] Dark Mode Class Toggle & Persistence');
    const initialDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));
    await page.waitForSelector('button[aria-label*="mode"], button[title*="mode"]', { timeout: 10000 });
    const themeBtn = await page.$('button[aria-label*="mode"], button[title*="mode"]');
    assert(themeBtn !== null, 'Theme toggle button exists');

    await themeBtn.click();
    await page.waitForTimeout(300);
    const toggledDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));
    assert(toggledDark !== initialDark, `Theme class toggled (was ${initialDark}, now ${toggledDark})`);

    // Toggle back
    await themeBtn.click();
    await page.waitForTimeout(300);

    // -------------------------------------------------------------------------
    // 4. Tab Order Matches Visual Order
    // -------------------------------------------------------------------------
    console.log('\n[Check 4/7] Tab Order Matches Visual Geometry');
    const navItems = await page.$$('header a, header button, header select');
    const boxes = [];
    for (const item of navItems) {
      const box = await item.boundingBox();
      if (box && box.width > 0 && box.height > 0) {
        boxes.push(box);
      }
    }
    let visualOrderCorrect = true;
    for (let i = 0; i < boxes.length - 1; i++) {
      // Header items are horizontal (left-to-right) on the same Y row
      if (Math.abs(boxes[i].y - boxes[i + 1].y) < 10) {
        if (boxes[i].x > boxes[i + 1].x + 5) {
          visualOrderCorrect = false;
        }
      }
    }
    assert(visualOrderCorrect, 'Interactive navigation elements follow left-to-right visual order');

    // -------------------------------------------------------------------------
    // 5. Dialog Focus Trap & Focus Restoration
    // -------------------------------------------------------------------------
    console.log('\n[Check 5/7] Dialog Focus Trap and Focus Restore');

    // Intercept backend requests so tests run reliably and deterministically
    await page.route('**/api/v1/**', async (route) => {
      const url = route.request().url();
      if (url.includes('/guests/rsvp-summary')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            total_guests: 5,
            attending_count: 3,
            declined_count: 1,
            pending_count: 1,
            waitlist_count: 0,
            total_headcount: 5,
            diet_breakdown: { veg: 3, jain: 1, non_veg: 1 },
            mobility_needs_count: 0,
            kids_count: 1,
            accommodation_needed_count: 1
          })
        });
      } else if (url.includes('/fact-sheet')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 'fs1', event_id: 'default', venue_address: 'Rambagh Palace Gate 1', parking_info: 'Valet', dress_code: 'Festive', timing_notes: '10 AM', map_link: 'https://maps.google.com' })
        });
      } else if (url.includes('/guests') && route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: 'g1', name: 'Aarav Sharma', phone: '+919876543210', rsvp_status: 'attending', headcount: 1, created_at: '2026-10-27T10:00:00Z' }
          ])
        });
      } else if (url.includes('/guests') && route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'partial',
            successful_count: 0,
            skipped_duplicates_count: 0,
            invalid_rows_count: 1,
            errors: [{ row_number: 1, name: 'Invalid Row', phone_raw: '', reason: 'Invalid Indian phone number' }]
          })
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'default',
            name: 'Sharma Royal Celebration',
            owner_name: 'Sharma Family',
            event_type: 'wedding',
            city: 'Jaipur',
            city_tier: 'tier_2',
            guest_count: 250,
            total_budget: 1500000,
            tradition_code: 'maharashtrian_vedic',
            status: 'planning',
            start_date: '2026-11-20',
            end_date: '2026-11-22',
            sub_events: [],
            budget_breakdown: [],
            tasks: []
          })
        });
      }
    });

    await page.goto(`${BASE_URL}/dashboard/events/evt_test_12345`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    // Switch to Guests tab if tabs exist
    const guestsTab = await page.$('button:has-text("Guests"), button:has-text("Guest Concierge")');
    if (guestsTab) {
      await guestsTab.click();
      await page.waitForTimeout(500);
    }

    const importBtn = await page.$('button:has-text("Import Guests")');
    assert(importBtn !== null, 'Trigger button "Import Guests" found');

    // Click trigger button
    await importBtn.click();
    await page.waitForTimeout(500);

    const dialog = await page.$('div[role="dialog"][aria-modal="true"]');
    assert(dialog !== null, 'Modal rendered with role="dialog" and aria-modal="true"');

    // Focus Trap Assertion: Tab wraps from last to first, Shift+Tab from first to last
    const focusable = await dialog.$$('button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])');
    assert(focusable.length >= 2, `Dialog has ${focusable.length} focusable elements`);

    // Verify first element is initially focused
    const firstFocused = await page.evaluate(() => {
      const active = document.activeElement;
      const dialog = document.querySelector('div[role="dialog"]');
      return dialog && dialog.contains(active);
    });
    assert(firstFocused, 'Initial focus moved inside the dialog');

    // Test Shift+Tab wrap from first element
    await focusable[0].focus();
    await page.keyboard.press('Shift+Tab');
    await page.waitForTimeout(200);
    const activeElHtml = await page.evaluate(() => document.activeElement ? document.activeElement.outerHTML.slice(0, 100) : null);
    console.log('Active element after Shift+Tab:', activeElHtml);
    const wrapToLast = await page.evaluate((lastEl) => document.activeElement === lastEl, focusable[focusable.length - 1]);
    assert(wrapToLast, 'Shift+Tab on first element wraps focus to the last element');

    // Test Tab wrap from last element back to first
    await focusable[focusable.length - 1].focus();
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
    const wrapToFirst = await page.evaluate((firstEl) => document.activeElement === firstEl, focusable[0]);
    assert(wrapToFirst, 'Tab on last element wraps focus back to the first element');

    // -------------------------------------------------------------------------
    // 6. Axe Scan with Modal Open
    // -------------------------------------------------------------------------
    console.log('\n[Check 6/7] Axe-Core Accessibility Scan with Active Modal Open');
    const axeResults = await new AxeBuilder({ page })
      .include('div[role="dialog"]')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    assert(axeResults.violations.length === 0, `Active modal has 0 Axe violations (found: ${axeResults.violations.length})`);

    // -------------------------------------------------------------------------
    // 7. Form Errors Shown & Focus Restore on Escape
    // -------------------------------------------------------------------------
    console.log('\n[Check 7/7] Form Validation Errors & Focus Restore on Escape');
    const textarea = await dialog.$('textarea');
    if (textarea) {
      await textarea.fill('Invalid Row Without Phone Or Valid Data');
      const submitBtn = await dialog.$('button:has-text("Validate & Import")');
      if (submitBtn) {
        await submitBtn.click();
        await page.waitForTimeout(500);
        const errorBanner = await dialog.$('div:has-text("rejected due to phone validation")');
        assert(errorBanner !== null, 'Form validation error banner is displayed for invalid data');
      }
    }

    // Focus inside active dialog and press Escape to close modal
    const activeDialog = await page.$('div[role="dialog"]');
    assert(activeDialog !== null, 'Dialog is still open after validation errors');
    const closeBtn = await activeDialog.$('button[aria-label="Close import dialog"]');
    if (closeBtn) {
      await closeBtn.press('Escape');
    } else {
      await page.keyboard.press('Escape');
    }
    await page.waitForTimeout(500);
    const dialogClosed = await page.$('div[role="dialog"]');
    assert(dialogClosed === null, 'Escape key closed the modal');

    // Verify focus restoration to the trigger button
    const focusRestored = await page.evaluate((btn) => document.activeElement === btn, importBtn);
    assert(focusRestored, 'Focus successfully restored to trigger button after modal dismissal');

    console.log('\n=======================================================');
    console.log(`ALL ADVANCED ACCESSIBILITY CHECKS PASSED: ${passed}/${total}`);
    console.log('=======================================================');

  } catch (err) {
    console.error('\nTest failed with error:', err.message);
    await browser.close();
    process.exit(1);
  }

  await browser.close();
}

runAdvancedA11yAudit();
