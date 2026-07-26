// lib/payout-address-intake.js — FIN-d (spec row 13d-a): the typed wallet-address intake.
//
// 13b recorded WHICH rail the user chose ({type:"wallet", status:"awaiting_details"}), but a button
// cannot carry the address itself (2026-07-26 Dais 裁定: button では渡せない情報がある). This module
// closes that gap: the wallet tap asks for the address, a durable pending-intake marker
// ({status:"awaiting_address"}) claims the NEXT typed message from that chat, EIP-55 validates what
// the user typed, and only a write we can read back flips payout_destination to usable.
//
// The 13b rules carry over unchanged:
//   NEVER CLOBBER — every write is a compare-and-set on the CURRENT status (awaiting_details →
//                   awaiting_address → usable), so a replayed message, a raced webhook, or a second
//                   pasted address can never silently overwrite a registered destination.
//   NEVER LIE     — the usable write is verified by an independent read-back before the ✅ goes out.
//                   A write we cannot see in the database is a visible failure, never a false success.
//   VISIBLE       — every rejection names its reason (checksum失敗 / 形式不正), copy quoted from
//                   lib/i18n.js (Dais-owned), never invented here.
//
// EIP-55 comes from the same audited keccak lib/agent-wallet.js already uses — Node's SHA3-256 is NOT
// Ethereum's keccak256 (different padding), and a hand-rolled checksum that is subtly wrong does not
// fail: it silently sends money nowhere.
"use strict";

const { FINANCIAL_STRINGS } = require("./i18n.js");
const { sendMessage } = require("./telegram.js");
const { toChecksumAddress } = require("./agent-wallet.js");

const COPY = FINANCIAL_STRINGS.ja.payoutAddress;
const CHANGE_COMMAND = COPY.changeCommand;

// { ok:true, address } — checksummed form when the input carried case information, lowercased when it
// did not (all-lower/all-upper has no checksum to verify, per EIP-55 itself).
// { ok:false, reason:"format"|"checksum" } — the reason feeds the visible rejection copy.
function validateWalletAddress(text) {
  const match = /^0x([0-9a-fA-F]{40})$/.exec(String(text || "").trim());
  if (!match) return { ok: false, reason: "format" };
  const [, hex] = match;
  if (hex === hex.toLowerCase() || hex === hex.toUpperCase()) {
    return { ok: true, address: `0x${hex.toLowerCase()}` };
  }
  const checksummed = toChecksumAddress(hex.toLowerCase());
  if (checksummed !== `0x${hex}`) return { ok: false, reason: "checksum" };
  return { ok: true, address: checksummed };
}

// 0x6592…EDc7 style: enough to recognise your own address, never the whole thing re-typed by us.
function shortWalletAddress(address) {
  const value = String(address || "");
  return `${value.slice(0, 6)}…${value.slice(-4)}`;
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

// The tenant-scoped CAS filter shared by both writes: only THIS user's row, only a wallet rail, only
// when the destination is in the status the caller believes it is in.
function casUrl(opts, uid, fromStatus) {
  return `${supaBase(opts.supaUrl)}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}` +
    "&payout_destination->>type=eq.wallet" +
    `&payout_destination->>status=eq.${encodeURIComponent(fromStatus)}` +
    "&select=uid,payout_destination";
}

async function casPatch(uid, fromStatus, record, opts) {
  if (!uid || !opts.supaUrl || !opts.supaKey) return null;
  const f = opts.fetchImpl || fetch;
  const response = await f(casUrl(opts, uid, fromStatus), {
    method: "PATCH",
    headers: supaHeaders(opts.supaKey, "return=representation"),
    body: JSON.stringify({ payout_destination: record }),
  }).catch(() => null);
  if (!response || !response.ok) return null;
  const rows = await response.json().catch(() => null);
  const written = Array.isArray(rows) && rows[0] ? rows[0].payout_destination : null;
  if (!written || written.type !== "wallet" || written.status !== record.status) return null;
  return written;
}

// The pending-intake marker. Durable storage is the existing payout_destination column — no new
// table, and the status field doubles as the router's "does the next typed message belong to me?".
async function markAwaitingAddress(uid, fromStatus, nowMs, opts = {}) {
  return casPatch(uid, fromStatus, {
    type: "wallet",
    status: "awaiting_address",
    asked_at: new Date(nowMs).toISOString(),
  }, opts);
}

// CAS awaiting_address → usable, then an INDEPENDENT read-back: return=representation shows what the
// PATCH touched, the GET shows what the database now actually holds. Only agreement is success.
async function saveWalletAddress(uid, address, nowMs, opts = {}) {
  const record = {
    type: "wallet",
    address,
    status: "usable",
    confirmed_at: new Date(nowMs).toISOString(),
  };
  const written = await casPatch(uid, "awaiting_address", record, opts);
  if (!written || written.address !== address) return null;
  const f = opts.fetchImpl || fetch;
  const url = `${supaBase(opts.supaUrl)}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}` +
    "&select=uid,payout_destination&limit=1";
  const response = await f(url, { headers: supaHeaders(opts.supaKey) }).catch(() => null);
  if (!response || !response.ok) return null;
  const rows = await response.json().catch(() => null);
  const stored = Array.isArray(rows) && rows[0] ? rows[0].payout_destination : null;
  if (!stored || stored.status !== "usable" || stored.address !== address) return null;
  return stored;
}

// Ask for the address. Marker FIRST, question second: a question without a marker would let the
// user's reply fall through to feedback, while a marker without a question just waits — the safe
// failure. deps.fromStatus is the status the CAS must find (awaiting_details on the tap path,
// the current status on the 「送金先を変更」 path).
async function askWalletAddress(uid, chatId, deps = {}) {
  const chat = String(chatId || "");
  if (!uid || !chat) return { asked: false, reason: "unreachable" };
  const fromStatus = deps.fromStatus || "awaiting_details";
  const nowMs = deps.nowMs == null ? Date.now() : deps.nowMs;
  const mark = deps.markAwaitingAddress || ((u, from, at) => markAwaitingAddress(u, from, at, deps));
  const marker = await mark(uid, fromStatus, nowMs);
  if (!marker) return { asked: false, reason: "marker_failed" };
  const sent = await (deps.sendMessage || sendMessage)(deps.token, chat, COPY.ask);
  if (!sent || !sent.ok) return { asked: false, reason: "telegram_failed" };
  return { asked: true };
}

// The typed-message leg. Returns { handled:false } whenever this message is not ours — the caller
// (server.js) then lets feedback / commands / the ask-location flow see it untouched. Claiming a
// message and claiming it correctly are the same decision here, so the guards come first:
//   - bot commands (/start, /panel, …) are never an address and never claimed mid-intake
//   - only the linked chat's own actor may answer (same actorId===chatId rule as the callbacks)
//   - only a wallet destination in awaiting_address has a pending intake
async function handleTypedPayoutAddress(text, row, deps = {}) {
  const trimmed = String(text || "").trim();
  const destination = row && row.payout_destination;
  const chatId = String(deps.chatId || "");
  const actorId = String(deps.actorId || "");
  const send = deps.sendMessage || sendMessage;

  // 「送金先を変更」: an existing wallet destination (usually usable) goes back to awaiting_address
  // and the same single question is asked again. A bank rail is left alone — its details flow is the
  // 13d bank sibling, and silently switching someone's rail is exactly the clobber we forbid.
  if (trimmed === CHANGE_COMMAND) {
    if (!row || !row.uid || !destination || destination.type !== "wallet" || !chatId) return { handled: false };
    if (actorId !== chatId) return { handled: true, ok: false, reason: "scope_mismatch" };
    const asked = await askWalletAddress(row.uid, chatId, { ...deps, fromStatus: destination.status });
    if (!asked.asked) return { handled: true, ok: false, reason: asked.reason };
    return { handled: true, ok: true, action: "change" };
  }

  if (!destination || destination.type !== "wallet" || destination.status !== "awaiting_address") {
    return { handled: false };
  }
  if (!row.uid || !chatId || trimmed.startsWith("/")) return { handled: false };
  if (actorId !== chatId) return { handled: true, ok: false, reason: "scope_mismatch" };

  const validated = validateWalletAddress(trimmed);
  if (!validated.ok) {
    await send(deps.token, chatId,
      validated.reason === "checksum" ? COPY.rejectedChecksum : COPY.rejectedFormat);
    return { handled: true, ok: false, reason: validated.reason };
  }

  const nowMs = deps.nowMs == null ? Date.now() : deps.nowMs;
  const save = deps.saveWalletAddress || ((uid, address, at) => saveWalletAddress(uid, address, at, deps));
  const stored = await save(row.uid, validated.address, nowMs);
  if (!stored) {
    await send(deps.token, chatId, COPY.saveFailed);
    return { handled: true, ok: false, reason: "persist_failed" };
  }
  await send(deps.token, chatId, COPY.confirmed.replace("{short}", shortWalletAddress(stored.address)));
  return { handled: true, ok: true, address: stored.address };
}

module.exports = {
  CHANGE_COMMAND,
  validateWalletAddress,
  shortWalletAddress,
  markAwaitingAddress,
  saveWalletAddress,
  askWalletAddress,
  handleTypedPayoutAddress,
};
