"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  runNextBrowserJob,
  startBrowserJobLoop,
} = require("./browser-job-runtime.js");

const JOB = Object.freeze({
  id: "job-1",
  uid: "u-1",
  telegram_chat_id: "42",
  goal: "find and register",
  locale: "en",
});

function successfulDeps(overrides = {}) {
  const traces = [];
  return {
    traces,
    claimJob: async () => JOB,
    appendTrace: async (_id, stage) => { traces.push(stage); },
    finishJob: async () => true,
    sendMessage: async () => ({ ok: true, result: { message_id: 77 } }),
    sendPhoto: async () => ({ ok: true, result: { message_id: 78 } }),
    telegramToken: "token",
    driver: {
      openSession: async () => ({ id: "s1", websocketUrl: "ws://steel-browser.railway.internal:8080/" }),
      discoverAndAct: async () => ({
        selectedUrl: "https://fresh.example/done",
        selectedOrigin: "https://fresh.example",
        selectionReason: "matched",
        action: "registered",
        sideEffectStarted: true,
      }),
      readProviderReceipt: async () => ({
        confirmed: true,
        status: "registered",
        confirmationId: "r1",
        currentUrl: "https://fresh.example/done",
      }),
      captureEvidence: async () => ({
        mimeType: "image/png",
        bytes: Buffer.from("cloud-png"),
      }),
      releaseSession: async () => ({ released: true }),
    },
    ...overrides,
  };
}

test("the cloud worker claims one durable job and runs the complete generic browser task", async () => {
  const deps = successfulDeps();
  const result = await runNextBrowserJob(deps);
  assert.equal(result.status, "completed");
  assert.equal(result.selected_url, "https://fresh.example/done");
  assert.equal(result.telegram_message_id, "77");
  assert.equal(result.steel_released, true);
});

test("no queued job constructs no browser and causes no side effect", async () => {
  const result = await runNextBrowserJob({
    claimJob: async () => null,
    driver: { openSession: async () => { throw new Error("must not run"); } },
  });
  assert.deepEqual(result, { status: "idle" });
});

test("the worker injects agent-owned identity only when constructing the browser driver", async () => {
  let driverOptions;
  const deps = successfulDeps({
    driver: undefined,
    agentEmail: "browser-owner@example.test",
    makeDriver(options) {
      driverOptions = options;
      return successfulDeps().driver;
    },
  });
  const result = await runNextBrowserJob(deps);
  assert.equal(result.status, "completed");
  assert.equal(driverOptions.agentEmail, "browser-owner@example.test");
  assert.doesNotMatch(JSON.stringify(result), /browser-owner@example\.test/i);
});

test("the loop has an overlap guard so a slow browser job cannot be claimed twice", async () => {
  let claims = 0;
  let resolveClaim;
  const claimWait = new Promise((resolve) => { resolveClaim = resolve; });
  const scheduled = [];
  const loop = startBrowserJobLoop({
    enabled: true,
    intervalMs: 1000,
    setTimeoutImpl: (fn) => { scheduled.push(fn); return scheduled.length; },
    clearTimeoutImpl: () => {},
    runOnce: async () => {
      claims += 1;
      await claimWait;
    },
  });
  const first = loop.runNow();
  const second = loop.runNow();
  await Promise.resolve();
  assert.equal(claims, 1);
  resolveClaim();
  await Promise.all([first, second]);
  loop.close();
});
