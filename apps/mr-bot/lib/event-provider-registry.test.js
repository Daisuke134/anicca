"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  createEventProviderRegistry,
  isVerifiedEventProviderRegistry,
  promoteEventProvider,
} = require("./event-provider-registry.js");

const PROVIDERS = ["luma", "connpass", "peatix", "meetup", "doorkeeper", "eventbrite"];
const CAPABILITIES = [
  "discovery", "registration", "effect_readback", "screenshot_evidence", "ticket_or_qr",
];

test("creates one secret-free ordered provider registry with exact capability keys", () => {
  const registry = createEventProviderRegistry();

  assert.deepEqual(registry.provider_order, PROVIDERS);
  assert.match(registry.registry_id, /^event-provider-registry:[0-9a-f]{64}$/);
  assert.equal(isVerifiedEventProviderRegistry(registry), true);
  assert.equal(isVerifiedEventProviderRegistry(structuredClone(registry)), false);
  for (const provider of PROVIDERS) {
    assert.deepEqual(Object.keys(registry.providers[provider]), CAPABILITIES);
  }
  assert.equal(registry.providers.luma.registration.status, "active");
  assert.equal(registry.providers.connpass.discovery.status, "active");
  assert.equal(registry.providers.connpass.registration.status, "advisory_only");
  assert.equal(registry.providers.peatix.discovery.status, "blocked");
  assert.doesNotMatch(JSON.stringify(registry), /api.?key|token|cookie|password|9222|9223/i);
  assert.equal(Object.isFrozen(registry), true);
  assert.equal(Object.isFrozen(registry.providers.connpass.registration), true);
});

test("promotes one provider write surface only with a complete external live proof", () => {
  const registry = createEventProviderRegistry();
  const promoted = promoteEventProvider({
    registry,
    provider: "connpass",
    live_proof: {
      provider_marker_ref: "provider-marker://connpass/verified-registration",
      screenshot_ref: `object://sha256/${"a".repeat(64)}`,
      admission_ref: "provider-ticket://connpass/verified-admission",
      calendar_event_ref: `calendar-evidence://google/event/${"b".repeat(64)}`,
      telegram_card_id: "1001",
      telegram_photo_id: "1002",
    },
  });

  assert.equal(promoted.providers.connpass.registration.status, "active");
  assert.equal(promoted.providers.connpass.effect_readback.status, "active");
  assert.equal(promoted.providers.connpass.screenshot_evidence.status, "active");
  assert.equal(promoted.providers.connpass.ticket_or_qr.status, "active");
  assert.notEqual(promoted.registry_id, registry.registry_id);
  assert.equal(registry.providers.connpass.registration.status, "advisory_only");
});

test("rejects unknown providers, forged registries, and incomplete promotion evidence", () => {
  const registry = createEventProviderRegistry();
  assert.throws(() => promoteEventProvider({
    registry, provider: "unknown", live_proof: {},
  }), /event provider registry invalid/i);
  assert.throws(() => promoteEventProvider({
    registry: structuredClone(registry), provider: "connpass", live_proof: {},
  }), /event provider registry invalid/i);
  assert.throws(() => promoteEventProvider({
    registry,
    provider: "connpass",
    live_proof: {
      provider_marker_ref: "provider-marker://connpass/verified-registration",
      screenshot_ref: `object://sha256/${"a".repeat(64)}`,
    },
  }), /event provider registry invalid/i);
});
