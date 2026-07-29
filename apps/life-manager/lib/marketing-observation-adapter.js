"use strict";

const crypto = require("node:crypto");

const { buildRuntimeJob } = require("./runtime-job-store.js");
const {
  verifyMarketingDailyReceipt,
} = require("./marketing-daily-adapter.js");

const LOOP_ID = "marketing.observation";
const CAPABILITY = "marketing.observation.collect";
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const PUBLICATION_JOB_ID = /^marketing-daily:[0-9a-f]{64}$/;
const PUBLICATION_REF = /^runtime-receipt:\/\/(marketing-daily:[0-9a-f]{64})$/;
const PRODUCT_REF = /^product:\/\/([A-Za-z0-9][A-Za-z0-9._-]{0,127})$/;
const WINDOW_REF = /^metric-window:\/\/(2h|24h|72h|7d)$/;
const WINDOWS = Object.freeze({
  "2h": 2 * 60 * 60 * 1000,
  "24h": 24 * 60 * 60 * 1000,
  "72h": 72 * 60 * 60 * 1000,
  "7d": 7 * 24 * 60 * 60 * 1000,
});
const PLATFORM_METRICS = Object.freeze([
  "views",
  "likes",
  "comments",
  "shares",
]);
const PRODUCT_METRICS = Object.freeze([
  "installs",
  "activations",
  "trials",
  "paid",
  "proceeds_minor",
]);
const REWARD_ORDER = Object.freeze([
  "views",
  "likes",
  "comments",
  "shares",
  "installs",
  "activations",
  "trials",
  "paid",
  "proceeds_minor",
]);
const UNAVAILABLE_REASONS = new Set([
  "source_unavailable",
  "source_delayed",
  "metric_not_returned",
  "metric_not_supported",
  "attribution_not_configured",
  "attribution_unavailable",
]);
const RECEIPT_KEYS = new Set([
  "schema_version",
  "kind",
  "status",
  "product_id",
  "publication_job_id",
  "creative_id",
  "platform",
  "public_url",
  "provider_post_id",
  "provider_route",
  "video_sha256",
  "caption_sha256",
  "window",
  "opened_at",
  "due_at",
  "observed_at",
  "metrics",
  "reward",
]);

function required(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function identifier(value, label) {
  const text = required(value, label);
  if (!IDENTIFIER.test(text)) throw new Error(`${label} is invalid`);
  return text;
}

function exactWindow(value) {
  const text = required(value, "marketing observation window");
  if (!Object.hasOwn(WINDOWS, text)) {
    throw new Error("marketing observation window is invalid");
  }
  return text;
}

function exactInstant(value, label) {
  const text = required(value, label);
  const milliseconds = Date.parse(text);
  if (!Number.isFinite(milliseconds)) throw new Error(`${label} is invalid`);
  return { text, milliseconds };
}

function buildMarketingObservationJob(input = {}) {
  const tenantId = identifier(input.tenantId, "marketing observation tenant");
  const productId = identifier(input.productId, "marketing observation product");
  const publicationJobId = required(
    input.publicationJobId,
    "marketing publication job",
  );
  if (!PUBLICATION_JOB_ID.test(publicationJobId)) {
    throw new Error("marketing publication job is invalid");
  }
  const window = exactWindow(input.window);
  const inputRefs = {
    product_ref: `product://${productId}`,
    publication_receipt_ref: `runtime-receipt://${publicationJobId}`,
    observation_window_ref: `metric-window://${window}`,
  };
  const digest = crypto.createHash("sha256")
    .update(JSON.stringify({ tenant_id: tenantId, input_refs: inputRefs }))
    .digest("hex");
  return buildRuntimeJob({
    jobId: `marketing-observation:${digest}`,
    tenantId,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "none",
    effectKey: null,
    inputRefs,
    maxAttempts: 3,
  });
}

function normalizeJob(job) {
  const refs = job && job.input_refs;
  if (
    !refs
    || typeof refs !== "object"
    || Array.isArray(refs)
    || JSON.stringify(Object.keys(refs).sort()) !== JSON.stringify([
      "observation_window_ref",
      "product_ref",
      "publication_receipt_ref",
    ])
  ) {
    throw new Error("marketing observation job contract is invalid");
  }
  const product = PRODUCT_REF.exec(String(refs.product_ref || ""));
  const publication = PUBLICATION_REF.exec(
    String(refs.publication_receipt_ref || ""),
  );
  const window = WINDOW_REF.exec(String(refs.observation_window_ref || ""));
  if (!product || !publication || !window) {
    throw new Error("marketing observation job contract is invalid");
  }
  const tenantId = String(job.tenant_id || "");
  const expected = buildMarketingObservationJob({
    tenantId,
    productId: product[1],
    publicationJobId: publication[1],
    window: window[1],
  });
  if (
    job.loop_id !== LOOP_ID
    || job.capability !== CAPABILITY
    || job.effect_class !== "none"
    || job.effect_key !== null
    || job.job_id !== expected.job_id
  ) {
    throw new Error("marketing observation job contract is invalid");
  }
  return {
    tenantId,
    productId: product[1],
    publicationJobId: publication[1],
    publicationReceiptRef: refs.publication_receipt_ref,
    window: window[1],
  };
}

function unavailable(reason) {
  return { status: "unavailable", value: null, reason };
}

function normalizeMetricEnvelope(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} metric envelope is invalid`);
  }
  if (
    value.status === "measured"
    && Number.isInteger(value.value)
    && value.value >= 0
    && typeof value.source === "string"
    && value.source.length >= 1
    && value.source.length <= 100
  ) {
    return {
      status: "measured",
      value: value.value,
      source: value.source,
    };
  }
  if (
    value.status === "unavailable"
    && value.value === null
    && UNAVAILABLE_REASONS.has(value.reason)
  ) {
    return unavailable(value.reason);
  }
  throw new Error(`${label} metric envelope is invalid`);
}

function normalizeMetricGroup(input, names, label) {
  if (
    !input
    || typeof input !== "object"
    || Array.isArray(input)
    || JSON.stringify(Object.keys(input).sort())
      !== JSON.stringify([...names].sort())
  ) {
    throw new Error(`${label} metric envelope is invalid`);
  }
  return Object.fromEntries(
    names.map((name) => [
      name,
      normalizeMetricEnvelope(input[name], `${label}.${name}`),
    ]),
  );
}

function normalizePostizMetrics(input) {
  if (!Array.isArray(input)) throw new Error("Postiz metric response is invalid");
  const labels = new Map();
  for (const row of input) {
    if (!row || typeof row !== "object" || Array.isArray(row)) {
      throw new Error("Postiz metric response is invalid");
    }
    const label = String(row.label || "").trim().toLowerCase();
    if (!["views", "likes", "comments", "shares"].includes(label)) continue;
    if (labels.has(label)) throw new Error("Postiz metric response is invalid");
    const series = row.data;
    const total = Array.isArray(series) && series.length
      ? String(series.at(-1)?.total ?? "")
      : "";
    if (!/^(0|[1-9][0-9]*)$/.test(total)) {
      throw new Error("Postiz metric total is invalid");
    }
    const value = Number(total);
    if (!Number.isSafeInteger(value)) {
      throw new Error("Postiz metric total is invalid");
    }
    labels.set(label, { status: "measured", value, source: "postiz" });
  }
  return Object.fromEntries(
    PLATFORM_METRICS.map((name) => [
      name,
      labels.get(name) || unavailable("metric_not_returned"),
    ]),
  );
}

function verifiedPublication(value) {
  if (
    !verifyMarketingDailyReceipt(value)
    || typeof value.provider_post_id !== "string"
    || !value.provider_post_id
    || typeof value.provider_route !== "string"
    || !value.provider_route
  ) {
    throw new Error("marketing publication receipt is not observable");
  }
  return value;
}

function deepestMetric(metrics) {
  let deepest = null;
  for (const name of REWARD_ORDER) {
    const group = PLATFORM_METRICS.includes(name)
      ? metrics.platform
      : metrics.product;
    if (group[name].status === "measured") deepest = name;
  }
  return deepest;
}

function verifyMarketingObservationReceipt(receipt) {
  if (
    !receipt
    || typeof receipt !== "object"
    || Array.isArray(receipt)
    || Object.keys(receipt).some((key) => !RECEIPT_KEYS.has(key))
    || receipt.schema_version !== 1
    || receipt.kind !== "marketing_attribution_observation"
    || !["scorable", "insufficient"].includes(receipt.status)
    || !IDENTIFIER.test(String(receipt.product_id || ""))
    || !PUBLICATION_JOB_ID.test(String(receipt.publication_job_id || ""))
    || !IDENTIFIER.test(String(receipt.creative_id || ""))
    || !["instagram", "tiktok"].includes(receipt.platform)
    || typeof receipt.public_url !== "string"
    || !receipt.public_url.startsWith("https://")
    || typeof receipt.provider_post_id !== "string"
    || !receipt.provider_post_id
    || typeof receipt.provider_route !== "string"
    || !receipt.provider_route
    || !/^[0-9a-f]{64}$/.test(String(receipt.video_sha256 || ""))
    || !/^[0-9a-f]{64}$/.test(String(receipt.caption_sha256 || ""))
    || !Object.hasOwn(WINDOWS, receipt.window)
  ) {
    return false;
  }
  let opened;
  let due;
  let observed;
  try {
    opened = exactInstant(receipt.opened_at, "opened_at").milliseconds;
    due = exactInstant(receipt.due_at, "due_at").milliseconds;
    observed = exactInstant(receipt.observed_at, "observed_at").milliseconds;
  } catch {
    return false;
  }
  if (
    due !== opened + WINDOWS[receipt.window]
    || observed < due
    || !receipt.metrics
    || typeof receipt.metrics !== "object"
    || Array.isArray(receipt.metrics)
    || JSON.stringify(Object.keys(receipt.metrics).sort())
      !== JSON.stringify(["platform", "product"])
  ) {
    return false;
  }
  let metrics;
  try {
    metrics = {
      platform: normalizeMetricGroup(
        receipt.metrics.platform,
        PLATFORM_METRICS,
        "platform",
      ),
      product: normalizeMetricGroup(
        receipt.metrics.product,
        PRODUCT_METRICS,
        "product",
      ),
    };
  } catch {
    return false;
  }
  const deepest = deepestMetric(metrics);
  return Boolean(
    receipt.reward
    && typeof receipt.reward === "object"
    && !Array.isArray(receipt.reward)
    && receipt.reward.deepest_metric === deepest
    && receipt.reward.effect === (deepest ? "eligible" : "no_change")
    && receipt.status === (deepest ? "scorable" : "insufficient")
  );
}

function safeMarketingObservationSummary(receipt) {
  if (!verifyMarketingObservationReceipt(receipt)) {
    throw new Error("marketing observation receipt verification failed");
  }
  return {
    status: receipt.status,
    product_id: receipt.product_id,
    creative_id: receipt.creative_id,
    platform: receipt.platform,
    public_url: receipt.public_url,
    window: receipt.window,
    deepest_metric: receipt.reward.deepest_metric,
    reward_effect: receipt.reward.effect,
    observed_at: receipt.observed_at,
  };
}

function requiredProvider(value, method, label) {
  if (!value || typeof value[method] !== "function") {
    throw new Error(`marketing observation ${label} provider is required`);
  }
  return value;
}

function createMarketingObservationLoopAdapter(deps = {}) {
  const now = deps.now || (() => new Date().toISOString());
  return Object.freeze({
    async plan(input) {
      return [buildMarketingObservationJob(input)];
    },
    async execute(job) {
      const contract = normalizeJob(job);
      const receiptProvider = requiredProvider(
        deps.receiptProvider,
        "get",
        "receipt",
      );
      const platformMetricProvider = requiredProvider(
        deps.platformMetricProvider,
        "collect",
        "platform metric",
      );
      const productMetricProvider = requiredProvider(
        deps.productMetricProvider,
        "collect",
        "product metric",
      );
      const publication = verifiedPublication(await receiptProvider.get(
        contract.tenantId,
        contract.publicationReceiptRef,
      ));
      const opened = exactInstant(
        publication.published_at,
        "publication published_at",
      );
      const dueMilliseconds = opened.milliseconds + WINDOWS[contract.window];
      const dueAt = new Date(dueMilliseconds).toISOString();
      const observed = exactInstant(now(), "observation time");
      if (observed.milliseconds < dueMilliseconds) {
        throw new Error("marketing observation window is not due");
      }
      const platform = normalizeMetricGroup(
        await platformMetricProvider.collect({
          tenantId: contract.tenantId,
          productId: contract.productId,
          publication,
          window: contract.window,
        }),
        PLATFORM_METRICS,
        "platform",
      );
      const product = normalizeMetricGroup(
        await productMetricProvider.collect({
          tenantId: contract.tenantId,
          productId: contract.productId,
          publication,
          window: contract.window,
        }),
        PRODUCT_METRICS,
        "product",
      );
      const metrics = { platform, product };
      const deepest = deepestMetric(metrics);
      const receipt = {
        schema_version: 1,
        kind: "marketing_attribution_observation",
        status: deepest ? "scorable" : "insufficient",
        product_id: contract.productId,
        publication_job_id: contract.publicationJobId,
        creative_id: publication.creative_id,
        platform: publication.platform,
        public_url: publication.public_url,
        provider_post_id: publication.provider_post_id,
        provider_route: publication.provider_route,
        video_sha256: publication.video_sha256,
        caption_sha256: publication.caption_sha256,
        window: contract.window,
        opened_at: opened.text,
        due_at: dueAt,
        observed_at: observed.text,
        metrics,
        reward: {
          deepest_metric: deepest,
          effect: deepest ? "eligible" : "no_change",
        },
      };
      if (!verifyMarketingObservationReceipt(receipt)) {
        throw new Error("marketing observation receipt verification failed");
      }
      return { receipt };
    },
    async reconcile() {
      return { state: "absent" };
    },
    verify: verifyMarketingObservationReceipt,
    report: safeMarketingObservationSummary,
  });
}

module.exports = {
  CAPABILITY,
  LOOP_ID,
  buildMarketingObservationJob,
  createMarketingObservationLoopAdapter,
  normalizePostizMetrics,
  safeMarketingObservationSummary,
  verifyMarketingObservationReceipt,
};
