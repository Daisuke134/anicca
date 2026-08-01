#!/usr/bin/env node
"use strict";

const { buildRollingEventCoverage } = require("../lib/rolling-event-coverage.js");
const { collectLumaInventory } = require("../lib/luma-discovery.js");
const { normalizeLumaEventDetail } = require("../lib/luma-event-detail.js");
const { buildLumaDateInventory } = require("../lib/luma-date-inventory.js");
const { inferEventPreferenceRanking } = require("../lib/event-preference-ranking.js");

const CASES = Object.freeze([
  { preference: "AI agentを作る人との出会いを最優先する。全候補は残す。", expected: "ai-builders", expectedIndex: 0, titles: ["AI Agent Builders Tokyo", "Weekend Pottery Social", "Traditional Tea Gathering"] },
  { preference: "cryptoとweb3のbuilderを高く評価する。全候補は残す。", expected: "crypto-founders", expectedIndex: 1, titles: ["Home Cooking Circle", "Crypto and Web3 Founders Night", "Classical Music Listening"] },
  { preference: "英語で国際的な人と話せるeventを高く評価する。全候補は残す。", expected: "english-network", expectedIndex: 0, titles: ["English International Networking Tokyo", "Silent Drawing Session", "Local History Lecture"] },
  { preference: "startup founderとinvestorに会える機会を優先する。全候補は残す。", expected: "founder-pitch", expectedIndex: 1, titles: ["Tokyo Garden Walk", "Startup Founder Pitch and Investor Night", "Board Game Evening"] },
  { preference: "product managementとuser researchを学べるeventを優先する。全候補は残す。", expected: "product-research", expectedIndex: 0, titles: ["Product Management and User Research Meetup", "Weekend Karaoke", "Ceramic Painting"] },
  { preference: "個人finance、NISA、長期資産形成を学べるeventを優先する。全候補は残す。", expected: "finance-nisa", expectedIndex: 0, titles: ["Personal Finance and NISA Workshop", "Anime Fan Social", "Urban Photography Walk"] },
  { preference: "健康と運動を続けられる対面活動を優先する。全候補は残す。", expected: "health-running", expectedIndex: 0, titles: ["Morning Running and Wellness Club", "Indie Film Screening", "Calligraphy Practice"] },
  { preference: "creative technologyとdigital artの人に会えるeventを優先する。全候補は残す。", expected: "creative-tech", expectedIndex: 0, titles: ["Creative Technology and Digital Art Meetup", "Language Textbook Study", "Neighborhood Cleanup"] },
]);

async function snapshotFor(entry) {
  const slugs = entry.titles.map((title, index) => (
    index === entry.expectedIndex ? entry.expected : `candidate-${entry.expected}-${index}`
  ));
  const coverage = buildRollingEventCoverage({
    tenantId: "connector-eval",
    timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z",
    resolvedDays: [],
  });
  let round = 0;
  const inventory = await collectLumaInventory({
    readSnapshot: async () => {
      round += 1;
      return round === 1 ? slugs.map((slug, index) => ({
        href: `https://luma.com/${slug}`,
        title: entry.titles[index],
        cardText: `${entry.titles[index]} 19:00`,
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
      name: entry.titles[index],
      startDate: `2026-08-02T${String(9 + index).padStart(2, "0")}:00:00.000Z`,
      endDate: `2026-08-02T${String(10 + index).padStart(2, "0")}:00:00.000Z`,
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      eventStatus: "https://schema.org/EventScheduled",
      location: { "@type": "Place", name: "Tokyo public venue" },
    }],
    controls: ["Register"],
  }));
  return buildLumaDateInventory({ coverage, inventory, details, now: "2026-08-02T01:00:00.000Z" });
}

async function runEventPreferenceRankingEval(options = {}) {
  const apiKey = String(options.apiKey || process.env.GEMINI_API_KEY || "").trim();
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  if (!apiKey || typeof fetchImpl !== "function") throw new Error("event preference ranking eval unavailable");
  let preserved = 0;
  let topMatches = 0;
  const failedTopCaseIndexes = [];
  for (const [index, entry] of CASES.entries()) {
    const snapshot = await snapshotFor(entry);
    const expectedRefs = new Set(snapshot.days[0].events.map((event) => event.event_ref));
    const expectedTopRef = `luma-event://event/${entry.expected}`;
    if (!expectedRefs.has(expectedTopRef)) throw new Error("event preference ranking eval fixture invalid");
    const ranking = await inferEventPreferenceRanking({
      dateInventory: snapshot,
      date: "2026-08-02",
      preferences: entry.preference,
    }, { apiKey, fetchImpl });
    const actualRefs = ranking.ranked_events.map((row) => row.event_ref);
    if (actualRefs.length === expectedRefs.size && actualRefs.every((ref) => expectedRefs.has(ref))) preserved += 1;
    if (actualRefs[0] === expectedTopRef) topMatches += 1;
    else failedTopCaseIndexes.push(index + 1);
  }
  const result = Object.freeze({
    case_count: CASES.length,
    full_candidate_preservation_count: preserved,
    expected_top_match_count: topMatches,
    candidate_preservation_rate: preserved / CASES.length,
    expected_top_match_rate: topMatches / CASES.length,
    failed_top_case_indexes: Object.freeze(failedTopCaseIndexes),
  });
  if (preserved !== CASES.length || topMatches !== CASES.length) {
    throw new Error(`event preference ranking eval failed ${JSON.stringify(result)}`);
  }
  return result;
}

async function main() {
  try {
    const result = await runEventPreferenceRankingEval();
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}

if (require.main === module) main();

module.exports = { CASES, runEventPreferenceRankingEval };
