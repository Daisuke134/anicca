import { chromium } from 'playwright';
const browser = await chromium.launch();
const targets = [
  ['retreat', 'desktop-light'],
  ['cafe', 'desktop-light'],
  ['comedy', 'desktop-light'],
  ['fashion', 'desktop-light'],
  ['monk', 'desktop-light'],
  ['thankful', 'desktop-light'],
  ['privacy/en', 'desktop-light'],
  ['seo/buddhist-ai-agent', 'desktop-light'],
];
for (const [route, label] of targets) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: 'light' });
  const page = await ctx.newPage();
  try {
    await page.goto('https://aniccaai.com/' + route, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1500);
    const safe = route.replace(/\//g, '-');
    await page.screenshot({ path: '/tmp/tier-final-recon/' + safe + '-' + label + '.png', fullPage: true });
    console.log('OK', route);
  } catch (e) {
    console.log('FAIL', route, e.message.slice(0, 80));
  }
  await ctx.close();
}
await browser.close();
