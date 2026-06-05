import { chromium } from 'playwright';
const browser = await chromium.launch();
const routes = ['ja','app','research','playbook','cfo','income','socials','faq','donation','letter'];
for (const r of routes) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: 'light' });
  const page = await ctx.newPage();
  try {
    await page.goto('https://aniccaai.com/' + r, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1500);
    await page.screenshot({ path: '/tmp/tier-a-recon-iter2/' + r + '-desktop-light.png', fullPage: true });
    console.log('OK', r);
  } catch (e) {
    console.log('FAIL', r, e.message.slice(0, 80));
  }
  await ctx.close();
}
await browser.close();
