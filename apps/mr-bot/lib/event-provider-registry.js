"use strict";

const { createHash } = require("node:crypto");

const PROVIDER_ORDER = Object.freeze([
  "luma", "connpass", "peatix", "meetup", "doorkeeper", "eventbrite",
]);
const CAPABILITIES = Object.freeze([
  "discovery", "registration", "effect_readback", "screenshot_evidence", "ticket_or_qr",
]);
const REGISTRIES = new WeakSet();
const SAFE_REF = /^[a-z][a-z0-9+.-]*:\/\/[A-Za-z0-9._~:/?#@!$&'()*+,;=%-]{1,900}$/;
const SHA_REF = /^object:\/\/sha256\/[0-9a-f]{64}$/;
const CALENDAR_REF = /^calendar-evidence:\/\/google\/event\/[0-9a-f]{64}$/;
const POSITIVE_ID = /^[1-9][0-9]{0,30}$/;

function invalid() { throw new Error("event provider registry invalid"); }

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => (
      `${JSON.stringify(key)}:${stableJson(value[key])}`
    )).join(",")}}`;
  }
  return JSON.stringify(value);
}

function capability(status, reason) {
  return Object.freeze({ status, reason });
}

function provider(statuses) {
  return Object.freeze(Object.fromEntries(CAPABILITIES.map((name) => [name, statuses[name]])));
}

function verified(core) {
  const registryId = createHash("sha256").update(stableJson(core), "utf8").digest("hex");
  const value = Object.freeze({
    registry_id: `event-provider-registry:${registryId}`,
    provider_order: PROVIDER_ORDER,
    providers: Object.freeze(core.providers),
  });
  REGISTRIES.add(value);
  return value;
}

function createEventProviderRegistry() {
  const active = () => capability("active", "live_proof_verified");
  const advisory = () => capability("advisory_only", "live_proof_required");
  const blocked = () => capability("blocked", "adapter_not_verified");
  return verified({ providers: Object.fromEntries(PROVIDER_ORDER.map((name) => {
    if (name === "luma") return [name, provider(Object.fromEntries(CAPABILITIES.map((key) => [key, active()])))];
    if (name === "connpass") return [name, provider(Object.fromEntries(CAPABILITIES.map((key) => (
      [key, key === "discovery" ? capability("active", "official_api_verified") : advisory()]
    ))))];
    return [name, provider(Object.fromEntries(CAPABILITIES.map((key) => [key, blocked()])))];
  })) });
}

function isVerifiedEventProviderRegistry(value) {
  return Boolean(value && typeof value === "object" && REGISTRIES.has(value));
}

function validProof(value, providerName) {
  return Boolean(
    value && typeof value === "object" && !Array.isArray(value)
    && SAFE_REF.test(String(value.provider_marker_ref || ""))
    && String(value.provider_marker_ref).includes(`://${providerName}/`)
    && SHA_REF.test(String(value.screenshot_ref || ""))
    && SAFE_REF.test(String(value.admission_ref || ""))
    && String(value.admission_ref).includes(`://${providerName}/`)
    && CALENDAR_REF.test(String(value.calendar_event_ref || ""))
    && POSITIVE_ID.test(String(value.telegram_card_id || ""))
    && POSITIVE_ID.test(String(value.telegram_photo_id || ""))
  );
}

function promoteEventProvider(input = {}) {
  if (!isVerifiedEventProviderRegistry(input.registry)) invalid();
  const providerName = String(input.provider || "");
  if (!PROVIDER_ORDER.includes(providerName) || providerName === "luma") invalid();
  if (!validProof(input.live_proof, providerName)) invalid();
  const providers = Object.fromEntries(PROVIDER_ORDER.map((name) => {
    if (name !== providerName) return [name, input.registry.providers[name]];
    return [name, provider(Object.fromEntries(CAPABILITIES.map((key) => (
      [key, capability("active", key === "discovery" ? "official_discovery_verified" : "live_proof_verified")]
    ))))];
  }));
  return verified({ providers });
}

module.exports = {
  createEventProviderRegistry,
  isVerifiedEventProviderRegistry,
  promoteEventProvider,
};
