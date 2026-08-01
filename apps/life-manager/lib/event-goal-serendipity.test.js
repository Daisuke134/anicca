"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { collectLumaInventory } = require("./luma-discovery.js");
const { normalizeLumaEventDetail } = require("./luma-event-detail.js");
const { buildLumaDateInventory } = require("./luma-date-inventory.js");
const { validateEventPreferenceRanking } = require("./event-preference-ranking.js");
const {
  inferEventGoalSerendipity,
  isVerifiedEventGoalSerendipity,
  validateEventGoalSerendipity,
} = require("./event-goal-serendipity.js");

const GOALS = "Life Managerを成長させ、founder、engineer、investorとの接点を増やし、毎日東京で新しい経験を得る。";

async function sources() {
  const coverage = buildRollingEventCoverage({
    tenantId: "dais-local",
    timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z",
    resolvedDays: [],
  });
  const slugs = ["ai-founder-night", "pottery-social"];
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
  const details = [
    normalizeLumaEventDetail({
      canonicalUrl: "https://luma.com/ai-founder-night",
      jsonLd: [{
        "@type": "Event",
        name: "AI Founder Night",
        description: "AI founders demonstrate products and discuss company building with engineers.",
        startDate: "2026-08-02T09:00:00.000Z",
        endDate: "2026-08-02T11:00:00.000Z",
        eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
        eventStatus: "https://schema.org/EventScheduled",
        organizer: [{ name: "Tokyo Startup Community" }],
        location: { name: "Shibuya Startup Hub", address: "Shibuya, Tokyo" },
      }],
      controls: ["Register"],
    }),
    normalizeLumaEventDetail({
      canonicalUrl: "https://luma.com/pottery-social",
      jsonLd: [{
        "@type": "Event",
        name: "Pottery Social",
        description: "Beginners make pottery together and meet people from different backgrounds.",
        startDate: "2026-08-02T12:00:00.000Z",
        endDate: "2026-08-02T14:00:00.000Z",
        eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
        eventStatus: "https://schema.org/EventScheduled",
        organizer: [{ name: "Tokyo Creative Club" }],
        attendee: [{ name: "Public Guest" }],
        location: { name: "Asakusa Studio", address: "Asakusa, Tokyo" },
      }],
      controls: ["Register"],
    }),
  ];
  const dateInventory = buildLumaDateInventory({
    coverage, inventory, details, now: "2026-08-02T01:00:00.000Z",
  });
  const preferenceRanking = validateEventPreferenceRanking({ ranked_events: [
    { event_ref: "luma-event://event/ai-founder-night", preference_fit: "strong", preference_reason: "AI founderへの関心と合います。" },
    { event_ref: "luma-event://event/pottery-social", preference_fit: "weak", preference_reason: "直接の好みではないが候補に残します。" },
  ] }, {
    dateInventory,
    date: "2026-08-02",
    preferences: "AIとfounderを優先するが全候補を残す。",
  });
  return { dateInventory, preferenceRanking };
}

function factorsForAi(overrides = {}) {
  return [
    { factor: "description", status: "used", evidence_excerpt: "AI founders demonstrate products", assessment: "product demoと会社作りの議論があります。" },
    { factor: "organizers", status: "used", evidence_excerpt: "Tokyo Startup Community", assessment: "startup communityが主催しています。" },
    { factor: "participants", status: "unavailable", evidence_excerpt: null, assessment: "公開participant metadataがないため人物像を推測しません。" },
    { factor: "place", status: "used", evidence_excerpt: "Shibuya Startup Hub", assessment: "東京で対面参加できます。" },
    { factor: "time", status: "used", evidence_excerpt: "2026-08-02T09:00:00.000Z", assessment: "開始終了時刻が明示されています。" },
  ].map((row) => row.factor === (overrides.factor || "") ? { ...row, ...overrides } : row);
}

function factorsForPottery() {
  return [
    { factor: "description", status: "used", evidence_excerpt: "meet people from different backgrounds", assessment: "異分野の人との接点があります。" },
    { factor: "organizers", status: "used", evidence_excerpt: "Tokyo Creative Club", assessment: "creative communityが主催しています。" },
    { factor: "participants", status: "used", evidence_excerpt: "Public Guest", assessment: "公開participant metadataが一件あります。" },
    { factor: "place", status: "used", evidence_excerpt: "Asakusa Studio", assessment: "東京の対面会場です。" },
    { factor: "time", status: "used", evidence_excerpt: "2026-08-02T12:00:00.000Z", assessment: "開始終了時刻が明示されています。" },
  ];
}

function decision(overrides = {}) {
  return {
    ranked_events: [
      {
        event_ref: "luma-event://event/ai-founder-night",
        goal_alignment: "strong",
        serendipity_potential: "high",
        goal_reason: "Life Managerを見せられるfounderとengineerの接点に直結します。",
        serendipity_reason: "demoと会社作りの会話から予期しない協力関係が生まれ得ます。",
        factor_assessments: factorsForAi(),
      },
      {
        event_ref: "luma-event://event/pottery-social",
        goal_alignment: "weak",
        serendipity_potential: "medium",
        goal_reason: "事業との直接整合は弱いですが外出と新しい経験には合います。",
        serendipity_reason: "異分野の参加者との偶発的な接点が期待できます。",
        factor_assessments: factorsForPottery(),
      },
    ],
    ...overrides,
  };
}

test("accepts a grounded immutable ranking with all five factors and every candidate", async () => {
  const input = await sources();
  const result = validateEventGoalSerendipity(decision(), { ...input, goals: GOALS });
  assert.equal(result.ranked_events.length, 2);
  assert.deepEqual(result.ranked_events[0].factor_assessments.map((row) => row.factor), [
    "description", "organizers", "participants", "place", "time",
  ]);
  assert.equal(result.ranked_events[0].factor_assessments[2].status, "unavailable");
  assert.equal(result.ranked_events[1].factor_assessments[2].status, "used");
  assert.match(result.goals_hash, /^sha256:[0-9a-f]{64}$/);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(isVerifiedEventGoalSerendipity(result), true);
  assert.equal(isVerifiedEventGoalSerendipity(structuredClone(result)), false);
});

test("rejects fake provenance, omitted candidates, factor gaps, invented evidence, and invented participants", async () => {
  const input = await sources();
  const valid = decision().ranked_events;
  const cases = [
    { input: { ...input, dateInventory: structuredClone(input.dateInventory) }, value: decision() },
    { input: { ...input, preferenceRanking: structuredClone(input.preferenceRanking) }, value: decision() },
    { input, value: { ranked_events: valid.slice(0, 1) } },
    { input, value: decision({ ranked_events: [{ ...valid[0], factor_assessments: factorsForAi().slice(0, 4) }, valid[1]] }) },
    { input, value: decision({ ranked_events: [{ ...valid[0], factor_assessments: factorsForAi({ factor: "description", evidence_excerpt: "invented evidence" }) }, valid[1]] }) },
    { input, value: decision({ ranked_events: [{ ...valid[0], factor_assessments: factorsForAi({ factor: "participants", status: "used", evidence_excerpt: "Imaginary Investor" }) }, valid[1]] }) },
  ];
  for (const row of cases) {
    assert.throws(() => validateEventGoalSerendipity(row.value, {
      ...row.input, goals: GOALS,
    }), /event goal serendipity invalid/i);
  }
});

test("Gemini receives goals and provider factors as untrusted data with no missing-factor shortcut", async () => {
  const input = await sources();
  let request;
  const result = await inferEventGoalSerendipity({ ...input, goals: GOALS }, {
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
  assert.equal(result.ranked_events.length, 2);
  const prompt = request.body.contents[0].parts[0].text;
  assert.match(prompt, /untrusted data/i);
  assert.match(prompt, /exactly once/i);
  assert.match(prompt, /participant metadata is unavailable/i);
  assert.match(prompt, /Life Managerを成長させ/);
  assert.equal(request.options.headers["x-goog-api-key"], "fixture-key");
  assert.equal(request.body.generationConfig.responseMimeType, "application/json");
});

test("model failure and invalid JSON never become an ungrounded fallback", async () => {
  const input = { ...await sources(), goals: GOALS };
  await assert.rejects(inferEventGoalSerendipity(input, {
    apiKey: "fixture-key", fetchImpl: async () => ({ ok: false, status: 503 }),
  }), /event goal serendipity unavailable/i);
  await assert.rejects(inferEventGoalSerendipity(input, {
    apiKey: "fixture-key",
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ candidates: [{ content: { parts: [{ text: "not json" }] } }] }),
    }),
  }), /event goal serendipity unavailable/i);
});
