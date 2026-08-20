"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  PROMOTION_CONFIRMATION,
  buildHonneEnCanaryTelegramJob,
} = require("../lib/marketing-canary.js");
const { parseArgs, runHonneEnCanary } = require("./honne-en-canary.js");

const RECEIPT = {
  schema_version: 1,
  kind: "marketing_video_distribution",
  status: "published",
  product_id: "honne-ai",
  format_id: "reelclaw",
  form: "relationship-confession",
  locale: "en",
  slot: "2026-08-21T02:00:00.000Z",
  creative_id: "HEN-001-aaaaaaaaaaaa",
  platform: "tiktok",
  video_sha256: "a".repeat(64),
  caption_sha256: "b".repeat(64),
  public_url: "https://www.tiktok.com/@honne_reveal/video/7999999999999999999",
  provider_post_id: "postiz-7999999999999999999",
  provider_route: "postiz",
  provider_reconciled: true,
  published_at: "2026-08-21T02:01:00.000Z",
};
const TELEGRAM_RECEIPT = {
  schema_version: 1,
  kind: "telegram_marketing_liveness",
  lane: "honne-en-canary",
  product: "honne-ai",
  locale: "en",
  platform: "tiktok",
  slot: RECEIPT.slot,
  status: "published",
  public_url: RECEIPT.public_url,
  retry_state: "not_required",
  message_id: 42,
  chat_id_hash: "d".repeat(64),
  sent_at: "2026-08-21T02:02:00.000Z",
};

test("canary args require exactly one tenant and publication job", () => {
  assert.deepEqual(
    parseArgs(["run", "--tenant", "dais-local", "--job-id", "publication-job"]),
    { tenant: "dais-local", jobId: "publication-job" },
  );
  assert.throws(() => parseArgs(["run", "--tenant", "dais-local"]), /--job-id/i);
});

test("controlled canary promotes one job, publishes one receipt, sends one URL receipt, and replays idempotently", async () => {
  const calls = [];
  let claimCount = 0;
  const handlers = {};
  const query = async (sql, params) => {
    calls.push({ sql, params });
    if (sql.includes("SELECT job_id, tenant_id, capability")) return { rows: [{ job_id: "publication-job" }] };
    if (sql.includes("UPDATE public.lm_runtime_jobs")) return { rows: [{ job_id: "publication-job" }] };
    if (sql.includes("SELECT r.receipt")) {
      return { rows: [{ receipt: params[1] === "publication-job" ? RECEIPT : TELEGRAM_RECEIPT }] };
    }
    throw new Error(`unexpected SQL: ${sql}`);
  };
  const claimJobs = async ({ capabilities }) => {
    claimCount += 1;
    return [{
      job_id: capabilities[0] === "marketing.video.publish"
        ? "publication-job"
        : enqueueCalls[0].jobId,
      tenant_id: "dais-local",
      attempt: 1,
      capability: capabilities[0],
      effect_class: capabilities[0] === "marketing.video.publish" ? "publish" : "message",
      input_refs: {},
    }];
  };
  const enqueueCalls = [];
  const enqueueJob = async (job) => {
    enqueueCalls.push(job);
    return { created: job.capability === "marketing.liveness.telegram" && enqueueCalls.length === 2, job };
  };
  let executionCount = 0;
  const result = await runHonneEnCanary(
    ["run", "--tenant", "dais-local", "--job-id", "publication-job"],
    {
      env: {
        LM_HONNE_EN_CANARY_CONFIRM: PROMOTION_CONFIRMATION,
        LM_RUNTIME_TENANT_ID: "dais-local",
      },
      query,
      handlers,
      livenessHandlers: {},
      claimExactCanaryJob: async ({ jobId, capability }) => {
        claimCount += 1;
        return {
        job_id: jobId,
        tenant_id: "dais-local",
        attempt: 1,
        loop_id: capability,
        capability,
        effect_class: capability === "marketing.video.publish" ? "publish" : "message",
        effect_key: `effect:${jobId}`,
        input_refs: {},
        max_attempts: 3,
        };
      },
      enqueueJob,
      verifyDirectPublicUrl: async (url) => ({ status: 200, url }),
      executeCapabilityJob: async () => { executionCount += 1; },
    },
  );
  assert.equal(claimCount, 2);
  assert.equal(executionCount, 2);
  assert.equal(result.publication.public_url, RECEIPT.public_url);
  assert.equal(result.publication.provider_reconciled, true);
  assert.equal(result.telegram.created, true);
  assert.equal(result.telegram.message_id, 42);
  assert.equal(result.telegram.replay_created, false);
  assert.equal(enqueueCalls.length, 3);
  assert.ok(calls.some(({ sql }) => sql.includes("platform_ref' = 'platform://tiktok'")));
});
