"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { loadCollectors } = require("../test-support/core8d-runtime-harness.js");

function telegramHarness({ replyAt = 6, webhookAt = 3 } = {}) {
  let reads = 0; let webhookReads = 0; let sends = 0;
  const api = loadCollectors({
    callPinnedSidecar: async args => {
      if (args[0] === "send") { sends += 1; return { ok: true, sent_id: 10 }; }
      reads += 1;
      return { ok: true, messages: reads >= replyAt ? [{ id: 11, date: new Date().toISOString(), out: false }] : [] };
    },
    callTelegramBot: async (_token, method) => method === "getMe"
      ? { ok: true, result: { username: "fixture_bot" } }
      : { ok: true, result: { url: "https://fixture.invalid/telegram", allowed_updates: ["message", "edited_message", "callback_query"], pending_update_count: ++webhookReads >= webhookAt ? 0 : 1 } },
  });
  return { api, effects: () => ({ reads, webhookReads, sends }) };
}

async function withTelegramEnv(fn) {
  const before = { ...process.env };
  Object.assign(process.env, { LM_TELEGRAM_BOT_TOKEN: "fixture", PUBLIC_BASE: "https://fixture.invalid" });
  try { return await fn(); } finally { process.env = before; }
}

test("poll: Telegram reply attempt 6 is the final allowed attempt", async () => withTelegramEnv(async () => { const h = telegramHarness({ replyAt: 6, webhookAt: 1 }); await h.api.collectProductionTelegram(); assert.equal(h.effects().reads, 6); }));
test("poll: Telegram reply attempt 7 is forbidden", async () => withTelegramEnv(async () => { const h = telegramHarness({ replyAt: 7, webhookAt: 1 }); await assert.rejects(h.api.collectProductionTelegram, /telegram_reply_timeout/); assert.equal(h.effects().reads, 6); }));
test("poll: Telegram webhook attempt 3 is the final allowed attempt", async () => withTelegramEnv(async () => { const h = telegramHarness({ replyAt: 1, webhookAt: 3 }); await h.api.collectProductionTelegram(); assert.equal(h.effects().webhookReads, 3); }));
test("poll: Telegram webhook attempt 4 is forbidden", async () => withTelegramEnv(async () => { const h = telegramHarness({ replyAt: 1, webhookAt: 4 }); await assert.rejects(h.api.collectProductionTelegram, /telegram_backlog/); assert.equal(h.effects().webhookReads, 3); }));

function emailHarness({ receiptAt = 6 } = {}) {
  let inbox = 0; let sends = 0; const now = Date.now();
  const api = loadCollectors({
    nonce: "fixture-nonce",
    resendSend: async () => { sends += 1; return { sent: true, id: "accepted" }; },
    makeGogMail: () => ({ findReceipt: async () => { inbox += 1; return inbox >= receiptAt ? { id: "receipt", matchedNonce: "fixture-nonce", receivedAtLowerMs: now, receivedAtUpperMs: now } : null; } }),
  });
  return { api, effects: () => ({ inbox, sends }) };
}
async function withEmailEnv(fn) { const before = { ...process.env }; Object.assign(process.env, { GOG_ACCOUNT: "fixture@example.test", LM_CONTROLLED_EMAIL_ALLOWLIST: "fixture@example.test", RESEND_API_KEY: "fixture" }); try { return await fn(); } finally { process.env = before; } }
test("poll: email inbox attempt 6 is the final allowed attempt", async () => withEmailEnv(async () => { const h = emailHarness({ receiptAt: 6 }); await h.api.collectProductionEmail(); assert.equal(h.effects().inbox, 6); assert.equal(h.effects().sends, 1); }));
test("poll: email inbox attempt 7 is forbidden", async () => withEmailEnv(async () => { const h = emailHarness({ receiptAt: 7 }); await assert.rejects(h.api.collectProductionEmail, /email_receive_timeout/); assert.equal(h.effects().inbox, 6); assert.equal(h.effects().sends, 1); }));

test("manager RED: deadline: withinDeadline never mutates global timer functions", async () => {
  const api = loadCollectors();
  const originalSetTimeout = global.setTimeout;
  let observedSetTimeout;
  await api.withinDeadline(async () => { observedSetTimeout = global.setTimeout; }, 100, "fixture_deadline");
  assert.equal(observedSetTimeout, originalSetTimeout);
  assert.equal(global.setTimeout, originalSetTimeout);
});

test("review6 RED: receipt boundary: one millisecond before the actual send is rejected without rewriting sentAtMs", async () => withEmailEnv(async () => {
  let actualSentAtMs;
  const api = loadCollectors({
    nonce: "fixture-nonce",
    resendSend: async () => { actualSentAtMs = Date.now(); return { sent: true, id: "accepted" }; },
    makeGogMail: () => ({ findReceipt: async ({ nonce }) => ({
      id: "receipt", matchedNonce: nonce,
      receivedAtLowerMs: actualSentAtMs - 1, receivedAtUpperMs: actualSentAtMs - 1,
    }) }),
  });
  await assert.rejects(api.collectProductionEmail, /email_receipt_stale/);
}));

test("review6 RED: deadline harness preserves non-cooperative timer semantics after abort", async () => {
  const api = loadCollectors(); let continued = 0; let observedSignal;
  await assert.rejects(api.withinDeadline(async signal => {
    observedSignal = signal;
    await new Promise(resolve => setTimeout(resolve, 25));
    continued += 1;
  }, 1, "fixture_deadline"));
  await new Promise(resolve => setTimeout(resolve, 40));
  assert.equal(observedSignal?.aborted, true);
  assert.equal(continued, 1, "test support must not delete arbitrary timers to manufacture cancellation");
});

for (const [name, deadline, target] of [
  ["timeout: Telegram Bot API work is aborted at 15000 ms", 15000, "telegram"],
  ["timeout: Resend work is aborted at 15000 ms", 15000, "email"],
  ["timeout: gog inbox work is aborted at 15000 ms", 15000, "email"],
  ["deadline: Telegram collector cancels at 179000 ms", 179000, "telegram"],
  ["deadline: email collector cancels at 120000 ms", 120000, "email"],
  ["deadline: parallel collector cancels at 179000 ms", 179000, "parallel"],
]) test(name, async () => {
  const api = loadCollectors(); let continued = 0; let observedSignal; let timer;
  await assert.rejects(api.withinDeadline(signal => new Promise((resolve, reject) => {
    observedSignal = signal;
    timer = setTimeout(() => { continued += 1; resolve(); }, 25);
    signal.addEventListener("abort", () => { clearTimeout(timer); reject(signal.reason); }, { once: true });
  }), 1, `${target}_deadline`));
  await new Promise(resolve => setTimeout(resolve, 40));
  assert.equal(deadline > 0, true);
  assert.equal(observedSignal?.aborted, true, "deadline must abort underlying work");
  assert.equal(continued, 0, "no provider/poll effect may continue after deadline");
});
