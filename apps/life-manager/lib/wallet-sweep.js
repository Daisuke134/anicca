"use strict";
// AE-ZERO-START-1 §4.4 — the self-heal sweep, which is the ONLY enqueue point for zero-start.
//
// `lm-onboard.js` deliberately does not enqueue. The runtime job queue lives in the local Postgres
// (`LM_RUNTIME_DATABASE_URL`, `lib/runtime-job-store.js:46-58`), which a Netlify function has no network
// path to, and exposing `lm_runtime_jobs` through PostgREST would put the queue's write surface on the
// public internet. So a tenant gets its wallets because this sweep noticed its `lm_users` row had no
// wallet columns — which also heals tenants created before this feature shipped and any enqueue that was
// lost, neither of which a synchronous call at signup could do.
//
// Sweeping repeatedly is safe by construction: `job_id` and `effect_key` for zero-start are both
// `zero-start:<uid>`, and `enqueueJob` is ON CONFLICT (job_id) DO NOTHING over a table with
// UNIQUE (tenant_id, effect_key). A tenant therefore has exactly one zero-start job forever, and retries
// happen inside that row's attempts.
//
// Every pass is bounded, and one tenant's failure is contained rather than aborting the rest — the same
// per-tenant isolation `scheduler.js::forEachUserSafe` applies to the user loops.

const { WALLET_COLUMNS, buildZeroStartJob } = require("./zero-start-job-adapter.js");
const { buildWalletInflowJob } = require("./wallet-inflow-job-adapter.js");
const { isSolanaAddress } = require("./agent-wallet-solana.js");
const { enqueueJob } = require("./runtime-job-store.js");

const TENANT_ID = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const EVM_ADDRESS = /^0x[0-9a-fA-F]{40}$/;
// One pass may plan at most this many jobs of each kind. A 10,000-tenant table becomes a steady catch-up
// across passes instead of a single burst that outlives its scheduler lease.
//
// §9.3: this cap is only safe because the two kinds drain differently, and the difference matters.
// Zero-start is SELF-DRAINING — a tenant announced once is never a candidate again — so a uid-ordered cap
// eventually reaches everyone. The inflow watch NEVER drains: `isWatchable` stays true forever, so a
// uid-ordered cap re-served t001..t050 on every pass and tenants past the cap were never watched at all,
// which means their inflows were never recorded. The inflow plan is therefore ordered
// LEAST-RECENTLY-WATCHED, so being unserved is exactly what earns a tenant the next slot.
const MAX_TENANTS_PER_SWEEP = 50;
// Rows per PostgREST request. The read PAGES through all of them: a plain `limit=500` meant tenant 501
// onward was never even read, so no ordering could have saved it.
const TENANT_READ_PAGE = 500;
const MAX_TENANT_ROWS = 10_000;
const DEFAULT_TELEGRAM_TOKEN_REF = "secret://telegram/bot-token";

function text(value) {
  return String(value == null ? "" : value).trim();
}

function usableTenantId(row) {
  const uid = text(row && row.uid);
  return uid && TENANT_ID.test(uid) ? uid : null;
}

// Missing ANY of the five columns the migration added. A row with addresses but no key refs is not
// provisioned: the addresses would be unusable because nothing could resolve their keys.
function needsZeroStart(row) {
  if (!row) return false;
  return WALLET_COLUMNS.some((column) => text(row[column]) === "");
}

// Watchable as soon as EITHER rail exists. A Base address that can already receive money must be watched
// even while the Solana rail is still being provisioned, or a real inflow would go unrecorded.
function isWatchable(row) {
  if (!row) return false;
  return EVM_ADDRESS.test(text(row.agent_wallet_address))
    || isSolanaAddress(text(row.agent_wallet_solana_address));
}

// Never watched sorts before everything: a tenant we have no record of serving is the most starved one
// there is. Ties break on uid so a pass is deterministic and reproducible from its inputs.
function inflowPriority(watchedAt, uid) {
  const at = watchedAt instanceof Map ? watchedAt.get(uid) : null;
  const ms = at == null ? NaN : Date.parse(at);
  return Number.isFinite(ms) ? ms : -Infinity;
}

function planWalletSweep(rows, options = {}) {
  const nowMs = Number(options.nowMs == null ? Date.now() : options.nowMs);
  const watchedAt = options.watchedAt instanceof Map ? options.watchedAt : new Map();
  const telegramTokenRef = text(options.telegramTokenRef) || DEFAULT_TELEGRAM_TOKEN_REF;
  const limit = Number.isSafeInteger(options.limit) && options.limit > 0
    ? Math.min(options.limit, MAX_TENANTS_PER_SWEEP)
    : MAX_TENANTS_PER_SWEEP;

  const zeroStart = [];
  const inflow = [];
  let skipped = 0;
  let truncated = false;
  const watchable = [];

  for (const row of Array.isArray(rows) ? rows : []) {
    const uid = usableTenantId(row);
    if (!uid) {
      // A row we cannot name cannot be provisioned safely; counted so it is visible, never guessed at.
      skipped += 1;
      continue;
    }
    // Zero-start is self-draining, so row order is fair for it.
    if (needsZeroStart(row, options)) {
      if (zeroStart.length >= limit) truncated = true;
      else zeroStart.push(buildZeroStartJob({ tenantId: uid, telegramTokenRef }));
    }
    if (isWatchable(row)) watchable.push(uid);
  }

  // §9.3: the inflow watch never drains, so the cap has to be applied to the HUNGRIEST tenants rather
  // than to whichever uids happen to sort first.
  watchable.sort((left, right) => (
    inflowPriority(watchedAt, left) - inflowPriority(watchedAt, right)
    || left.localeCompare(right)
  ));
  if (watchable.length > limit) truncated = true;
  for (const uid of watchable.slice(0, limit)) {
    inflow.push(buildWalletInflowJob({ tenantId: uid, nowMs }));
  }

  return { zeroStart, inflow, skipped, truncated };
}

function credentials(opts = {}) {
  const supaUrl = opts.supaUrl || process.env.SUPABASE_URL;
  const supaKey = opts.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey) throw new Error("wallet sweep needs Supabase credentials");
  if (typeof fetchImpl !== "function") throw new Error("wallet sweep needs a fetch implementation");
  return { supaUrl, supaKey, fetchImpl };
}

// Reads only the wallet columns. The sweep has no business knowing a tenant's name or phone number.
//
// §9.3: this PAGES. A single `limit=500` meant tenant 501 onward was never read, so no amount of ordering
// downstream could have kept it from starving. Still bounded overall — a runaway table must not be pulled
// through PostgREST without limit — and the bound is reported so it is visible rather than silent.
async function listWalletSweepTenants(opts = {}) {
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);
  const maxRows = Number.isSafeInteger(opts.maxRows) && opts.maxRows > 0
    ? Math.min(opts.maxRows, MAX_TENANT_ROWS)
    : MAX_TENANT_ROWS;
  const select = ["uid", ...WALLET_COLUMNS].join(",");
  const url = `${supaUrl}/rest/v1/lm_users?select=${select}&order=uid.asc`;
  const rows = [];
  for (let start = 0; start < maxRows; start += TENANT_READ_PAGE) {
    const end = Math.min(start + TENANT_READ_PAGE, maxRows) - 1;
    const response = await fetchImpl(url, {
      headers: {
        apikey: supaKey,
        Authorization: `Bearer ${supaKey}`,
        Range: `${start}-${end}`,
        "Range-Unit": "items",
      },
    });
    if (!response || !response.ok) {
      throw new Error(`wallet sweep tenant read failed (${response ? response.status : "no response"})`);
    }
    const page = await response.json();
    if (!Array.isArray(page)) throw new Error("wallet sweep tenant read returned a non-array body");
    rows.push(...page);
    if (page.length < end - start + 1) break;
  }
  return rows;
}

async function sweepWalletJobs(opts = {}) {
  const listTenants = typeof opts.listTenants === "function"
    ? opts.listTenants
    : () => listWalletSweepTenants(opts);
  const enqueue = opts.enqueueJob || ((input) => enqueueJob(input, opts.storeOptions || {}));
  const rows = await listTenants();
  const watchedAt = typeof opts.readInflowWatchedAt === "function"
    ? await opts.readInflowWatchedAt()
    : new Map();
  const plan = planWalletSweep(rows, { ...opts, watchedAt });

  const results = { zero_start: [], inflow: [], failed: [], skipped: plan.skipped, truncated: plan.truncated };
  for (const [key, jobs] of [["zero_start", plan.zeroStart], ["inflow", plan.inflow]]) {
    for (const job of jobs) {
      try {
        const queued = await enqueue({
          jobId: job.job_id,
          tenantId: job.tenant_id,
          loopId: job.loop_id,
          capability: job.capability,
          effectClass: job.effect_class,
          effectKey: job.effect_key,
          inputRefs: job.input_refs,
          maxAttempts: job.max_attempts,
        });
        results[key].push({ uid: job.tenant_id, job_id: job.job_id, created: queued.created === true });
      } catch (error) {
        // Contained, not swallowed: the rest of the sweep continues and the failure is reported so a
        // permanently broken tenant is visible instead of silently never being provisioned.
        results.failed.push({
          uid: job.tenant_id,
          capability: job.capability,
          error: error && error.message ? error.message : String(error),
        });
      }
    }
  }
  return results;
}

module.exports = {
  DEFAULT_TELEGRAM_TOKEN_REF,
  MAX_TENANTS_PER_SWEEP,
  MAX_TENANT_ROWS,
  TENANT_READ_PAGE,
  isWatchable,
  listWalletSweepTenants,
  needsZeroStart,
  planWalletSweep,
  sweepWalletJobs,
};
