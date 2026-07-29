"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildMarketingObservationJob,
  createMarketingObservationLoopAdapter,
  normalizePostizMetrics,
  safeMarketingObservationSummary,
  verifyMarketingObservationReceipt,
} = require("./marketing-observation-adapter.js");

const PUBLICATION_JOB_ID = `marketing-daily:${"a".repeat(64)}`;
const PUBLICATION = Object.freeze({
  schema_version: 1,
  kind: "marketing_daily_distribution",
  status: "published",
  creative_id: "B01",
  platform: "tiktok",
  video_sha256: "b".repeat(64),
  caption_sha256: "c".repeat(64),
  public_url: "https://www.tiktok.com/@life_manager/video/7999999999999999999",
  provider_post_id: "postiz-post-B01",
  provider_route: "postiz",
  provider_reconciled: false,
  published_at: "2026-07-29T12:00:00.000Z",
});

function unavailable(reason = "source_unavailable") {
  return { status: "unavailable", value: null, reason };
}

function job(window = "2h") {
  return buildMarketingObservationJob({
    tenantId: "tenant-a",
    productId: "life-manager",
    publicationJobId: PUBLICATION_JOB_ID,
    window,
  });
}

test("observation job is deterministic, reference-only, and independently windowed", () => {
  const value = job("24h");

  assert.equal(value.loop_id, "marketing.observation");
  assert.equal(value.capability, "marketing.observation.collect");
  assert.equal(value.effect_class, "none");
  assert.equal(value.effect_key, null);
  assert.deepEqual(value.input_refs, {
    product_ref: "product://life-manager",
    publication_receipt_ref: `runtime-receipt://${PUBLICATION_JOB_ID}`,
    observation_window_ref: "metric-window://24h",
  });
  assert.equal(job("24h").job_id, value.job_id);
  assert.notEqual(job("2h").job_id, value.job_id);
  assert.doesNotMatch(JSON.stringify(value), /password|api[_-]?key|token/i);
});

test("each publication can become scorable without requiring an IG/TikTok pair", async () => {
  const adapter = createMarketingObservationLoopAdapter({
    receiptProvider: {
      async get(tenantId, ref) {
        assert.equal(tenantId, "tenant-a");
        assert.equal(ref, `runtime-receipt://${PUBLICATION_JOB_ID}`);
        return PUBLICATION;
      },
    },
    platformMetricProvider: {
      async collect(input) {
        assert.equal(input.publication.public_url, PUBLICATION.public_url);
        return {
          views: { status: "measured", value: 0, source: "postiz" },
          likes: { status: "measured", value: 0, source: "postiz" },
          comments: unavailable("metric_not_returned"),
          shares: unavailable("metric_not_returned"),
        };
      },
    },
    productMetricProvider: {
      async collect() {
        return {
          installs: unavailable("attribution_not_configured"),
          activations: unavailable("attribution_not_configured"),
          trials: unavailable("attribution_not_configured"),
          paid: unavailable("attribution_not_configured"),
          proceeds_minor: unavailable("attribution_not_configured"),
        };
      },
    },
    now: () => "2026-07-29T14:01:00.000Z",
  });

  const execution = await adapter.execute(job());
  assert.equal(execution.receipt.status, "scorable");
  assert.equal(execution.receipt.reward.deepest_metric, "likes");
  assert.equal(execution.receipt.reward.effect, "eligible");
  assert.equal(execution.receipt.metrics.platform.views.value, 0);
  assert.equal(execution.receipt.metrics.product.installs.value, null);
  assert.equal(verifyMarketingObservationReceipt(execution.receipt), true);
  assert.equal(adapter.verify(execution.receipt), true);
  assert.deepEqual(adapter.report(execution.receipt), {
    status: "scorable",
    product_id: "life-manager",
    creative_id: "B01",
    platform: "tiktok",
    public_url: PUBLICATION.public_url,
    window: "2h",
    deepest_metric: "likes",
    reward_effect: "eligible",
    observed_at: "2026-07-29T14:01:00.000Z",
  });
});

test("empty provider responses become insufficient nulls, never synthetic zero", async () => {
  const normalized = normalizePostizMetrics([]);
  assert.deepEqual(normalized, {
    views: unavailable("metric_not_returned"),
    likes: unavailable("metric_not_returned"),
    comments: unavailable("metric_not_returned"),
    shares: unavailable("metric_not_returned"),
  });

  const adapter = createMarketingObservationLoopAdapter({
    receiptProvider: { get: async () => PUBLICATION },
    platformMetricProvider: { collect: async () => normalized },
    productMetricProvider: {
      collect: async () => ({
        installs: unavailable("source_delayed"),
        activations: unavailable("source_delayed"),
        trials: unavailable("source_delayed"),
        paid: unavailable("source_delayed"),
        proceeds_minor: unavailable("source_delayed"),
      }),
    },
    now: () => "2026-07-30T12:01:00.000Z",
  });

  const execution = await adapter.execute(job("24h"));
  assert.equal(execution.receipt.status, "insufficient");
  assert.equal(execution.receipt.reward.deepest_metric, null);
  assert.equal(execution.receipt.reward.effect, "no_change");
  assert.equal(execution.receipt.metrics.platform.views.value, null);
  assert.equal(verifyMarketingObservationReceipt(execution.receipt), true);
});

test("Postiz response normalization preserves measured zero and rejects malformed totals", () => {
  assert.deepEqual(normalizePostizMetrics([
    { label: "Views", data: [{ total: "0", date: "2026-07-29" }] },
    { label: "Likes", data: [{ total: "3", date: "2026-07-29" }] },
  ]), {
    views: { status: "measured", value: 0, source: "postiz" },
    likes: { status: "measured", value: 3, source: "postiz" },
    comments: unavailable("metric_not_returned"),
    shares: unavailable("metric_not_returned"),
  });
  assert.throws(
    () => normalizePostizMetrics([
      { label: "Views", data: [{ total: "-1", date: "2026-07-29" }] },
    ]),
    /Postiz metric/i,
  );
});

test("scope mismatch, early observation, and malformed metric envelopes fail closed", async () => {
  const base = {
    receiptProvider: { get: async () => PUBLICATION },
    platformMetricProvider: {
      collect: async () => ({
        views: unavailable(),
        likes: unavailable(),
        comments: unavailable(),
        shares: unavailable(),
      }),
    },
    productMetricProvider: {
      collect: async () => ({
        installs: unavailable(),
        activations: unavailable(),
        trials: unavailable(),
        paid: unavailable(),
        proceeds_minor: unavailable(),
      }),
    },
  };
  await assert.rejects(
    createMarketingObservationLoopAdapter({
      ...base,
      now: () => "2026-07-29T13:59:59.000Z",
    }).execute(job()),
    /window is not due/i,
  );
  await assert.rejects(
    createMarketingObservationLoopAdapter({
      ...base,
      platformMetricProvider: {
        collect: async () => ({
          views: { status: "measured", value: -1, source: "postiz" },
          likes: unavailable(),
          comments: unavailable(),
          shares: unavailable(),
        }),
      },
      now: () => "2026-07-29T14:01:00.000Z",
    }).execute(job()),
    /metric envelope/i,
  );
  const wrongProductJob = {
    ...job(),
    input_refs: {
      ...job().input_refs,
      product_ref: "product://another",
    },
  };
  await assert.rejects(
    createMarketingObservationLoopAdapter({
      ...base,
      now: () => "2026-07-29T14:01:00.000Z",
    }).execute(wrongProductJob),
    /job contract/i,
  );
});

test("safe summary rejects a forged receipt", () => {
  assert.throws(
    () => safeMarketingObservationSummary({
      kind: "marketing_attribution_observation",
      status: "scorable",
    }),
    /verification failed/i,
  );
});
