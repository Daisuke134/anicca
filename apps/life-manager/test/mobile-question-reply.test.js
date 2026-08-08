"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { replyMobileQuestion } = require("../lib/mobile-question.js");
const { createMemoryMobileStore } = require("../lib/mobile-store.js");

test("reply consumes only the authenticated user's open question once", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a", product_locale: "en" }, { uid: "user-b", product_locale: "en" }] });
  await store.createQuestion({ uid: "user-a" }, { id: "question:v1:one", type: "origin", prompt: "Where?" });
  let applied = 0;
  const deps = { store, applyAnswer: async (scope, question, answer) => { applied++; assert.equal(scope.uid, "user-a"); assert.equal(question.id, "question:v1:one"); assert.equal(answer, "Shibuya"); } };
  const result = await replyMobileQuestion({ uid: "user-a", productLocale: "en" }, "question:v1:one", "Shibuya", deps);
  assert.equal(result.status, "answered");
  assert.equal(applied, 1);
  await assert.rejects(() => replyMobileQuestion({ uid: "user-a", productLocale: "en" }, "question:v1:one", "Shibuya", deps), (error) => error.code === "question_stale");
  await assert.rejects(() => replyMobileQuestion({ uid: "user-b", productLocale: "en" }, "question:v1:one", "Shibuya", deps), (error) => error.code === "question_stale");
  assert.equal(applied, 1);
});

test("reply validates text and never acts as a general chat endpoint", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a" }] });
  await assert.rejects(() => replyMobileQuestion({ uid: "user-a" }, null, "hello", { store }), (error) => error.code === "question_required");
  await assert.rejects(() => replyMobileQuestion({ uid: "user-a" }, "question:v1:none", "hello", { store }), (error) => error.code === "question_stale");
});

test("destination replies patch the stored Calendar event before re-analysis", async () => {
  const store = createMemoryMobileStore({ users: [{ uid: "user-a", gmail_account_id: "account-a", calendar_provider: "composio_gcal" }] });
  await store.createQuestion({ uid: "user-a" }, { id: "question:v1:destination", type: "destination", eventId: "event-1", prompt: "Where?" });
  const patches = [];
  const result = await replyMobileQuestion({ uid: "user-a" }, "question:v1:destination", "Tokyo Tower", {
    store,
    calendar: { async patchEvent(uid, input) { patches.push({ uid, input }); return { successful: true }; } },
  });
  assert.equal(result.status, "answered");
  assert.deepEqual(patches, [{ uid: "user-a", input: { calendar_id: "primary", event_id: "event-1", location: "Tokyo Tower" } }]);
});

test("question claim survives downstream failure and resumes apply/outbox before final answer", async () => {
  const calls = [];
  let applyAttempts = 0;
  let status = "open";
  const question = { id: "question-resume", type: "origin", prompt: "Where?", eventId: null, answer: null };
  const store = {
    async claimOpenQuestion(_scope, id, answer) {
      assert.equal(id, question.id);
      if (status === "answered") return null;
      if (status === "claimed" && question.answer !== answer) throw new Error("answer conflict");
      status = "claimed"; question.answer = answer; return { ...question, status };
    },
    async completeQuestionReply() { status = "answered"; calls.push("complete"); return { ...question, status }; },
  };
  const deps = {
    store,
    applyAnswer: async () => { applyAttempts++; calls.push("apply"); if (applyAttempts === 1) throw new (require("../lib/mobile-utils.js").MobileError)("question_apply_failed", "temporary", 502, true); },
    analyzeNextEvent: async (_scope, input) => { calls.push(input.analysisId); return { status: "route_ready" }; },
  };
  await assert.rejects(() => replyMobileQuestion({ uid: "user-a" }, { questionId: question.id, answer: "Shibuya" }, deps), (error) => error.code === "question_apply_failed");
  assert.equal(status, "claimed");
  const result = await replyMobileQuestion({ uid: "user-a" }, { questionId: question.id, answer: "Shibuya" }, deps);
  assert.equal(result.status, "answered");
  assert.equal(status, "answered");
  assert.deepEqual(calls, ["apply", "apply", "question-reply:question-resume", "complete"]);
});
