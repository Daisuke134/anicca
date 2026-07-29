"use strict";

const { isDeepStrictEqual } = require("node:util");

const EFFECT_CLASSES = new Set(["none", "publish", "message", "money"]);
const REFERENCE_KEY = /_(?:ref|refs)$/;
let defaultPool;

function nonEmpty(value, label, max = 200) {
  const text = String(value == null ? "" : value).trim();
  if (!text || text.length > max) throw new Error(`${label} invalid`);
  return text;
}

function positiveInteger(value, label, max) {
  if (!Number.isInteger(value) || value < 1 || value > max) {
    throw new Error(`${label} invalid`);
  }
  return value;
}

function referenceObject(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("runtime input refs must be reference-only");
  }
  for (const [key, ref] of Object.entries(value)) {
    if (!REFERENCE_KEY.test(key)) {
      throw new Error("runtime input refs must be reference-only");
    }
    const values = Array.isArray(ref) ? ref : [ref];
    if (values.length < 1 || values.some((item) => (
      typeof item !== "string" || !item.trim() || item.length > 1000
    ))) {
      throw new Error("runtime input refs must be reference-only");
    }
  }
  if (Buffer.byteLength(JSON.stringify(value)) > 16_384) {
    throw new Error("runtime input refs too large");
  }
  return JSON.parse(JSON.stringify(value));
}

function database(opts = {}) {
  if (typeof opts.query === "function") return { query: opts.query };
  const connectionString = String(
    opts.connectionString
      || process.env.LM_RUNTIME_DATABASE_URL
      || process.env.LM_FEEDBACK_DATABASE_URL
      || "",
  ).trim();
  if (!connectionString) throw new Error("runtime job store unavailable");
  if (!defaultPool) {
    const Pool = opts.Pool || require("pg").Pool;
    defaultPool = new Pool({ connectionString, max: 8 });
  }
  return { query: defaultPool.query.bind(defaultPool) };
}

function buildRuntimeJob(input) {
  const effectClass = nonEmpty(input && input.effectClass, "runtime effect class", 20);
  if (!EFFECT_CLASSES.has(effectClass)) throw new Error("runtime effect class invalid");
  const suppliedEffectKey = input && input.effectKey;
  const effectKey = suppliedEffectKey == null ? null : String(suppliedEffectKey).trim();
  if (
    (effectClass === "none" && effectKey)
    || (effectClass !== "none" && (!effectKey || effectKey.length > 500))
  ) {
    throw new Error("runtime effect key invalid");
  }

  return Object.freeze({
    job_id: nonEmpty(input && input.jobId, "runtime job id"),
    tenant_id: nonEmpty(input && input.tenantId, "runtime tenant id"),
    loop_id: nonEmpty(input && input.loopId, "runtime loop id"),
    capability: nonEmpty(input && input.capability, "runtime capability"),
    effect_class: effectClass,
    effect_key: effectKey,
    input_refs: referenceObject(input && input.inputRefs),
    max_attempts: positiveInteger(input && input.maxAttempts, "runtime max attempts", 20),
  });
}

function assertSameJob(existing, expected) {
  const fields = [
    "job_id",
    "tenant_id",
    "loop_id",
    "capability",
    "effect_class",
    "effect_key",
    "input_refs",
    "max_attempts",
  ];
  const same = fields.every((field) => isDeepStrictEqual(existing[field], expected[field]));
  if (!same) throw new Error("runtime job id collision");
}

async function enqueueJob(input, opts = {}) {
  const job = buildRuntimeJob(input);
  const { query } = database(opts);
  const inserted = (await query(`
    INSERT INTO public.lm_runtime_jobs (
      job_id, tenant_id, loop_id, capability, effect_class, effect_key, input_refs, max_attempts
    ) VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8)
    ON CONFLICT (job_id) DO NOTHING
    RETURNING *
  `, [
    job.job_id,
    job.tenant_id,
    job.loop_id,
    job.capability,
    job.effect_class,
    job.effect_key,
    JSON.stringify(job.input_refs),
    job.max_attempts,
  ])).rows;
  if (inserted.length === 1) return { created: true, job: inserted[0] };
  if (inserted.length > 1) throw new Error("runtime enqueue returned multiple rows");

  const existing = (await query(`
    SELECT * FROM public.lm_runtime_jobs
    WHERE job_id = $1 AND tenant_id = $2
    LIMIT 1
  `, [job.job_id, job.tenant_id])).rows;
  if (existing.length !== 1) throw new Error("runtime job id collision");
  assertSameJob(existing[0], job);
  return { created: false, job: existing[0] };
}

async function claimJobs(input, opts = {}) {
  const workerId = nonEmpty(input && input.workerId, "runtime worker id");
  const capabilities = input && input.capabilities;
  if (
    !Array.isArray(capabilities)
    || capabilities.length < 1
    || capabilities.length > 50
  ) {
    throw new Error("runtime capabilities invalid");
  }
  const boundedCapabilities = capabilities.map((value) => (
    nonEmpty(value, "runtime capability")
  ));
  const tenantId = input.tenantId == null
    ? null
    : nonEmpty(input.tenantId, "runtime tenant id");
  const limit = positiveInteger(input.limit == null ? 1 : input.limit, "runtime claim limit", 50);
  const leaseSeconds = positiveInteger(
    input.leaseSeconds == null ? 180 : input.leaseSeconds,
    "runtime lease",
    900,
  );
  if (leaseSeconds < 30) throw new Error("runtime lease invalid");
  const { query } = database(opts);
  return (await query(
    "SELECT * FROM public.claim_lm_runtime_jobs($1, $2::text[], $3, $4, $5)",
    [workerId, boundedCapabilities, tenantId, limit, leaseSeconds],
  )).rows;
}

function identity(input, withWorker = true) {
  const value = {
    tenantId: nonEmpty(input && input.tenantId, "runtime tenant id"),
    jobId: nonEmpty(input && input.jobId, "runtime job id"),
    attempt: positiveInteger(input && input.attempt, "runtime attempt", 20),
  };
  if (withWorker) value.workerId = nonEmpty(input && input.workerId, "runtime worker id");
  return value;
}

async function oneRow(query, sql, params, lostMessage) {
  const rows = (await query(sql, params)).rows;
  if (rows.length !== 1) throw new Error(lostMessage);
  return rows[0];
}

async function heartbeatJob(input, opts = {}) {
  const id = identity(input);
  const leaseSeconds = positiveInteger(
    input.leaseSeconds == null ? 180 : input.leaseSeconds,
    "runtime lease",
    900,
  );
  if (leaseSeconds < 30) throw new Error("runtime lease invalid");
  const { query } = database(opts);
  return oneRow(
    query,
    "SELECT * FROM public.heartbeat_lm_runtime_job($1, $2, $3, $4, $5)",
    [id.tenantId, id.jobId, id.attempt, id.workerId, leaseSeconds],
    "runtime heartbeat lost lease",
  );
}

function receiptObject(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("runtime receipt invalid");
  }
  if (Buffer.byteLength(JSON.stringify(value)) > 16_384) {
    throw new Error("runtime receipt too large");
  }
  return value;
}

async function completeJob(input, opts = {}) {
  const id = identity(input);
  const receipt = receiptObject(input.receipt);
  const { query } = database(opts);
  return oneRow(
    query,
    "SELECT * FROM public.complete_lm_runtime_job($1, $2, $3, $4, $5::jsonb)",
    [id.tenantId, id.jobId, id.attempt, id.workerId, JSON.stringify(receipt)],
    "runtime completion lost lease",
  );
}

async function failJob(input, opts = {}) {
  const id = identity(input);
  const errorCode = nonEmpty(input && input.errorCode, "runtime error code");
  const unknownEffect = input.unknownEffect === true;
  const { query } = database(opts);
  return oneRow(
    query,
    "SELECT * FROM public.fail_lm_runtime_job($1, $2, $3, $4, $5, $6)",
    [id.tenantId, id.jobId, id.attempt, id.workerId, errorCode, unknownEffect],
    "runtime failure lost lease",
  );
}

async function resolveReconciliation(input, opts = {}) {
  const id = identity(input, false);
  if (!["present", "absent"].includes(input.decision)) {
    throw new Error("runtime reconciliation decision invalid");
  }
  const receipt = receiptObject(input.receipt);
  const { query } = database(opts);
  return oneRow(
    query,
    "SELECT * FROM public.resolve_lm_runtime_effect($1, $2, $3, $4, $5::jsonb)",
    [id.tenantId, id.jobId, id.attempt, input.decision, JSON.stringify(receipt)],
    "runtime reconciliation lost job",
  );
}

async function closeRuntimeJobStore() {
  const pool = defaultPool;
  defaultPool = undefined;
  if (pool) await pool.end();
}

module.exports = {
  buildRuntimeJob,
  enqueueJob,
  claimJobs,
  heartbeatJob,
  completeJob,
  failJob,
  resolveReconciliation,
  closeRuntimeJobStore,
};
