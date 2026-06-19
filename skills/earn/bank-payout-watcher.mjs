// bank-payout-watcher.mjs — LIVE daemon entry for ③ JP bank-direct. Wires the SAFE bankWatcherPass to real
// Supabase (recipients) + the GMO 一括振込 adapter. Hardened against the adversary's double-pay findings:
//   - FIND-A: claim() is an ATOMIC compare-and-swap (PATCH ...&status=eq.queued, return=representation) —
//     returns ONLY ids we actually flipped, so concurrent passes can't both submit the same recipient.
//   - FIND-B: on adapter failure bankWatcherPass leaves rows 'processing' (no auto-requeue). makeGmoAdapter
//     also stamps a deterministic idempotency key so a manual retry of the SAME batch can be de-duped.
//   - FIND-C: getBalance() reads the REAL GMO 残高照会 balance (token-gated), not just an env cap.
//   - FIND-D: pollCompletions() promotes 'submitted'→'paid' (or requeues) from GMO bulktransfer/status.
//   - FIND-005: markPaid sets 'submitted' (accepted ≠ 振込完了) + persists the ref.
// Pure pieces are unit-tested; live pass() needs Supabase env + GMO_AOZORA_ACCESS_TOKEN (sunabar sandbox
// first) — gated no-fake (returns {gated} without a token).
//
// Invariant (資金決済法): own-funds 給付 only.
import { createHash } from "node:crypto";
import { bankWatcherPass } from "./bank-watcher.mjs";
import { bankRecipientsFromRows } from "./lib/bank-recipients.mjs";
import { buildBulkTransferRequest, submitBulkTransfer, API_BASE } from "./gmo-furikomi.mjs";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function sb(path, opts = {}) {
  return fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    ...opts,
    headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json", ...(opts.headers || {}) },
  });
}

// ---- pure helpers (unit-tested) -------------------------------------------------------------------

// FIND-005: accepted (200 + apptransferNo) is NOT 振込完了. status='submitted' + persist ref for the poll.
export function buildSubmittedPatch(info = {}) {
  const ref = info.res && (info.res.apptransferNo || info.res.applyNo) ? `;ref=${info.res.apptransferNo || info.res.applyNo}` : "";
  // FIND-103: preserve the original bank notes so a needs_review row a human re-queues is still parseable by
  // parseBankRecipient (otherwise the operator-recovery re-queue would silently drop the row).
  const base = info.raw ? `${info.raw};` : "";
  return { status: "submitted", notes: `${base}submitted;provider=${info.provider};amount=${info.amount};currency=${info.currency}${ref}` };
}
export const buildClaimPatch = () => ({ status: "processing" });   // FIND-A: queued -> processing (atomic via filter)
// FIND-109: release happens ONLY on a pre-dispatch skip (nothing sent), so it must FULLY reset the row to a
// fresh queued state — restoring the original notes (raw) to STRIP the claimed_at the claim stamped. Otherwise
// the claimed_at dispatch-guard (bank-recipients.mjs) would refuse this legitimately-skipped recipient forever.
export const buildReleasePatch = (raw) => (raw ? { status: "queued", notes: raw } : { status: "queued" });

// FIND-A: a CAS PATCH returns the row IFF it was still 'queued' when WE patched it. 1 row => we claimed it.
export function claimedFromRows(rows) {
  return Array.isArray(rows) && rows.length === 1;
}

// deterministic idempotency key for a batch (FIND-B defense): same recipients+amounts => same key.
// FIND-006: sha256 (not a 32-bit hash) to make collisions cryptographically negligible. GMO honoring the
// x-idempotency-key header is UNVERIFIED until a live token; the primary defense is no-auto-requeue.
export function idempotencyKey(transfers = []) {
  const sig = transfers.map((t) => `${t.to}:${t.amount}`).sort().join("|");
  return `anicca-ubi-${createHash("sha256").update(sig).digest("hex").slice(0, 32)}`;
}

// FIND-002/D: the submit ref is stored inside notes ("...;ref=R1"); parse it back for the completion poll.
export function parseRef(notes) {
  const m = String(notes || "").match(/(?:^|;)ref=([^;]+)/);
  return m ? m[1] : null;
}
// FIND-101: claim stamps claimed_at into notes; reconcile keys on THIS (a real claim time), not applied_at.
export function parseClaimedAt(notes) {
  const m = String(notes || "").match(/(?:^|;)claimed_at=([^;]+)/);
  return m ? m[1] : null;
}

// FIND-004: testable CAS core. items may be ids OR recipient objects ({id,...}); patchQueued(item) -> rows
// PostgREST returned (1 row IFF we flipped queued). Returns the claimed items' ids.
export async function claimWith(patchQueued, items = []) {
  const claimed = [];
  for (const item of items) {
    const rows = await patchQueued(item);
    if (claimedFromRows(rows)) claimed.push(item && item.id !== undefined ? item.id : item);
  }
  return claimed;
}

// FIND-003: flag rows stuck in 'processing' beyond a threshold to 'needs_review' (operator path) — NEVER
// auto-pay/requeue without GMO confirmation. deps injected for unit test.
export async function reconcileStuck({ readProcessing, flagNeedsReview, olderThanMs = 1800000, now }) {
  const rows = await readProcessing();
  const flagged = [];
  for (const r of rows || []) {
    const ts = r.ts ? Date.parse(r.ts) : NaN;
    // FIND-103: a 'processing' row with NULL/unparseable claimed_at is itself anomalous (claim never stamped
    // it, or it predates the stamp) — flag it too rather than silently dropping it. Fresh, validly-stamped
    // in-flight rows (ts within the window) are the ONLY ones left alone.
    const aged = Number.isFinite(ts) ? now - ts >= olderThanMs : true;
    if (aged) { await flagNeedsReview(r.id); flagged.push(r.id); }
  }
  return { flagged };
}

export function todayYmd(d = new Date()) {
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
}

// GMO adapter factory — token + submit injected (tests pass a mock). Stamps the idempotency key.
export function makeGmoAdapter({ accountId, remitterName, transferDesignatedDate, token, submit = submitBulkTransfer }) {
  return async (transfers) => {
    const req = buildBulkTransferRequest({ accountId, remitterName, transferDesignatedDate, transfers });
    req.idempotencyKey = idempotencyKey(transfers); // FIND-B: dedupe a same-batch retry
    return submit(req, token);
  };
}

// FIND-D: completion poll — promote 'submitted'->'paid' on confirmed completion.
// FIND-100 (critical): a 'failed' verdict from the UNVERIFIED queryStatus must NEVER auto-requeue an
// irreversible transfer (that re-introduces the double-pay lever). 'completed'->markPaid is safe
// (idempotent, sends no money); 'failed'->flagNeedsReview for a human/operator to confirm with GMO before
// any re-send. 'pending' is left as-is. deps injected so the state machine is unit-tested without a token.
export async function pollCompletions({ readSubmitted, queryStatus, markPaid, flagNeedsReview }) {
  const rows = await readSubmitted();
  const done = [], review = [], pending = [];
  for (const row of rows || []) {
    const st = await queryStatus(row.ref);
    if (st === "completed") { await markPaid(row.id); done.push(row.id); }
    else if (st === "failed") { await flagNeedsReview(row.id); review.push(row.id); } // NO auto-requeue
    else pending.push(row.id);
  }
  return { done, review, pending };
}

// ---- live Supabase + GMO wiring -------------------------------------------------------------------

async function readBankRecipients() {
  const res = await sb("recipients?status=eq.queued&select=id,notes&order=applied_at.asc.nullslast");
  const rows = await res.json().catch(() => []);
  return bankRecipientsFromRows(Array.isArray(rows) ? rows : []);
}

// FIND-A: atomic CAS — PATCH guarded by &status=eq.queued; row returned only if WE flipped it.
// FIND-101: also stamp claimed_at into notes (preserving the original bank notes) so reconcile can age rows.
async function claim(recipients) {
  const nowIso = new Date().toISOString();
  return claimWith(async (r) => {
    const notes = `${r.raw || ""};claimed_at=${nowIso}`.replace(/^;/, "");
    const res = await sb(`recipients?id=eq.${r.id}&status=eq.queued`, { method: "PATCH", headers: { Prefer: "return=representation" }, body: JSON.stringify({ ...buildClaimPatch(), notes }) });
    if (!res.ok) { console.error(`[bank-watcher] claim CAS failed ${r.id}: HTTP ${res.status}`); return []; }
    return res.json().catch(() => []);
  }, recipients);
}
async function release(recipients) {
  for (const r of recipients) await sb(`recipients?id=eq.${r.id}`, { method: "PATCH", headers: { Prefer: "return=minimal" }, body: JSON.stringify(buildReleasePatch(r.raw)) });
}

// FIND-002/D live wiring: read 'submitted' rows + their ref, query GMO completion, promote paid / requeue.
async function readSubmitted() {
  const res = await sb("recipients?status=eq.submitted&select=id,notes");
  const rows = await res.json().catch(() => []);
  return (Array.isArray(rows) ? rows : []).map((r) => ({ id: r.id, ref: parseRef(r.notes) })).filter((r) => r.ref);
}
async function queryStatus(ref) { // GMO bulktransfer/status — UNVERIFIED endpoint/shape until live token
  const token = process.env.GMO_AOZORA_ACCESS_TOKEN;
  if (!token || !ref) return "pending";
  try {
    const res = await fetch(`${API_BASE}/bulktransfer/status?apptransferNo=${encodeURIComponent(ref)}`, { headers: { Authorization: `Bearer ${token}`, "x-access-token": token, Accept: "application/json" } });
    if (!res.ok) return "pending";
    const j = await res.json();
    const s = String(j.status || j.transferStatus || "").toLowerCase();
    if (/complete|done|success|完了/.test(s)) return "completed";
    if (/fail|error|reject|失敗|却下/.test(s)) return "failed";
    return "pending";
  } catch { return "pending"; }
}
async function markCompleted(id) { await sb(`recipients?id=eq.${id}`, { method: "PATCH", headers: { Prefer: "return=minimal" }, body: JSON.stringify({ status: "paid" }) }); }
async function flagNeedsReview(id) { await sb(`recipients?id=eq.${id}`, { method: "PATCH", headers: { Prefer: "return=minimal" }, body: JSON.stringify({ status: "needs_review" }) }); }

// FIND-D: completion-poll pass (cron: promote submitted->paid; FIND-100: GMO-reported failures go to
// needs_review for a human, NEVER auto-requeue an irreversible transfer).
export async function pollPass() {
  if (!process.env.GMO_AOZORA_ACCESS_TOKEN) return { outcome: "gated", reason: "no_token" };
  if (!SUPABASE_URL || !SUPABASE_KEY) return { outcome: "gated", reason: "no_supabase" };
  return pollCompletions({ readSubmitted, queryStatus, markPaid: markCompleted, flagNeedsReview });
}

// FIND-003: operator reconcile — flag 'processing' rows older than threshold to 'needs_review'.
export async function reconcilePass() {
  if (!SUPABASE_URL || !SUPABASE_KEY) return { outcome: "gated", reason: "no_supabase" };
  return reconcileStuck({
    readProcessing: async () => {
      const res = await sb("recipients?status=eq.processing&select=id,notes");
      const rows = await res.json().catch(() => []);
      return (Array.isArray(rows) ? rows : []).map((r) => ({ id: r.id, ts: parseClaimedAt(r.notes) }));
    },
    flagNeedsReview: async (id) => { await sb(`recipients?id=eq.${id}`, { method: "PATCH", headers: { Prefer: "return=minimal" }, body: JSON.stringify({ status: "needs_review" }) }); },
    now: Date.now(),
  });
}
async function markPaid(id, info) {
  const res = await sb(`recipients?id=eq.${id}`, { method: "PATCH", headers: { Prefer: "return=minimal" }, body: JSON.stringify(buildSubmittedPatch(info)) });
  if (!res.ok) console.error(`[bank-watcher] submitted PATCH failed ${id}: HTTP ${res.status}`); // never swallow
  return res.ok;
}

// FIND-C: real available balance from GMO 残高照会. UNVERIFIED endpoint shape until a live token confirms it;
// env GMO_JPY_POOL is a DEV-ONLY override (logged) — never the production source of truth.
async function getBalance() {
  const token = process.env.GMO_AOZORA_ACCESS_TOKEN;
  const accountId = process.env.GMO_AOZORA_ACCOUNT_ID;
  if (token && accountId) {
    try {
      // UNVERIFIED: confirm path + response field against GMO docs on first live token.
      const res = await fetch(`${API_BASE}/accounts/${accountId}/balances`, { headers: { Authorization: `Bearer ${token}`, Accept: "application/json" } });
      if (res.ok) {
        const j = await res.json();
        const bal = parseInt(j.balance ?? j.availableBalance ?? (j.balances && j.balances[0] && j.balances[0].balance), 10);
        if (Number.isInteger(bal)) return bal;
      }
      console.error(`[bank-watcher] balance fetch unexpected (HTTP ${res.status}) — refusing env fallback for safety`);
      return 0; // FIND-C: do NOT silently distribute against an env cap if the real balance is unknown
    } catch (e) {
      console.error(`[bank-watcher] balance fetch error: ${e.message} — returning 0 (no spend)`);
      return 0;
    }
  }
  const dev = parseInt(process.env.GMO_JPY_POOL_DEV || "0", 10);
  if (dev) console.error("[bank-watcher] DEV balance from GMO_JPY_POOL_DEV — NOT a real balance");
  return dev;
}

export async function pass() {
  const token = process.env.GMO_AOZORA_ACCESS_TOKEN;
  if (!token) { console.error("[bank-watcher] no GMO_AOZORA_ACCESS_TOKEN — gated"); return { outcome: "gated", reason: "no_token" }; }
  if (!SUPABASE_URL || !SUPABASE_KEY) { console.error("[bank-watcher] missing Supabase env"); return { outcome: "gated", reason: "no_supabase" }; }
  const gmo = makeGmoAdapter({
    accountId: process.env.GMO_AOZORA_ACCOUNT_ID,
    remitterName: process.env.GMO_REMITTER_NAME || "ｱﾆﾂﾁﾔ",
    transferDesignatedDate: todayYmd(),
    token,
  });
  const opts = { reserve: parseInt(process.env.BANK_RESERVE_JPY || "0", 10), feePerTransfer: parseInt(process.env.GMO_FEE_JPY || "130", 10) };
  return bankWatcherPass({ readBankRecipients, getBalance, claim, release, markPaid, adapters: { gmo }, opts });
}

if (process.argv[1] && process.argv[1].endsWith("bank-payout-watcher.mjs")) {
  const cmd = process.argv[2] || "pass"; // pass | poll | reconcile
  const fn = cmd === "poll" ? pollPass : cmd === "reconcile" ? reconcilePass : pass;
  fn().then((r) => console.log(JSON.stringify(r))).catch((e) => { console.error("bank-watcher error:", e.message); process.exit(0); });
}
