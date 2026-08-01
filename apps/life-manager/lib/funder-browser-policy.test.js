"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const { createCloakBrowserDailyDriverForTest } = require("./cloakbrowser-daily-driver.js");
const { validateFunderBrowserRoutes } = require("./funder-browser-policy.js");

function fixture(contextCount = 1) {
  const calls = [];
  const page = { async goto(url) { calls.push(["goto", url]); }, async close() { calls.push(["close-page"]); } };
  const context = { pages: () => [], async newPage() { calls.push(["new-page"]); return page; } };
  return { calls, page, connectOverCDP: async (endpoint) => ({ contexts: () => (calls.push(["connect", endpoint]), Array.from({ length: contextCount }, () => context)), async close() { calls.push(["close-browser"]); } }) };
}

const ATTEMPT_ID = "11111111-1111-4111-8111-111111111111";
const NOW = Date.parse("2026-08-02T03:00:00.000Z");
const dayGate = () => ({ schema_version: 1, tenant_id: "dais-local", attempt_id: ATTEMPT_ID, tokyo_day: "2026-08-02", gate_id: `funder-day-gate:${"a".repeat(64)}`, gate_digest: "a".repeat(64), funder_id: "yc-f26", decision: "allow", submit_allowed: true });
const freshnessGate = () => ({ schema_version: 1, tenant_id: "dais-local", attempt_id: ATTEMPT_ID, evaluated_at: "2026-08-02T02:00:00.000Z", expires_at: "2026-08-02T04:00:00.000Z", gate_id: `funder-freshness-gate:${"b".repeat(64)}`, gate_digest: "b".repeat(64), funder_id: "yc-f26", decision: "allow", submit_allowed: true });
const submission = { specPath: "/fixture/spec.json", payloadPath: "/fixture/payload.json" };
const persisted = async (_day, _fresh, bound) => ({ submission: bound, cleanup() {} });

test("official funder form uses only :9222 shared context and closes only its owned page", async () => {
  const fx = fixture();
  const driver = createCloakBrowserDailyDriverForTest({ connectOverCDP: fx.connectOverCDP, now: () => NOW }, persisted);
  const result = await driver.withFunderPage("https://apply.ycombinator.com/home", { tenant_id: "dais-local", attempt_id: ATTEMPT_ID, funder_id: "yc-f26", allowed_origins: ["https://apply.ycombinator.com"] }, dayGate(), freshnessGate(), submission, async (page, metadata) => {
    assert.equal(page, fx.page); assert.equal(metadata.endpoint, "http://127.0.0.1:9222"); assert.equal(metadata.submission, submission); return "ready";
  });
  assert.equal(result, "ready");
  assert.equal(fx.calls.some(([name]) => name === "close-browser"), false);
  assert.deepEqual(fx.calls.at(-1), ["close-page"]);
});

test("funder page rejects origin drift, credentials, and multiple shared contexts", async () => {
  const driver = createCloakBrowserDailyDriverForTest({ connectOverCDP: fixture().connectOverCDP, now: () => NOW }, persisted);
  const policy = { tenant_id: "dais-local", attempt_id: ATTEMPT_ID, funder_id: "yc-f26", allowed_origins: ["https://apply.ycombinator.com"] };
  const gate = dayGate(), fresh = freshnessGate();
  await assert.rejects(driver.withFunderPage("https://evil.example/form", policy, gate, fresh, submission, async () => {}), /funder/i);
  await assert.rejects(driver.withFunderPage("https://u:p@apply.ycombinator.com/home", policy, gate, fresh, submission, async () => {}), /funder/i);
  await assert.rejects(driver.withFunderPage("https://apply.ycombinator.com/home", policy, null, fresh, submission, async () => {}), /submission-day/i);
  await assert.rejects(driver.withFunderPage("https://apply.ycombinator.com/home", policy, { ...gate, submit_allowed: false }, fresh, submission, async () => {}), /submission-day/i);
  await assert.rejects(driver.withFunderPage("https://apply.ycombinator.com/home", policy, gate, null, submission, async () => {}), /freshness/i);
  await assert.rejects(driver.withFunderPage("https://apply.ycombinator.com/home", policy, gate, { ...fresh, decision: "refresh_required", submit_allowed: false }, submission, async () => {}), /freshness/i);
  await assert.rejects(driver.withFunderPage("https://apply.ycombinator.com/home", policy, gate, { ...fresh, attempt_id: "22222222-2222-4222-8222-222222222222" }, submission, async () => {}), /freshness/i);
  await assert.rejects(driver.withFunderPage("https://apply.ycombinator.com/home", policy, gate, { ...fresh, expires_at: "2026-08-02T02:59:59.000Z" }, submission, async () => {}), /freshness/i);
  const bindingRequired = createCloakBrowserDailyDriverForTest({ connectOverCDP: fixture().connectOverCDP, now: () => NOW }, async (_day, _fresh, bound) => bound ? { submission: bound, cleanup() {} } : false);
  await assert.rejects(bindingRequired.withFunderPage("https://apply.ycombinator.com/home", policy, gate, fresh, null, async () => {}), /persisted gate/i);
  const unverified = createCloakBrowserDailyDriverForTest({ connectOverCDP: fixture().connectOverCDP, now: () => NOW }, async () => false);
  await assert.rejects(unverified.withFunderPage("https://apply.ycombinator.com/home", policy, gate, fresh, submission, async () => {}), /persisted gate/i);
  const many = createCloakBrowserDailyDriverForTest({ connectOverCDP: fixture(2).connectOverCDP, now: () => NOW }, persisted);
  await assert.rejects(many.withFunderPage("https://apply.ycombinator.com/home", policy, gate, fresh, submission, async () => {}), /shared context/i);
});

test("every active funder route is bound to the one daily-driver and never launches a browser", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, "../config/funder-form-routes.json"), "utf8"));
  const result = validateFunderBrowserRoutes(manifest);
  assert.deepEqual(result, { route_count: 2, browser_ref: "browser-profile://cloakbrowser/daily-driver", endpoint: "http://127.0.0.1:9222" });
  assert.throws(() => validateFunderBrowserRoutes({ ...manifest, endpoint: "http://127.0.0.1:9223" }), /funder browser/i);
  assert.throws(() => validateFunderBrowserRoutes({ ...manifest, routes: [{ ...manifest.routes[0], launch_command: "chromium.launch()" }] }), /funder browser/i);
});
