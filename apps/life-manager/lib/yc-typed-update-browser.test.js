"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const { createYcTypedUpdateBrowserAdapter } = require("./yc-typed-update-browser.js");

const ID = "0b61fe42-e383-490d-b60e-04f1ad7ec5df";
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
const digest = (value) => createHash("sha256").update(stable(value)).digest("hex");

function fakeDriver() {
  const calls = [];
  const values = {};
  const choices = {};
  let demoReady = false;
  return {
    calls,
    driver: {
      async navigate(route) { calls.push(["navigate", route]); },
      async setText(name, value) { calls.push(["setText", name, value]); values[name] = value; },
      async setChoice(question, option) { calls.push(["setChoice", question, option]); choices[question] = option; },
      async setFile(file) { calls.push(["setFile", file]); demoReady = true; },
      async activate(text) { calls.push(["activate", text]); },
      async readText(name) { calls.push(["readText", name]); return values[name]; },
      async readChoice(question) { calls.push(["readChoice", question]); return choices[question]; },
      async readDemo() { calls.push(["readDemo"]); return { ready: demoReady, duration_seconds: 50.833333, width: 1920, height: 1080 }; },
    },
  };
}

test("progress update uses only its exact route, fields, choices, and one update control", async () => {
  const fx = fakeDriver();
  const payload = {
    productLink: "https://github.com/Daisuke134/life-manager",
    productCreds: "No login is required.",
    howfar: "Current progress.",
    worked: "Current work.",
    techstack: "Current stack.",
    people_using: true,
    have_revenue: false,
  };
  const operation = { operation_type: "progress_update", route: `/apps/${ID}/edit/progress`, payload, expected_readback_digest: digest(payload) };
  const adapter = createYcTypedUpdateBrowserAdapter({ driver: fx.driver });
  await adapter.apply(operation);
  assert.deepEqual(fx.calls.slice(-3), [
    ["setChoice", "Are people using your product?", "Yes"],
    ["setChoice", "Do you have revenue?", "No"],
    ["activate", "Submit update"],
  ]);
  assert.equal(fx.calls.filter(([name]) => name === "activate").length, 1);
  assert.deepEqual(await adapter.readback(operation), { result: "confirmed", readback_digest: digest(payload) });
});

test("demo upload binds the resolved local file to the planned artifact digest", async () => {
  const fx = fakeDriver();
  const artifactDigest = "a".repeat(64);
  const payload = { demo_video: { source_ref: "application-kit://videos/life-manager-yc-demo.mp4", artifact_digest: artifactDigest } };
  const operation = { operation_type: "demo_update", route: `/apps/${ID}/edit/demo`, payload, asset_digest: artifactDigest, expected_readback_digest: digest(payload) };
  const adapter = createYcTypedUpdateBrowserAdapter({ driver: fx.driver, artifactResolver: async () => ({ path: "/private/application-kit/videos/life-manager-yc-demo.mp4", digest: artifactDigest }) });
  await adapter.apply(operation);
  assert.deepEqual(fx.calls, [["navigate", operation.route], ["setFile", "/private/application-kit/videos/life-manager-yc-demo.mp4"], ["activate", "Save & back"]]);
  assert.deepEqual(await adapter.readback(operation), { result: "confirmed", readback_digest: digest(payload) });
  const mismatch = createYcTypedUpdateBrowserAdapter({ driver: fakeDriver().driver, artifactResolver: async () => ({ path: "/private/demo.mp4", digest: "b".repeat(64) }) });
  await assert.rejects(() => mismatch.apply(operation), /artifact/i);
});

test("unsafe routes and application submission controls fail before browser mutation", async () => {
  const fx = fakeDriver();
  const adapter = createYcTypedUpdateBrowserAdapter({ driver: fx.driver });
  await assert.rejects(() => adapter.apply({ operation_type: "progress_update", route: `/apps/${ID}/edit`, payload: {}, expected_readback_digest: "a".repeat(64) }), /route/i);
  assert.deepEqual(fx.calls, []);
  assert.doesNotMatch(JSON.stringify(adapter), /Submit application/);
});
