import { chromium } from 'playwright';
const browser = await chromium.launch();
const targets = [
  ['en', {width:1440,height:900}, 'light', 'en-desktop-light'],
  ['en', {width:1440,height:900}, 'dark', 'en-desktop-dark'],
  ['en', {width:375,height:812}, 'light', 'en-mobile-light'],
  ['ja', {width:1440,height:900}, 'light', 'ja-desktop-light'],
  ['install', {width:1440,height:900}, 'light', 'install-desktop-light'],
];
for (const [route, vp, theme, name] of targets) {
  const ctx = await browser.newContext({ viewport: vp, colorScheme: theme });
  const page = await ctx.newPage();
  try {
    await page.goto('https://aniccaai.com/' + route, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/v2-recon/' + name + '.png', fullPage: true });
    console.log('OK', name);
  } catch (e) {
    console.log('FAIL', name, e.message.slice(0,80));
  }
  await ctx.close();
}
await browser.close();
