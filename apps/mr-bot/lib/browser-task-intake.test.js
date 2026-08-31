"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { handleBrowserTaskMessage } = require("./browser-task-intake.js");

const USER = Object.freeze({
  uid: "u-1",
  paid: true,
  tg_onboard_stage: "done",
  telegram_chat_id: "42",
});

test("a linked paid user's natural-language task is classified, durably queued, then acknowledged", async () => {
  const order = [];
  const result = await handleBrowserTaskMessage({
    text: "Find and register me for a free public AI event",
    chatId: "42",
    messageId: "91",
    updateId: "7001",
    user: USER,
  }, {
    classify: async () => ({
      accepted: true,
      goal: "Find and register the user for a free public AI event",
      actionKind: "registration",
      locale: "en",
      requiresLogin: false,
      principalKind: "none",
    }),
    enqueue: async (input) => {
      order.push(["enqueue", input]);
      return { created: true, job: { id: "job-1", status: "queued" } };
    },
    sendMessage: async (_token, chat, text) => {
      order.push(["send", chat, text]);
      return { ok: true, result: { message_id: 501 } };
    },
    telegramToken: "token",
  });

  assert.deepEqual(result, { handled: true, queued: true, jobId: "job-1", telegramMessageId: "501" });
  assert.deepEqual(order.map(([kind]) => kind), ["enqueue", "send"]);
  assert.match(order[1][2], /job-1/);
});

test("a duplicate Telegram delivery never creates or sends a second visible receipt", async () => {
  let sends = 0;
  const result = await handleBrowserTaskMessage({
    text: "Find and register me",
    chatId: "42",
    messageId: "91",
    updateId: "7001",
    user: USER,
  }, {
    classify: async () => ({
      accepted: true,
      goal: "Find and register the user",
      actionKind: "registration",
      locale: "en",
      requiresLogin: false,
      principalKind: "none",
    }),
    enqueue: async () => ({ created: false, job: { id: "job-1", status: "queued" } }),
    sendMessage: async () => { sends += 1; },
    telegramToken: "token",
  });
  assert.deepEqual(result, { handled: true, queued: false, jobId: "job-1", duplicate: true });
  assert.equal(sends, 0);
});

test("non-tasks and users outside the linked paid boundary preserve the existing Telegram flow", async () => {
  const explode = async () => { throw new Error("must not run"); };
  assert.deepEqual(await handleBrowserTaskMessage({
    text: "hello", chatId: "42", messageId: "1", updateId: "1", user: null,
  }, { classify: explode }), { handled: false });
  assert.deepEqual(await handleBrowserTaskMessage({
    text: "hello", chatId: "42", messageId: "1", updateId: "1",
    user: { ...USER, paid: false },
  }, { classify: explode }), { handled: false });
  assert.deepEqual(await handleBrowserTaskMessage({
    text: "hello", chatId: "42", messageId: "1", updateId: "1", user: USER,
  }, { classify: async () => ({ accepted: false, reason: "not_explicitly_actionable" }) }), {
    handled: false,
    reason: "not_explicitly_actionable",
  });
});
