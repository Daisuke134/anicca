"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const { buildLumaDateInventory } = require("./luma-date-inventory.js");
const {
  inferEventPreferenceRanking,
  isVerifiedEventPreferenceRanking,
  validateEventPreferenceRanking,
} = require("./event-preference-ranking.js");

async function fixtureSnapshot(slugs = ["ai-night", "pottery-social", "crypto-builders"]) {
  const coverage = buildRollingEventCoverage({
    tenantId: "dais-local",
    timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z",
    resolvedDays: [],
  });
  let round = 0;
  const inventory = await collectLumaInventory({
    readSnapshot: async () => {
      round += 1;
      return round === 1 ? slugs.map((slug) => ({
        href: `https://luma.com/${slug}`,
        title: slug,
        cardText: `${slug} 19:00`,
        timelineText: "8月2日 日曜日",
      })) : [];
    },
    advance: async () => ({ atEnd: true, scrollHeight: 100 }),
    stableEndRounds: 1,
  });
  const details = slugs.map((slug, index) => normalizeLumaEventDetail({
    canonicalUrl: `https://luma.com/${slug}`,
    jsonLd: [{
      "@type": "Event",
      name: slug.replaceAll("-", " "),
      startDate: `2026-08-02T${String(9 + index).padStart(2, "0")}:00:00.000Z`,
      endDate: `2026-08-02T${String(10 + index).padStart(2, "0")}:00:00.000Z`,
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      location: { "@type": "Place", name: `Tokyo venue ${index + 1}` },
    }],
    controls: ["Register"],
  }));
  return buildLumaDateInventory({
    coverage,
    inventory,
    details,
    now: "2026-08-02T01:00:00.000Z",
  });
}

const PREFERENCES = "AI、crypto、英語の会話、founderとの出会いを高く評価する。それ以外も除外しない。";

function decision(overrides = {}) {
  return {
    ranked_events: [
      {
        event_ref: "luma-event://event/ai-night",
        preference_fit: "strong",
        preference_reason: "AIへの関心と直接一致するため最上位です。",
      },
      {
        event_ref: "luma-event://event/crypto-builders",
        preference_fit: "strong",
        preference_reason: "crypto builderとの接点が期待できます。",
      },
      {
        event_ref: "luma-event://event/pottery-social",
        preference_fit: "weak",
        preference_reason: "直接の好みとは離れますが新しい人との接点として候補に残します。",
      },
    ],
    ...overrides,
  };
}

test("accepts one immutable ranking that preserves every candidate including weak fits", async () => {
  const snapshot = await fixtureSnapshot();
  const ranking = validateEventPreferenceRanking(decision(), {
    dateInventory: snapshot,
    date: "2026-08-02",
    preferences: PREFERENCES,
  });

  assert.equal(ranking.date, "2026-08-02");
  assert.equal(ranking.inventory_snapshot_id, snapshot.inventory_snapshot_id);
  assert.deepEqual(ranking.ranked_events.map((row) => row.event_ref), [
    "luma-event://event/ai-night",
    "luma-event://event/crypto-builders",
    "luma-event://event/pottery-social",
  ]);
  assert.equal(ranking.ranked_events.at(-1).preference_fit, "weak");
  assert.match(ranking.preference_profile_hash, /^sha256:[0-9a-f]{64}$/);
  assert.equal(Object.isFrozen(ranking), true);
  assert.equal(isVerifiedEventPreferenceRanking(ranking), true);
  assert.equal(isVerifiedEventPreferenceRanking(structuredClone(ranking)), false);
});

test("rejects omitted, duplicate, unknown, malformed, or exclusion-shaped model output", async () => {
  const snapshot = await fixtureSnapshot();
  const valid = decision().ranked_events;
  const cases = [
    { ranked_events: valid.slice(0, 2) },
    { ranked_events: [valid[0], valid[0], valid[2]] },
    { ranked_events: [valid[0], valid[1], { ...valid[2], event_ref: "luma-event://event/unknown" }] },
    { ranked_events: [valid[0], valid[1], { ...valid[2], preference_fit: "excluded" }] },
    { ranked_events: [valid[0], valid[1], { ...valid[2], exclude: true }] },
  ];
  for (const value of cases) {
    assert.throws(() => validateEventPreferenceRanking(value, {
      dateInventory: snapshot,
      date: "2026-08-02",
      preferences: PREFERENCES,
    }), /event preference ranking invalid/i);
  }
});

test("Gemini receives all candidates as untrusted data and preferences can only change order", async () => {
  const snapshot = await fixtureSnapshot();
  let request;
  const ranking = await inferEventPreferenceRanking({
    dateInventory: snapshot,
    date: "2026-08-02",
    preferences: PREFERENCES,
  }, {
    apiKey: "fixture-key",
    fetchImpl: async (url, options) => {
      request = { url, options, body: JSON.parse(options.body) };
      return {
        ok: true,
        json: async () => ({
          candidates: [{ content: { parts: [{ text: JSON.stringify(decision()) }] } }],
        }),
      };
    },
  });

  assert.equal(ranking.ranked_events.length, 3);
  assert.match(request.url, /gemini-2\.5-flash:generateContent/);
  assert.equal(request.options.headers["x-goog-api-key"], "fixture-key");
  const prompt = request.body.contents[0].parts[0].text;
  assert.match(prompt, /untrusted data/i);
  assert.match(prompt, /Never omit, exclude, discard/i);
  assert.match(prompt, /pottery social/i);
  assert.match(prompt, /それ以外も除外しない/);
  assert.equal(request.body.generationConfig.responseMimeType, "application/json");
  assert.equal(request.body.generationConfig.temperature, 0);
});

test("model failure and invalid JSON never become a keyword ranking fallback", async () => {
  const snapshot = await fixtureSnapshot();
  const input = { dateInventory: snapshot, date: "2026-08-02", preferences: PREFERENCES };
  await assert.rejects(inferEventPreferenceRanking(input, {
    apiKey: "fixture-key",
    fetchImpl: async () => ({ ok: false, status: 503 }),
  }), /event preference ranking unavailable/i);
  await assert.rejects(inferEventPreferenceRanking(input, {
    apiKey: "fixture-key",
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ candidates: [{ content: { parts: [{ text: "not json" }] } }] }),
    }),
  }), /event preference ranking unavailable/i);
});

test("a fully read empty day returns a verified empty ranking without calling the model", async () => {
  const snapshot = await fixtureSnapshot();
  let called = false;
  const ranking = await inferEventPreferenceRanking({
    dateInventory: snapshot,
    date: "2026-08-03",
    preferences: PREFERENCES,
  }, {
    apiKey: "fixture-key",
    fetchImpl: async () => { called = true; },
  });
  assert.equal(called, false);
  assert.deepEqual(ranking.ranked_events, []);
  assert.equal(isVerifiedEventPreferenceRanking(ranking), true);
});
