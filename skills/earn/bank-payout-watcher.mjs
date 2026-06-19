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

// PATCH body when a rail ACCEPTED the transfer. FIND-005: GMO bulktransfer is async — a 200 +
// apptransferNo means ACCEPTED, not 振込完了. So status='submitted' (honest), not 'paid'. A later poll of
// bulktransfer/status promotes 'submitted'→'paid'. The apptransferNo is persisted for that poll + audit.
export function buildSubmittedPatch(info = {}) {
  const ref = info.res && (info.res.apptransferNo || info.res.applyNo) ? `;ref=${info.res.apptransferNo || info.res.applyNo}` : "";
  return { status: "submitted", notes: `submitted;provider=${info.provider};amount=${info.amount};currency=${info.currency}${ref}` };
}
// FIND-002 idempotency: claim 'processing' BEFORE submit; revert to 'queued' only on a FAILED rail.
export const buildClaimPatch = () => ({ status: "processing" });
export const buildRevertPatch = () => ({ status: "queued" });

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

async function patchRecipient(id, body, label) {
  const res = await sb(`recipients?id=eq.${id}`, { method: "PATCH", headers: { Prefer: "return=minimal" }, body: JSON.stringify(body) });
  if (!res.ok) console.error(`[bank-watcher] ${label} PATCH failed for ${id}: HTTP ${res.status}`); // FIND-002/005: never swallow
  return res.ok;
}
async function markPaid(id, info) { return patchRecipient(id, buildSubmittedPatch(info), "submitted"); }
async function claim(ids) { for (const id of ids) await patchRecipient(id, buildClaimPatch(), "claim"); }
async function revert(id) { return patchRecipient(id, buildRevertPatch(), "revert"); }

async function getPool() {
  // FIND-003: in production this MUST be the real GMO 残高照会API balance, not env. env is a dev cap only;
  // bankWatcherPass also passes balance=pool so planBankFanout's guard rejects any spend > this pool.
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
  return bankWatcherPass({ readBankRecipients, getPool, markPaid, claim, revert, adapters: { gmo }, opts });
}

if (process.argv[1] && process.argv[1].endsWith("bank-payout-watcher.mjs")) {
  pass().then((r) => console.log(JSON.stringify(r))).catch((e) => { console.error("bank-watcher error:", e.message); process.exit(0); });
}
