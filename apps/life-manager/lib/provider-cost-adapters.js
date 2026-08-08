"use strict";

const crypto = require("node:crypto");
const { recordProviderCost } = require("./ledger.js");

const GEMINI_WALL_TIME_USD_PER_MINUTE = 0.023;

function requestId(provider, input = {}) {
  if (input.requestId != null && String(input.requestId).trim()) return String(input.requestId);
  if (input.id != null && String(input.id).trim()) return `${provider}:${String(input.id)}`;
  return `${provider}:${Date.now()}:${crypto.randomUUID()}`;
}

function quantity(value, fallback = 1) {
  const number = Number(value == null ? fallback : value);
  return Number.isFinite(number) && number >= 0 ? number : fallback;
}

function money(value) {
  if (value == null || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}

function objectOrEmpty(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

async function write(event, deps = {}) {
  const writer = deps.recordProviderCost || recordProviderCost;
  return writer(event, deps);
}

function unknownEvent({ provider, sku, operation, uid, requestId: id, quantity: amount, unit, pricingVersion, metadata, estimatedUsd = null }) {
  return {
    uid: uid == null ? null : String(uid), provider, sku, operation,
    requestId: requestId(provider, { requestId: id }), quantity: quantity(amount), unit, pricingVersion,
    estimatedUsd: money(estimatedUsd), actualBilledUsd: null, actualStatus: "unknown",
    metadata: objectOrEmpty(metadata),
  };
}

async function recordGoogleGeocoding(input = {}, deps = {}) {
  return write(unknownEvent({
    provider: "google", sku: "geocoding", operation: "geocoding", uid: input.uid,
    requestId: input.requestId, quantity: input.quantity, unit: "request",
    pricingVersion: "google-maps-2026-08", metadata: input.metadata,
  }), deps);
}

async function recordGoogleRoutes(input = {}, deps = {}) {
  return write(unknownEvent({
    provider: "google", sku: "routes", operation: "routes", uid: input.uid,
    requestId: input.requestId, quantity: input.quantity, unit: "request",
    pricingVersion: "google-maps-2026-08", metadata: input.metadata,
  }), deps);
}

async function recordGoogleTransit(input = {}, deps = {}) {
  return write(unknownEvent({
    provider: "google", sku: "directions-transit", operation: "transit", uid: input.uid,
    requestId: input.requestId, quantity: input.quantity, unit: "request",
    pricingVersion: "google-maps-2026-08", metadata: input.metadata,
  }), deps);
}

async function recordTransitOperation(input = {}, deps = {}) {
  const operation = String(input.operation || "plan");
  return write(unknownEvent({
    provider: "transit", sku: "jp-public", operation, uid: input.uid,
    requestId: input.requestId, quantity: input.quantity, unit: "request",
    pricingVersion: "transit-api-2026-08", metadata: input.metadata,
  }), deps);
}

async function recordComposioOperation(input = {}, deps = {}) {
  const tool = String(input.tool || "tool");
  return write(unknownEvent({
    provider: "composio", sku: tool, operation: "tool_execute", uid: input.uid,
    requestId: input.requestId, quantity: input.quantity, unit: "call",
    pricingVersion: "composio-2026-08", metadata: { ...objectOrEmpty(input.metadata), tool },
  }), deps);
}

async function recordGeminiSession(input = {}, deps = {}) {
  const seconds = quantity(input.durationSeconds, 0);
  const estimate = money(input.estimatedUsd) != null
    ? money(input.estimatedUsd)
    : seconds > 0 ? seconds / 60 * GEMINI_WALL_TIME_USD_PER_MINUTE : null;
  const usage = input.usageMetadata == null ? null : objectOrEmpty(input.usageMetadata);
  return write(unknownEvent({
    provider: "gemini", sku: "live", operation: "session", uid: input.uid,
    requestId: input.requestId, quantity: seconds, unit: "seconds",
    pricingVersion: usage ? "gemini-live-token-metadata-2026-08" : "gemini-live-wall-time-2026-08",
    estimatedUsd: estimate,
    metadata: { ...objectOrEmpty(input.metadata), ...(usage ? { usage } : {}) },
  }), deps);
}

function cdrCost(cdr = {}) {
  const cost = cdr.cost;
  const amount = cost && typeof cost === "object" ? cost.amount : cost;
  const currency = cost && typeof cost === "object" && cost.currency ? String(cost.currency).toUpperCase() : "USD";
  if (currency !== "USD") return null;
  return money(amount != null ? amount : (cdr.price != null ? cdr.price : cdr.amount));
}

async function recordTelnyxCdr(input = {}, deps = {}) {
  const cdr = objectOrEmpty(input.cdr);
  const actual = cdrCost(cdr);
  return write({
    uid: input.uid == null ? null : String(input.uid), provider: "telnyx", sku: "voice",
    operation: "call_cdr", requestId: requestId("telnyx", { requestId: input.requestId, id: cdr.id || cdr.call_control_id }),
    quantity: quantity(input.durationSeconds, 0), unit: "seconds", pricingVersion: "telnyx-cdr-2026-08",
    estimatedUsd: null, actualBilledUsd: actual, actualStatus: actual == null ? "unknown" : "measured",
    metadata: { ...objectOrEmpty(input.metadata), ...(cdr.id ? { cdrId: String(cdr.id) } : {}),
      ...(cdr.call_control_id ? { callControlId: String(cdr.call_control_id) } : {}) },
  }, deps);
}

async function recordResendSend(input = {}, deps = {}) {
  const recipients = quantity(input.recipientCount, 1);
  return write(unknownEvent({
    provider: "resend", sku: "email", operation: "send", uid: input.uid,
    requestId: input.requestId || input.responseId, quantity: recipients, unit: "recipient",
    pricingVersion: "resend-2026-08",
    metadata: { ...objectOrEmpty(input.metadata), ...(input.responseId ? { responseId: String(input.responseId) } : {}) },
  }), deps);
}

async function recordAllocation(input = {}, deps = {}) {
  const provider = String(input.provider || "unknown");
  const actual = money(input.amountUsd);
  const period = input.period == null ? null : String(input.period);
  return write({
    uid: input.uid == null ? null : String(input.uid), provider,
    sku: String(input.sku || "allocation"), operation: "allocation",
    requestId: requestId(provider, { requestId: input.requestId, id: period }),
    quantity: quantity(input.quantity), unit: String(input.unit || "period"),
    pricingVersion: String(input.pricingVersion || `${provider}-allocation-2026-08`),
    estimatedUsd: money(input.estimatedUsd), actualBilledUsd: actual,
    actualStatus: actual == null ? "unknown" : "measured",
    metadata: { ...objectOrEmpty(input.metadata), ...(period ? { period } : {}) },
  }, deps);
}

async function recordRailwayAllocation(input = {}, deps = {}) {
  return recordAllocation({ ...input, provider: "railway" }, deps);
}

async function recordSupabaseAllocation(input = {}, deps = {}) {
  return recordAllocation({ ...input, provider: "supabase" }, deps);
}

module.exports = {
  recordGoogleGeocoding,
  recordGoogleRoutes,
  recordGoogleTransit,
  recordTransitOperation,
  recordComposioOperation,
  recordGeminiSession,
  recordTelnyxCdr,
  recordResendSend,
  recordRailwayAllocation,
  recordSupabaseAllocation,
  recordAllocation,
};
