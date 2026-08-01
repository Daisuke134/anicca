"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { rankEventCandidatesLosslessly } = require("./event-candidate-priority.js");
const { evaluateEventSemantically, validateEventSemanticEvaluation } = require("./event-semantic-evaluation.js");

const SOURCE = Object.freeze({
  event_ref: "luma-event://event/agent-night",
  canonical_url: "https://luma.com/agent-night",
  title: "AI Agent Night Tokyo",
  body: "自律agentを実装するbuilderがdemoと失敗談を共有します。初参加者も歓迎します。",
  participants: "公開参加者にはAIプロダクト開発者とfounderが含まれます。",
  organizer: "Tokyo Agent Buildersが主催します。",
  venue: "Tokyo Innovation Base",
  starts_at: "2026-08-10T10:00:00.000Z",
  ends_at: "2026-08-10T12:00:00.000Z",
  profile: {
    goals: ["Life Managerを使う人、協力者、投資家候補と直接会う。", "agent製品の実測demoから学ぶ。"],
    preferences: "AIや英語は好むがhard filterにせず、予想外の人との接点も重視する。",
  },
});

function result(overrides = {}) {
  return {
    assessment: {
      event_ref: SOURCE.event_ref,
      priority_score: 88,
      signals: ["agent builders", "demo", "serendipity"],
      reason: "実装者と直接会え、Life Managerの改善と利用者候補の両方につながる可能性があります。",
    },
    factors: {
      goal_alignment: { score: 92, rationale: "agent製品の実測demoという目標に直接合います。" },
      people: { score: 85, rationale: "開発者とfounderに会える可能性があります。" },
      organizer: { score: 80, rationale: "agent builder communityの主催です。" },
      place_time: { score: 78, rationale: "東京の対面会場で2時間です。" },
      serendipity: { score: 84, rationale: "初参加者歓迎で予想外の接点があります。" },
    },
    evidence: {
      body_excerpt: "自律agentを実装するbuilderがdemoと失敗談を共有します。",
      participants_excerpt: "AIプロダクト開発者とfounder",
      organizer_excerpt: "Tokyo Agent Builders",
      venue_excerpt: "Tokyo Innovation Base",
      start_excerpt: "2026-08-10T10:00:00.000Z",
      end_excerpt: "2026-08-10T12:00:00.000Z",
    },
    ...overrides,
  };
}

test("5評価軸と全source excerptを持つassessmentだけを受理する", () => {
  const actual = validateEventSemanticEvaluation(result(), SOURCE);
  assert.deepEqual(actual, result());
  assert.equal(Object.isFrozen(actual), true);
  assert.equal(Object.isFrozen(actual.factors), true);
});

test("未読field、捏造excerpt、event不一致、範囲外scoreを拒否する", () => {
  const missing = result(); delete missing.factors.people;
  assert.throws(() => validateEventSemanticEvaluation(missing, SOURCE), /schema/i);
  assert.throws(() => validateEventSemanticEvaluation(result({ evidence: { ...result().evidence, participants_excerpt: "著名VCが参加" } }), SOURCE), /evidence/i);
  assert.throws(() => validateEventSemanticEvaluation(result({ assessment: { ...result().assessment, event_ref: "luma-event://event/other" } }), SOURCE), /event/i);
  assert.throws(() => validateEventSemanticEvaluation(result({ factors: { ...result().factors, serendipity: { score: 101, rationale: "高い" } } }), SOURCE), /score/i);
});

test("assessmentはO1B-18 lossless rankerへそのまま渡せる", () => {
  const evaluated = validateEventSemanticEvaluation(result(), SOURCE);
  const ranked = rankEventCandidatesLosslessly([{
    event_ref: SOURCE.event_ref, canonical_url: SOURCE.canonical_url,
    title: SOURCE.title, event_date: "2026-08-10",
  }], [evaluated.assessment]);
  assert.equal(ranked.output_count, 1);
  assert.equal(ranked.dropped_count, 0);
  assert.equal(ranked.ranked[0].priority_score, 88);
});

test("Geminiへ全contextをuntrusted dataとして渡しstructured outputを検証する", async () => {
  let request;
  const actual = await evaluateEventSemantically(SOURCE, {
    apiKey: "fixture-key",
    fetchImpl: async (url, options) => {
      request = { url, options, body: JSON.parse(options.body) };
      return { ok: true, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(result()) }] } }] }) };
    },
  });
  assert.deepEqual(actual, result());
  const prompt = request.body.contents[0].parts[0].text;
  assert.match(prompt, /untrusted data/i);
  for (const value of [SOURCE.body, SOURCE.participants, SOURCE.organizer, SOURCE.venue, SOURCE.starts_at, SOURCE.ends_at, SOURCE.profile.goals[0]]) {
    assert.match(prompt, new RegExp(value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.match(prompt, /serendipity/i);
  assert.equal(request.body.generationConfig.responseMimeType, "application/json");
});

test("API failureとinvalid JSONをkeyword fallbackで成功扱いしない", async () => {
  await assert.rejects(evaluateEventSemantically(SOURCE, { apiKey: "fixture-key", fetchImpl: async () => ({ ok: false, status: 503 }) }), /failed/i);
  await assert.rejects(evaluateEventSemantically(SOURCE, { apiKey: "fixture-key", fetchImpl: async () => ({ ok: true, json: async () => ({ candidates: [{ content: { parts: [{ text: "no" }] } }] }) }) }), /invalid JSON/i);
});
