"use strict";
// FIN-d (spec row 13d-a): the typed wallet-address intake.
//
// 13b stored WHICH rail the user chose ({type:"wallet", status:"awaiting_details"}) but a button can
// never carry the address itself (2026-07-26 Dais 裁定: button では渡せない情報がある). This module is
// the typed leg: the wallet tap asks for an address, the pending marker claims the next typed message
// from that chat, EIP-55 validates it with the same audited keccak the agent wallet uses, and only a
// write we can READ BACK flips payout_destination to usable. These tests pin:
//   - validation: EIP-55 vectors pass, a wrong-case address is rejected with a visible reason, an
//     all-lower/all-upper address (no checksum info) is accepted but stored lowercased
//   - the marker: asking writes {status:"awaiting_address"} via compare-and-set, never blind
//   - the confirm: CAS to usable + independent read-back before the ✅ message — a write we cannot
//     see in the database is a visible failure, never a false success (13b principle)
//   - scope: another actor's message, a bot command, or a chat with no pending intake changes nothing
//   - 「送金先を変更」 re-opens the question for an existing wallet destination

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  CHANGE_COMMAND,
  validateWalletAddress,
  shortWalletAddress,
  markAwaitingAddress,
  saveWalletAddress,
  askWalletAddress,
  handleTypedPayoutAddress,
} = require("./payout-address-intake.js");
const { isPayoutDestinationUsable, handlePayoutCallback } = require("./payout-question.js");
const { FINANCIAL_STRINGS } = require("./i18n.js");

const NOW = Date.parse("2026-07-26T09:00:00.000Z");
const SUPA = { supaUrl: "https://fixture.supabase.co", supaKey: "fixture-key" };
// Published EIP-55 test vectors — the checksum must come from the audited keccak, not a hand-rolled one.
const CHECKSUMMED = "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359";
const CHECKSUMMED_2 = "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed";

function jsonResponse(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

// ---- validation ----

test("FIN-d: EIP-55 checksummed addresses validate and are stored in their checksummed form", () => {
  for (const address of [CHECKSUMMED, CHECKSUMMED_2, "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB"]) {
    assert.deepEqual(validateWalletAddress(address), { ok: true, address });
  }
  assert.deepEqual(validateWalletAddress(`  ${CHECKSUMMED}  `), { ok: true, address: CHECKSUMMED },
    "surrounding whitespace is the user's messenger, not their mistake");
});

test("FIN-d: a mixed-case address with a WRONG checksum is rejected as checksum, not silently accepted", () => {
  // One flipped letter case = the exact typo EIP-55 exists to catch.
  const wrong = CHECKSUMMED.replace("fB69", "Fb69");
  assert.deepEqual(validateWalletAddress(wrong), { ok: false, reason: "checksum" });
});

test("FIN-d: an all-lowercase or all-uppercase address carries no checksum info — accepted, stored lowercased", () => {
  const lower = CHECKSUMMED.toLowerCase();
  assert.deepEqual(validateWalletAddress(lower), { ok: true, address: lower });
  assert.deepEqual(validateWalletAddress(`0x${CHECKSUMMED.slice(2).toUpperCase()}`), { ok: true, address: lower });
});

test("FIN-d: anything that is not 0x + 40 hex is rejected as format", () => {
  const malformed = [
    "", "hello", "0x", "0x123", `${CHECKSUMMED}ab`, CHECKSUMMED.slice(0, -1),
    CHECKSUMMED.slice(2), `0y${CHECKSUMMED.slice(2)}`, "0xZZ6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
    "please send to 0xfb6916095ca1df60bb79ce92ce3ea74c37c5d359 thanks",
  ];
  for (const value of malformed) {
    assert.deepEqual(validateWalletAddress(value), { ok: false, reason: "format" }, JSON.stringify(value));
  }
});

test("FIN-d: the confirmation shortens the address 0xABCD…WXYZ style", () => {
  assert.equal(shortWalletAddress(CHECKSUMMED), "0xfB69…d359");
});

test("FIN-d: a usable wallet destination (status usable + address) opens the 13d-b gate; awaiting_address does not", () => {
  assert.equal(isPayoutDestinationUsable({ type: "wallet", status: "usable", address: CHECKSUMMED }), true);
  assert.equal(isPayoutDestinationUsable({ type: "wallet", status: "awaiting_address", asked_at: "x" }), false);
  assert.equal(isPayoutDestinationUsable({ type: "wallet", status: "usable", address: "" }), false);
  assert.equal(isPayoutDestinationUsable({ type: "wallet", status: "usable" }), false);
});

// ---- the pending-intake marker ----

test("FIN-d: asking writes the awaiting_address marker by compare-and-set and verifies it before sending", async () => {
  const requests = [];
  const sent = [];
  const marker = { type: "wallet", status: "awaiting_address", asked_at: new Date(NOW).toISOString() };
  const outcome = await askWalletAddress("u1", "7", {
    ...SUPA, token: "t", nowMs: NOW,
    fetchImpl: async (url, init) => {
      requests.push({ url: String(url), init });
      return jsonResponse([{ uid: "u1", payout_destination: marker }]);
    },
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
  });
  assert.deepEqual(outcome, { asked: true });
  assert.equal(requests.length, 1);
  const [request] = requests;
  assert.equal(request.init.method, "PATCH");
  assert.match(request.url, /uid=eq\.u1/, "scoped to one tenant");
  assert.match(request.url, /payout_destination->>type=eq\.wallet/, "only a wallet rail may be asked for an address");
  assert.match(request.url, /payout_destination->>status=eq\.awaiting_details/, "compare-and-set from the rail answer");
  assert.match(String(request.init.headers.Prefer), /return=representation/, "read back what we wrote");
  assert.deepEqual(JSON.parse(request.init.body), { payout_destination: marker });
  // The question itself, verbatim from i18n (Dais-owned copy — quoted, never invented).
  assert.equal(sent.length, 1);
  assert.deepEqual(sent[0], ["t", "7", FINANCIAL_STRINGS.ja.payoutAddress.ask]);
});

test("FIN-d: a marker that did not land sends no question — asking without a durable marker loses the reply", async () => {
  const explode = async () => { throw new Error("no marker, no question"); };
  for (const [label, fetchImpl] of [
    ["no row claimed", async () => jsonResponse([])],
    ["http error", async () => jsonResponse([], 500)],
    ["network error", async () => { throw new Error("network"); }],
    ["row without the marker", async () => jsonResponse([{ uid: "u1", payout_destination: null }])],
    ["wrong status written", async () => jsonResponse([{ uid: "u1", payout_destination: { type: "wallet", status: "awaiting_details" } }])],
  ]) {
    const outcome = await askWalletAddress("u1", "7", { ...SUPA, token: "t", nowMs: NOW, fetchImpl, sendMessage: explode });
    assert.deepEqual(outcome, { asked: false, reason: "marker_failed" }, label);
  }
  assert.deepEqual(await askWalletAddress("u1", "7", { token: "t", sendMessage: explode }),
    { asked: false, reason: "marker_failed" }, "an unconfigured database cannot hold a marker");
  assert.deepEqual(await askWalletAddress("", "7", { ...SUPA, sendMessage: explode }), { asked: false, reason: "unreachable" });
  assert.deepEqual(await askWalletAddress("u1", "", { ...SUPA, sendMessage: explode }), { asked: false, reason: "unreachable" });
});

test("FIN-d: a rejected Telegram send is reported — the marker stands, the failure is not dressed as asked", async () => {
  const outcome = await askWalletAddress("u1", "7", {
    ...SUPA, token: "t", nowMs: NOW,
    markAwaitingAddress: async () => ({ type: "wallet", status: "awaiting_address" }),
    sendMessage: async () => ({ ok: false, description: "blocked" }),
  });
  assert.deepEqual(outcome, { asked: false, reason: "telegram_failed" });
});

// ---- the wallet tap triggers the address question ----

test("FIN-d: answering the rail question with wallet asks for the address immediately", async () => {
  const asks = [];
  const outcome = await handlePayoutCallback("payout:answer:wallet", {
    uid: "u1", chatId: "7", actorId: "7", nowMs: NOW,
    savePayoutAnswer: async () => ({ type: "wallet", status: "awaiting_details", answered_at: new Date(NOW).toISOString() }),
    askWalletAddress: async (uid, chatId) => { asks.push([uid, chatId]); return { asked: true }; },
  });
  assert.equal(outcome.ok, true);
  assert.deepEqual(outcome.addressAsk, { asked: true }, "the tap→address-question chain must be visible in the outcome");
  assert.deepEqual(asks, [["u1", "7"]]);
});

test("FIN-d: the bank rail does not trigger the wallet-address question", async () => {
  const outcome = await handlePayoutCallback("payout:answer:bank", {
    uid: "u1", chatId: "7", actorId: "7", nowMs: NOW,
    savePayoutAnswer: async () => ({ type: "bank", status: "awaiting_details", answered_at: new Date(NOW).toISOString() }),
    askWalletAddress: async () => { throw new Error("bank must not ask for a wallet address"); },
  });
  assert.equal(outcome.ok, true);
  assert.equal("addressAsk" in outcome, false);
});

// ---- the typed address ----

function pendingRow(overrides = {}) {
  return {
    uid: "u1",
    telegram_chat_id: "7", // production rows always carry this (they are looked up by it)
    payout_destination: { type: "wallet", status: "awaiting_address", asked_at: new Date(NOW).toISOString() },
    ...overrides,
  };
}

function typedDeps(overrides = {}) {
  return { token: "t", chatId: "7", actorId: "7", nowMs: NOW, ...SUPA, ...overrides };
}

test("FIN-d: a valid typed address is CAS-written, read back, and confirmed with the quoted short form", async () => {
  const sent = [];
  const writes = [];
  const outcome = await handleTypedPayoutAddress(CHECKSUMMED, pendingRow(), typedDeps({
    saveWalletAddress: async (...args) => {
      writes.push(args);
      return { type: "wallet", address: CHECKSUMMED, status: "usable", confirmed_at: new Date(NOW).toISOString() };
    },
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
  }));
  assert.equal(outcome.handled, true);
  assert.equal(outcome.ok, true);
  assert.equal(outcome.address, CHECKSUMMED);
  assert.deepEqual(writes, [["u1", CHECKSUMMED, NOW]]);
  assert.equal(sent.length, 1);
  assert.equal(sent[0][2], FINANCIAL_STRINGS.ja.payoutAddress.confirmed.replace("{short}", "0xfB69…d359"));
});

test("FIN-d: the default persist is a CAS from awaiting_address to usable, verified by an independent read-back", async () => {
  const requests = [];
  const usable = { type: "wallet", address: CHECKSUMMED, status: "usable", confirmed_at: new Date(NOW).toISOString() };
  const saved = await saveWalletAddress("u1", CHECKSUMMED, NOW, {
    ...SUPA,
    fetchImpl: async (url, init = {}) => {
      requests.push({ url: String(url), init });
      return jsonResponse([{ uid: "u1", payout_destination: usable }]);
    },
  });
  assert.deepEqual(saved, usable);
  assert.equal(requests.length, 2, "one CAS write + one independent read-back");
  const [patch, read] = requests;
  assert.equal(patch.init.method, "PATCH");
  assert.match(patch.url, /uid=eq\.u1/);
  assert.match(patch.url, /payout_destination->>status=eq\.awaiting_address/, "only a pending intake may be completed");
  assert.match(patch.url, /payout_destination->>type=eq\.wallet/);
  assert.deepEqual(JSON.parse(patch.init.body), { payout_destination: usable });
  assert.equal(String(read.init.method || "GET").toUpperCase(), "GET");
  assert.match(read.url, /uid=eq\.u1/);
});

test("FIN-d: a write that cannot be read back is a failure reply, never a false success", async () => {
  // The PATCH claims success but the independent read shows something else — 13b principle: never lie.
  let call = 0;
  const saved = await saveWalletAddress("u1", CHECKSUMMED, NOW, {
    ...SUPA,
    fetchImpl: async () => {
      call += 1;
      if (call === 1) return jsonResponse([{ uid: "u1", payout_destination: { type: "wallet", address: CHECKSUMMED, status: "usable" } }]);
      return jsonResponse([{ uid: "u1", payout_destination: { type: "wallet", status: "awaiting_address" } }]);
    },
  });
  assert.equal(saved, null);

  for (const [label, fetchImpl] of [
    ["no row claimed", async () => jsonResponse([])],
    ["http error", async () => jsonResponse([], 500)],
    ["network error", async () => { throw new Error("network"); }],
  ]) {
    assert.equal(await saveWalletAddress("u1", CHECKSUMMED, NOW, { ...SUPA, fetchImpl }), null, label);
  }

  const sent = [];
  const outcome = await handleTypedPayoutAddress(CHECKSUMMED, pendingRow(), typedDeps({
    saveWalletAddress: async () => null,
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
  }));
  assert.deepEqual(outcome, { handled: true, ok: false, reason: "persist_failed" });
  assert.equal(sent.length, 1);
  assert.equal(sent[0][2], FINANCIAL_STRINGS.ja.payoutAddress.saveFailed);
});

test("FIN-d: an invalid address is rejected visibly with the RIGHT reason and writes nothing", async () => {
  const explode = async () => { throw new Error("an invalid address must never be written"); };
  const sent = [];
  const deps = typedDeps({ saveWalletAddress: explode, sendMessage: async (...args) => { sent.push(args); return { ok: true }; } });

  const checksum = await handleTypedPayoutAddress(CHECKSUMMED.replace("fB69", "Fb69"), pendingRow(), deps);
  assert.deepEqual(checksum, { handled: true, ok: false, reason: "checksum" });
  assert.equal(sent[0][2], FINANCIAL_STRINGS.ja.payoutAddress.rejectedChecksum);

  const format = await handleTypedPayoutAddress("not-an-address", pendingRow(), deps);
  assert.deepEqual(format, { handled: true, ok: false, reason: "format" });
  assert.equal(sent[1][2], FINANCIAL_STRINGS.ja.payoutAddress.rejectedFormat);
  assert.equal(sent.length, 2);
});

test("FIN-d: no pending intake → the typed message is not claimed (feedback and ask keep working)", async () => {
  const explode = async () => { throw new Error("no pending intake must touch nothing"); };
  const deps = typedDeps({ saveWalletAddress: explode, sendMessage: explode, markAwaitingAddress: explode });
  // No row at all (another chat / unlinked user).
  assert.deepEqual(await handleTypedPayoutAddress(CHECKSUMMED, null, deps), { handled: false });
  // A rail answered but bank, or wallet not yet asked, or already usable.
  assert.deepEqual(await handleTypedPayoutAddress(CHECKSUMMED, pendingRow({ payout_destination: null }), deps), { handled: false });
  assert.deepEqual(await handleTypedPayoutAddress(CHECKSUMMED,
    pendingRow({ payout_destination: { type: "bank", status: "awaiting_details" } }), deps), { handled: false });
  assert.deepEqual(await handleTypedPayoutAddress(CHECKSUMMED,
    pendingRow({ payout_destination: { type: "wallet", status: "awaiting_details" } }), deps), { handled: false });
  // A second address while usable (no 変更) must NOT silently overwrite the registered one.
  assert.deepEqual(await handleTypedPayoutAddress(CHECKSUMMED_2,
    pendingRow({ payout_destination: { type: "wallet", status: "usable", address: CHECKSUMMED } }), deps), { handled: false });
});

test("FIN-d: bot commands are never claimed by the pending intake — /start keeps working mid-intake", async () => {
  const explode = async () => { throw new Error("a command is not an address"); };
  const deps = typedDeps({ saveWalletAddress: explode, sendMessage: explode });
  assert.deepEqual(await handleTypedPayoutAddress("/start", pendingRow(), deps), { handled: false });
  assert.deepEqual(await handleTypedPayoutAddress("/panel", pendingRow(), deps), { handled: false });
});

test("FIN-d: another actor in the chat cannot answer the intake — nothing written, nothing sent", async () => {
  const explode = async () => { throw new Error("out-of-scope actors must not write"); };
  const outcome = await handleTypedPayoutAddress(CHECKSUMMED, pendingRow(),
    typedDeps({ actorId: "9", saveWalletAddress: explode, sendMessage: explode }));
  assert.deepEqual(outcome, { handled: true, ok: false, reason: "scope_mismatch" });
});

// ---- 送金先を変更 ----

test("FIN-d: 「送金先を変更」 on a usable wallet re-opens the intake by CAS from usable and re-asks", async () => {
  const marks = [];
  const sent = [];
  const usableRow = pendingRow({ payout_destination: { type: "wallet", status: "usable", address: CHECKSUMMED } });
  const outcome = await handleTypedPayoutAddress(CHANGE_COMMAND, usableRow, typedDeps({
    markAwaitingAddress: async (...args) => { marks.push(args); return { type: "wallet", status: "awaiting_address" }; },
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
  }));
  assert.equal(outcome.handled, true);
  assert.equal(outcome.ok, true);
  assert.equal(marks.length, 1);
  assert.equal(marks[0][0], "u1");
  assert.equal(marks[0][1], "usable", "the CAS must expect the CURRENT status, not awaiting_details");
  // Same single-question discipline: the re-ask is the same one question, verbatim.
  assert.equal(sent.length, 1);
  assert.equal(sent[0][2], FINANCIAL_STRINGS.ja.payoutAddress.ask);
});

test("FIN-d: 「送金先を変更」 with no wallet destination on file is not claimed", async () => {
  const explode = async () => { throw new Error("nothing to change"); };
  const deps = typedDeps({ markAwaitingAddress: explode, sendMessage: explode });
  assert.deepEqual(await handleTypedPayoutAddress(CHANGE_COMMAND, null, deps), { handled: false });
  assert.deepEqual(await handleTypedPayoutAddress(CHANGE_COMMAND, pendingRow({ payout_destination: null }), deps), { handled: false });
  // The bank leg's details flow is 13d's bank sibling, not this atomic — a bank rail is left alone.
  assert.deepEqual(await handleTypedPayoutAddress(CHANGE_COMMAND,
    pendingRow({ payout_destination: { type: "bank", status: "awaiting_details" } }), deps), { handled: false });
});

test("FIN-d: change → new address → confirmed: the whole re-registration round trip", async () => {
  let stored = { type: "wallet", status: "usable", address: CHECKSUMMED, confirmed_at: new Date(NOW).toISOString() };
  const sent = [];
  const deps = typedDeps({
    markAwaitingAddress: async (uid, fromStatus, at) => {
      if (!stored || stored.status !== fromStatus) return null;
      stored = { type: "wallet", status: "awaiting_address", asked_at: new Date(at).toISOString() };
      return stored;
    },
    saveWalletAddress: async (uid, address, at) => {
      if (!stored || stored.status !== "awaiting_address") return null;
      stored = { type: "wallet", address, status: "usable", confirmed_at: new Date(at).toISOString() };
      return stored;
    },
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
  });

  const change = await handleTypedPayoutAddress(CHANGE_COMMAND, pendingRow({ payout_destination: stored }), deps);
  assert.equal(change.ok, true);
  assert.equal(stored.status, "awaiting_address");

  const replaced = await handleTypedPayoutAddress(CHECKSUMMED_2, pendingRow({ payout_destination: stored }), deps);
  assert.equal(replaced.ok, true);
  assert.equal(stored.address, CHECKSUMMED_2);
  assert.equal(isPayoutDestinationUsable(stored), true);
  assert.equal(sent.length, 2);
  assert.equal(sent[1][2], FINANCIAL_STRINGS.ja.payoutAddress.confirmed.replace("{short}", "0x5aAe…eAed"));
});

test("a row whose telegram_chat_id names another chat is refused even with matching actor", async () => {
  // Review finding: the money-bearing write must not trust an upstream row lookup blindly.
  const deps = typedDeps();
  const row = { uid: "u1", telegram_chat_id: "999", payout_destination: { type: "wallet", status: "awaiting_address" } };
  const out = await handleTypedPayoutAddress(CHECKSUMMED, row, { ...deps, chatId: "7", actorId: "7" });
  assert.equal(out.handled, true);
  assert.equal(out.ok, false);
  assert.equal(out.reason, "row_chat_mismatch"); // refusal precedes any I/O in the handler
});
