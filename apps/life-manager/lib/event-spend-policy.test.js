"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const { buildLumaDateInventory } = require("./luma-date-inventory.js");
const {
  authorizeEventSpend,
  createEventSpendPolicy,
  inspectSavedLumaPaymentMethod,
  isVerifiedEventSpendDecision,
  isVerifiedEventSpendPolicy,
} = require("./event-spend-policy.js");

async function inventory() {
  const coverage = buildRollingEventCoverage({
    tenantId: "dais-local", timeZone: "Asia/Tokyo", now: "2026-08-01T16:00:00.000Z", resolvedDays: [],
  });
  const slugs = ["free", "paid", "unknown"];
  let round = 0;
  const discovered = await collectLumaInventory({
    readSnapshot: async () => (++round === 1 ? slugs.map((slug) => ({ href: `https://luma.com/${slug}`, title: slug, cardText: slug, timelineText: "Aug 5" })) : []),
    advance: async () => ({ atEnd: true, scrollHeight: 100 }), stableEndRounds: 1,
  });
  const detail = (slug, offers) => normalizeLumaEventDetail({
    canonicalUrl: `https://luma.com/${slug}`,
    jsonLd: [{
      "@type": "Event", name: slug, description: `${slug} event`,
      startDate: `2026-08-05T${slug === "free" ? "09" : slug === "paid" ? "12" : "15"}:00:00+09:00`,
      endDate: `2026-08-05T${slug === "free" ? "10" : slug === "paid" ? "13" : "16"}:00:00+09:00`,
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled", location: { name: "Tokyo", address: "Tokyo" }, offers,
    }], controls: ["Register"],
  });
  return buildLumaDateInventory({
    coverage, inventory: discovered,
    details: [
      detail("free", { price: 0, priceCurrency: "JPY", availability: "https://schema.org/InStock", url: "https://luma.com/free" }),
      detail("paid", { price: 2500, priceCurrency: "JPY", availability: "https://schema.org/InStock", url: "https://luma.com/paid" }),
      detail("unknown", undefined),
    ], now: "2026-08-02T01:00:00.000Z",
  });
}

test("the current zero-yen policy permits free events and advances past paid or unknown prices without approval", async () => {
  const dateInventory = await inventory();
  const policy = createEventSpendPolicy({ tenantId: "dais-local", limits: [], savedPaymentMethod: null });
  assert.equal(isVerifiedEventSpendPolicy(policy), true);
  assert.equal(isVerifiedEventSpendPolicy(structuredClone(policy)), false);
  const free = authorizeEventSpend({ policy, dateInventory, eventRef: "luma-event://event/free" });
  const paid = authorizeEventSpend({ policy, dateInventory, eventRef: "luma-event://event/paid" });
  const unknown = authorizeEventSpend({ policy, dateInventory, eventRef: "luma-event://event/unknown" });
  assert.deepEqual([free.allowed, free.reason, free.payment_mode], [true, "free", "none"]);
  assert.deepEqual([paid.allowed, paid.reason], [false, "paid_disabled"]);
  assert.deepEqual([unknown.allowed, unknown.reason], [false, "price_unknown"]);
  assert.doesNotMatch(JSON.stringify([paid, unknown]), /approval_required|ask_user/i);
  assert.equal(isVerifiedEventSpendDecision(free), true);
});

test("one verified saved method enables no-human paid spend only inside both caps", async () => {
  const dateInventory = await inventory();
  const saved = await inspectSavedLumaPaymentMethod({
    inspect: async () => ({ status: "saved", provider_binding: "opaque-provider-binding" }),
  });
  const allowedPolicy = createEventSpendPolicy({
    tenantId: "dais-local", savedPaymentMethod: saved,
    limits: [{ currency: "JPY", per_event_minor: 3000, rolling_30_day_minor: 10000, spent_30_day_minor: 7000 }],
  });
  const allowed = authorizeEventSpend({ policy: allowedPolicy, dateInventory, eventRef: "luma-event://event/paid" });
  assert.deepEqual([allowed.allowed, allowed.reason, allowed.payment_mode], [true, "paid_policy_allowed", "saved"]);
  assert.equal(allowed.remaining_after_minor, 500);
  assert.match(allowed.payment_method_ref, /^payment-method:\/\/luma\/saved\/[0-9a-f]{64}$/);

  const perEvent = createEventSpendPolicy({
    tenantId: "dais-local", savedPaymentMethod: saved,
    limits: [{ currency: "JPY", per_event_minor: 2000, rolling_30_day_minor: 10000, spent_30_day_minor: 0 }],
  });
  assert.equal(authorizeEventSpend({ policy: perEvent, dateInventory, eventRef: "luma-event://event/paid" }).reason, "per_event_cap_exceeded");
  const rolling = createEventSpendPolicy({
    tenantId: "dais-local", savedPaymentMethod: saved,
    limits: [{ currency: "JPY", per_event_minor: 3000, rolling_30_day_minor: 10000, spent_30_day_minor: 8000 }],
  });
  assert.equal(authorizeEventSpend({ policy: rolling, dateInventory, eventRef: "luma-event://event/paid" }).reason, "rolling_cap_exceeded");
});

test("fake payment evidence, fake policy, fake inventory, duplicate currencies, and negative limits fail closed", async () => {
  const dateInventory = await inventory();
  const saved = await inspectSavedLumaPaymentMethod({ inspect: async () => ({ status: "saved", provider_binding: "binding" }) });
  assert.throws(() => createEventSpendPolicy({
    tenantId: "dais-local", savedPaymentMethod: structuredClone(saved),
    limits: [{ currency: "JPY", per_event_minor: 1, rolling_30_day_minor: 1, spent_30_day_minor: 0 }],
  }), /event spend policy invalid/i);
  for (const limits of [
    [{ currency: "JPY", per_event_minor: -1, rolling_30_day_minor: 1, spent_30_day_minor: 0 }],
    [{ currency: "JPY", per_event_minor: 1, rolling_30_day_minor: 1, spent_30_day_minor: 0 }, { currency: "JPY", per_event_minor: 1, rolling_30_day_minor: 1, spent_30_day_minor: 0 }],
  ]) assert.throws(() => createEventSpendPolicy({ tenantId: "dais-local", savedPaymentMethod: saved, limits }), /event spend policy invalid/i);
  const policy = createEventSpendPolicy({ tenantId: "dais-local", limits: [], savedPaymentMethod: null });
  assert.throws(() => authorizeEventSpend({ policy: structuredClone(policy), dateInventory, eventRef: "luma-event://event/free" }), /event spend policy invalid/i);
  assert.throws(() => authorizeEventSpend({ policy, dateInventory: structuredClone(dateInventory), eventRef: "luma-event://event/free" }), /event spend policy invalid/i);
});
