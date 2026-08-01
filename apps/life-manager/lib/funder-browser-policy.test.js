"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const { createCloakBrowserDailyDriver } = require("./cloakbrowser-daily-driver.js");
const { validateFunderBrowserRoutes } = require("./funder-browser-policy.js");

function fixture(contextCount = 1) {
  const calls = [];
  const page = { async goto(url) { calls.push(["goto", url]); }, async close() { calls.push(["close-page"]); } };
  const context = { pages: () => [], async newPage() { calls.push(["new-page"]); return page; } };
  return { calls, page, connectOverCDP: async (endpoint) => ({ contexts: () => (calls.push(["connect", endpoint]), Array.from({ length: contextCount }, () => context)), async close() { calls.push(["close-browser"]); } }) };
}

test("official funder form uses only :9222 shared context and closes only its owned page", async () => {
  const fx = fixture();
  const driver = createCloakBrowserDailyDriver({ connectOverCDP: fx.connectOverCDP });
  const result = await driver.withFunderPage("https://apply.ycombinator.com/home", { allowed_origins: ["https://apply.ycombinator.com"] }, async (page, metadata) => {
    assert.equal(page, fx.page); assert.equal(metadata.endpoint, "http://127.0.0.1:9222"); return "ready";
  });
  assert.equal(result, "ready");
  assert.equal(fx.calls.some(([name]) => name === "close-browser"), false);
  assert.deepEqual(fx.calls.at(-1), ["close-page"]);
});

test("funder page rejects origin drift, credentials, and multiple shared contexts", async () => {
  const driver = createCloakBrowserDailyDriver({ connectOverCDP: fixture().connectOverCDP });
  await assert.rejects(driver.withFunderPage("https://evil.example/form", { allowed_origins: ["https://apply.ycombinator.com"] }, async () => {}), /funder/i);
  await assert.rejects(driver.withFunderPage("https://u:p@apply.ycombinator.com/home", { allowed_origins: ["https://apply.ycombinator.com"] }, async () => {}), /funder/i);
  const many = createCloakBrowserDailyDriver({ connectOverCDP: fixture(2).connectOverCDP });
  await assert.rejects(many.withFunderPage("https://apply.ycombinator.com/home", { allowed_origins: ["https://apply.ycombinator.com"] }, async () => {}), /shared context/i);
});

test("every active funder route is bound to the one daily-driver and never launches a browser", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, "../config/funder-form-routes.json"), "utf8"));
  const result = validateFunderBrowserRoutes(manifest);
  assert.deepEqual(result, { route_count: 2, browser_ref: "browser-profile://cloakbrowser/daily-driver", endpoint: "http://127.0.0.1:9222" });
  assert.throws(() => validateFunderBrowserRoutes({ ...manifest, endpoint: "http://127.0.0.1:9223" }), /funder browser/i);
  assert.throws(() => validateFunderBrowserRoutes({ ...manifest, routes: [{ ...manifest.routes[0], launch_command: "chromium.launch()" }] }), /funder browser/i);
});
