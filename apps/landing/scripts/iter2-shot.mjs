import { chromium } from 'playwright';
const browser = await chromium.launch();
const targets = [
  ['en', {width:1440,height:900}, 'light', 'en-desktop-light'],
  ['en', {width:1440,height:900}, 'dark', 'en-desktop-dark'],
  ['en', {width:375,height:812}, 'light', 'en-mobile-light'],
  ['factory', {width:1440,height:900}, 'light', 'factory-desktop-light'],
];
for (const [route, vp, theme, name] of targets) {
  const ctx = await browser.newContext({ viewport: vp, colorScheme: theme });
  const page = await ctx.newPage();
  await page.goto('https://aniccaai.com/' + route, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/tier-a-recon-iter2/' + name + '.png', fullPage: true });
  console.log('OK', name);
  await ctx.close();
}
await browser.close();
