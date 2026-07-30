"use strict";
// AE-ZERO-START-1 §11 / §12.3 NEW-4 — the three facts the sweep reads out of the runtime's own receipts.
//
// These were inline SQL inside `scripts/runtime-up.js`, which meant the sweep's most important decisions —
// who has been told, who is next in line, which row may be re-activated — were unreachable from a test. The
// §12.2 sweep drain invariant has to exercise the REAL ordering, so it lives here instead.
//
// §12.3 NEW-4 is a one-clause change with a large consequence: the ordering key advances on ATTEMPT, not on
// success. Ordering by successes only, combined with "never served sorts first", makes a permanently failing
// tenant permanently the most starved — so it holds the front of the queue forever and starves every healthy
// tenant instead. That is §9.3's starvation with the victims swapped.

const ANNOUNCED_TENANTS_SQL = `
  SELECT DISTINCT r.tenant_id
  FROM public.lm_runtime_job_receipts r
  JOIN public.lm_runtime_jobs j
    ON j.job_id = r.job_id
    AND j.tenant_id = r.tenant_id
  WHERE j.capability = $1
    AND r.outcome = 'completed'
    AND r.receipt->>'kind' = 'tenant_zero_start'
    AND r.receipt->>'status' = 'started'
`;

// Deliberately NOT filtered on outcome: every attempt counts, successful or not. See NEW-4 above.
const INFLOW_ATTEMPTED_AT_SQL = `
  SELECT j.tenant_id, max(r.created_at) AS attempted_at
  FROM public.lm_runtime_job_receipts r
  JOIN public.lm_runtime_jobs j
    ON j.job_id = r.job_id
    AND j.tenant_id = r.tenant_id
  WHERE j.capability = $1
  GROUP BY j.tenant_id
`;

const ZERO_START_ROW_SQL = `
  SELECT status, attempt, max_attempts
  FROM public.lm_runtime_jobs
  WHERE tenant_id = $1 AND job_id = $2
`;

// §11.3 — the only reap PostgreSQL permits. Measured: a generation-suffixed job_id violates
// UNIQUE (tenant_id, effect_key); DELETE violates the receipts foreign key and then the receipts
// immutability trigger; resetting `attempt` collides with the receipt primary key (job_id, attempt). So the
// row goes back to 'queued' with `attempt` UNTOUCHED, which the next claim increments — every receipt row
// survives as audit evidence.
const REACTIVATE_ZERO_START_SQL = `
  UPDATE public.lm_runtime_jobs
  SET status = 'queued',
      completed_at = NULL,
      lease_owner = NULL,
      lease_expires_at = NULL,
      available_at = clock_timestamp(),
      updated_at = clock_timestamp()
  WHERE tenant_id = $1
    AND job_id = $2
    AND status IN ('completed', 'dead_letter')
    AND attempt < max_attempts
  RETURNING job_id
`;

const TERMINAL_STATUSES = Object.freeze(["completed", "dead_letter"]);

function isoString(value) {
  if (value instanceof Date) return value.toISOString();
  const text = String(value == null ? "" : value).trim();
  if (!text) return null;
  const ms = Date.parse(text);
  return Number.isFinite(ms) ? new Date(ms).toISOString() : null;
}

function requiredQuery(query) {
  if (typeof query !== "function") throw new Error("wallet sweep receipt reader needs a query function");
  return query;
}

function createWalletSweepReceiptReaders({ query, zeroStartCapability, inflowCapability }) {
  const run = requiredQuery(query);
  const zeroStart = String(zeroStartCapability || "").trim();
  const inflow = String(inflowCapability || "").trim();
  if (!zeroStart || !inflow) throw new Error("wallet sweep receipt reader needs both capability names");

  return {
    // §11.5 — the signal for "needs a zero-start" is a completed ANNOUNCEMENT, not the wallet columns.
    async readAnnouncedTenants() {
      const result = await run(ANNOUNCED_TENANTS_SQL, [zeroStart]);
      return new Set((result.rows || []).map((row) => row.tenant_id));
    },

    // §12.3 NEW-4 — least-recently-ATTEMPTED. A tenant we tried and failed is not more starved than one we
    // have not tried at all, so failing cannot buy a permanent place at the front.
    async readInflowWatchedAt() {
      const result = await run(INFLOW_ATTEMPTED_AT_SQL, [inflow]);
      const ordering = new Map();
      for (const row of result.rows || []) {
        const at = isoString(row.attempted_at);
        if (row.tenant_id && at) ordering.set(row.tenant_id, at);
      }
      return ordering;
    },

    async reapZeroStartJob({ tenantId }) {
      const jobId = `zero-start:${tenantId}`;
      const current = await run(ZERO_START_ROW_SQL, [tenantId, jobId]);
      const rows = current.rows || [];
      if (rows.length !== 1) return { reaped: false, reason: "absent" };
      const row = rows[0];
      if (!TERMINAL_STATUSES.includes(row.status)) return { reaped: false, reason: "active" };
      if (Number(row.attempt) >= Number(row.max_attempts)) return { reaped: false, reason: "exhausted" };
      const reactivated = await run(REACTIVATE_ZERO_START_SQL, [tenantId, jobId]);
      return (reactivated.rows || []).length === 1
        ? { reaped: true, reason: "reactivated" }
        : { reaped: false, reason: "race" };
    },
  };
}

module.exports = {
  ANNOUNCED_TENANTS_SQL,
  INFLOW_ATTEMPTED_AT_SQL,
  REACTIVATE_ZERO_START_SQL,
  TERMINAL_STATUSES,
  ZERO_START_ROW_SQL,
  createWalletSweepReceiptReaders,
};
