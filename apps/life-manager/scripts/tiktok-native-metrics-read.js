#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const { chromium } = require("playwright-core");
const { resolveDataRoot } = require("../lib/runtime-paths.js");
const { extractTikTokNativeMetrics, persistTikTokNativeSnapshot } = require("../lib/tiktok-native-metric-source.js");

async function main() {
  const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const browser = await chromium.connectOverCDP(process.env.LM_CDP_ENDPOINT || "http://127.0.0.1:9222");
  try {
    const context = browser.contexts()[0];
    const page = context.pages().find((candidate) => candidate.url() === input.publicUrl) || await context.newPage();
    if (page.url() !== input.publicUrl) await page.goto(input.publicUrl, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.waitForTimeout(2_000);
    const metrics = extractTikTokNativeMetrics(await page.locator("script").allTextContents(), input);
    const result = persistTikTokNativeSnapshot({
      ...input,
      dataDir: resolveDataRoot(process.env),
      observedAt: new Date().toISOString(),
      metrics,
    });
    process.stdout.write(`${JSON.stringify({ created: result.created, file: result.file, post: result.snapshot.post })}\n`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
