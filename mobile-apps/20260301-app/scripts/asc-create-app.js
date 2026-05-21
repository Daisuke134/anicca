// ASC App Creation via Playwright Browser Automation
// Skill: ~/.claude/skills/asc-app-create-ui/SKILL.md
// 2FA: writes NEED_2FA to /tmp/factory-signal, reads code from /tmp/2fa-code
// Cookies: saved to ~/.asc/playwright-cookies.json
const { chromium } = require('/opt/homebrew/lib/node_modules/playwright');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const APP_NAME = 'AffirmFlow';
const BUNDLE_ID = 'com.anicca.affirmflow';
const SKU = 'AffirmFlow2026';
const APPLE_ID = 'keiodaisuke@gmail.com';
const APPLE_PASSWORD = 'Chatgpt12345';
const COOKIE_PATH = path.join(process.env.HOME, '.asc', 'playwright-cookies.json');
const SIGNAL_PATH = '/tmp/factory-signal';
const CODE_PATH = '/tmp/2fa-code';

function log(msg) { console.log(`[${new Date().toISOString().slice(11,19)}] ${msg}`); }

async function wait2FACode() {
  // Signal that 2FA is needed
  fs.writeFileSync(SIGNAL_PATH, 'NEED_2FA');
  log('Wrote NEED_2FA to ' + SIGNAL_PATH);
  try {
    execSync('openclaw system event --text "NEED_HUMAN_INPUT: Apple 2FA code needed for ASC login. Enter code." --mode now 2>/dev/null', { shell: '/bin/zsh' });
  } catch (e) {}

  // Wait for /tmp/2fa-code to appear (poll every 2s, max 5 min)
  log('Waiting for 2FA code at ' + CODE_PATH + '...');
  if (fs.existsSync(CODE_PATH)) fs.unlinkSync(CODE_PATH);
  for (let i = 0; i < 150; i++) {
    await new Promise(r => setTimeout(r, 2000));
    if (fs.existsSync(CODE_PATH)) {
      const code = fs.readFileSync(CODE_PATH, 'utf-8').trim();
      if (code.length >= 6) {
        log('Got 2FA code: ' + code);
        fs.unlinkSync(CODE_PATH);
        return code;
      }
    }
  }
  throw new Error('Timed out waiting for 2FA code (5 min)');
}

async function saveCookies(context) {
  const dir = path.dirname(COOKIE_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const cookies = await context.cookies();
  fs.writeFileSync(COOKIE_PATH, JSON.stringify(cookies, null, 2));
  log('Cookies saved to ' + COOKIE_PATH);
}

async function loadCookies(context) {
  if (fs.existsSync(COOKIE_PATH)) {
    const cookies = JSON.parse(fs.readFileSync(COOKIE_PATH, 'utf-8'));
    await context.addCookies(cookies);
    log('Cookies loaded from ' + COOKIE_PATH);
    return true;
  }
  return false;
}

(async () => {
  log('=== ASC App Creation: ' + APP_NAME + ' ===');

  // Preflight
  log('[1] Preflight: checking existing app...');
  try {
    const result = execSync(`asc apps list --bundle-id "${BUNDLE_ID}" --output json 2>/dev/null`);
    const data = JSON.parse(result);
    if (data.data && data.data.length > 0) {
      log('App already exists! ID: ' + data.data[0].id);
      console.log(JSON.stringify({ success: true, appId: data.data[0].id, existing: true }));
      // process.exit(0); — skip for cookie capture
    }
    log('No existing app. Proceeding.');
  } catch (e) {
    log('Could not check existing apps, proceeding.');
  }

  // Launch browser
  log('[2] Launching browser...');
  const browser = await chromium.launch({ headless: false, slowMo: 200 });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  // Try loading saved cookies
  const hadCookies = await loadCookies(context);
  const page = await context.newPage();

  try {
    // Navigate to ASC
    log('[3] Navigating to App Store Connect...');
    await page.goto('https://appstoreconnect.apple.com/apps', { timeout: 60000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    let currentUrl = page.url();
    log('URL: ' + currentUrl);

    // Check if we need to login
    const needsLogin = currentUrl.includes('idmsa.apple.com') ||
      currentUrl.includes('appleid.apple.com') ||
      await page.frames().some(f => f.url().includes('idmsa.apple.com'));

    if (needsLogin || !currentUrl.includes('appstoreconnect.apple.com/apps')) {
      log('[LOGIN] Signing in...');

      // Find auth iframe
      let authFrame = page.frames().find(f => f.url().includes('idmsa.apple.com') || f.url().includes('appleid.apple.com'));
      if (!authFrame) {
        // Maybe it's a direct page
        if (currentUrl.includes('idmsa.apple.com') || currentUrl.includes('appleid.apple.com')) {
          authFrame = page.mainFrame();
        } else {
          await page.waitForTimeout(5000);
          authFrame = page.frames().find(f => f.url().includes('idmsa.apple.com') || f.url().includes('appleid.apple.com'));
        }
      }

      if (!authFrame) throw new Error('Cannot find Apple login frame. URL: ' + page.url());
      log('Auth frame found: ' + authFrame.url().substring(0, 60));

      // Enter Apple ID
      const emailInput = authFrame.locator('#account_name_text_field');
      await emailInput.waitFor({ timeout: 15000 });
      await emailInput.click();
      await emailInput.fill(APPLE_ID);
      log('Entered Apple ID');
      await page.waitForTimeout(500);

      // Click sign-in (email step)
      await authFrame.locator('#sign-in').click();
      log('Clicked sign-in (email)');
      await page.waitForTimeout(4000);

      // Handle "Continue with Password" button (Japanese or English)
      const authFrame2 = page.frames().find(f => f.url().includes('idmsa.apple.com') || f.url().includes('appleid.apple.com')) || authFrame;
      const continueBtn = authFrame2.locator('button:has-text("パスワードで続行"), button:has-text("Continue with Password"), button:has-text("Continue"), #continue-password').first();
      if (await continueBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
        await continueBtn.click();
        log('Clicked "Continue with Password"');
        await page.waitForTimeout(3000);
      }

      // Enter password
      const pwInput = authFrame2.locator('#password_text_field');
      await pwInput.waitFor({ timeout: 10000 });
      await pwInput.click();
      await pwInput.fill(APPLE_PASSWORD);
      log('Entered password');
      await page.waitForTimeout(500);

      await authFrame2.locator('#sign-in').click();
      log('Clicked sign-in (password)');
      await page.waitForTimeout(6000);

      // Check for 2FA
      const authFrame3 = page.frames().find(f => f.url().includes('idmsa.apple.com') || f.url().includes('appleid.apple.com')) || page.mainFrame();

      const has2FA =
        await authFrame3.locator('#char0').isVisible().catch(() => false) ||
        await authFrame3.locator('.security-code-fields').isVisible().catch(() => false) ||
        await authFrame3.locator('input[id^="char"]').first().isVisible().catch(() => false) ||
        await page.getByText('確認コード').isVisible().catch(() => false) ||
        await page.getByText('verification code').isVisible().catch(() => false) ||
        await page.getByText('Verification Code').isVisible().catch(() => false);

      if (has2FA) {
        log('[2FA] Two-factor authentication required');
        await page.screenshot({ path: 'scripts/asc-2fa-screen.png' });

        const code = await wait2FACode();

        // Enter code digit by digit (#char0 to #char5)
        let entered = false;
        for (let i = 0; i < code.length; i++) {
          const charInput = authFrame3.locator(`#char${i}`);
          if (await charInput.isVisible().catch(() => false)) {
            await charInput.fill(code[i]);
            entered = true;
          }
        }

        if (!entered) {
          // Try single input field
          const singleInput = authFrame3.locator('input[type="tel"], input[type="number"], input.form-security-code-input').first();
          if (await singleInput.isVisible().catch(() => false)) {
            await singleInput.fill(code);
            entered = true;
          }
        }

        if (!entered) {
          // Keyboard fallback
          await page.keyboard.type(code, { delay: 100 });
        }

        log('2FA code entered');
        await page.waitForTimeout(5000);

        // Handle "Trust this browser" prompt
        const trustBtn = authFrame3.locator('button:has-text("Trust"), button:has-text("信頼する"), button:has-text("信頼")').first();
        if (await trustBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
          await trustBtn.click();
          log('Clicked Trust');
        }

        // Wait for redirect to ASC
        log('Waiting for ASC redirect...');
        for (let i = 0; i < 30; i++) {
          await page.waitForTimeout(2000);
          currentUrl = page.url();
          if (currentUrl.includes('appstoreconnect.apple.com') && !currentUrl.includes('auth')) {
            log('Logged in! URL: ' + currentUrl);
            break;
          }
          // Check trust button again
          const af = page.frames().find(f => f.url().includes('idmsa.apple.com')) || page.mainFrame();
          const tb = af.locator('button:has-text("Trust"), button:has-text("信頼")').first();
          if (await tb.isVisible().catch(() => false)) {
            await tb.click();
            log('Clicked Trust (retry)');
          }
        }
      }

      // Save cookies after successful login
      await saveCookies(context);
    }

    // Now on apps page
    await page.waitForTimeout(3000);
    currentUrl = page.url();
    log('[4] Apps page. URL: ' + currentUrl);
    await page.screenshot({ path: 'scripts/asc-apps-page.png' });

    // Click "New App" button (opens dropdown)
    log('[5] Opening New App dropdown...');
    // ASC "+" button or "New App" button
    let clickedNewApp = false;
    const newAppSelectors = [
      'button:has-text("New App")',
      'a:has-text("New App")',
      '[class*="toolbar"] button',
      'button[aria-label="Create"]',
      'button[aria-label="New App"]',
    ];

    for (const sel of newAppSelectors) {
      const el = page.locator(sel).first();
      if (await el.isVisible().catch(() => false)) {
        await el.click();
        log('Clicked: ' + sel);
        clickedNewApp = true;
        break;
      }
    }

    if (!clickedNewApp) {
      // Scan for blue "+" button by looking at all buttons
      const buttons = await page.locator('button, a[role="button"]').all();
      for (const btn of buttons) {
        const text = (await btn.textContent().catch(() => '')) || '';
        const label = (await btn.getAttribute('aria-label').catch(() => '')) || '';
        const combined = (text + ' ' + label).toLowerCase();
        if (combined.includes('new') || combined.includes('追加') || combined.includes('create') || text.trim() === '+') {
          log('Found candidate button: "' + text.trim() + '" aria="' + label + '"');
          await btn.click();
          clickedNewApp = true;
          break;
        }
      }
    }

    await page.waitForTimeout(2000);

    // Click "New App" menu item in dropdown
    const menuItems = page.locator('[role="menuitem"], [role="option"], a, button').filter({ hasText: /^New App$|^新規App$/ });
    if (await menuItems.first().isVisible().catch(() => false)) {
      await menuItems.first().click();
      log('Clicked "New App" menu item');
    }

    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'scripts/asc-new-app-dialog.png' });

    // Fill form
    log('[6] Filling form...');

    // Platform: iOS checkbox
    log('  Platform: iOS');
    const iosCheckboxes = [
      page.locator('label:has-text("iOS") input[type="checkbox"]').first(),
      page.locator('input[type="checkbox"][value="iOS"]').first(),
      page.locator('label:has-text("iOS")').first(),
      page.locator('text=iOS').first(),
    ];
    for (const cb of iosCheckboxes) {
      if (await cb.isVisible().catch(() => false)) {
        await cb.click();
        log('  iOS selected');
        break;
      }
    }
    await page.waitForTimeout(1500);

    // Name
    log('  Name: ' + APP_NAME);
    const nameInput = page.getByLabel('Name').first();
    if (await nameInput.isVisible().catch(() => false)) {
      await nameInput.click();
      await nameInput.fill('');
      await nameInput.type(APP_NAME, { delay: 80 });
    } else {
      // Try by placeholder or CSS
      const nameAlt = page.locator('input[placeholder*="name" i], input[name*="name" i]').first();
      if (await nameAlt.isVisible().catch(() => false)) {
        await nameAlt.click();
        await nameAlt.fill('');
        await nameAlt.type(APP_NAME, { delay: 80 });
      }
    }
    await page.waitForTimeout(1000);

    // Primary Language
    log('  Primary Language: English (U.S.)');
    const langSelect = page.getByLabel('Primary Language').first();
    if (await langSelect.isVisible().catch(() => false)) {
      await langSelect.selectOption({ label: 'English (U.S.)' });
    }
    await page.waitForTimeout(2000);

    // Bundle ID (async loading)
    log('  Bundle ID: ' + BUNDLE_ID);
    const bundleSelect = page.getByLabel('Bundle ID').first();
    if (await bundleSelect.isVisible().catch(() => false)) {
      // Wait for dropdown to populate
      for (let i = 0; i < 15; i++) {
        const options = await bundleSelect.locator('option').allTextContents();
        if (options.some(o => o.includes(BUNDLE_ID) || o.includes('affirmflow'))) {
          log('  Bundle ID options loaded');
          break;
        }
        await page.waitForTimeout(1000);
        if (i > 0 && i % 5 === 0) log('  Still waiting for bundle IDs...');
      }
      // Select matching option
      const options = await bundleSelect.locator('option').all();
      for (const opt of options) {
        const text = await opt.textContent();
        if (text && text.includes(BUNDLE_ID)) {
          const val = await opt.getAttribute('value');
          await bundleSelect.selectOption(val || text);
          log('  Selected: ' + text.trim());
          break;
        }
      }
    }
    await page.waitForTimeout(1000);

    // SKU
    log('  SKU: ' + SKU);
    const skuInput = page.getByLabel('SKU').first();
    if (await skuInput.isVisible().catch(() => false)) {
      await skuInput.click();
      await skuInput.fill('');
      await skuInput.type(SKU, { delay: 80 });
    }
    await page.waitForTimeout(1000);

    // User Access: Full Access (radio with span overlay — skill workaround)
    log('  User Access: Full Access');
    // Method 1: Find radio by value/label and use scrollIntoView + direct click
    const fullAccessRadio = page.locator('input[type="radio"]').last();
    if (await fullAccessRadio.isVisible().catch(() => false)) {
      await fullAccessRadio.evaluate(el => {
        el.scrollIntoView({ block: 'center' });
        el.click();
      });
      log('  Full Access radio clicked via evaluate');
    } else {
      // Method 2: Click the label/span
      const fullLabel = page.locator('span:has-text("Full Access"), label:has-text("Full Access")').first();
      if (await fullLabel.isVisible().catch(() => false)) {
        await fullLabel.click();
        log('  Full Access clicked via label');
      }
    }

    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'scripts/asc-form-filled.png' });

    // Click Create
    log('[7] Clicking Create...');
    const createBtn = page.locator('button:has-text("Create"), button:has-text("作成")').first();
    if (await createBtn.isVisible().catch(() => false)) {
      const disabled = await createBtn.isDisabled();
      if (disabled) {
        log('Create button DISABLED. Taking debug screenshot.');
        await page.screenshot({ path: 'scripts/asc-create-disabled.png' });
        // Try re-triggering form validation
        const skuField = page.getByLabel('SKU').first();
        if (await skuField.isVisible().catch(() => false)) {
          await skuField.click();
          await skuField.fill('');
          await skuField.type(SKU, { delay: 100 });
          await page.keyboard.press('Tab');
        }
        await page.waitForTimeout(2000);
        const stillDisabled = await createBtn.isDisabled();
        if (stillDisabled) {
          log('Create still disabled. Check screenshots for validation errors.');
          await page.screenshot({ path: 'scripts/asc-still-disabled.png' });
        } else {
          await createBtn.click();
          log('Create clicked after re-trigger');
        }
      } else {
        await createBtn.click();
        log('Create clicked!');
      }
    }

    // Wait for app creation
    log('[8] Waiting for app creation...');
    await page.waitForTimeout(10000);

    const finalUrl = page.url();
    log('Final URL: ' + finalUrl);
    await page.screenshot({ path: 'scripts/asc-result.png' });

    // Save cookies
    await saveCookies(context);

    // Extract App ID
    const appIdMatch = finalUrl.match(/\/apps\/(\d+)/);
    if (appIdMatch) {
      const appId = appIdMatch[1];
      log('SUCCESS! App ID: ' + appId);
      console.log(JSON.stringify({ success: true, appId, appName: APP_NAME, bundleId: BUNDLE_ID }));

      // Clean up signal file
      if (fs.existsSync(SIGNAL_PATH)) fs.unlinkSync(SIGNAL_PATH);
    } else {
      log('Could not confirm creation from URL. Check screenshots.');

      // Try API verification
      try {
        const result = execSync(`asc apps list --bundle-id "${BUNDLE_ID}" --output json 2>/dev/null`);
        const data = JSON.parse(result);
        if (data.data && data.data.length > 0) {
          const appId = data.data[0].id;
          log('Verified via API! App ID: ' + appId);
          console.log(JSON.stringify({ success: true, appId, appName: APP_NAME, bundleId: BUNDLE_ID }));
        }
      } catch (e) {
        log('API verification also failed.');
        console.log(JSON.stringify({ success: false, error: 'Could not verify app creation' }));
      }
    }

    // Keep browser open briefly for visual confirmation
    log('Browser stays open 30s for visual check...');
    await page.waitForTimeout(30000);

  } catch (error) {
    log('ERROR: ' + error.message);
    await page.screenshot({ path: 'scripts/asc-error.png' }).catch(() => {});
    console.log(JSON.stringify({ success: false, error: error.message }));
  } finally {
    await browser.close();
    log('Browser closed.');
  }
})();
