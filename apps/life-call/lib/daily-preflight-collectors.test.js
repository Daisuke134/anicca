"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const {
  validateEmailObservation,
  validateTelegramObservation,
} = require("./daily-preflight-collectors.js");
const { createEmailCollector, createTelegramCollector } = require("./daily-preflight.test-support.js");

const NOW = Date.parse("2026-07-21T06:00:00Z");
const hash = "sha256:0123456789abcdef";
const telegramGood = () => ({
  sentId: 41, replyId: 42, sentAtMs: NOW - 1000, replyAtMs: NOW,
  webhookUrl: "https://life.example/telegram", expectedWebhookUrl: "https://life.example/telegram",
  allowedUpdates: ["message", "edited_message", "callback_query"], lastError: false,
  pendingUpdateSamples: [1, 0],
});
const emailGood = () => ({
  recipient: "controlled@aniccaai.com", receiveIdentity: "controlled@aniccaai.com",
  providerAcceptedId: "provider-id", receiptMessageId: "gmail-id",
  nonce: "a".repeat(32), receivedNonce: "a".repeat(32), sentAtMs: NOW - 1000, receivedAtMs: NOW,
});
const EMAIL_ALLOWLIST = ["controlled@aniccaai.com"];

test("telegram observation rejects missing/rejected round trip, timeout, URL/update/error/backlog", () => {
  const cases = [
    v => { delete v.sentId; }, v => { delete v.replyId; }, v => { v.replyAtMs = 0; },
    v => { v.webhookUrl = "https://wrong.example/telegram"; },
    v => { v.allowedUpdates = ["message"]; }, v => { v.lastError = true; },
    v => { v.pendingUpdateSamples = [1, 1, 1]; },
  ];
  for (const mutate of cases) { const value = telegramGood(); mutate(value); assert.throws(() => validateTelegramObservation(value, NOW)); }
  assert.deepEqual(validateTelegramObservation(telegramGood(), NOW).pendingUpdateSamples, [1, 0]);
});

test("email observation rejects ownership, send, timeout, nonce mismatch, and stale receipt", () => {
  const cases = [
    v => { v.recipient = "other@example.com"; },
    v => { v.providerAcceptedId = ""; }, v => { v.receiptMessageId = ""; },
    v => { v.receivedNonce = `${v.nonce}x`; }, v => { v.receivedAtMs = v.sentAtMs - 1; },
    v => { v.receivedAtMs = NOW - 900001; },
  ];
  for (const mutate of cases) { const value = emailGood(); mutate(value); assert.throws(() => validateEmailObservation(value, NOW, EMAIL_ALLOWLIST)); }
  assert.equal(validateEmailObservation(emailGood(), NOW, EMAIL_ALLOWLIST).providerRef.startsWith("sha256:"), true);
});

test("telegram adapter sends once and bounded-polls [1,0]", async () => {
  let sends = 0; let command; let peer; const pending = [1, 0];
  const collect = createTelegramCollector({
    env: { LM_TELEGRAM_BOT_TOKEN: "token", ANICCA_PROXY_BASE_URL: "https://life.example" }, now: () => NOW,
    botCall: async method => method === "getMe" ? { ok: true, result: { username: "LifeBot" } } : { ok: true, result: {
      url: "https://life.example/telegram", allowed_updates: ["message", "edited_message", "callback_query"],
      pending_update_count: pending.shift(),
    } },
    mtprotoSend: async (derivedPeer, sentCommand) => { sends += 1; peer = derivedPeer; command = sentCommand; return { id: 41, atMs: NOW - 1 }; },
    mtprotoRead: async () => [{ id: 42, atMs: NOW, inbound: true }], sleep: async () => {},
  });
  const result = await collect();
  assert.equal(sends, 1); assert.equal(peer, "@LifeBot");
  assert.match(command, /^\/panel core8d_[a-f0-9]{24}$/);
  assert.deepEqual(result.pendingUpdateSamples, [1, 0]);
});

test("telegram adapter fails closed on reply timeout without a duplicate send", async () => {
  let sends = 0;
  const collect = createTelegramCollector({
    env: { LM_TELEGRAM_BOT_TOKEN: "token", ANICCA_PROXY_BASE_URL: "https://life.example" }, now: () => NOW,
    botCall: async method => method === "getMe" ? { ok: true, result: { username: "LifeBot" } } : { ok: true, result: {} },
    mtprotoSend: async () => { sends += 1; return { id: 41, atMs: NOW }; },
    mtprotoRead: async () => [], sleep: async () => {}, maxReplyPolls: 2,
  });
  await assert.rejects(collect, /telegram_reply_timeout/);
  assert.equal(sends, 1);
});

test("telegram adapter fails closed when MTProto rejects the one send", async () => {
  let sends = 0;
  const collect = createTelegramCollector({
    env: { LM_TELEGRAM_BOT_TOKEN: "token", ANICCA_PROXY_BASE_URL: "https://life.example" },
    botCall: async () => ({ ok: true, result: { username: "LifeBot" } }),
    mtprotoSend: async () => { sends += 1; throw new Error("raw provider secret"); },
  });
  await assert.rejects(collect, error => !String(error).includes("raw provider secret"));
  assert.equal(sends, 1);
});

test("email adapter sends exactly once and accepts only exact nonce receipt", async () => {
  let sends = 0;
  const collect = createEmailCollector({
    env: { GOG_ACCOUNT: "controlled@aniccaai.com", LM_CONTROLLED_EMAIL_ALLOWLIST: "controlled@aniccaai.com", RESEND_API_KEY: "key" },
    now: () => NOW, randomNonce: () => "fixednonce",
    send: async () => { sends += 1; return { sent: true, id: "provider-id" }; },
    findReceipt: async ({ nonce }) => ({ id: nonce === "fixednonce" ? "gmail-id" : "", matchedNonce: nonce, receivedAtMs: NOW }), sleep: async () => {},
  });
  const result = await collect(); assert.equal(sends, 1); assert.equal(result.inboxReceived, true);
});

test("email adapter derives recipient from GOG_ACCOUNT and rejects outside fixed allowlist before send", async () => {
  let sends = 0;
  const collect = createEmailCollector({
    env: { GOG_ACCOUNT: "outside@example.com", LM_CONTROLLED_EMAIL_ALLOWLIST: "controlled@aniccaai.com", RESEND_API_KEY: "key" },
    send: async () => { sends += 1; return { sent: true, id: "provider-id" }; },
  });
  await assert.rejects(collect, /email_recipient_not_controlled/);
  assert.equal(sends, 0);
});

test("email adapter rejects send rejection, nonce mismatch, timeout, and stale receipt without duplicate sends", async () => {
  const base = { GOG_ACCOUNT: "controlled@aniccaai.com", LM_CONTROLLED_EMAIL_ALLOWLIST: "controlled@aniccaai.com", RESEND_API_KEY: "key" };
  for (const scenario of ["send", "mismatch", "timeout", "stale"]) {
    let sends = 0;
    const collect = createEmailCollector({
      env: base, now: () => NOW, randomNonce: () => "a".repeat(32), maxPolls: 2, sleep: async () => {},
      send: async () => { sends += 1; return scenario === "send" ? { sent: false } : { sent: true, id: "provider-id" }; },
      findReceipt: async ({ nonce }) => scenario === "timeout" ? null : {
        id: "gmail-id", matchedNonce: scenario === "mismatch" ? `${nonce}x` : nonce,
        receivedAtMs: scenario === "stale" ? NOW - 900001 : NOW,
      },
    });
    await assert.rejects(collect);
    assert.equal(sends, 1, scenario);
  }
});

test("collector failures never contain raw provider errors or PII", async () => {
  const collect = createEmailCollector({
    env: { GOG_ACCOUNT: "person@example.com", LM_CONTROLLED_EMAIL_ALLOWLIST: "person@example.com", RESEND_API_KEY: "key" },
    send: async () => ({ sent: false, error: "raw secret person@example.com" }),
  });
  await assert.rejects(collect, error => !String(error).includes("person@example.com") && !String(error).includes("raw secret"));
});

test("test-support Telegram mirror requires fake exec before any sidecar invocation", async () => {
  const invocations = []; let botCalls = 0;
  const execFileImpl = async (file, args, options) => {
    invocations.push({ file, args, options });
    if (args[1] === "send") return { stdout: JSON.stringify({ ok: true, sent_id: 41 }) };
    return { stdout: JSON.stringify({ ok: true, messages: [{ id: 42, date: new Date(NOW).toISOString(), out: false,
      text: "https://opaque.example/panel?t=must-not-leave-adapter" }] }) };
  };
  const fetchImpl = async url => {
    botCalls += 1;
    return { ok: true, json: async () => url.endsWith("/getMe")
      ? { ok: true, result: { username: "LifeBot" } }
      : { ok: true, result: { url: "https://life.example/telegram",
        allowed_updates: ["message", "edited_message", "callback_query"], pending_update_count: 0 } } };
  };
  const collect = createTelegramCollector({
    env: { LM_TELEGRAM_BOT_TOKEN: "token", ANICCA_PROXY_BASE_URL: "https://life.example" },
    fetchImpl, execFileImpl, now: () => NOW, sleep: async () => {},
  });
  const result = await collect();
  assert.equal(botCalls, 2);
  assert.deepEqual(invocations.map(({ file, args }) => ({ file, args })), [
    { file: "/Users/anicca/.cache/telegram-user-venv/bin/python", args: ["/Users/anicca/anicca/skills/tools/telegram-user/tg_user.py", "send", "@LifeBot", invocations[0].args[3]] },
    { file: "/Users/anicca/.cache/telegram-user-venv/bin/python", args: ["/Users/anicca/anicca/skills/tools/telegram-user/tg_user.py", "read", "@LifeBot", "20"] },
  ]);
  assert.match(invocations[0].args[3], /^\/panel core8d_[a-f0-9]{24}$/);
  assert.equal(invocations.every(({ options }) => options.shell !== true), true);
  assert.doesNotMatch(JSON.stringify(result), /opaque|panel\?t=/);
});

test("test-support email mirror uses acceptance and exact receipt without caller success booleans", async () => {
  const nonce = "c".repeat(32); let receives = 0;
  const collect = createEmailCollector({
    env: { GOG_ACCOUNT: "controlled@aniccaai.com", LM_CONTROLLED_EMAIL_ALLOWLIST: "controlled@aniccaai.com", RESEND_API_KEY: "key" },
    now: () => NOW, randomNonce: () => nonce,
    fetchImpl: async () => ({ ok: true, status: 200, json: async () => ({ id: "provider-id" }) }),
    mailFactory: () => ({ findReceipt: async () => { receives += 1; return { id: "gmail-id", matchedNonce: nonce, receivedAtMs: NOW }; } }),
  });
  const result = await collect();
  assert.equal(receives, 1);
  assert.equal(result.providerAccepted, true);
  assert.equal(result.inboxReceived, true);
});
