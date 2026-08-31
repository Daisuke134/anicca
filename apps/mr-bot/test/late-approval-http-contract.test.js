"use strict";

// DAILY #5 Task 4: the callback is the only path that may cross the mail boundary.  These are
// intentionally transport-shaped contract tests even though the state store is in-memory: the
// production HTTP route supplies the same chat ownership, signed callback, and store calls.
const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");

const {
  createLateDraft,
  createInMemoryLateApprovalStore,
  decideLateDraft,
  claimApprovedDelivery,
  recordLateDelivery,
  recordLateApprovalCard,
  createLateApprovalCallbackData,
  handleLateApprovalCallback,
} = require("../lib/late-approval.js");
const { lateApprovalCardRequest } = require("../lib/late-notice.js");

const NOW = Date.parse("2026-08-08T06:00:00.000Z");
const SECRET = "fixture-late-approval-secret";

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body, text: async () => JSON.stringify(body) };
}

function draftInput(status = "resolved") {
  return {
    uid: "uid-1",
    eventKey: `calendar:event-${status}`,
    recipientStatus: status,
    recipients: status === "resolved" ? [{
      display_name: "Meeting partner",
      email: "partner@example.invalid",
      source: "calendar",
      evidence_refs: ["calendar:event:1:attendee:0"],
      confidence: 1,
      event_role: "attendee",
    }] : [],
    evidenceSnapshot: { refs: status === "resolved" ? ["calendar:event:1:attendee:0"] : [], status },
    bodySnapshot: "Hi — Dais is running 15 minutes late to the meeting.",
    etaEvidence: { basis: "route_eta_from_live_location", routeMinutes: 43, etaMinutes: 15 },
    nowMs: NOW,
  };
}

function callback(action, draftId, overrides = {}) {
  return createLateApprovalCallbackData({
    action,
    draftId,
    secret: SECRET,
    expiresAtMs: NOW + 10 * 60_000,
    ...overrides,
  });
}

function baseOptions(store, overrides = {}) {
  const calls = [];
  return {
    store,
    secret: SECRET,
    chatId: "100",
    actorId: "100",
    owner: { uid: "uid-1", telegram_chat_id: "100" },
    nowMs: NOW,
    callbackQueryId: "cb-1",
    messageId: "777",
    token: "telegram-token",
    sendLateNotice: async (_uid, _event, options) => {
      calls.push(["mail", options]);
      return { sent: true, id: "resend-message-1" };
    },
    editMessageText: async (_token, chatId, messageId, text, extra) => {
      calls.push(["edit", text, extra, chatId, messageId]);
      return { ok: true, result: { message_id: 77 } };
    },
    sendMessage: async () => { throw new Error("late receipt must edit the approval card"); },
    reflectAnswer: async (input) => {
      calls.push(["reflect", input.label]);
      return { ok: true };
    },
    calls,
    ...overrides,
  };
}

test("signed and owned Send decides, claims, mails, records the provider receipt, then posts one Telegram receipt", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft(draftInput(), store);
  const card = lateApprovalCardRequest({
    telegramToken: "telegram-token", nowMs: NOW, callbackSecret: SECRET,
    user: { uid: draft.uid, telegram_chat_id: "100" },
  }, { id: draft.eventKey, summary: "the meeting" }, draft);
  assert.match(card.text, /Meeting partner <partner@example\.invalid>/);
  assert.match(card.text, /source: calendar/);
  assert.match(card.text, /evidence: calendar:event:1:attendee:0/);
  assert.match(card.text, /ETA.*route_eta_from_live_location/);
  assert.match(card.text, /Hi — Dais is running/);
  assert.equal(card.extra.reply_markup.inline_keyboard[0].length, 2);
  assert.ok(card.extra.reply_markup.inline_keyboard[0].every((button) => button.callback_data.startsWith("late:")));
  const opts = baseOptions(store);
  const result = await handleLateApprovalCallback(callback("send", draft.draftId), opts);

  assert.equal(result.handled, true);
  assert.equal(result.ok, true);
  assert.equal(result.sent, true);
  assert.equal(result.draft.status, "sent");
  assert.deepEqual(opts.calls.map((entry) => entry[0]), ["mail", "reflect", "edit"]);
  assert.equal(opts.calls[0][1].providerIdempotencyKey, draft.providerIdempotencyKey);
  assert.equal(opts.calls[0][1].bodySnapshot, draft.bodySnapshot);
  assert.match(opts.calls[2][1], /resend-message-1/);
  assert.match(opts.calls[2][1], /&lt;partner@example\.invalid&gt;/);

  // A replay observes the durable sent row and cannot call either external transport again.
  const replay = await handleLateApprovalCallback(callback("send", draft.draftId), {
    ...opts,
    callbackQueryId: "cb-replay",
  });
  assert.equal(replay.ok, true);
  assert.equal(replay.sent, false);
  assert.deepEqual(opts.calls.map((entry) => entry[0]), ["mail", "reflect", "edit"]);
});

test("concurrent copies of one signed callback produce one provider send and one Telegram receipt", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft({ ...draftInput(), eventKey: "calendar:event-concurrent-receipt" }, store);
  let mailCalls = 0;
  let telegramCalls = 0;
  let mailStarted;
  let resolveMailStarted;
  mailStarted = new Promise((resolve) => { resolveMailStarted = resolve; });
  const options = baseOptions(store, {
    sendLateNotice: async () => {
      mailCalls += 1;
      resolveMailStarted();
      if (mailCalls === 1) await new Promise((resolve) => setTimeout(resolve, 20));
      return { sent: true, id: "resend-concurrent-1" };
    },
    editMessageText: async () => {
      telegramCalls += 1;
      return { ok: true, result: { message_id: 700 + telegramCalls } };
    },
  });
  const data = callback("send", draft.draftId);
  const first = handleLateApprovalCallback(data, { ...options, callbackQueryId: "same-callback" });
  await mailStarted;
  const second = handleLateApprovalCallback(data, { ...options, callbackQueryId: "same-callback" });
  await Promise.all([first, second]);

  assert.equal(mailCalls, 1);
  assert.equal(telegramCalls, 1);
});

test("a concurrent callback that sees the old draft recovers a durable provider receipt into the Telegram outbox", async () => {
  const durableStore = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft({ ...draftInput(), eventKey: "calendar:event-stale-callback" }, durableStore);
  const decision = await decideLateDraft({
    uid: draft.uid, draftId: draft.draftId, decision: "send", idempotencyKey: "seed-decision", nowMs: NOW,
  }, durableStore);
  const claim = await claimApprovedDelivery({ draftId: draft.draftId, workerId: "seed-worker", nowMs: NOW }, durableStore);
  await recordLateDelivery({
    uid: draft.uid, draftId: draft.draftId, providerMessageId: "resend-stale-1",
    deliveredAt: new Date(NOW).toISOString(), claimToken: claim.claimToken, workerId: "seed-worker", nowMs: NOW,
  }, durableStore);

  // The callback read happened before the provider receipt committed; all subsequent operations
  // must still use the durable row and enqueue/send only the Telegram receipt.
  const staleSnapshot = {
    ...draft,
    status: "awaiting_decision",
    decision: decision.decision,
    idempotencyKey: decision.idempotencyKey,
  };
  const store = {
    ...durableStore,
    async getLateDraft() { return staleSnapshot; },
  };
  let mailCalls = 0;
  let telegramCalls = 0;
  const result = await handleLateApprovalCallback(callback("send", draft.draftId), baseOptions(store, {
    sendLateNotice: async () => { mailCalls += 1; throw new Error("provider must not resend"); },
    editMessageText: async () => {
      telegramCalls += 1;
      return { ok: true, result: { message_id: 702 } };
    },
  }));

  assert.equal(result.ok, true);
  assert.equal(result.sent, true);
  assert.equal(mailCalls, 0);
  assert.equal(telegramCalls, 1);
});

test("an accepted Telegram edit followed by a timeout retries the same approval card without duplicate email or visible receipt", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft({ ...draftInput(), eventKey: "calendar:event-edit-timeout" }, store);
  let mailCalls = 0;
  const editCalls = [];
  let editAttempts = 0;
  const options = baseOptions(store, {
    messageId: "777",
    sendLateNotice: async () => {
      mailCalls += 1;
      return { sent: true, id: "resend-edit-timeout-1" };
    },
    sendMessage: async () => { throw new Error("receipt must edit the approval card"); },
    editMessageText: async (_token, chatId, messageId, text) => {
      editAttempts += 1;
      editCalls.push({ chatId, messageId, text });
      if (editAttempts === 1) throw new Error("Telegram timed out after accepting the edit");
      return { ok: false, description: "Bad Request: message is not modified" };
    },
  });

  const data = callback("send", draft.draftId);
  const first = await handleLateApprovalCallback(data, { ...options, callbackQueryId: "edit-timeout-1" });
  const retry = await handleLateApprovalCallback(data, { ...options, callbackQueryId: "edit-timeout-2" });

  assert.equal(first.ok, false);
  assert.equal(retry.ok, true);
  assert.equal(mailCalls, 1);
  assert.equal(editCalls.length, 2);
  assert.deepEqual(editCalls.map((call) => [call.chatId, call.messageId]), [["100", "777"], ["100", "777"]]);
  assert.equal(new Set(editCalls.map((call) => call.messageId)).size, 1, "one visible Telegram message is edited");
  assert.equal((await store.getDraft(draft.draftId)).telegramReceiptMessageId, "777");
});

test("an accepted Telegram edit followed by a receipt-record failure retries the same approval card without resending email", async () => {
  const durableStore = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft({ ...draftInput(), eventKey: "calendar:event-edit-record-failure" }, durableStore);
  let mailCalls = 0;
  let editCalls = 0;
  let recordCalls = 0;
  const store = {
    ...durableStore,
    async recordLateTelegramReceipt(input) {
      recordCalls += 1;
      if (recordCalls === 1) throw new Error("receipt database write failed after Telegram accepted");
      return durableStore.recordLateTelegramReceipt(input);
    },
  };
  const options = baseOptions(store, {
    messageId: "778",
    sendLateNotice: async () => {
      mailCalls += 1;
      return { sent: true, id: "resend-edit-record-failure-1" };
    },
    sendMessage: async () => { throw new Error("receipt must edit the approval card"); },
    editMessageText: async (_token, _chatId, messageId) => {
      editCalls += 1;
      return editCalls === 1
        ? { ok: true, result: { message_id: Number(messageId) } }
        : { ok: false, description: "Bad Request: message is not modified" };
    },
  });

  const data = callback("send", draft.draftId);
  const first = await handleLateApprovalCallback(data, { ...options, callbackQueryId: "edit-record-failure-1" });
  const retry = await handleLateApprovalCallback(data, { ...options, callbackQueryId: "edit-record-failure-2" });

  assert.equal(first.ok, false);
  assert.equal(retry.ok, true);
  assert.equal(mailCalls, 1);
  assert.equal(editCalls, 2);
  assert.equal(recordCalls, 2);
  assert.equal((await durableStore.getDraft(draft.draftId)).telegramReceiptMessageId, "778");
});

test("a replayed callback message id cannot override the durable approval card target", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft({ ...draftInput(), eventKey: "calendar:event-durable-card-target" }, store);
  await recordLateApprovalCard({
    uid: draft.uid, draftId: draft.draftId, chatId: "100", telegramMessageId: "700", nowMs: NOW,
  }, store);
  const editCalls = [];
  const options = baseOptions(store, {
    // This is a replayed/stale callback value; the stored approval card is message 700.
    messageId: "777",
    editMessageText: async (_token, chatId, messageId) => {
      editCalls.push({ chatId, messageId });
      return { ok: true, result: { message_id: Number(messageId) } };
    },
  });

  const result = await handleLateApprovalCallback(callback("send", draft.draftId), options);

  assert.equal(result.ok, true);
  assert.deepEqual(editCalls, [{ chatId: "100", messageId: "700" }]);
  assert.equal((await store.getDraft(draft.draftId)).telegramReceiptMessageId, "700");
});

test("Telegram receipt failure retries the receipt without resending the provider email", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft({ ...draftInput(), eventKey: "calendar:event-receipt-retry" }, store);
  let mailCalls = 0;
  let telegramCalls = 0;
  const options = baseOptions(store, {
    sendLateNotice: async () => {
      mailCalls += 1;
      return { sent: true, id: "resend-retry-1" };
    },
    editMessageText: async () => {
      telegramCalls += 1;
      return telegramCalls === 1
        ? { ok: false, error: "telegram unavailable" }
        : { ok: true, result: { message_id: 701 } };
    },
  });
  const data = callback("send", draft.draftId);
  const first = await handleLateApprovalCallback(data, { ...options, callbackQueryId: "retry-1" });
  assert.equal(first.sent, true);
  assert.equal(first.ok, false);
  const retry = await handleLateApprovalCallback(data, { ...options, callbackQueryId: "retry-2" });

  assert.equal(retry.ok, true);
  assert.equal(mailCalls, 1);
  assert.equal(telegramCalls, 2);
});

test("callback ownership, signature, and expiry fail closed before any state mutation", async () => {
  const store = createInMemoryLateApprovalStore({ nowMs: NOW });
  const draft = await createLateDraft(draftInput(), store);
  const calls = [];
  const common = baseOptions(store, {
    sendLateNotice: async () => { calls.push("mail"); throw new Error("must not send"); },
    sendMessage: async () => { calls.push("telegram"); },
  });

  const stranger = await handleLateApprovalCallback(callback("send", draft.draftId), {
    ...common, actorId: "999",
  });
  assert.deepEqual(stranger, { handled: true, ok: false, reason: "scope_mismatch" });
  assert.equal((await store.getDraft(draft.draftId)).decision, null);

  const signed = callback("send", draft.draftId);
  const tamperChar = signed.endsWith("x") ? "y" : "x";
  const tampered = `${signed.slice(0, -1)}${tamperChar}`;
  const forged = await handleLateApprovalCallback(tampered, common);
  assert.equal(forged.reason, "invalid_callback");
  assert.equal((await store.getDraft(draft.draftId)).decision, null);

  const expired = await handleLateApprovalCallback(callback("send", draft.draftId, { expiresAtMs: NOW - 1 }), common);
  assert.deepEqual(expired, { handled: true, ok: false, reason: "expired" });
  assert.equal((await store.getDraft(draft.draftId)).decision, null);
  assert.deepEqual(calls, []);
});

test("Don't send is terminal and missing or ambiguous recipients never expose a send boundary", async () => {
  const noSendStore = createInMemoryLateApprovalStore({ nowMs: NOW });
  const noSendDraft = await createLateDraft(draftInput(), noSendStore);
  const noSendOptions = baseOptions(noSendStore, {
    sendLateNotice: async () => { throw new Error("do_not_send must never mail"); },
  });
  const declined = await handleLateApprovalCallback(callback("do_not_send", noSendDraft.draftId), noSendOptions);
  assert.equal(declined.ok, true);
  assert.equal(declined.sent, false);
  assert.equal((await noSendStore.getDraft(noSendDraft.draftId)).status, "do_not_send");
  assert.deepEqual(noSendOptions.calls.map((entry) => entry[0]), ["reflect"]);

  for (const status of ["recipient_missing", "recipient_ambiguous"]) {
    const store = createInMemoryLateApprovalStore({ nowMs: NOW });
    const draft = await createLateDraft(draftInput(status), store);
    let mailCalls = 0;
    const result = await handleLateApprovalCallback(callback("send", draft.draftId), baseOptions(store, {
      sendLateNotice: async () => { mailCalls += 1; throw new Error("recipient must not mail"); },
    }));
    assert.equal(result.ok, false);
    assert.equal(result.reason, status);
    assert.equal(mailCalls, 0);
    assert.equal((await store.getDraft(draft.draftId)).status, status);
  }
});

test("POST /telegram routes the signed late callback through the production server and sends once", { concurrency: false }, async () => {
  const envKeys = [
    "LM_TELEGRAM_BOT_TOKEN", "LM_TELEGRAM_WEBHOOK_SECRET", "LM_LATE_APPROVAL_CALLBACK_SECRET",
    "LM_UID_SECRET", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "RESEND_API_KEY", "LIFE_RUN_LOOPS",
  ];
  const previousEnv = Object.fromEntries(envKeys.map((key) => [key, process.env[key]]));
  Object.assign(process.env, {
    LM_TELEGRAM_BOT_TOKEN: "fixture-telegram-token",
    LM_TELEGRAM_WEBHOOK_SECRET: "fixture-webhook-secret",
    LM_LATE_APPROVAL_CALLBACK_SECRET: SECRET,
    LM_UID_SECRET: "fixture-uid-secret",
    SUPABASE_URL: "https://fixture.supabase.co",
    SUPABASE_SERVICE_ROLE_KEY: "fixture-service-role",
    RESEND_API_KEY: "fixture-resend-key",
    LIFE_RUN_LOOPS: "false",
  });

  const originalCreateServer = http.createServer;
  const originalFetch = global.fetch;
  const originalLog = console.log;
  let productionServer;
  const row = {
    draft_id: "draft-http-1",
    uid: "uid-1",
    event_key: "calendar:event-http-1",
    status: "awaiting_decision",
    recipient_status: "resolved",
    recipient_snapshot: [{ display_name: "Meeting partner", email: "partner@example.invalid", source: "calendar", evidence_refs: ["calendar:event-http-1:attendee:0"] }],
    evidence_snapshot: { refs: ["calendar:event-http-1:attendee:0"], source: "calendar" },
    body_snapshot: "Stored HTTP body — do not regenerate",
    eta_evidence_snapshot: { basis: "route_eta_from_live_location", routeMinutes: 43, etaMinutes: 15 },
    decision: null,
    provider_idempotency_key: "a".repeat(64),
    claim_token: null,
    claim_worker_id: null,
    provider_message_id: null,
    delivered_at: null,
    telegram_approval_chat_id: "100",
    telegram_approval_message_id: "777",
  };
  const calls = [];

  function jsonClone(value) {
    return JSON.parse(JSON.stringify(value));
  }
  global.fetch = async (input, init = {}) => {
    const url = new URL(String(input));
    const method = String(init.method || "GET").toUpperCase();
    if (url.hostname === "api.telegram.org") {
      const operation = url.pathname.split("/").pop();
      calls.push([`telegram:${operation}`, JSON.parse(init.body || "{}")]);
      return response(200, { ok: true, result: { message_id: 9001 } });
    }
    if (url.hostname === "api.resend.com") {
      calls.push(["resend", { headers: init.headers, body: JSON.parse(init.body || "{}") }]);
      return response(200, { id: "resend-http-1" });
    }
    if (url.pathname === "/rest/v1/lm_users" && method === "GET") {
      const chat = String(url.searchParams.get("telegram_chat_id") || "").replace(/^eq\./, "");
      return response(200, [chat === "200"
        ? { uid: "uid-other", telegram_chat_id: "200" }
        : { uid: "uid-1", telegram_chat_id: "100", name: "Dais", email: "dais@example.invalid" }]);
    }
    if (url.pathname.startsWith("/rest/v1/rpc/") && method === "POST") {
      const rpc = url.pathname.split("/").pop();
      const body = JSON.parse(init.body || "{}");
      calls.push([`rpc:${rpc}`, body]);
      if (rpc === "lm_get_late_draft") {
        return response(200, body.p_uid === row.uid && body.p_draft_id === row.draft_id ? jsonClone(row) : []);
      }
      if (rpc === "lm_decide_late_draft") {
        row.decision = body.p_decision;
        return response(200, jsonClone(row));
      }
      if (rpc === "lm_claim_late_delivery") {
        row.status = "send_claimed";
        row.claim_token = "claim-http-token-123456789012345678901234";
        row.claim_worker_id = body.p_worker_id;
        row.claim_acquired_at = new Date().toISOString();
        row.claim_expires_at = new Date(Date.now() + 120_000).toISOString();
        return response(200, { ...jsonClone(row), claimed: true });
      }
      if (rpc === "lm_record_late_delivery") {
        row.status = "sent";
        row.provider_message_id = body.p_provider_message_id;
        row.delivered_at = body.p_delivered_at;
        return response(200, jsonClone(row));
      }
      if (rpc === "lm_record_late_approval_card") {
        row.telegram_approval_chat_id = body.p_chat_id;
        row.telegram_approval_message_id = body.p_telegram_message_id;
        return response(200, jsonClone(row));
      }
      if (rpc === "lm_enqueue_late_telegram_receipt") {
        row.telegram_receipt_status = row.telegram_receipt_status || "pending";
        row.telegram_receipt_chat_id = body.p_chat_id;
        row.telegram_receipt_text = body.p_receipt_text;
        return response(200, jsonClone(row));
      }
      if (rpc === "lm_claim_late_telegram_receipt") {
        if (row.telegram_receipt_status === "sent") {
          return response(200, { ...jsonClone(row), claimed: false, reason: "telegram_sent" });
        }
        row.telegram_receipt_status = "send_claimed";
        row.telegram_receipt_claim_token = "telegram-claim-http-token-123456789012345678901234";
        row.telegram_receipt_worker_id = body.p_worker_id;
        row.telegram_receipt_claimed_at = new Date().toISOString();
        row.telegram_receipt_claim_expires_at = new Date(Date.now() + 120_000).toISOString();
        row.telegram_receipt_attempts = Number(row.telegram_receipt_attempts || 0) + 1;
        return response(200, { ...jsonClone(row), claimed: true });
      }
      if (rpc === "lm_record_late_telegram_receipt") {
        row.telegram_receipt_status = "sent";
        row.telegram_receipt_message_id = body.p_telegram_message_id;
        return response(200, jsonClone(row));
      }
    }
    throw new Error(`unexpected ${method} ${url}`);
  };
  http.createServer = (handler) => {
    productionServer = originalCreateServer(handler);
    return productionServer;
  };
  console.log = () => {};

  try {
    const serverPath = require.resolve("../server.js");
    delete require.cache[serverPath];
    require(serverPath);
    assert.ok(productionServer, "the production HTTP server must be captured");
    await new Promise((resolve) => productionServer.listen(0, "127.0.0.1", resolve));
    const origin = `http://127.0.0.1:${productionServer.address().port}`;
    const post = (chatId, actorId, data, callbackId) => new Promise((resolve, reject) => {
      const body = JSON.stringify({ callback_query: {
        id: callbackId,
        from: { id: Number(actorId) },
        data,
        message: { message_id: 777, chat: { id: Number(chatId) }, text: row.body_snapshot },
      } });
      const request = http.request(`${origin}/telegram`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "content-length": Buffer.byteLength(body),
          "x-telegram-bot-api-secret-token": "fixture-webhook-secret",
        },
      }, (res) => { res.resume(); res.on("end", () => resolve(res.statusCode)); });
      request.on("error", reject);
      request.end(body);
    });

    const sendData = callback("send", row.draft_id, { nowMs: Date.now(), expiresAtMs: Date.now() + 600_000 });
    assert.equal(await post("100", "100", sendData, "cb-http-send"), 200);
    assert.equal(await post("100", "100", sendData, "cb-http-replay"), 200);
    assert.equal(calls.filter((entry) => entry[0] === "resend").length, 1);
    assert.equal(calls.filter((entry) => entry[0] === "rpc:lm_record_late_delivery").length, 1);
    assert.equal(calls.filter((entry) => entry[0] === "telegram:editMessageText").length, 2,
      "one edit acknowledges the callback and one edit replaces the card with the receipt");
    assert.equal(calls.find((entry) => entry[0] === "resend")[1].headers["Idempotency-Key"], "a".repeat(64));
    assert.equal(row.status, "sent");

    // The same signed button copied into another Telegram chat never reaches a decision/claim RPC.
    const stateRpc = (entry) => [
      "rpc:lm_decide_late_draft", "rpc:lm_claim_late_delivery", "rpc:lm_record_late_delivery",
    ].includes(entry[0]);
    const beforeRpc = calls.filter(stateRpc).length;
    assert.equal(await post("200", "200", sendData, "cb-http-cross-tenant"), 200);
    assert.equal(calls.filter(stateRpc).length, beforeRpc);
  } finally {
    console.log = originalLog;
    http.createServer = originalCreateServer;
    global.fetch = originalFetch;
    if (productionServer && productionServer.listening) {
      await new Promise((resolve) => productionServer.close(resolve));
    }
    for (const key of envKeys) {
      if (previousEnv[key] === undefined) delete process.env[key];
      else process.env[key] = previousEnv[key];
    }
  }
});
