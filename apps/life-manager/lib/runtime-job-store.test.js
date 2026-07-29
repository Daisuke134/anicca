"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {
  buildRuntimeJob,
  enqueueJob,
  claimJobs,
  heartbeatJob,
  completeJob,
  failJob,
  resolveReconciliation,
} = require("./runtime-job-store.js");

const MIGRATION = fs.readFileSync(path.join(
  __dirname,
  "../migrations/20260729_runtime_jobs.sql",
), "utf8");

function sampleJob(overrides = {}) {
  return {
    jobId: "job-001",
    tenantId: "tenant-a",
    loopId: "marketing.an icca.slideshow",
    capability: "content.publish",
    effectClass: "publish",
    effectKey: "tiktok:anicca:asset-001",
    inputRefs: {
      product_ref: "product:anicca",
      asset_ref: "object:sha256:abc",
    },
    maxAttempts: 3,
    ...overrides,
  };
}

test("runtime job is tenant-bound, reference-only, bounded, and immutable", () => {
  const job = buildRuntimeJob(sampleJob());
  assert.equal(job.job_id, "job-001");
  assert.equal(job.tenant_id, "tenant-a");
  assert.equal(job.effect_class, "publish");
  assert.equal(job.max_attempts, 3);
  assert.deepEqual(job.input_refs, {
    product_ref: "product:anicca",
    asset_ref: "object:sha256:abc",
  });
  assert.equal(Object.isFrozen(job), true);

  assert.throws(() => buildRuntimeJob(sampleJob({
    inputRefs: { password: "do-not-store-secrets" },
  })), /reference-only/i);
  assert.throws(() => buildRuntimeJob(sampleJob({
    effectClass: "money",
    effectKey: "",
  })), /effect key/i);
  assert.throws(() => buildRuntimeJob(sampleJob({ maxAttempts: 0 })), /max attempts/i);
});

test("enqueue is idempotent by job id and rejects a cross-tenant collision", async () => {
  const calls = [];
  const existing = {
    job_id: "job-001",
    tenant_id: "tenant-a",
    loop_id: "marketing.anicca.slideshow",
    capability: "content.publish",
    effect_class: "publish",
    effect_key: "tiktok:anicca:asset-001",
    input_refs: sampleJob().inputRefs,
    max_attempts: 3,
    status: "queued",
  };
  const query = async (sql, params) => {
    calls.push({ sql, params });
    if (/INSERT INTO public\.lm_runtime_jobs/i.test(sql)) return { rows: [] };
    return { rows: [existing] };
  };

  const result = await enqueueJob(sampleJob({
    loopId: "marketing.anicca.slideshow",
  }), { query });
  assert.deepEqual(result, { created: false, job: existing });
  assert.match(calls[0].sql, /ON CONFLICT \(job_id\) DO NOTHING/i);
  assert.match(calls[1].sql, /WHERE job_id = \$1 AND tenant_id = \$2/i);
  assert.equal(calls[1].params[1], "tenant-a");

  await assert.rejects(
    enqueueJob(sampleJob(), {
      query: async (sql) => (/INSERT/i.test(sql) ? { rows: [] } : { rows: [] }),
    }),
    /collision/i,
  );
});

test("claim filters capabilities, has a bounded lease, and uses one narrow atomic RPC", async () => {
  const calls = [];
  const rows = [{ job_id: "job-001", tenant_id: "tenant-a", attempt: 1 }];
  const query = async (sql, params) => {
    calls.push({ sql, params });
    return { rows };
  };
  const claimed = await claimJobs({
    workerId: "worker-publish-1",
    capabilities: ["content.publish", "content.render"],
    tenantId: "tenant-a",
    limit: 2,
    leaseSeconds: 180,
  }, { query });

  assert.deepEqual(claimed, rows);
  assert.match(calls[0].sql, /claim_lm_runtime_jobs\(\$1, \$2::text\[\], \$3, \$4, \$5\)/i);
  assert.deepEqual(calls[0].params, [
    "worker-publish-1",
    ["content.publish", "content.render"],
    "tenant-a",
    2,
    180,
  ]);
});

test("heartbeat, completion, failure, and reconciliation are tenant and attempt scoped", async () => {
  const calls = [];
  const query = async (sql, params) => {
    calls.push({ sql, params });
    return { rows: [{ job_id: "job-001", tenant_id: "tenant-a", attempt: 1 }] };
  };
  const identity = {
    tenantId: "tenant-a",
    jobId: "job-001",
    attempt: 1,
    workerId: "worker-publish-1",
  };

  await heartbeatJob({ ...identity, leaseSeconds: 180 }, { query });
  await completeJob({
    ...identity,
    receipt: { provider_id: "post-123", url: "https://example.com/post/123" },
  }, { query });
  await failJob({ ...identity, errorCode: "TIMEOUT", unknownEffect: true }, { query });
  await resolveReconciliation({
    tenantId: "tenant-a",
    jobId: "job-001",
    attempt: 1,
    decision: "absent",
    receipt: { lookup: "not_found" },
  }, { query });

  for (const call of calls) {
    assert.equal(call.params[0], "tenant-a");
    assert.equal(call.params[1], "job-001");
    assert.equal(call.params[2], 1);
  }
  assert.match(calls[0].sql, /heartbeat_lm_runtime_job/i);
  assert.match(calls[1].sql, /complete_lm_runtime_job/i);
  assert.match(calls[2].sql, /fail_lm_runtime_job/i);
  assert.equal(calls[2].params[5], true);
  assert.match(calls[3].sql, /resolve_lm_runtime_effect/i);
  assert.equal(calls[3].params[3], "absent");
});

test("migration enforces atomic claim, bounded retry, unique effects, and immutable receipts", () => {
  assert.match(MIGRATION, /CREATE TABLE IF NOT EXISTS public\.lm_runtime_jobs/i);
  assert.match(MIGRATION, /CREATE TABLE IF NOT EXISTS public\.lm_runtime_job_receipts/i);
  assert.match(MIGRATION, /PRIMARY KEY \(job_id, attempt\)/i);
  assert.match(MIGRATION, /UNIQUE \(tenant_id, effect_key\)/i);
  assert.match(MIGRATION, /FOR UPDATE SKIP LOCKED/i);
  assert.match(MIGRATION, /UPDATE public\.lm_runtime_jobs[\s\S]*RETURNING/i);
  assert.match(MIGRATION, /attempt < max_attempts/i);
  assert.match(MIGRATION, /dead_letter/i);
  assert.match(MIGRATION, /status = 'reconciling'/i);
  assert.match(MIGRATION, /OLD TABLE|immutable/i);
  assert.doesNotMatch(MIGRATION, /advisory_(?:lock|xact_lock)/i);
});
