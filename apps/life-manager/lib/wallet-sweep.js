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
const MAX_TENANTS_PER_SWEEP = 50;
const TENANT_READ_LIMIT = 500;
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

function planWalletSweep(rows, options = {}) {
  const nowMs = Number(options.nowMs == null ? Date.now() : options.nowMs);
  const telegramTokenRef = text(options.telegramTokenRef) || DEFAULT_TELEGRAM_TOKEN_REF;
  const limit = Number.isSafeInteger(options.limit) && options.limit > 0
    ? Math.min(options.limit, MAX_TENANTS_PER_SWEEP)
    : MAX_TENANTS_PER_SWEEP;

  const zeroStart = [];
  const inflow = [];
  let skipped = 0;
  let truncated = false;

  for (const row of Array.isArray(rows) ? rows : []) {
    const uid = usableTenantId(row);
    if (!uid) {
      // A row we cannot name cannot be provisioned safely; counted so it is visible, never guessed at.
      skipped += 1;
      continue;
    }
    if (needsZeroStart(row)) {
      if (zeroStart.length >= limit) {
        truncated = true;
      } else {
        zeroStart.push(buildZeroStartJob({ tenantId: uid, telegramTokenRef }));
      }
    }
    if (isWatchable(row)) {
      if (inflow.length >= limit) {
        truncated = true;
      } else {
        inflow.push(buildWalletInflowJob({ tenantId: uid, nowMs }));
      }
    }
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
async function listWalletSweepTenants(opts = {}) {
  const { supaUrl, supaKey, fetchImpl } = credentials(opts);
  const limit = Number.isSafeInteger(opts.readLimit) && opts.readLimit > 0
    ? Math.min(opts.readLimit, TENANT_READ_LIMIT)
    : TENANT_READ_LIMIT;
  const select = ["uid", ...WALLET_COLUMNS].join(",");
  const url = `${supaUrl}/rest/v1/lm_users?select=${select}&order=uid.asc&limit=${limit}`;
  const response = await fetchImpl(url, {
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}` },
  });
  if (!response || !response.ok) {
    throw new Error(`wallet sweep tenant read failed (${response ? response.status : "no response"})`);
  }
  const rows = await response.json();
  if (!Array.isArray(rows)) throw new Error("wallet sweep tenant read returned a non-array body");
  return rows;
}

async function sweepWalletJobs(opts = {}) {
  const listTenants = typeof opts.listTenants === "function"
    ? opts.listTenants
    : () => listWalletSweepTenants(opts);
  const enqueue = opts.enqueueJob || ((input) => enqueueJob(input, opts.storeOptions || {}));
  const rows = await listTenants();
  const plan = planWalletSweep(rows, opts);

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
  TENANT_READ_LIMIT,
  isWatchable,
  listWalletSweepTenants,
  needsZeroStart,
  planWalletSweep,
  sweepWalletJobs,
};
