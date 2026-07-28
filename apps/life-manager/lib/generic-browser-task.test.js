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
    discoverAndAct: async (_session, context) => {
      events.push({ stage: "driver_action" });
      await context.onSelected({
        selectedUrl: "https://events.example/ai",
        selectedOrigin: "https://events.example",
        selectionReason: "free, public, online, and matches the delegated request",
      });
      await context.onActionStarted({ action: "registered agent-owned email" });
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
    captureEvidence: async () => {
      events.push({ stage: "driver_evidence" });
      return { mimeType: "image/png", bytes: Buffer.from("cloud-png") };
    },
    releaseSession: async (id) => {
      events.push({ stage: "release", id });
      return { released: true };
    },
    sendTelegram: async (_chatId, text) => {
      events.push({ stage: "telegram", text });
      return { ok: true, result: { message_id: 9001 } };
    },
    sendTelegramEvidence: async (_chatId, evidence, caption) => {
      events.push({ stage: "telegram_evidence", evidence, caption });
      return { ok: true, result: { message_id: 9002 } };
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
  assert.equal(result.evidence_message_id, "9002");
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
      "action_observed",
      "driver_readback",
      "provider_readback",
      "driver_evidence",
      "telegram",
      "telegram_sent",
      "telegram_evidence",
      "evidence_sent",
      "release",
      "steel_released",
      "finish",
    ],
  );
});

test("a login or challenge page becomes handoff_required, never completed", async () => {
  const { deps } = fixture({
    readProviderReceipt: async () => ({
      confirmed: false,
      status: "login required",
      confirmationId: null,
      currentUrl: "https://events.example/login",
      handoffRequired: true,
      handoffReason: "login",
    }),
  });
  const result = await runGenericBrowserTask(JOB, deps);
  assert.equal(result.status, "handoff_required");
  assert.equal(result.provider_receipt.handoff_required, true);
  assert.equal(result.provider_receipt.handoff_reason, "login");
});

test("a timeout after browser execution starts is possibly_completed and releases Steel", async () => {
  let releases = 0;
  const { deps } = fixture({
    actionTimeoutMs: 5,
    discoverAndAct: async (_session, context) => {
      await context.onActionStarted({ action: "delegated action" });
      return new Promise(() => {});
    },
    releaseSession: async () => {
      releases += 1;
      return { released: true };
    },
  });
  const result = await runGenericBrowserTask(JOB, deps);
  assert.equal(result.status, "possibly_completed");
  assert.equal(releases, 1);
});

test("Telegram rejection does not erase the provider receipt or skip release and finish", async () => {
  let finished;
  let releases = 0;
  const { deps } = fixture({
    sendTelegram: async () => { throw new Error("Telegram rejected"); },
    releaseSession: async () => {
      releases += 1;
      return { released: true };
    },
    finishJob: async (_id, terminal) => { finished = terminal; },
  });
  const result = await runGenericBrowserTask(JOB, deps);
  assert.equal(result.status, "completed");
  assert.equal(result.telegram_message_id, null);
  assert.equal(releases, 1);
  assert.equal(finished.status, "completed");
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
