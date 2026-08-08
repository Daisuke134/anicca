"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { projectSemanticMessage, assertLocalizedText, projectLocalizedRouteName } = require("../lib/mobile-localization.js");

function row(overrides = {}) {
  return {
    id: "message:v1:route-1", sequence: 1, createdAt: "2026-08-08T00:00:00.000Z", key: "chat.route_ready",
    args: { eventTitle: "userContent.eventTitle", leaveAt: "route.leaveAt", arriveAt: "route.arriveAt", bufferSeconds: "route.bufferSeconds" },
    userContent: { eventTitle: "打ち合わせ", eventLocation: "渋谷駅" },
    route: {
      status: "route_ready", provider: "transit", providerAttribution: "Transit API", computedAt: "2026-08-08T00:00:00.000Z",
      timezone: "Asia/Tokyo", eventId: "event-1", origin: { displayNames: { en: "Shibuya Station", ja: "渋谷駅" }, userContent: "自宅" },
      destination: { displayNames: { en: "Roppongi", ja: "六本木" }, userContent: "六本木" }, leaveAt: "2026-08-08T01:00:00.000Z",
      arriveAt: "2026-08-08T01:27:00.000Z", durationSeconds: 1620, bufferSeconds: 180, transferCount: 1,
      fare: { currency: "JPY", amount: 220, medium: "IC" }, geometry: null,
      steps: [{ sequence: 1, mode: "train", instruction: { en: "Take the Toei Oedo Line", ja: "都営大江戸線に乗る" }, from: { en: "渋谷駅", ja: "渋谷駅" }, to: { en: "六本木", ja: "六本木" }, service: { en: "Toei Oedo Line", ja: "都営大江戸線" }, headsign: { en: "toward Daimon", ja: "大門方面" }, platform: null, departAt: "2026-08-08T01:05:00.000Z", arriveAt: "2026-08-08T01:20:00.000Z", durationSeconds: 900 }],
    },
    ...overrides,
  };
}

test("semantic message projection is fully English or fully Japanese while preserving user content", () => {
  const english = projectSemanticMessage(row(), "en");
  assert.match(english.text, /Your next event/u);
  assert.doesNotMatch(english.text, /[\u3040-\u30ff\u3400-\u9fff]/u);
  assert.equal(english.userContent.eventTitle, "打ち合わせ");
  assert.equal(english.route.origin.displayName, "Shibuya Station");

  const japanese = projectSemanticMessage(row(), "ja");
  assert.match(japanese.text, /次の予定/u);
  assert.doesNotMatch(japanese.text, /Your next event|Leave by|arrive with/u);
  assert.equal(japanese.userContent.eventTitle, "打ち合わせ");
  assert.equal(japanese.route.origin.displayName, "渋谷駅");
});

test("locale guard rejects generated mixed scripts and unknown provider names", () => {
  assert.throws(() => assertLocalizedText("en", "English 渋谷"), (error) => error.code === "mixed_locale");
  assert.throws(() => assertLocalizedText("ja", "Your next event is ready"), (error) => error.code === "mixed_locale");
  assert.equal(projectLocalizedRouteName({ displayNames: { en: "Shibuya", ja: "渋谷" } }, "ja"), "渋谷");
  assert.throws(() => projectLocalizedRouteName({ displayNames: { en: "Shibuya" } }, "ja"), (error) => error.code === "localization_unavailable");
});

test("question and route-unavailable projections localize their concrete reason", () => {
  const destination = projectSemanticMessage({
    ...row(), key: "chat.needs_information", type: "question",
    question: { id: "question-1", type: "destination", prompt: "Where will this event take place?" },
    route: null,
  }, "ja");
  assert.equal(destination.question.prompt, "予定の場所を教えてください。");
  assert.match(destination.text, /予定の場所/u);
  assert.doesNotMatch(destination.question.prompt, /Where|event/u);

  const unavailable = projectSemanticMessage({
    ...row(), key: "chat.route_unavailable", type: "route_unavailable", route: null,
    args: { reason: "provider_unavailable" },
  }, "en");
  assert.match(unavailable.text, /provider/u);
});
