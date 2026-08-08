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
