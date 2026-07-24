"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  runPersonalizedAction,
  selectManagedAccount,
  hasCompletedAction,
} = require("./personalized-action");

const intents = [
  {
    id: "goal-10i",
    uid: "current-user",
    kind: "explicit_goal",
    statement: "Complete one personalized action from current context",
    provenance: {
      source: "user_message",
      evidence: "explicit atomic 10i instruction",
      observedAt: "2026-07-24T00:00:00.000Z",
    },
    confidenceTier: "explicit",
    confidence: 0.9,
    expiresAt: "2026-07-25T00:00:00.000Z",
    status: "active",
    supersedes: null,
  },
  {
    id: "delegation-10i",
    uid: "current-user",
    kind: "delegation",
    statement: "Delegate one reversible web or email action and post-action reports",
    provenance: {
      source: "user_message",
      evidence: "explicit atomic 10i instruction",
      observedAt: "2026-07-24T00:00:00.000Z",
    },
    confidenceTier: "explicit",
    confidence: 0.9,
    expiresAt: "2026-07-25T00:00:00.000Z",
    status: "active",
    supersedes: null,
  },
];

const candidate = {
  id: "upcoming-event-prep",
  category: "life_admin",
  description: "Send one preparation brief for a real upcoming calendar event",
  benefit: "medium",
  urgency: "medium",
  cost: "low",
  risk: "low",
  reversible: true,
  supportsIntentIds: ["goal-10i", "delegation-10i"],
  violatesIntentIds: [],
  delegationId: "delegation-10i",
  materialPreference: false,
  previouslyAsked: false,
};

test("an explicit delegated reversible candidate acts once and reports after the email receipt", async () => {
  const calls = [];
  const receipt = await runPersonalizedAction({
    intents,
    candidate,
    nowMs: Date.parse("2026-07-24T09:00:00.000Z"),
    executeEmail: async () => {
      calls.push("email");
      return { provider_id: "gmail-message-1", message_id: "<receipt@example.invalid>" };
    },
    createCalendarReport: async () => {
      calls.push("calendar");
      return { provider_id: "calendar-event-1" };
    },
    sendTelegramReport: async ({ honestFailure }) => {
      calls.push(`telegram:${honestFailure}`);
      return { provider_id: "telegram-message-1" };
    },
  });

  assert.deepEqual(calls, ["email", "calendar", "telegram:false"]);
  assert.deepEqual(receipt, {
    schema_version: 1,
    candidate_id: "upcoming-event-prep",
    decision: "act",
    decision_reason: "delegated-reversible-low-risk:delegation-10i",
    outcome: "completed",
    email_provider_id: "gmail-message-1",
    email_message_id: "<receipt@example.invalid>",
    calendar_provider_id: "calendar-event-1",
    telegram_provider_id: "telegram-message-1",
    honest_failure: false,
    approval_questions: 0,
  });
});

test("an email failure creates no fake email receipt and sends one honest post-action report", async () => {
  const calls = [];
  const receipt = await runPersonalizedAction({
    intents,
    candidate,
    nowMs: Date.parse("2026-07-24T09:00:00.000Z"),
    executeEmail: async () => {
      calls.push("email");
      throw new Error("raw provider detail must not escape");
    },
    createCalendarReport: async () => {
      calls.push("calendar");
      return { provider_id: "calendar-event-2" };
    },
    sendTelegramReport: async ({ honestFailure }) => {
      calls.push(`telegram:${honestFailure}`);
      return { provider_id: "telegram-message-2" };
    },
  });

  assert.deepEqual(calls, ["email", "calendar", "telegram:true"]);
  assert.equal(receipt.outcome, "reported_failure");
  assert.equal(receipt.email_provider_id, null);
  assert.equal(receipt.email_message_id, null);
  assert.equal(receipt.honest_failure, true);
  assert.equal(JSON.stringify(receipt).includes("raw provider"), false);
  assert.equal(receipt.approval_questions, 0);
});

test("a non-act decision causes zero provider calls and never asks an unnecessary question", async () => {
  let providerCalls = 0;
  const receipt = await runPersonalizedAction({
    intents: [],
    candidate: { ...candidate, delegationId: null, supportsIntentIds: [] },
    nowMs: Date.parse("2026-07-24T09:00:00.000Z"),
    executeEmail: async () => { providerCalls += 1; },
    createCalendarReport: async () => { providerCalls += 1; },
    sendTelegramReport: async () => { providerCalls += 1; },
  });
  assert.equal(providerCalls, 0);
  assert.equal(receipt.decision, "skip");
  assert.equal(receipt.approval_questions, 0);
});

test("production context falls back only to one exact Gmail+Calendar managed account", () => {
  const account = { email: "managed@example.invalid", services: ["calendar", "gmail"] };
  assert.equal(selectManagedAccount({ email: null }, [account]), "managed@example.invalid");
  assert.equal(selectManagedAccount({ email: null }, [account, { ...account, email: "other@example.invalid" }]), null);
  assert.equal(selectManagedAccount({ email: "profile@example.invalid" }, []), "profile@example.invalid");
});

test("provider-side calendar marker prevents a second 10i execution", () => {
  assert.equal(hasCompletedAction([]), false);
  assert.equal(hasCompletedAction([{ id: "event-1" }]), true);
  assert.equal(hasCompletedAction({ items: [{ id: "event-1" }] }), true);
});
