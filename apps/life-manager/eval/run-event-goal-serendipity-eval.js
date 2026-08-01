#!/usr/bin/env node
"use strict";

const { buildRollingEventCoverage } = require("../lib/rolling-event-coverage.js");
const { collectLumaInventory } = require("../lib/luma-discovery.js");
const { normalizeLumaEventDetail } = require("../lib/luma-event-detail.js");
const { buildLumaDateInventory } = require("../lib/luma-date-inventory.js");
const { validateEventPreferenceRanking } = require("../lib/event-preference-ranking.js");
const { inferEventGoalSerendipity } = require("../lib/event-goal-serendipity.js");

const CASES = Object.freeze([
  {
    goals: "Life Managerを成長させるAI founderとengineerに会い、product demoの協力者を見つける。",
    expectedIndex: 1,
    events: [
      ["pottery", "Beginners make pottery and relax together.", "Creative Club", null, "Asakusa Studio"],
      ["ai-founder", "AI founders demonstrate products and discuss company building with engineers.", "Startup Community", null, "Shibuya Hub"],
      ["history", "A lecture about local history and architecture.", "History Society", "Public History Guest", "Tokyo Hall"],
    ],
  },
  {
    goals: "fundraisingのためinvestorとstartup founderに会い、pitchへのfeedbackを得る。",
    expectedIndex: 2,
    events: [
      ["running", "A social morning run for beginners.", "Wellness Club", null, "Yoyogi Park"],
      ["cooking", "Neighbors cook seasonal food together.", "Food Circle", "Public Cooking Guest", "Community Kitchen"],
      ["investor-pitch", "Startup founders pitch to angel investors and receive fundraising feedback.", "Founder Network", null, "Tokyo Venture Hall"],
    ],
  },
  {
    goals: "英語で国際的なfounderやproduct builderと会話し、海外展開の視点を得る。",
    expectedIndex: 0,
    events: [
      ["global-network", "International founders and product builders network in English.", "Global Startup Circle", null, "Roppongi Center"],
      ["calligraphy", "Japanese calligraphy practice in a quiet room.", "Arts Group", null, "Ueno Room"],
      ["film", "A screening of one independent film.", "Cinema Club", "Public Film Guest", "Shinjuku Theater"],
    ],
  },
  {
    goals: "creative technologyの異分野協業を見つけ、予想外のserendipityを増やす。",
    expectedIndex: 1,
    events: [
      ["textbook", "Participants silently study language textbooks.", "Study Group", null, "Library Room"],
      ["creative-tech", "Artists and engineers build interactive installations together in mixed teams.", "Creative Technology Lab", "Public Artist", "Digital Studio"],
      ["tea", "A guided tasting of traditional tea.", "Tea Society", null, "Tea Room"],
    ],
  },
  {
    goals: "個人finance、NISA、長期資産形成を学び、実行可能な知識を得る。",
    expectedIndex: 0,
    events: [
      ["finance-nisa", "A practical workshop about personal finance, NISA, fees, and long-term investing.", "Financial Education Group", null, "Marunouchi Classroom"],
      ["anime", "Fans discuss recent anime series.", "Anime Circle", "Public Anime Guest", "Ikebukuro Cafe"],
      ["photo", "A casual urban photography walk.", "Photo Club", null, "Tokyo Station"],
    ],
  },
  {
    goals: "家に留まらず、異なるbackgroundの人と東京で会い、新しい経験と接点を得る。",
    expectedIndex: 2,
    events: [
      ["solo-study", "A silent individual study session with no group discussion.", "Study Room", null, "Library"],
      ["recording", "Attendees listen to an archived audio recording.", "Archive Society", null, "Audio Room"],
      ["community-dinner", "People from different professions share dinner and rotate conversation partners.", "Open Community", "Public Community Guest", "Tokyo Dining Hall"],
    ],
  },
]);

async function sourceFor(entry) {
  const coverage = buildRollingEventCoverage({
    tenantId: "connector-goal-eval",
    timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z",
    resolvedDays: [],
  });
  let round = 0;
  const inventory = await collectLumaInventory({
    readSnapshot: async () => {
      round += 1;
      return round === 1 ? entry.events.map(([slug], index) => ({
        href: `https://luma.com/${slug}`,
        title: slug,
        cardText: `${slug} ${19 + index}:00`,
        timelineText: "8月2日 日曜日",
      })) : [];
    },
    advance: async () => ({ atEnd: true, scrollHeight: 100 }),
    stableEndRounds: 1,
  });
  const details = entry.events.map(([slug, description, organizer, attendee, venue], index) => (
    normalizeLumaEventDetail({
      canonicalUrl: `https://luma.com/${slug}`,
      jsonLd: [{
        "@type": "Event",
        name: slug,
        description,
        startDate: `2026-08-02T${String(9 + index).padStart(2, "0")}:00:00.000Z`,
        endDate: `2026-08-02T${String(10 + index).padStart(2, "0")}:00:00.000Z`,
        eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
        eventStatus: "https://schema.org/EventScheduled",
        organizer: [{ name: organizer }],
        attendee: attendee ? [{ name: attendee }] : undefined,
        location: { name: venue, address: "Tokyo, JP" },
      }],
      controls: ["Register"],
    })
  ));
  const dateInventory = buildLumaDateInventory({ coverage, inventory, details, now: "2026-08-02T01:00:00.000Z" });
  const preferenceRanking = validateEventPreferenceRanking({
    ranked_events: entry.events.map(([slug]) => ({
      event_ref: `luma-event://event/${slug}`,
      preference_fit: "moderate",
      preference_reason: "Grounded goal evaluationへ全候補を渡します。",
    })),
  }, {
    dateInventory,
    date: "2026-08-02",
    preferences: "全候補を残し、goalとserendipityの根拠で次に評価する。",
  });
  return { dateInventory, preferenceRanking };
}

async function runEventGoalSerendipityEval(options = {}) {
  const apiKey = String(options.apiKey || process.env.GEMINI_API_KEY || "").trim();
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  if (!apiKey || typeof fetchImpl !== "function") throw new Error("event goal serendipity eval unavailable");
  let preserved = 0;
  let topMatches = 0;
  let fiveFactorComplete = 0;
  let participantHonest = 0;
  const failedTopCaseIndexes = [];
  for (const [caseIndex, entry] of CASES.entries()) {
    const source = await sourceFor(entry);
    let decision;
    try {
      decision = await inferEventGoalSerendipity({ ...source, goals: entry.goals }, { apiKey, fetchImpl });
    } catch (error) {
      throw new Error(`event goal serendipity eval case ${caseIndex + 1} failed: ${error.message}`);
    }
    const expectedRefs = new Set(entry.events.map(([slug]) => `luma-event://event/${slug}`));
    const actualRefs = decision.ranked_events.map((row) => row.event_ref);
    if (actualRefs.length === expectedRefs.size && actualRefs.every((ref) => expectedRefs.has(ref))) preserved += 1;
    const expectedTop = `luma-event://event/${entry.events[entry.expectedIndex][0]}`;
    if (actualRefs[0] === expectedTop) topMatches += 1;
    else failedTopCaseIndexes.push(caseIndex + 1);
    if (decision.ranked_events.every((row) => row.factor_assessments.length === 5)) fiveFactorComplete += 1;
    const bySlug = new Map(entry.events.map((event) => [event[0], event]));
    if (decision.ranked_events.every((row) => {
      const slug = row.event_ref.split("/").at(-1);
      const attendee = bySlug.get(slug)[3];
      const factor = row.factor_assessments.find((candidate) => candidate.factor === "participants");
      return attendee ? factor.status === "used" : factor.status === "unavailable" && factor.evidence_excerpt === null;
    })) participantHonest += 1;
  }
  const result = Object.freeze({
    case_count: CASES.length,
    full_candidate_preservation_count: preserved,
    expected_top_match_count: topMatches,
    five_factor_complete_count: fiveFactorComplete,
    participant_honesty_count: participantHonest,
    failed_top_case_indexes: Object.freeze(failedTopCaseIndexes),
  });
  if ([preserved, topMatches, fiveFactorComplete, participantHonest].some((count) => count !== CASES.length)) {
    throw new Error(`event goal serendipity eval failed ${JSON.stringify(result)}`);
  }
  return result;
}

async function main() {
  try {
    process.stdout.write(`${JSON.stringify(await runEventGoalSerendipityEval())}\n`);
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}

if (require.main === module) main();

module.exports = { CASES, runEventGoalSerendipityEval };
