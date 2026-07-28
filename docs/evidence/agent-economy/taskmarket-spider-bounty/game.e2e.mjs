import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright";

const htmlPath = new URL("./index.html", import.meta.url);
const html = await readFile(htmlPath, "utf8");

assert.match(html, /<!doctype html>/i);
assert.doesNotMatch(html, /<script[^>]+src=/i);
assert.doesNotMatch(html, /<link[^>]+href=["']https?:/i);
assert.doesNotMatch(html, /\bfetch\s*\(|XMLHttpRequest|WebSocket\s*\(/);
assert.match(html, /not an identification or medical guide/i);
assert.match(html, /image credits/i);

const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
const context = browser.contexts()[0];
const page = await context.newPage();
const consoleErrors = [];
const networkRequests = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("request", (request) => networkRequests.push(request.url()));

await page.setViewportSize({ width: 390, height: 844 });
await page.goto(pathToFileURL(htmlPath.pathname).href);
await page.waitForSelector('[data-testid="card"]');

assert.equal(await page.locator('[data-testid="card"]').count(), 16);
assert.equal(await page.locator('[data-testid="progress"]').textContent(), "0 / 8 pairs");
assert.match(await page.locator('[data-testid="turn"]').textContent(), /Player 1/);

await page.locator('[data-testid="player-1-name"]').fill("Ari");
await page.locator('[data-testid="player-2-name"]').fill("Bo");

const cardData = await page.locator('[data-testid="card"]').evaluateAll((cards) =>
  cards.map((card, index) => ({ index, spider: card.dataset.spider })),
);
const bySpider = Map.groupBy(cardData, (card) => card.spider);
assert.equal(bySpider.size, 8);
for (const pair of bySpider.values()) assert.equal(pair.length, 2);

const firstPair = [...bySpider.values()][0];
await page.locator('[data-testid="card"]').nth(firstPair[0].index).press("Enter");
await page.locator('[data-testid="card"]').nth(firstPair[1].index).click();
await page.waitForFunction(() => document.querySelector('[data-testid="progress"]').textContent.includes("1 / 8"));
assert.equal(await page.locator('[data-testid="player-1-score"]').textContent(), "1");
assert.match(await page.locator('[data-testid="turn"]').textContent(), /Ari/);

const unmatchedGroups = [...bySpider.values()].slice(1);
const mismatchA = unmatchedGroups[0][0];
const mismatchB = unmatchedGroups[1][0];
const lockedCard = unmatchedGroups[2][0];
await page.locator('[data-testid="card"]').nth(mismatchA.index).click();
await page.locator('[data-testid="card"]').nth(mismatchB.index).click();
await page.locator('[data-testid="card"]').nth(lockedCard.index).click();
assert.equal(
  await page.locator('[data-testid="card"]').nth(lockedCard.index).getAttribute("aria-pressed"),
  "false",
);
await page.waitForTimeout(900);
assert.match(await page.locator('[data-testid="turn"]').textContent(), /Bo/);
assert.equal(
  await page.locator('[data-testid="card"]').nth(mismatchA.index).getAttribute("aria-pressed"),
  "false",
);

for (const pair of unmatchedGroups) {
  await page.locator('[data-testid="card"]').nth(pair[0].index).click();
  await page.locator('[data-testid="card"]').nth(pair[1].index).click();
  await page.waitForTimeout(40);
}
await page.waitForSelector('[data-testid="game-over"]:not([hidden])');
assert.match(await page.locator('[data-testid="result"]').textContent(), /wins|draw/i);

await page.locator('[data-testid="play-again"]').click();
assert.equal(await page.locator('[data-testid="progress"]').textContent(), "0 / 8 pairs");
assert.equal(await page.locator('[data-testid="player-1-score"]').textContent(), "0");
assert.equal(await page.locator('[data-testid="player-1-name"]').inputValue(), "Ari");

await page.locator('[data-testid="new-players"]').click();
assert.equal(await page.locator('[data-testid="player-1-name"]').inputValue(), "");
assert.equal(await page.locator('[data-testid="player-2-name"]').inputValue(), "");

await page.setViewportSize({ width: 320, height: 700 });
const overflow = await page.evaluate(() => ({
  fits: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  viewport: document.documentElement.clientWidth,
  document: document.documentElement.scrollWidth,
  elements: [...document.querySelectorAll("body *")]
    .filter((element) => element.getBoundingClientRect().right > document.documentElement.clientWidth)
    .map((element) => ({
      tag: element.tagName,
      className: element.className,
      right: Math.round(element.getBoundingClientRect().right),
    }))
    .slice(0, 8),
}));
assert.equal(overflow.fits, true, JSON.stringify(overflow));
assert.deepEqual(consoleErrors, []);
assert.deepEqual(networkRequests.filter((url) => !url.startsWith("file:")), []);

await page.close();
console.log("PASS: spider memory game acceptance E2E");
