// lib/payout-question.js — FIN-b (spec row 13b): the payout-destination closed question.
//
// The weekly discovery announcement has always offered a "登録する" button, but pressing it did
// nothing: handleDiscoveryCallback acknowledged the tap and returned, so lm_users.payout_destination
// stayed null and the FINANCIAL organ had nowhere to send money. This module is the missing round
// trip — the tap opens the §9.11 closed question, the tapped answer is written to payout_destination,
// and the question is asked exactly once in a user's lifetime.
//
// Three rules shape the code:
//   ASK ONCE      — we read the column before sending. A row that already carries a destination is
//                   never asked again, and a read we could not perform is "unknown", never "empty":
//                   guessing "not answered" is how a user gets the same question every week.
//   NEVER CLOBBER — the write is a compare-and-set (payout_destination=is.null), so a replayed or
//                   concurrent tap cannot overwrite a destination the user already gave us.
//   NEVER LIE     — we ask PostgREST to return the row it wrote and compare it to what we sent. A
//                   persist that we cannot see in the database is reported as a failure, never as a
//                   registered destination.
//
// What is stored is the RAIL the user chose, marked `awaiting_details`. The account number / wallet
// address itself is a separate step (13c/13d), and isPayoutDestinationUsable() exists so that step
// cannot mistake "they told us which rail" for "we know where to send money".
"use strict";

const { FINANCIAL_STRINGS } = require("./i18n.js");
const { sendMessage } = require("./telegram.js");

const PAYOUT_RAILS = Object.freeze(["bank", "wallet"]);
const PAYOUT_ANSWERS = Object.freeze(["bank", "wallet", "later"]);
const PAYOUT_CALLBACK = /^payout:answer:(bank|wallet|later)$/;

function payoutQuestionMessage() {
  const copy = FINANCIAL_STRINGS.ja.payoutQuestion;
  return {
    text: copy.text,
    extra: { reply_markup: { inline_keyboard: [[
      { text: copy.bankButton, callback_data: "payout:answer:bank" },
      { text: copy.walletButton, callback_data: "payout:answer:wallet" },
      { text: copy.laterButton, callback_data: "payout:answer:later" },
    ]] } },
  };
}

function payoutDestinationRecord(rail, nowMs) {
  if (!PAYOUT_RAILS.includes(rail)) throw new Error(`unknown payout rail: ${String(rail).slice(0, 20)}`);
  return { type: rail, status: "awaiting_details", answered_at: new Date(nowMs).toISOString() };
}

// A destination is only spendable once someone recorded the actual account/address AND flipped the
// status. The rail answer alone must never open a transfer.
function isPayoutDestinationUsable(destination) {
  if (!destination || typeof destination !== "object") return false;
  if (!PAYOUT_RAILS.includes(destination.type)) return false;
  if (destination.status !== "ready") return false;
  return typeof destination.destination === "string" && destination.destination.trim().length > 0;
}

function supaHeaders(key, prefer) {
  return {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
    ...(prefer ? { Prefer: prefer } : {}),
  };
}

function supaBase(url) {
  return String(url).replace(/\/$/, "");
}

// null = we do not know (unconfigured, network error, non-2xx, unparseable). { destination } = we know,
// and `destination` may legitimately be null. The caller must treat those two cases differently.
async function readPayoutDestination(uid, opts = {}) {
  if (!uid || !opts.supaUrl || !opts.supaKey) return null;
  const f = opts.fetchImpl || fetch;
  const url = `${supaBase(opts.supaUrl)}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}` +
    "&select=uid,payout_destination&limit=1";
  const response = await f(url, { headers: supaHeaders(opts.supaKey) }).catch(() => null);
  if (!response || !response.ok) return null;
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) return null;
  return { destination: (rows[0] && rows[0].payout_destination) || null };
}

// Returns the persisted record, or null. Null covers every failure AND the "someone already registered
// a destination" case — in both, the caller must not tell the user their answer was saved.
async function savePayoutAnswer(uid, rail, nowMs, opts = {}) {
  if (!uid || !opts.supaUrl || !opts.supaKey || !PAYOUT_RAILS.includes(rail)) return null;
  const f = opts.fetchImpl || fetch;
  const record = payoutDestinationRecord(rail, nowMs);
  const url = `${supaBase(opts.supaUrl)}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}` +
    "&payout_destination=is.null&select=uid,payout_destination";
  const response = await f(url, {
    method: "PATCH",
    headers: supaHeaders(opts.supaKey, "return=representation"),
    body: JSON.stringify({ payout_destination: record }),
  }).catch(() => null);
  if (!response || !response.ok) return null;
  const rows = await response.json().catch(() => null);
  const written = Array.isArray(rows) && rows[0] ? rows[0].payout_destination : null;
  // Read back what the database actually holds before calling it saved.
  if (!written || written.type !== rail || written.status !== record.status) return null;
  return written;
}

async function askPayoutQuestion(deps = {}) {
  const chatId = String(deps.chatId || "");
  if (!deps.uid || !chatId) return { asked: false, reason: "unreachable" };
  const read = deps.readPayoutDestination || ((uid) => readPayoutDestination(uid, deps));
  const existing = await read(deps.uid);
  if (!existing) return { asked: false, reason: "lookup_failed" };
  if (existing.destination) return { asked: false, reason: "already_answered" };
  const message = payoutQuestionMessage();
  const result = await (deps.sendMessage || sendMessage)(deps.token, chatId, message.text, message.extra);
  if (!result || !result.ok) return { asked: false, reason: "telegram_failed" };
  return { asked: true };
}

async function handlePayoutCallback(data, opts = {}) {
  const match = PAYOUT_CALLBACK.exec(String(data || ""));
  if (!match) return { ignored: true };
  const [, answer] = match;
  // ［あとで］ writes nothing: the gate stays honestly locked and the weekly announcement stays eligible.
  if (answer === "later") return { handled: true, ok: true, answer, persisted: false };
  const chatId = String(opts.chatId || "");
  const actorId = String(opts.actorId || "");
  if (!opts.uid || !chatId || !actorId || actorId !== chatId) {
    return { handled: true, ok: false, answer, reason: "scope_mismatch" };
  }
  const nowMs = opts.nowMs == null ? Date.now() : opts.nowMs;
  const save = opts.savePayoutAnswer || ((uid, rail, at) => savePayoutAnswer(uid, rail, at, opts));
  const destination = await save(opts.uid, answer, nowMs);
  if (!destination) return { handled: true, ok: false, answer, reason: "persist_failed" };
  return { handled: true, ok: true, answer, destination };
}

module.exports = {
  PAYOUT_RAILS,
  PAYOUT_ANSWERS,
  payoutQuestionMessage,
  payoutDestinationRecord,
  isPayoutDestinationUsable,
  readPayoutDestination,
  savePayoutAnswer,
  askPayoutQuestion,
  handlePayoutCallback,
};
