"use strict";
// FIN-b (spec row 13b): the payout-destination closed question.
//
// Before this module the discovery announcement offered a "登録する" button that led nowhere —
// handleDiscoveryCallback acknowledged the tap and returned, so the one question the FINANCIAL organ
// needs answered was never asked and lm_users.payout_destination stayed null forever. These tests pin
// the whole round trip: the tap opens the §9.11 closed question, the tapped answer is written to
// payout_destination and read back before we call it saved, and once it is answered the question is
// never asked again.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const {
  PAYOUT_ANSWERS,
  payoutQuestionMessage,
  payoutDestinationRecord,
  isPayoutDestinationUsable,
  readPayoutDestination,
  savePayoutAnswer,
  askPayoutQuestion,
  handlePayoutCallback,
} = require("./payout-question.js");
const { FINANCIAL_STRINGS } = require("./i18n.js");
const { handleDiscoveryCallback } = require("./feature-discovery.js");
const { routeCallbackData } = require("./telegram.js");

const NOW = Date.parse("2026-07-25T09:00:00.000Z");
const SUPA = { supaUrl: "https://fixture.supabase.co", supaKey: "fixture-key" };

function jsonResponse(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test("FIN-b: the question is the §9.11 FINANCIAL copy verbatim with exactly three closed choices", () => {
  const message = payoutQuestionMessage();
  assert.equal(message.text, FINANCIAL_STRINGS.ja.payoutQuestion.text);

  const spec = fs.readFileSync(path.join(__dirname,
    "../../../docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md"), "utf8");
  const copy = FINANCIAL_STRINGS.ja.payoutQuestion.text.replace(/\n/g, "\\n");
  assert.ok(spec.includes(`「${copy}」`), "payout question copy must stay verbatim from spec §9.11 FINANCIAL");

  const rows = message.extra.reply_markup.inline_keyboard;
  const buttons = rows.flat();
  assert.equal(buttons.length, 3, "a closed question offers two or three choices, never free input");
  assert.deepEqual(buttons.map((b) => b.text), [
    FINANCIAL_STRINGS.ja.payoutQuestion.bankButton,
    FINANCIAL_STRINGS.ja.payoutQuestion.walletButton,
    FINANCIAL_STRINGS.ja.payoutQuestion.laterButton,
  ]);
  assert.deepEqual(buttons.map((b) => b.callback_data), [
    "payout:answer:bank", "payout:answer:wallet", "payout:answer:later",
  ]);
  assert.deepEqual(PAYOUT_ANSWERS, ["bank", "wallet", "later"]);
  // Every button label the question renders is present in the copy itself — the message and the
  // keyboard cannot drift apart.
  for (const button of buttons) {
    assert.ok(FINANCIAL_STRINGS.ja.payoutQuestion.text.includes(button.text), `${button.text} must appear in the copy`);
  }
});

test("FIN-b: the persisted answer is a rail choice and is never mistaken for a transfer-ready destination", () => {
  const record = payoutDestinationRecord("wallet", NOW);
  assert.equal(record.type, "wallet");
  assert.equal(record.status, "awaiting_details");
  assert.equal(record.answered_at, new Date(NOW).toISOString());
  // 13d must not be able to read this row as "we know where to send money".
  assert.equal(isPayoutDestinationUsable(record), false);
  assert.equal(isPayoutDestinationUsable(null), false);
  assert.equal(isPayoutDestinationUsable({ type: "wallet", status: "ready" }), false, "ready still needs a destination");
  assert.equal(isPayoutDestinationUsable({ type: "wallet", status: "ready", destination: "0xabc" }), true);
  assert.throws(() => payoutDestinationRecord("later", NOW), /rail/);
  assert.throws(() => payoutDestinationRecord("paypal", NOW), /rail/);
});

test("FIN-b: pressing register on the discovery announcement opens the closed question", async () => {
  const sent = [];
  const outcome = await handleDiscoveryCallback("discovery:register:payout", {
    token: "t", chatId: "7", uid: "u1", nowMs: NOW,
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
    readPayoutDestination: async () => ({ destination: null }),
  });
  assert.equal(outcome.handled, true);
  assert.equal(outcome.gate, "payout");
  assert.equal(outcome.asked, true, "the register button must no longer be a dead end");
  assert.equal(sent.length, 1);
  assert.equal(sent[0][1], "7");
  assert.equal(sent[0][2], FINANCIAL_STRINGS.ja.payoutQuestion.text);
  assert.deepEqual(sent[0][3], payoutQuestionMessage().extra);
});

test("FIN-b: an already-registered destination is never asked again — but the tap gets a visible reply (CB-1)", async () => {
  const sent = [];
  const asked = await askPayoutQuestion({
    token: "t", chatId: "7", uid: "u1",
    readPayoutDestination: async () => ({ destination: { type: "bank", status: "awaiting_details" } }),
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
  });
  assert.deepEqual(asked, { asked: false, reason: "already_answered" });
  // §10.0-15 ③: the second tap must not be silent. The reply is the alreadyRegistered copy — never
  // the question itself, which stays asked-once-ever.
  assert.equal(sent.length, 1);
  assert.equal(sent[0][2], "送金先は登録済みです（銀行口座）。変更したい時は「送金先を変更」と送ってください。");
  assert.notEqual(sent[0][2], FINANCIAL_STRINGS.ja.payoutQuestion.text);

  const discoverySent = [];
  const viaDiscovery = await handleDiscoveryCallback("discovery:register:payout", {
    token: "t", chatId: "7", uid: "u1",
    readPayoutDestination: async () => ({ destination: { type: "wallet", status: "awaiting_details" } }),
    sendMessage: async (...args) => { discoverySent.push(args); return { ok: true }; },
  });
  assert.equal(viaDiscovery.handled, true);
  assert.equal(viaDiscovery.asked, false);
  assert.equal(viaDiscovery.reason, "already_answered");
  assert.equal(discoverySent.length, 1);
  assert.equal(discoverySent[0][2], "送金先は登録済みです（wallet）。変更したい時は「送金先を変更」と送ってください。");
});

test("FIN-b: an unreadable destination neither asks nor claims the question was answered", async () => {
  const asked = await askPayoutQuestion({
    token: "t", chatId: "7", uid: "u1",
    readPayoutDestination: async () => null,
    sendMessage: async () => { throw new Error("we must not ask on a guess"); },
  });
  assert.deepEqual(asked, { asked: false, reason: "lookup_failed" });

  const unreachable = await askPayoutQuestion({
    token: "t", chatId: "", uid: "u1",
    readPayoutDestination: async () => { throw new Error("no lookup without a chat"); },
    sendMessage: async () => { throw new Error("no send without a chat"); },
  });
  assert.deepEqual(unreachable, { asked: false, reason: "unreachable" });
});

test("FIN-b: a rejected Telegram send is reported as not asked", async () => {
  const asked = await askPayoutQuestion({
    token: "t", chatId: "7", uid: "u1",
    readPayoutDestination: async () => ({ destination: null }),
    sendMessage: async () => ({ ok: false, description: "blocked" }),
  });
  assert.deepEqual(asked, { asked: false, reason: "telegram_failed" });
});

test("FIN-b: reading the destination fails closed instead of reporting an empty answer", async () => {
  assert.equal(await readPayoutDestination("u1", { ...SUPA, fetchImpl: async () => jsonResponse([], 500) }), null);
  assert.equal(await readPayoutDestination("u1", { ...SUPA, fetchImpl: async () => { throw new Error("network"); } }), null);
  assert.equal(await readPayoutDestination("u1", { ...SUPA, fetchImpl: async () => jsonResponse({ message: "boom" }) }), null);
  assert.equal(await readPayoutDestination("u1", {}), null, "an unconfigured database is unknown, not empty");
  assert.deepEqual(
    await readPayoutDestination("u1", { ...SUPA, fetchImpl: async () => jsonResponse([]) }),
    { destination: null },
    "a real row-less answer is a known 'not answered yet'",
  );
  assert.deepEqual(
    await readPayoutDestination("u1", { ...SUPA, fetchImpl: async () => jsonResponse([{ uid: "u1", payout_destination: { type: "bank" } }]) }),
    { destination: { type: "bank" } },
  );
});

test("FIN-b: saving claims the still-empty column and verifies the written value before reporting success", async () => {
  const requests = [];
  const saved = await savePayoutAnswer("u1", "wallet", NOW, {
    ...SUPA,
    fetchImpl: async (url, init) => {
      requests.push({ url: String(url), init });
      return jsonResponse([{ uid: "u1", payout_destination: payoutDestinationRecord("wallet", NOW) }]);
    },
  });
  assert.deepEqual(saved, payoutDestinationRecord("wallet", NOW));
  assert.equal(requests.length, 1);
  const [request] = requests;
  assert.equal(request.init.method, "PATCH");
  assert.match(request.url, /\/rest\/v1\/lm_users\?/);
  assert.match(request.url, /uid=eq\.u1/, "the write must be scoped to one tenant");
  assert.match(request.url, /payout_destination=is\.null/, "the write is a compare-and-set, so it can never clobber");
  assert.match(String(request.init.headers.Prefer), /return=representation/, "we must read back what we wrote");
  assert.deepEqual(JSON.parse(request.init.body), { payout_destination: payoutDestinationRecord("wallet", NOW) });
});

test("FIN-b: every shape of a failed persist reports failure rather than success", async () => {
  const attempts = [
    ["http error", async () => jsonResponse([], 500)],
    ["network error", async () => { throw new Error("network"); }],
    ["no row claimed", async () => jsonResponse([])],
    ["unparseable body", async () => jsonResponse({ message: "boom" })],
    ["row without the value", async () => jsonResponse([{ uid: "u1", payout_destination: null }])],
    ["row with a different value", async () => jsonResponse([{ uid: "u1", payout_destination: { type: "bank", status: "awaiting_details" } }])],
  ];
  for (const [label, fetchImpl] of attempts) {
    assert.equal(await savePayoutAnswer("u1", "wallet", NOW, { ...SUPA, fetchImpl }), null, `${label} must not report success`);
  }
  assert.equal(await savePayoutAnswer("u1", "wallet", NOW, {}), null, "an unconfigured database cannot persist");
  assert.equal(await savePayoutAnswer("", "wallet", NOW, SUPA), null);
  assert.equal(await savePayoutAnswer("u1", "later", NOW, SUPA), null, "later is not a destination");
});

test("FIN-b: answering the question persists the chosen rail", async () => {
  const writes = [];
  const outcome = await handlePayoutCallback("payout:answer:wallet", {
    uid: "u1", chatId: "7", actorId: "7", nowMs: NOW,
    savePayoutAnswer: async (...args) => { writes.push(args); return payoutDestinationRecord("wallet", NOW); },
  });
  assert.deepEqual(outcome, {
    handled: true, ok: true, answer: "wallet", destination: payoutDestinationRecord("wallet", NOW),
  });
  assert.deepEqual(writes, [["u1", "wallet", NOW]]);
});

test("FIN-b: a failed persist never reports the destination as registered", async () => {
  const outcome = await handlePayoutCallback("payout:answer:bank", {
    uid: "u1", chatId: "7", actorId: "7", nowMs: NOW,
    savePayoutAnswer: async () => null,
  });
  assert.deepEqual(outcome, { handled: true, ok: false, answer: "bank", reason: "persist_failed" });
});

test("FIN-b: あとで leaves the column untouched so the gate stays honestly locked", async () => {
  const outcome = await handlePayoutCallback("payout:answer:later", {
    uid: "u1", chatId: "7", actorId: "7", nowMs: NOW,
    savePayoutAnswer: async () => { throw new Error("later must never write a destination"); },
  });
  assert.deepEqual(outcome, { handled: true, ok: true, answer: "later", persisted: false });
});

test("FIN-b: a callback from another chat or an unlinked user writes nothing", async () => {
  const explode = async () => { throw new Error("an out-of-scope callback must never write"); };
  assert.deepEqual(
    await handlePayoutCallback("payout:answer:wallet", { uid: "u1", chatId: "7", actorId: "9", savePayoutAnswer: explode }),
    { handled: true, ok: false, answer: "wallet", reason: "scope_mismatch" },
  );
  assert.deepEqual(
    await handlePayoutCallback("payout:answer:wallet", { uid: null, chatId: "7", actorId: "7", savePayoutAnswer: explode }),
    { handled: true, ok: false, answer: "wallet", reason: "scope_mismatch" },
  );
  assert.deepEqual(await handlePayoutCallback("payout:answer:paypal", {}), { ignored: true });
  assert.deepEqual(await handlePayoutCallback("payout:register", {}), { ignored: true });
  assert.deepEqual(await handlePayoutCallback("", {}), { ignored: true });
});

test("FIN-b: the payout callback reaches the shared Telegram router", async () => {
  const seen = [];
  const handlers = { payout: async (data) => { seen.push(data); return { handled: true }; } };
  assert.deepEqual(await routeCallbackData("payout:answer:bank", handlers), { handled: true });
  assert.deepEqual(seen, ["payout:answer:bank"]);
});

test("FIN-b: ask, answer, ask again — the whole round trip asks exactly once", async () => {
  let stored = null;
  const sent = [];
  const deps = {
    token: "t", chatId: "7", uid: "u1", actorId: "7", nowMs: NOW,
    readPayoutDestination: async () => ({ destination: stored }),
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
    savePayoutAnswer: async (uid, rail, at) => { stored = payoutDestinationRecord(rail, at); return stored; },
  };

  assert.deepEqual(await askPayoutQuestion(deps), { asked: true });
  assert.equal(sent.length, 1);

  const answered = await handlePayoutCallback("payout:answer:bank", deps);
  assert.equal(answered.ok, true);
  assert.deepEqual(stored, payoutDestinationRecord("bank", NOW));

  assert.deepEqual(await askPayoutQuestion(deps), { asked: false, reason: "already_answered" });
  // CB-1: the re-ask is answered visibly ("registered already"), but the QUESTION itself went out
  // exactly once — that is the invariant this round trip pins.
  assert.equal(sent.length, 2);
  assert.equal(sent.filter((args) => args[2] === FINANCIAL_STRINGS.ja.payoutQuestion.text).length, 1,
    "the payout question is asked once, ever");
  assert.equal(sent[1][2], "送金先は登録済みです（銀行口座）。変更したい時は「送金先を変更」と送ってください。");
});

// ---- CB-1 (spec §10.0-15): a payout tap must leave a durable, visible response ----

test("CB-1: a persisted answer edits the original question with the chosen label", async () => {
  const edits = [];
  const outcome = await handlePayoutCallback("payout:answer:bank", {
    uid: "u1", chatId: "7", actorId: "7", nowMs: NOW,
    token: "tok", messageId: "42", messageText: FINANCIAL_STRINGS.ja.payoutQuestion.text,
    savePayoutAnswer: async () => payoutDestinationRecord("bank", NOW),
    reflectAnswer: async (args) => { edits.push(args); return { ok: true }; },
  });
  assert.equal(outcome.ok, true);
  assert.equal(edits.length, 1);
  assert.equal(edits[0].messageId, "42");
  assert.equal(edits[0].messageText, FINANCIAL_STRINGS.ja.payoutQuestion.text);
  assert.equal(edits[0].label, FINANCIAL_STRINGS.ja.payoutQuestion.bankButton);
});

test("CB-1: あとで is reflected on the message (→ あとで, keyboard gone) and still persists nothing", async () => {
  const edits = [];
  const outcome = await handlePayoutCallback("payout:answer:later", {
    uid: "u1", chatId: "7", actorId: "7", nowMs: NOW,
    token: "tok", messageId: "42", messageText: FINANCIAL_STRINGS.ja.payoutQuestion.text,
    savePayoutAnswer: async () => { throw new Error("later must never write a destination"); },
    reflectAnswer: async (args) => { edits.push(args); return { ok: true }; },
  });
  assert.deepEqual(outcome, { handled: true, ok: true, answer: "later", persisted: false });
  assert.equal(edits.length, 1);
  assert.equal(edits[0].label, FINANCIAL_STRINGS.ja.payoutQuestion.laterButton);
});

test("CB-1: a re-tap (column already claimed) gets the visible already-registered reply", async () => {
  const sent = [], edits = [];
  const outcome = await handlePayoutCallback("payout:answer:wallet", {
    uid: "u1", chatId: "7", actorId: "7", nowMs: NOW,
    token: "tok", messageId: "42", messageText: FINANCIAL_STRINGS.ja.payoutQuestion.text,
    savePayoutAnswer: async () => null, // compare-and-set claimed no row: someone answered already
    readPayoutDestination: async () => ({ destination: { type: "bank", status: "awaiting_details" } }),
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
    reflectAnswer: async (args) => { edits.push(args); return { ok: true }; },
  });
  assert.equal(outcome.ok, false);
  assert.equal(outcome.reason, "already_answered");
  assert.equal(sent.length, 1);
  assert.equal(sent[0][2], "送金先は登録済みです（銀行口座）。変更したい時は「送金先を変更」と送ってください。");
  // The stale keyboard the user just tapped must die too — but with NO label appended, because the
  // rail on file may not be the rail of this tap.
  assert.equal(edits.length, 1);
  assert.equal(edits[0].messageText, "", "the already path strips the keyboard without rewriting the text");
});

test("CB-1: a genuinely failed persist stays persist_failed — no already-registered lie, no edit", async () => {
  const explode = async () => { throw new Error("a failed persist must not fake visibility"); };
  const outcome = await handlePayoutCallback("payout:answer:bank", {
    uid: "u1", chatId: "7", actorId: "7", nowMs: NOW,
    token: "tok", messageId: "42", messageText: FINANCIAL_STRINGS.ja.payoutQuestion.text,
    savePayoutAnswer: async () => null,
    readPayoutDestination: async () => null, // we cannot see the column — unknown, not "already"
    sendMessage: explode, reflectAnswer: explode,
  });
  assert.deepEqual(outcome, { handled: true, ok: false, answer: "bank", reason: "persist_failed" });
});
