#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const { chromium } = require("playwright-core");
const { resolveDataRoot } = require("../lib/runtime-paths.js");
const {
  extractTikTokNativeMetrics,
  persistTikTokCombinedSnapshot,
  persistTikTokNativeSnapshot,
} = require("../lib/tiktok-native-metric-source.js");

async function postizAnalytics(input) {
  if (!input.integrationId && !input.providerPostId) return null;
  if (!input.integrationId || !input.providerPostId || !process.env.LM_POSTIZ_API_KEY) {
    throw new Error("combined TikTok metrics require integrationId, providerPostId, and LM_POSTIZ_API_KEY");
  }
  const request = async (url) => {
    const response = await fetch(url, { headers: { Authorization: process.env.LM_POSTIZ_API_KEY } });
    if (!response.ok) throw new Error(`Postiz analytics HTTP ${response.status}`);
    return response.json();
  };
  const [account, post] = await Promise.all([
    request(`https://api.postiz.com/public/v1/analytics/${encodeURIComponent(input.integrationId)}?date=1`),
    request(`https://api.postiz.com/public/v1/analytics/post/${encodeURIComponent(input.providerPostId)}?date=1`),
  ]);
  return { account, post };
}

async function main() {
  const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const browser = await chromium.connectOverCDP(process.env.LM_CDP_ENDPOINT || "http://127.0.0.1:9222");
  try {
    const context = browser.contexts()[0];
    const page = context.pages().find((candidate) => candidate.url() === input.publicUrl) || await context.newPage();
    if (page.url() !== input.publicUrl) await page.goto(input.publicUrl, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.waitForTimeout(2_000);
    const metrics = extractTikTokNativeMetrics(await page.locator("script").allTextContents(), input);
    const provider = await postizAnalytics(input);
    const observedAt = new Date().toISOString();
    const result = provider ? persistTikTokCombinedSnapshot({
      ...input,
      dataDir: resolveDataRoot(process.env),
      observedAt,
      metrics,
      postizAccountAnalytics: provider.account,
      postizPostAnalytics: provider.post,
    }) : persistTikTokNativeSnapshot({
      ...input,
      dataDir: resolveDataRoot(process.env),
      observedAt,
      metrics,
    });
    process.stdout.write(`${JSON.stringify({ created: result.created, file: result.file, post: result.snapshot.post, account: result.snapshot.account_metrics })}\n`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
