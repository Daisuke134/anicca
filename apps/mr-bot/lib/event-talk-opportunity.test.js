"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  inferEventTalkOpportunity,
  validateEventTalkOpportunity,
} = require("./event-talk-opportunity.js");

const SOURCE = Object.freeze({
  canonicalUrl: "https://luma.com/agent-night",
  title: "AI Agent Night",
  body: "一般参加者を募集しています。5分間のライトニングトーク登壇者も募集中です。8月10日までに https://forms.example.com/speaker から応募してください。",
  now: "2026-08-01T00:00:00.000Z",
});

function openDecision(overrides = {}) {
  return {
    participation_kind: "both",
    talk_format: "lightning_talk",
    application_status: "open",
    should_create_talk_application: true,
    application_url: "https://forms.example.com/speaker",
    evidence_excerpt: "5分間のライトニングトーク登壇者も募集中です。",
    reason: "一般参加に加えて公開中の5分LT登壇枠があるためです。",
    ...overrides,
  };
}

test("公開中の登壇枠だけをtyped decisionとして受理する", () => {
  assert.deepEqual(validateEventTalkOpportunity(openDecision(), SOURCE), openDecision());
  assert.equal(Object.isFrozen(validateEventTalkOpportunity(openDecision(), SOURCE)), true);
});

test("実pageの改行は入力境界で正規化し、本文由来の連続した証拠だけを受理する", () => {
  const source = {
    ...SOURCE,
    body: "一般参加者を募集しています。\n5分間のライトニングトーク登壇者も募集中です。\n8月10日までに https://forms.example.com/speaker から応募してください。",
  };
  assert.deepEqual(validateEventTalkOpportunity(openDecision(), source), openDecision());
});

test("cross-field矛盾、本文にない根拠、架空・危険URLを拒否する", () => {
  assert.throws(() => validateEventTalkOpportunity(openDecision({
    application_status: "closed",
  }), SOURCE), /invariant/i);
  assert.throws(() => validateEventTalkOpportunity(openDecision({
    evidence_excerpt: "本文には存在しない登壇募集です。",
  }), SOURCE), /evidence/i);
  assert.throws(() => validateEventTalkOpportunity(openDecision({
    application_url: "http://127.0.0.1/steal",
  }), SOURCE), /URL/i);
  assert.throws(() => validateEventTalkOpportunity(openDecision({
    application_url: "https://forms.example.com/invented",
  }), SOURCE), /URL/i);
  assert.throws(() => validateEventTalkOpportunity(openDecision({
    unexpected: true,
  }), SOURCE), /schema/i);
});

test("一般参加だけ、締切済み、招待制はtalk applicationを作らない", () => {
  for (const decision of [
    openDecision({
      participation_kind: "audience_only", talk_format: null,
      application_status: "not_offered", should_create_talk_application: false,
      application_url: null, evidence_excerpt: "一般参加者を募集しています。",
      reason: "一般参加だけが公開されています。",
    }),
    openDecision({
      participation_kind: "both", application_status: "closed",
      should_create_talk_application: false, application_url: null,
      reason: "登壇枠は締め切られています。",
    }),
    openDecision({
      participation_kind: "both", application_status: "invite_only",
      should_create_talk_application: false, application_url: null,
      reason: "登壇は主催者からの招待制です。",
    }),
  ]) {
    assert.equal(validateEventTalkOpportunity(decision, SOURCE).should_create_talk_application, false);
  }
});

test("Gemini structured outputへ本文全体をuntrusted dataとして渡しschema検証する", async () => {
  let request;
  const actual = await inferEventTalkOpportunity(SOURCE, {
    apiKey: "fixture-key",
    fetchImpl: async (url, options) => {
      request = { url, options, body: JSON.parse(options.body) };
      return {
        ok: true,
        json: async () => ({
          candidates: [{ content: { parts: [{ text: JSON.stringify(openDecision()) }] } }],
        }),
      };
    },
  });
  assert.deepEqual(actual, openDecision());
  assert.match(request.url, /gemini-2\.5-flash:generateContent/);
  assert.equal(request.options.headers["x-goog-api-key"], "fixture-key");
  const prompt = request.body.contents[0].parts[0].text;
  assert.match(prompt, /untrusted data/i);
  assert.match(prompt, /ライトニングトーク登壇者も募集中/);
  assert.equal(request.body.generationConfig.responseMimeType, "application/json");
  assert.equal(request.body.generationConfig.temperature, 0);
});

test("model failureやinvalid JSONをkeyword fallbackで成功にしない", async () => {
  await assert.rejects(inferEventTalkOpportunity(SOURCE, {
    apiKey: "fixture-key",
    fetchImpl: async () => ({ ok: false, status: 503 }),
  }), /failed/i);
  await assert.rejects(inferEventTalkOpportunity(SOURCE, {
    apiKey: "fixture-key",
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ candidates: [{ content: { parts: [{ text: "not json" }] } }] }),
    }),
  }), /invalid JSON/i);
});
