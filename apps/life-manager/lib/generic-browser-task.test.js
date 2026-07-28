"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { runGenericBrowserTask } = require("./generic-browser-task.js");

const JOB = Object.freeze({
  id: "job-1",
  uid: "u-1",
  telegram_chat_id: "42",
  goal: "Find a suitable free public online AI event and register contact@aniccaai.com",
  locale: "en",
});

function fixture(overrides = {}) {
  const events = [];
  const deps = {
    appendTrace: async (_id, stage, meta) => {
      events.push({ stage, meta });
    },
    openSession: async () => {
      events.push({ stage: "open" });
      return { id: "steel-session-1", websocketUrl: "ws://steel-browser.railway.internal:8080/" };
    },
    discoverAndAct: async () => {
      events.push({ stage: "driver_action" });
      return {
        selectedUrl: "https://events.example/ai",
        selectedOrigin: "https://events.example",
        selectionReason: "free, public, online, and matches the delegated request",
        action: "registered agent-owned email",
        sideEffectStarted: true,
      };
    },
    readProviderReceipt: async () => {
      events.push({ stage: "driver_readback" });
      return {
        confirmed: true,
        status: "registered",
        confirmationId: "reg-123",
        currentUrl: "https://events.example/ai/confirmed",
      };
    },
    releaseSession: async (id) => {
      events.push({ stage: "release", id });
      return { released: true };
    },
    sendTelegram: async (_chatId, text) => {
      events.push({ stage: "telegram", text });
      return { ok: true, result: { message_id: 9001 } };
    },
    finishJob: async (_id, terminal) => {
      events.push({ stage: "finish", terminal });
    },
    ...overrides,
  };
  return { deps, events };
}

test("discovers an unregistered site, acts once, independently reads back, reports, then releases", async () => {
  const { deps, events } = fixture();
  const result = await runGenericBrowserTask(JOB, deps);

  assert.equal(result.status, "completed");
  assert.equal(result.session_id, "steel-session-1");
  assert.equal(result.selected_url, "https://events.example/ai");
  assert.equal(result.provider_receipt.confirmation_id, "reg-123");
  assert.equal(result.telegram_message_id, "9001");
  assert.equal(result.steel_released, true);
  assert.deepEqual(
    events.map((event) => event.stage),
    [
      "claimed",
      "open",
      "discovery",
      "driver_action",
      "selected",
      "action_started",
      "driver_readback",
      "provider_readback",
      "telegram",
      "telegram_sent",
      "finish",
      "release",
      "steel_released",
    ],
  );
});

test("a provider narration without independent confirmation is never completed", async () => {
  const { deps } = fixture({
    readProviderReceipt: async () => ({
      confirmed: false,
      status: "unknown",
      confirmationId: null,
      currentUrl: "https://events.example/ai",
    }),
  });
  const result = await runGenericBrowserTask(JOB, deps);
  assert.equal(result.status, "possibly_completed");
  assert.equal(result.provider_receipt.confirmed, false);
});

test("a post-action failure is possibly_completed, is never retried, and still releases Steel", async () => {
  let actionCalls = 0;
  let releases = 0;
  const error = new Error("provider page closed after click");
  error.sideEffectStarted = true;
  const { deps } = fixture({
    discoverAndAct: async () => {
      actionCalls += 1;
      throw error;
    },
    releaseSession: async () => {
      releases += 1;
      return { released: true };
    },
  });

  const result = await runGenericBrowserTask(JOB, deps);
  assert.equal(result.status, "possibly_completed");
  assert.equal(actionCalls, 1);
  assert.equal(releases, 1);
});

test("a pre-action failure is an honest failure and every opened Steel session is released", async () => {
  let releases = 0;
  const { deps } = fixture({
    discoverAndAct: async () => {
      throw new Error("search unavailable");
    },
    releaseSession: async () => {
      releases += 1;
      return { released: true };
    },
  });
  const result = await runGenericBrowserTask(JOB, deps);
  assert.equal(result.status, "failed");
  assert.equal(releases, 1);
});

