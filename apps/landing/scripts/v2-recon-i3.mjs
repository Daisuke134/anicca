import { chromium } from 'playwright';
const browser = await chromium.launch();
const targets = [
  ['manifesto', {width:1440,height:900}, 'light', 'manifesto-desktop-light'],
  ['manifesto/ja', {width:1440,height:900}, 'light', 'manifesto-ja-desktop-light'],
  ['account', {width:1440,height:900}, 'light', 'account-desktop-light'],
  ['manifesto', {width:375,height:812}, 'light', 'manifesto-mobile-light'],
];
for (const [route, vp, theme, name] of targets) {
  const ctx = await browser.newContext({ viewport: vp, colorScheme: theme });
  const page = await ctx.newPage();
  try {
    await page.goto('https://aniccaai.com/' + route, { waitUntil: 'networkidle', timeout: 30000 });
    await page.evaluate(async () => {
      const total = document.body.scrollHeight;
      for (let y = 0; y < total; y += 600) {
        window.scrollTo(0, y);
        await new Promise(r => setTimeout(r, 100));
      }
      window.scrollTo(0, 0);
      await new Promise(r => setTimeout(r, 600));
    });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: '/tmp/v2-recon-iter3/' + name + '.png', fullPage: true });
    console.log('OK', name);
  } catch (e) { console.log('FAIL', name, e.message.slice(0,80)); }
  await ctx.close();
}
await browser.close();
