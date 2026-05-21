const { chromium } = require('/opt/homebrew/lib/node_modules/playwright');

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 200 });
  const page = await browser.newPage();

  await page.goto('https://appstoreconnect.apple.com/login', { timeout: 30000 });
  await page.waitForTimeout(5000);

  console.log('URL:', page.url());
  await page.screenshot({ path: 'scripts/debug-1.png', fullPage: true });

  // Check if it's an iframe-based login
  const frames = page.frames();
  console.log('Frames:', frames.length);
  for (const f of frames) {
    console.log('  Frame:', f.url());
  }

  // Get all visible elements
  const inputs = await page.locator('input').all();
  console.log('\nAll inputs:', inputs.length);
  for (let i = 0; i < inputs.length; i++) {
    const type = await inputs[i].getAttribute('type').catch(() => '?');
    const id = await inputs[i].getAttribute('id').catch(() => '?');
    const name = await inputs[i].getAttribute('name').catch(() => '?');
    const placeholder = await inputs[i].getAttribute('placeholder').catch(() => '?');
    const visible = await inputs[i].isVisible().catch(() => false);
    console.log(`  input[${i}]: type=${type} id=${id} name=${name} placeholder=${placeholder} visible=${visible}`);
  }

  // Check iframes for Apple ID auth
  for (const f of frames) {
    if (f === page.mainFrame()) continue;
    const frameInputs = await f.locator('input').all().catch(() => []);
    console.log(`\nFrame inputs (${f.url().substring(0,60)}...):`, frameInputs.length);
    for (let i = 0; i < frameInputs.length; i++) {
      const type = await frameInputs[i].getAttribute('type').catch(() => '?');
      const id = await frameInputs[i].getAttribute('id').catch(() => '?');
      const placeholder = await frameInputs[i].getAttribute('placeholder').catch(() => '?');
      const visible = await frameInputs[i].isVisible().catch(() => false);
      console.log(`  input[${i}]: type=${type} id=${id} placeholder=${placeholder} visible=${visible}`);
    }
  }

  // Get page HTML (first 2000 chars)
  const html = await page.content();
  console.log('\nHTML (first 3000 chars):\n', html.substring(0, 3000));

  await page.waitForTimeout(5000);
  await browser.close();
})();
