"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { renderCfoTelegram } = require("./cfo-telegram.js");
const { deliverCfoTelegram } = require("./cfo-telegram-send.js");

const CLAIM = "70000000-0000-4000-8000-000000000001";
const SNAPSHOT_REF = "71000000-0000-4000-8000-000000000001";
const TOKEN = "telegram-token-secret";
const CHAT_ID = "telegram-chat-secret";
const UID = "owner-uid-secret";
const RPC_OPTIONS = { supaUrl: "https://db.example", supaKey: "service-role-secret", fetchImpl: async () => ({}) };

function snapshot(overrides = {}) {
  return {
    schemaVersion: 1,
    reportingDate: "2026-08-10",
    revision: 1,
    state: "complete",
    currency: "JPY",
    totals: { assetsMinor: 420000, liabilitiesMinor: 30000, netWorthMinor: 390000, changeMinor: 1200 },
    sources: [{
      sourceId: "moneytree_mufg", label: "三菱UFJ銀行", status: "fresh",
      asOf: "2026-08-10T06:02:00+09:00", amountMinor: 420000, verificationStatus: "provider_reported",
    }],
    excluded: [], repair: null, action: null, ...overrides,
  };
}

function input(overrides = {}) {
  return { uid: UID, chatId: CHAT_ID, telegramToken: TOKEN, snapshotPublicRef: SNAPSHOT_REF, snapshot: snapshot(), ...overrides };
}

function claim(decision = "send") {
  return {
    public_ref: CLAIM, decision, reporting_date: "2026-08-10", revision: 1,
    created_at: "2026-08-10T06:03:00.000Z",
  };
}

test("send claim renders Japanese summary, sends once with buttons, and records the exact message ID", async () => {
  const calls = [];
  const receipt = { claimPublicRef: CLAIM, messageId: 42 };
  const result = await deliverCfoTelegram(input(), {
    render: (args) => { calls.push(["render", args]); return renderCfoTelegram(args); },
    ...RPC_OPTIONS,
    claim: async (args, rpcOptions) => { calls.push(["claim", args, rpcOptions]); return claim(); },
    send: async (...args) => { calls.push(["send", args]); return { ok: true, result: { message_id: 42 } }; },
    record: async (args, rpcOptions) => { calls.push(["record", args, rpcOptions]); return receipt; },
  });

  assert.deepEqual(result, { status: "sent", messageId: 42 });
  assert.equal(Object.isFrozen(result), true);
  assert.deepEqual(calls.map(([kind]) => kind), ["render", "claim", "send", "record"]);
  assert.deepEqual(calls[1][1], {
    uid: UID, snapshotPublicRef: SNAPSHOT_REF, reportKind: "assets_liabilities",
    reportingDate: "2026-08-10", revision: 1,
  });
  assert.deepEqual(calls[1][2], RPC_OPTIONS);
  assert.equal(calls[2][1][0], TOKEN);
  assert.equal(calls[2][1][1], CHAT_ID);
  assert.match(calls[2][1][2], /今日のお金/);
  assert.ok(calls[2][1][3].reply_markup.inline_keyboard.length > 0);
  assert.deepEqual(calls[3][1], { claimPublicRef: CLAIM, messageId: 42 });
  assert.deepEqual(calls[3][2], RPC_OPTIONS);
});

test("sent and reconcile claims never send Telegram or write a receipt", async () => {
  for (const decision of ["sent", "reconcile"]) {
    const calls = [];
    const result = await deliverCfoTelegram(input(), {
      claim: async () => { calls.push("claim"); return claim(decision); },
      send: async () => { calls.push("send"); },
      record: async () => { calls.push("record"); },
    });
    assert.deepEqual(result, { status: decision === "sent" ? "already_sent" : "reconcile", messageId: null });
    assert.equal(Object.isFrozen(result), true);
    assert.deepEqual(calls, ["claim"]);
  }
});

test("global fetch path passes exact RPC options without an undefined fetchImpl", async () => {
  const rpcCalls = [];
  const result = await deliverCfoTelegram(input(), {
    supaUrl: "https://db.example", supaKey: "service-role-secret",
    claim: async (_claimInput, rpcOptions) => { rpcCalls.push(["claim", rpcOptions]); return claim(); },
    send: async () => ({ ok: true, result: { message_id: 42 } }),
    record: async (_recordInput, rpcOptions) => { rpcCalls.push(["record", rpcOptions]); },
  });
  assert.deepEqual(result, { status: "sent", messageId: 42 });
  assert.deepEqual(rpcCalls.map(([kind]) => kind), ["claim", "record"]);
  for (const [, rpcOptions] of rpcCalls) {
    assert.deepEqual(rpcOptions, { supaUrl: "https://db.example", supaKey: "service-role-secret" });
    assert.equal(Object.prototype.hasOwnProperty.call(rpcOptions, "fetchImpl"), false);
  }
});

test("invalid provider response writes no receipt and exposes no sensitive values", async () => {
  const raw = { ok: false, result: { message_id: "bad", token: TOKEN, chat_id: CHAT_ID, amount: 420000 } };
  let records = 0;
  await assert.rejects(
    deliverCfoTelegram(input(), {
      claim: async () => claim(),
      send: async () => raw,
      record: async () => { records += 1; },
    }),
    (error) => {
      assert.equal(error.message, "cfo_telegram_send_failed:provider_rejected");
      for (const secret of [TOKEN, CHAT_ID, UID, SNAPSHOT_REF, "420000", "bad"]) assert.doesNotMatch(error.message, new RegExp(secret));
      return true;
    },
  );
  assert.equal(records, 0);
});

test("invalid snapshot is rendered before the claim and cannot strand a delivery", async () => {
  let claims = 0;
  await assert.rejects(
    deliverCfoTelegram(input({ snapshot: snapshot({ totals: { assetsMinor: "420000", liabilitiesMinor: 30000, netWorthMinor: 390000, changeMinor: 1200 } }) }), {
      claim: async () => { claims += 1; return claim(); },
    }),
    /^Error: cfo_telegram_invalid:invalid_amount$/,
  );
  assert.equal(claims, 0);
});
