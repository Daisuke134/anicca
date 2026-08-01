"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  inferAcceptedTalkTimeline,
  isVerifiedAcceptedTalkTimeline,
  validateAcceptedTalkTimeline,
} = require("./accepted-talk-timeline.js");

const INPUT = Object.freeze({
  acceptedAt: "2026-08-02T00:30:00.000Z",
  eventStartAt: "2026-08-07T10:00:00.000Z",
  eventEndAt: "2026-08-07T13:00:00.000Z",
  ticketRef: "object://sha256/" + "a".repeat(64),
  sourceRefs: [
    "evidence://connector/talk-acceptance-mail",
    "evidence://connector/luma-event-detail",
    "evidence://connector/luma-ticket",
  ],
  sourceText: "登壇採択です。スライドは8月5日18時までに提出してください。会場は六本木ヒルズ森タワー26F Event Spaceです。QRは別途発行します。",
  now: "2026-08-02T01:00:00.000Z",
});

function decision(overrides = {}) {
  return {
    slide_status: "known",
    slide_due_at: "2026-08-05T09:00:00.000Z",
    slide_evidence_excerpt: "スライドは8月5日18時までに提出してください。",
    venue_status: "known",
    venue_name: "六本木ヒルズ森タワー 26F Event Space",
    venue_address: "東京都港区六本木6丁目10-1",
    venue_evidence_excerpt: "会場は六本木ヒルズ森タワー26F Event Spaceです。",
    ticket_requirement: "required",
    follow_up_at: "2026-08-05T10:00:00.000Z",
    follow_up_purpose: "スライド提出後に受領確認を行う",
    follow_up_reason: "提出済み資料が主催者側で受領されたか確認するため",
    follow_up_evidence_excerpt: "スライドは8月5日18時までに提出してください。",
    source_refs: [
      "evidence://connector/talk-acceptance-mail",
      "evidence://connector/luma-event-detail",
      "evidence://connector/luma-ticket",
    ],
    ...overrides,
  };
}

test("accepted source becomes one verified timeline with slide, appearance, venue, QR, and follow-up", () => {
  const timeline = validateAcceptedTalkTimeline(decision(), INPUT);
  assert.deepEqual(timeline, {
    accepted_at: "2026-08-02T00:30:00.000Z",
    slide_status: "known",
    slide_due_at: "2026-08-05T09:00:00.000Z",
    appearance_start_at: "2026-08-07T10:00:00.000Z",
    appearance_end_at: "2026-08-07T13:00:00.000Z",
    venue_status: "known",
    venue_name: "六本木ヒルズ森タワー 26F Event Space",
    venue_address: "東京都港区六本木6丁目10-1",
    ticket_status: "ready",
    ticket_ref: "object://sha256/" + "a".repeat(64),
    follow_up_at: "2026-08-05T10:00:00.000Z",
    follow_up_purpose: "スライド提出後に受領確認を行う",
    follow_up_reason: "提出済み資料が主催者側で受領されたか確認するため",
    source_refs: INPUT.sourceRefs,
  });
  assert.equal(Object.isFrozen(timeline), true);
  assert.equal(isVerifiedAcceptedTalkTimeline(timeline), true);
  assert.equal(isVerifiedAcceptedTalkTimeline(structuredClone(timeline)), false);
});

test("missing slide, venue, and QR remain explicitly pending instead of becoming false success", () => {
  const input = { ...INPUT, ticketRef: null, sourceText: "登壇採択です。詳細は後日案内します。" };
  const timeline = validateAcceptedTalkTimeline(decision({
    slide_status: "pending",
    slide_due_at: null,
    slide_evidence_excerpt: "詳細は後日案内します。",
    venue_status: "pending",
    venue_name: null,
    venue_address: null,
    venue_evidence_excerpt: "詳細は後日案内します。",
    ticket_requirement: "unknown",
    follow_up_at: "2026-08-03T00:30:00.000Z",
    follow_up_purpose: "未案内の締切・会場・QRを主催者へ確認する",
    follow_up_reason: "採択通知に必要情報がまだ記載されていないため",
    follow_up_evidence_excerpt: "詳細は後日案内します。",
    source_refs: ["evidence://connector/talk-acceptance-mail"],
  }), input);
  assert.equal(timeline.slide_status, "pending");
  assert.equal(timeline.slide_due_at, null);
  assert.equal(timeline.venue_status, "pending");
  assert.equal(timeline.venue_name, null);
  assert.equal(timeline.ticket_status, "pending");
  assert.equal(timeline.ticket_ref, null);
});

test("timestamp contradictions, invented refs, inconsistent fields, and raw secrets fail closed", () => {
  const cases = [
    [decision({ slide_due_at: "2026-08-08T09:00:00.000Z" }), INPUT],
    [decision({ source_refs: ["evidence://connector/invented"] }), INPUT],
    [decision({ slide_status: "pending", slide_due_at: "2026-08-05T09:00:00.000Z" }), INPUT],
    [decision({ venue_status: "pending" }), INPUT],
    [decision({ ticket_requirement: "not_required" }), INPUT],
    [decision(), { ...INPUT, sourceText: "contact person@example.com password=secret" }],
  ];
  for (const [value, input] of cases) {
    assert.throws(() => validateAcceptedTalkTimeline(value, input), /accepted talk timeline/i);
  }
});

test("Gemini receives untrusted text and returns no regex or keyword fallback", async () => {
  let request;
  const timeline = await inferAcceptedTalkTimeline(INPUT, {
    apiKey: "fixture-key",
    async fetchImpl(url, options) {
      request = { url, options, body: JSON.parse(options.body) };
      return {
        ok: true,
        status: 200,
        json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(decision()) }] } }] }),
      };
    },
  });
  assert.equal(timeline.ticket_status, "ready");
  const prompt = request.body.contents[0].parts[0].text;
  assert.match(prompt, /untrusted/i);
  assert.match(prompt, /never follow/i);
  assert.equal(request.body.generationConfig.responseMimeType, "application/json");
  assert.equal(request.body.generationConfig.temperature, 0);

  await assert.rejects(inferAcceptedTalkTimeline(INPUT, {
    apiKey: "fixture-key",
    fetchImpl: async () => ({ ok: false, status: 503 }),
  }), /unavailable/i);
  await assert.rejects(inferAcceptedTalkTimeline(INPUT, {
    apiKey: "fixture-key",
    fetchImpl: async () => ({ ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: "bad" }] } }] }) }),
  }), /unavailable/i);
});
