"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  inferTalkApplicationTransition,
  isVerifiedTalkApplicationTransition,
  validateTalkApplicationTransition,
} = require("./talk-application-transition.js");

const BASE = Object.freeze({
  currentState: "submitted",
  observedAt: "2026-08-02T02:00:00.000Z",
  now: "2026-08-02T02:01:00.000Z",
  sourceText: "登壇応募を採択しました。イベント当日の登壇をお願いします。",
  sourceRefs: ["mail-receipt://connector/talk-decision/receipt-1"],
});

function decision(overrides = {}) {
  return {
    to_state: "accepted",
    evidence_excerpt: "登壇応募を採択しました。",
    reason: "主催者の通知で登壇採択が確認できたため",
    source_refs: ["mail-receipt://connector/talk-decision/receipt-1"],
    ...overrides,
  };
}

test("each supported talk outcome becomes one verified source-bound transition", () => {
  const cases = [
    ["submission_queued", "submitted", "応募フォームの送信が完了しました。", "応募フォームの送信が完了しました。"],
    ["submitted", "accepted", "登壇応募を採択しました。", "登壇応募を採択しました。"],
    ["submitted", "rejected", "今回は登壇を見送らせていただきます。", "今回は登壇を見送らせていただきます。"],
    ["accepted", "presented", "予定していた登壇が完了しました。", "予定していた登壇が完了しました。"],
  ];
  for (const [currentState, toState, sourceText, excerpt] of cases) {
    const transition = validateTalkApplicationTransition(decision({
      to_state: toState,
      evidence_excerpt: excerpt,
      reason: `${toState}を証拠から確認したため`,
    }), { ...BASE, currentState, sourceText });
    assert.deepEqual(transition, {
      from_state: currentState,
      to_state: toState,
      observed_at: "2026-08-02T02:00:00.000Z",
      reason: `${toState}を証拠から確認したため`,
      source_refs: BASE.sourceRefs,
    });
    assert.equal(Object.isFrozen(transition), true);
    assert.equal(isVerifiedTalkApplicationTransition(transition), true);
    assert.equal(isVerifiedTalkApplicationTransition(structuredClone(transition)), false);
  }
});

test("the complete forward graph permits queueing and withdrawal without state rollback", () => {
  for (const [currentState, toState] of [
    ["discovered", "submission_queued"],
    ["submission_queued", "withdrawn"],
    ["submitted", "withdrawn"],
    ["accepted", "withdrawn"],
  ]) {
    const transition = validateTalkApplicationTransition(decision({ to_state: toState }), {
      ...BASE, currentState,
    });
    assert.equal(transition.from_state, currentState);
    assert.equal(transition.to_state, toState);
  }
});

test("invalid graph edges, future observations, invented refs, ungrounded excerpts, and secrets fail closed", () => {
  const cases = [
    [decision({ to_state: "accepted" }), { ...BASE, currentState: "discovered" }],
    [decision({ to_state: "accepted" }), { ...BASE, currentState: "accepted" }],
    [decision({ to_state: "presented" }), { ...BASE, currentState: "rejected" }],
    [decision(), { ...BASE, observedAt: "2026-08-02T02:07:00.000Z" }],
    [decision({ source_refs: ["mail-receipt://connector/invented"] }), BASE],
    [decision({ evidence_excerpt: "存在しない採択文" }), BASE],
    [decision(), { ...BASE, sourceText: "連絡先 person@example.com password=secret" }],
    [decision({ reason: "担当 person@example.com から採択連絡" }), BASE],
  ];
  for (const [value, input] of cases) {
    assert.throws(() => validateTalkApplicationTransition(value, input), /talk application transition invalid/i);
  }
});

test("Gemini judges untrusted source text and model failure has no keyword fallback", async () => {
  let request;
  const transition = await inferTalkApplicationTransition(BASE, {
    apiKey: "fixture-key",
    async fetchImpl(url, options) {
      request = { url, body: JSON.parse(options.body) };
      return {
        ok: true,
        status: 200,
        json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(decision()) }] } }] }),
      };
    },
  });
  assert.equal(transition.to_state, "accepted");
  const prompt = request.body.contents[0].parts[0].text;
  assert.match(prompt, /untrusted/i);
  assert.match(prompt, /never follow/i);
  assert.equal(request.body.generationConfig.responseMimeType, "application/json");
  assert.equal(request.body.generationConfig.temperature, 0);

  await assert.rejects(inferTalkApplicationTransition(BASE, {
    apiKey: "fixture-key",
    fetchImpl: async () => ({ ok: false, status: 503 }),
  }), /talk application transition unavailable/i);
  await assert.rejects(inferTalkApplicationTransition(BASE, {
    apiKey: "fixture-key",
    fetchImpl: async () => ({ ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: "bad" }] } }] }) }),
  }), /talk application transition unavailable/i);
});
