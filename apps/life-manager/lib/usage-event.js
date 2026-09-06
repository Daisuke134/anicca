"use strict";

const { recordCost } = require("./ledger.js");

const OUTCOMES = new Set(["success", "failure", "cache_hit"]);
const SECRET_KEY = /(api[_-]?key|authorization|credential|password|secret|token)/i;

function requiredText(value, name) {
  const text = value == null ? "" : String(value).trim();
  if (!text) throw new Error(`${name} is required`);
  return text;
}

function safeMeta(meta) {
  const source = meta == null ? {} : meta;
  if (!source || typeof source !== "object" || Array.isArray(source)) {
    throw new Error("meta must be an object");
  }
  for (const key of Object.keys(source)) {
    if (SECRET_KEY.test(key)) throw new Error(`secret-shaped metadata key: ${key}`);
  }
  return { ...source };
}

function finiteNonNegative(value) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : 0;
}

function normalizeUsageEvent(event = {}) {
  const tenantId = requiredText(event.tenantId, "tenantId");
  const provider = requiredText(event.provider, "provider");
  const feature = requiredText(event.feature, "feature");
  const outcome = requiredText(event.outcome, "outcome");
  if (!OUTCOMES.has(outcome)) throw new Error(`invalid outcome: ${outcome}`);

  const cacheHit = outcome === "cache_hit" || event.cacheHit === true;
  const quantity = cacheHit ? 0 : finiteNonNegative(event.providerUnits);
  const estUsd = cacheHit ? 0 : finiteNonNegative(event.estimatedCostUsd);
  const meta = safeMeta(event.meta);

  return {
    uid: tenantId,
    kind: "provider_usage",
    quantity,
    unit: event.providerUnit == null ? "request" : String(event.providerUnit),
    estUsd,
    meta: {
      ...meta,
      provider,
      feature,
      outcome,
      failure_class: event.failureClass == null ? null : String(event.failureClass),
      cache_hit: cacheHit,
      // Stripe/customer allowance is a later, separate acceptance boundary (COST-06).
      customer_usage: false,
    },
  };
}

async function recordUsageEvent(event, opts = {}) {
  const write = opts.recordCost || recordCost;
  return write(normalizeUsageEvent(event), opts);
}

module.exports = { normalizeUsageEvent, recordUsageEvent, OUTCOMES };
