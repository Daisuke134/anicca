"use strict";
// CB-1 (spec §10.0-15) for the ask flows: tapping オンライン/対面 or はい/別の場所 must visibly mark
// the original question message as answered (chosen label appended, keyboard removed). A replayed or
// cross-tenant callback must not touch anyone's message — the edit is gated on the same atomic
// consume that guards the DB write.

const test = require("node:test");
const assert = require("node:assert/strict");

const { handleAskCallback } = require("./ask.js");
const { parseUpdate } = require("./telegram.js");

test("CB-1: parseUpdate captures the callback message text so handlers can edit it", () => {
  const parsed = parseUpdate({ callback_query: {
    id: "cb1", from: { id: 7 }, data: "ask:yes:e1:r1",
    message: { message_id: 42, chat: { id: 7 }, text: "金曜の「集会」は、いつものTokyo Hallですか？" },
  } });
  assert.equal(parsed.kind, "callback");
  assert.equal(parsed.messageId, "42");
  assert.equal(parsed.messageText, "金曜の「集会」は、いつものTokyo Hallですか？");
  const noText = parseUpdate({ callback_query: {
    id: "cb2", from: { id: 7 }, data: "ask:yes:e1:r1",
    message: { message_id: 43, chat: { id: 7 } },
  } });
  assert.ok(!("messageText" in noText), "absent text stays absent, not an empty-string lie");
});

function recordingReflect(edits) {
  return async (args) => { edits.push(args); return { ok: true }; };
}

test("CB-1: a consumed online answer edits the original message with the chosen label", async () => {
  const edits = [];
  const out = await handleAskCallback("ask:calendar_online:online:r1", {
    uid: "u1", chatId: "7", actorId: "7", messageId: "42", messageText: "この予定はオンラインですか？",
    telegramToken: "tok", supaUrl: "https://s", supaKey: "k",
    consumeTyped: async () => ({ uid: "u1", event_id: "e1", semantic_key: "sk" }),
    reflectAnswer: recordingReflect(edits),
  });
  assert.equal(out.ok, true);
  assert.equal(edits.length, 1);
  assert.equal(edits[0].label, "オンライン");
  assert.equal(edits[0].messageId, "42");
  assert.equal(edits[0].messageText, "この予定はオンラインですか？");
});

test("CB-1: a consumed offline answer edits the original AND still sends the follow-up question", async () => {
  const edits = [], sent = [];
  const out = await handleAskCallback("ask:calendar_online:offline:r1", {
    uid: "u1", chatId: "7", actorId: "7", messageId: "42", messageText: "この予定はオンラインですか？",
    telegramToken: "tok", supaUrl: "https://s", supaKey: "k",
    consumeTyped: async () => ({ uid: "u1", event_id: "e1", semantic_key: "sk" }),
    reflectAnswer: recordingReflect(edits),
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
  });
  assert.equal(out.ok, true);
  assert.equal(edits.length, 1);
  assert.equal(edits[0].label, "対面");
  assert.equal(sent.length, 1, "the existing follow-up must keep flowing");
  assert.match(sent[0][2], /場所はどこですか/);
});

test("CB-1: an unknown, replayed, or cross-tenant typed callback edits nothing", async () => {
  const explode = async () => { throw new Error("a rejected callback must never edit a message"); };
  const replayed = await handleAskCallback("ask:calendar_online:online:r1", {
    uid: "u1", chatId: "7", actorId: "7", messageId: "42", messageText: "q",
    telegramToken: "tok", supaUrl: "https://s", supaKey: "k",
    consumeTyped: async () => null,
    reflectAnswer: explode,
  });
  assert.equal(replayed.ok, false);
  const crossTenant = await handleAskCallback("ask:calendar_online:online:r1", {
    uid: "u1", chatId: "7", actorId: "7", messageId: "42", messageText: "q",
    telegramToken: "tok", supaUrl: "https://s", supaKey: "k",
    consumeTyped: async () => ({ uid: "someone-else", event_id: "e1" }),
    reflectAnswer: explode,
  });
  assert.equal(crossTenant.ok, false);
  const scopeMismatch = await handleAskCallback("ask:calendar_online:online:r1", {
    uid: "u1", chatId: "7", actorId: "9", messageId: "42", messageText: "q",
    telegramToken: "tok", supaUrl: "https://s", supaKey: "k",
    consumeTyped: explode, reflectAnswer: explode,
  });
  assert.equal(scopeMismatch.ok, false);
});

test("CB-1: a successful はい answer edits the original message; a failed lookup edits nothing", async () => {
  const edits = [];
  const yes = await handleAskCallback("ask:yes:e1:r1", {
    chatId: "7", messageId: "42", messageText: "いつものTokyo Hallですか？", telegramToken: "tok",
    lookupCandidate: async () => ({ uid: "u1", eventId: "e1", candidate: "Tokyo Hall" }),
    patch: async () => true, remember: async () => true,
    reflectAnswer: recordingReflect(edits),
  });
  assert.equal(yes.ok, true);
  assert.equal(edits.length, 1);
  assert.equal(edits[0].label, "はい");

  const miss = await handleAskCallback("ask:yes:e1:r1", {
    chatId: "7", messageId: "42", messageText: "q", telegramToken: "tok",
    lookupCandidate: async () => null,
    reflectAnswer: async () => { throw new Error("no edit without a consumed answer"); },
  });
  assert.equal(miss.ok, false);
});

test("CB-1: 別の場所 marks the original answered and keeps the free-text follow-up", async () => {
  const edits = [], sent = [];
  const no = await handleAskCallback("ask:no:e1:r1", {
    chatId: "7", messageId: "42", messageText: "いつものTokyo Hallですか？",
    telegramToken: "tok", summary: "集会",
    sendMessage: async (...args) => { sent.push(args); return { ok: true }; },
    reflectAnswer: recordingReflect(edits),
  });
  assert.equal(no.ok, true);
  assert.equal(edits.length, 1);
  assert.equal(edits[0].label, "別の場所");
  assert.equal(sent.length, 1);
});
