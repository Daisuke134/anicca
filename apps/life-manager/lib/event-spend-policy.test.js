"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const { buildLumaDateInventory } = require("./luma-date-inventory.js");
const { inspectGoogleCalendarBusyInventory } = require("./google-calendar-busy-inventory.js");
const { evaluateCalendarCandidateGate } = require("./calendar-candidate-gate.js");
const { validateEventPreferenceRanking } = require("./event-preference-ranking.js");
const { validateEventGoalSerendipity } = require("./event-goal-serendipity.js");
const {
  authorizeEventSpend,
  authorizeEventSpendEffect,
  buildEventSpendSequence,
  createEventSpendPolicy,
  eventSpendDecisionForSequence,
  inspectSavedLumaPaymentMethod,
  isVerifiedEventSpendDecision,
  isVerifiedEventSpendPolicy,
  isVerifiedEventSpendSequence,
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

async function rankedAndCalendarReady(dateInventory) {
  const ordered = ["paid", "unknown", "free"].map((slug) => `luma-event://event/${slug}`);
  const preferenceRanking = validateEventPreferenceRanking({
    ranked_events: ordered.map((event_ref) => ({
      event_ref, preference_fit: "strong", preference_reason: "目的に合う候補です",
    })),
  }, { dateInventory, date: "2026-08-05", preferences: "人と会い、事業を前進させる" });
  const events = new Map(dateInventory.days.flatMap((day) => day.events).map((event) => [event.event_ref, event]));
  const goalDecision = validateEventGoalSerendipity({
    ranked_events: ordered.map((event_ref) => {
      const event = events.get(event_ref);
      return {
        event_ref,
        goal_alignment: "strong",
        goal_reason: "事業目標を前進させる可能性があります",
        serendipity_potential: "high",
        serendipity_reason: "新しい出会いの可能性があります",
        factor_assessments: [
          { factor: "description", status: "used", evidence_excerpt: event.description, assessment: "公開説明を確認しました" },
          { factor: "organizers", status: "unavailable", evidence_excerpt: null, assessment: "公開情報がありません" },
          { factor: "participants", status: "unavailable", evidence_excerpt: null, assessment: "公開情報がありません" },
          { factor: "place", status: "used", evidence_excerpt: "Tokyo", assessment: "東京の対面会場です" },
          { factor: "time", status: "used", evidence_excerpt: event.starts_at, assessment: "対象日の開催です" },
        ],
      };
    }),
  }, { dateInventory, preferenceRanking, goals: "毎日人に会い、事業を前進させる" });
  const busyInventory = await inspectGoogleCalendarBusyInventory({
    calendar: {
      async listCalendarsRaw() { return [{ id: "primary" }]; },
      async listAllEventsRaw() { return []; },
    },
    timeMin: "2026-08-02T00:00:00+09:00",
    timeMax: "2026-08-23T00:00:00+09:00",
    timeZone: "Asia/Tokyo",
    now: "2026-08-02T01:00:00.000Z",
  });
  const calendarGate = await evaluateCalendarCandidateGate({
    dateInventory, busyInventory, date: "2026-08-05", homeLocation: "Tokyo",
    routeMinutes: async () => 10,
  });
  return { goalDecision, calendarGate };
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

test("the execution sequence tries free first, then allowed paid, while preserving goal order inside each group", async () => {
  const dateInventory = await inventory();
  const { goalDecision, calendarGate } = await rankedAndCalendarReady(dateInventory);
  const saved = await inspectSavedLumaPaymentMethod({
    inspect: async () => ({ status: "saved", provider_binding: "opaque-provider-binding" }),
  });
  const policy = createEventSpendPolicy({
    tenantId: "dais-local", savedPaymentMethod: saved,
    limits: [{ currency: "JPY", per_event_minor: 3000, rolling_30_day_minor: 10000, spent_30_day_minor: 0 }],
  });
  const sequence = buildEventSpendSequence({ policy, dateInventory, calendarGate, goalDecision });
  assert.equal(isVerifiedEventSpendSequence(sequence), true);
  assert.deepEqual(sequence.ordered_candidates.map((row) => [row.event_ref, row.payment_mode]), [
    ["luma-event://event/free", "none"],
    ["luma-event://event/paid", "saved"],
  ]);
  assert.deepEqual(sequence.skipped, [
    { event_ref: "luma-event://event/unknown", reason: "price_unknown" },
  ]);
  assert.doesNotMatch(JSON.stringify(sequence.ordered_candidates), /payment-method/);
  const paidDecision = eventSpendDecisionForSequence(sequence, "luma-event://event/paid");
  const paidDetail = dateInventory.days.flatMap((day) => day.events)
    .find((event) => event.event_ref === "luma-event://event/paid");
  assert.deepEqual(authorizeEventSpendEffect({ decision: paidDecision, eventDetail: paidDetail }), {
    mode: "saved", event_spend_decision_id: paidDecision.event_spend_decision_id,
  });
  assert.throws(() => authorizeEventSpendEffect({
    decision: structuredClone(paidDecision), eventDetail: paidDetail,
  }), /event spend policy invalid/i);
  assert.throws(() => authorizeEventSpendEffect({
    decision: paidDecision, eventDetail: { ...paidDetail, ticket_price_minor: 2501 },
  }), /event spend policy invalid/i);
});

test("the zero-yen execution sequence keeps only free calendar-eligible candidates", async () => {
  const dateInventory = await inventory();
  const { goalDecision, calendarGate } = await rankedAndCalendarReady(dateInventory);
  const policy = createEventSpendPolicy({ tenantId: "dais-local", limits: [], savedPaymentMethod: null });
  const sequence = buildEventSpendSequence({ policy, dateInventory, calendarGate, goalDecision });
  assert.deepEqual(sequence.ordered_candidates.map((row) => row.event_ref), ["luma-event://event/free"]);
  assert.deepEqual(sequence.skipped, [
    { event_ref: "luma-event://event/paid", reason: "paid_disabled" },
    { event_ref: "luma-event://event/unknown", reason: "price_unknown" },
  ]);
  assert.throws(() => buildEventSpendSequence({
    policy, dateInventory, calendarGate: structuredClone(calendarGate), goalDecision,
  }), /event spend policy invalid/i);
});
