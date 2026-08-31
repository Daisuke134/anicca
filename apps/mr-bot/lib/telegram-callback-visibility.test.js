"use strict";
// CB-1 (spec §10.0-15): every inline-button tap must leave a durable, visible response in chat.
// These helpers are the mechanism: edit the original question message so the chosen answer is
// appended and the keyboard is gone. They wrap the raw Bot API and must NEVER throw — a failed
// edit degrades to "toast only", it must not take the webhook handler down with it.

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  editMessageReplyMarkup,
  markAnswered,
  reflectAnswer,
} = require("./telegram-callback-visibility.js");

function jsonResponse(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test("CB-1: editMessageReplyMarkup posts the edit to the Bot API with a 15s abort signal", async () => {
  const calls = [];
  const out = await editMessageReplyMarkup("tok", "7", "42", { inline_keyboard: [] }, {
    fetchImpl: async (url, init) => { calls.push({ url: String(url), init }); return jsonResponse({ ok: true, result: true }); },
  });
  assert.equal(out.ok, true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "https://api.telegram.org/bottok/editMessageReplyMarkup");
  const body = JSON.parse(calls[0].init.body);
  assert.equal(String(body.chat_id), "7");
  assert.equal(String(body.message_id), "42");
  assert.deepEqual(body.reply_markup, { inline_keyboard: [] });
  assert.ok(calls[0].init.signal instanceof AbortSignal, "every Bot API edit must carry an abort signal");
});

test("CB-1: a null markup removes the keyboard by omitting reply_markup", async () => {
  const calls = [];
  await editMessageReplyMarkup("tok", "7", "42", null, {
    fetchImpl: async (url, init) => { calls.push(JSON.parse(init.body)); return jsonResponse({ ok: true, result: true }); },
  });
  assert.equal(calls.length, 1);
  assert.ok(!("reply_markup" in calls[0]), "null markup means: strip the keyboard entirely");
});

test("CB-1: markAnswered appends the chosen label to the original text and drops the keyboard", async () => {
  const calls = [];
  const out = await markAnswered("tok", "7", "42", "収益の送金先を1つだけ教えてください。", "銀行口座を登録", {
    fetchImpl: async (url, init) => { calls.push({ url: String(url), body: JSON.parse(init.body), init }); return jsonResponse({ ok: true, result: true }); },
  });
  assert.equal(out.ok, true);
  assert.equal(calls[0].url, "https://api.telegram.org/bottok/editMessageText");
  assert.equal(calls[0].body.text, "収益の送金先を1つだけ教えてください。\n\n→ 銀行口座を登録");
  assert.equal(String(calls[0].body.chat_id), "7");
  assert.equal(String(calls[0].body.message_id), "42");
  assert.ok(!("reply_markup" in calls[0].body), "an answered message must not keep tappable buttons");
  assert.ok(calls[0].init.signal instanceof AbortSignal);
});

test("CB-1: non-2xx, thrown fetch, and api-level failure all return ok:false without throwing", async () => {
  const non2xx = await markAnswered("tok", "7", "42", "q", "a", { fetchImpl: async () => jsonResponse({ ok: false }, 400) });
  assert.equal(non2xx.ok, false);
  const thrown = await editMessageReplyMarkup("tok", "7", "42", null, { fetchImpl: async () => { throw new Error("network down"); } });
  assert.equal(thrown.ok, false);
  const apiFalse = await markAnswered("tok", "7", "42", "q", "a", { fetchImpl: async () => jsonResponse({ ok: false, description: "message is not modified" }) });
  assert.equal(apiFalse.ok, false);
});

test("CB-1: an unaddressable edit (missing token/chat/message) is a quiet no-op, never a fetch", async () => {
  const explode = async () => { throw new Error("must not reach the network"); };
  assert.equal((await markAnswered("", "7", "42", "q", "a", { fetchImpl: explode })).ok, false);
  assert.equal((await markAnswered("tok", "", "42", "q", "a", { fetchImpl: explode })).ok, false);
  assert.equal((await editMessageReplyMarkup("tok", "7", "", null, { fetchImpl: explode })).ok, false);
});

test("CB-1: reflectAnswer edits the text when the original is known, else at least strips the keyboard", async () => {
  const calls = [];
  const fetchImpl = async (url, init) => { calls.push({ url: String(url), body: JSON.parse(init.body) }); return jsonResponse({ ok: true, result: true }); };

  await reflectAnswer({ token: "tok", chatId: "7", messageId: "42", messageText: "質問", label: "はい", fetchImpl });
  assert.match(calls[0].url, /editMessageText$/);
  assert.equal(calls[0].body.text, "質問\n\n→ はい");

  await reflectAnswer({ token: "tok", chatId: "7", messageId: "42", messageText: "", label: "はい", fetchImpl });
  assert.match(calls[1].url, /editMessageReplyMarkup$/, "no original text still must kill the stale keyboard");
  assert.ok(!("reply_markup" in calls[1].body));
});
