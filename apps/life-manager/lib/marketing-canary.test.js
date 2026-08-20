"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  PROMOTION_CONFIRMATION,
  SHADOW_HOLD_AVAILABLE_AT,
  buildHonneEnCanaryTelegramJob,
  claimExactCanaryJob,
  promoteHonneEnTikTokCanary,
  verifyDirectPublicUrl,
} = require("./marketing-canary.js");

const URL = "https://www.tiktok.com/@honne_reveal/video/7999999999999999999";
const HASH = "a".repeat(64);

function receipt(overrides = {}) {
  return {
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
    video_sha256: HASH,
    caption_sha256: HASH,
    public_url: URL,
    provider_post_id: "postiz-7999999999999999999",
    provider_route: "postiz",
    provider_reconciled: true,
    published_at: "2026-08-21T02:01:00.000Z",
    ...overrides,
  };
}

test("promotion is exact, one-job, and rejects a second promotion", async () => {
  const calls = [];
  let eligible = true;
  const query = async (sql, params) => {
    calls.push({ sql, params });
    if (sql.includes("SELECT")) {
      return { rows: eligible ? [{ job_id: "canary-job" }] : [] };
    }
    eligible = false;
    return { rows: [{ job_id: "canary-job", available_at: "now" }] };
  };
  const promoted = await promoteHonneEnTikTokCanary({
    query,
    tenantId: "dais-local",
    jobId: "canary-job",
    confirmation: PROMOTION_CONFIRMATION,
  });
  assert.equal(promoted.job_id, "canary-job");
  assert.equal(calls.length, 2);
  assert.equal(calls[0].params[2], SHADOW_HOLD_AVAILABLE_AT);
  await assert.rejects(
    promoteHonneEnTikTokCanary({
      query,
      tenantId: "dais-local",
      jobId: "canary-job",
      confirmation: PROMOTION_CONFIRMATION,
    }),
    /eligible shadow TikTok/i,
  );
});

test("Telegram receipt job contains the reconciled direct TikTok URL", () => {
  const job = buildHonneEnCanaryTelegramJob({ tenantId: "dais-local", receipt: receipt() });
  assert.equal(job.capability, "marketing.liveness.telegram");
  assert.match(job.input_refs.marketing_liveness_ref, /7999999999999999999/);
  assert.equal(job.effect_class, "message");
});

test("Telegram receipt job refuses an unavailable or unreconciled publication", () => {
  assert.throws(
    () => buildHonneEnCanaryTelegramJob({ tenantId: "dais-local", receipt: receipt({ provider_reconciled: false }) }),
    /not reconciled/i,
  );
  assert.throws(
    () => buildHonneEnCanaryTelegramJob({ tenantId: "dais-local", receipt: receipt({ public_url: "unavailable" }) }),
    /not reconciled/i,
  );
});

test("exact canary claim updates only the selected eligible job", async () => {
  let sql = "";
  let params;
  const job = await claimExactCanaryJob({
    tenantId: "dais-local",
    jobId: "canary-job",
    capability: "marketing.video.publish",
    workerId: "canary-worker",
    query: async (text, values) => {
      sql = text;
      params = values;
      return { rows: [{ job_id: "canary-job", status: "running", attempt: 1 }] };
    },
  });
  assert.equal(job.status, "running");
  assert.match(sql, /WHERE tenant_id = \$1/);
  assert.match(sql, /AND job_id = \$2/);
  assert.deepEqual(params.slice(0, 4), ["dais-local", "canary-job", "marketing.video.publish", "canary-worker"]);
});

test("direct URL verifier rejects non-public responses and accepts a public response", async () => {
  await assert.rejects(
    verifyDirectPublicUrl(URL, async () => ({ status: 403 })),
    /publicly reachable/i,
  );
  await assert.rejects(
    verifyDirectPublicUrl(URL, async () => ({ status: 302 })),
    /publicly reachable/i,
  );
  const result = await verifyDirectPublicUrl(URL, async () => ({ status: 200 }));
  assert.equal(result.status, 200);
  assert.equal(result.url, URL);
});
