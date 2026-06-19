// bank-payout-watcher.mjs — LIVE daemon entry for ③ JP bank-direct. Wires bankWatcherPass to real
// Supabase (recipients) + the GMO 一括振込 adapter. Mirrors ubi-payout-watcher.mjs but for method=bank.
// Pure pieces (makeGmoAdapter, buildPaidPatch) are unit-tested; the live pass() needs Supabase env +
// GMO_AOZORA_ACCESS_TOKEN (sandbox sunabar first) — gated, no-fake (returns 'gated' without a token).
//
// Invariant (資金決済法): own-funds 給付 only — anicca sends its OWN JPY.

import { bankWatcherPass } from "./bank-watcher.mjs";
import { bankRecipientsFromRows } from "./lib/bank-recipients.mjs";
import { buildBulkTransferRequest, submitBulkTransfer } from "./gmo-furikomi.mjs";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function sb(path, opts = {}) {
  return fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    ...opts,
    headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json", ...(opts.headers || {}) },
  });
}

// PATCH body to mark a recipient paid (no-fake: only called after a succeeded rail).
export function buildPaidPatch(info = {}) {
  return { status: "paid", notes: `paid;provider=${info.provider};amount=${info.amount};currency=${info.currency}` };
}

// today YYYYMMDD (live script context; not the workflow sandbox). Optional override for tests/determinism.
export function todayYmd(d = new Date()) {
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
}

// GMO adapter factory — token + submit injected (submit defaults to the real API; tests pass a mock).
export function makeGmoAdapter({ accountId, remitterName, transferDesignatedDate, token, submit = submitBulkTransfer }) {
  return async (transfers) => {
    const req = buildBulkTransferRequest({ accountId, remitterName, transferDesignatedDate, transfers });
    return submit(req, token);
  };
}

async function readBankRecipients() {
  const res = await sb("recipients?status=eq.queued&select=id,notes&order=applied_at.asc.nullslast");
  const rows = await res.json().catch(() => []);
  return bankRecipientsFromRows(Array.isArray(rows) ? rows : []);
}

async function markPaid(id, info) {
  await sb(`recipients?id=eq.${id}`, { method: "PATCH", headers: { Prefer: "return=minimal" }, body: JSON.stringify(buildPaidPatch(info)) });
}

async function getPool() {
  // JPY pool available to distribute. Live: our GMO 法人/sandbox account balance (残高照会API). For now env.
  return parseInt(process.env.GMO_JPY_POOL || "0", 10);
}

export async function pass() {
  const token = process.env.GMO_AOZORA_ACCESS_TOKEN;
  if (!token) { console.error("[bank-watcher] no GMO_AOZORA_ACCESS_TOKEN — gated (sandbox/prod token required)"); return { outcome: "gated", reason: "no_token" }; }
  if (!SUPABASE_URL || !SUPABASE_KEY) { console.error("[bank-watcher] missing Supabase env"); return { outcome: "gated", reason: "no_supabase" }; }
  const gmo = makeGmoAdapter({
    accountId: process.env.GMO_AOZORA_ACCOUNT_ID,
    remitterName: process.env.GMO_REMITTER_NAME || "ｱﾆﾂﾁﬔ",
    transferDesignatedDate: todayYmd(),
    token,
  });
  const opts = { reserve: parseInt(process.env.BANK_RESERVE_JPY || "0", 10), feePerTransfer: parseInt(process.env.GMO_FEE_JPY || "130", 10) };
  return bankWatcherPass({ readBankRecipients, getPool, markPaid, adapters: { gmo }, opts });
}

if (process.argv[1] && process.argv[1].endsWith("bank-payout-watcher.mjs")) {
  pass().then((r) => console.log(JSON.stringify(r))).catch((e) => { console.error("bank-watcher error:", e.message); process.exit(0); });
}
