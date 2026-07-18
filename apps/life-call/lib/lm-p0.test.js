"use strict";

const test = require("node:test");
const assert = require("node:assert");
const {
  telnyxDialBody,
  telnyxStreamingStartBody,
} = require("./call-logic.js");
const {
  setWebhook,
  answerCallbackQuery,
  parseUpdate,
  routeCallbackData,
} = require("./telegram.js");
const {
  agentSearchCandidate,
  closedAskMessage,
  handleAskCallback,
} = require("./ask.js");
const { makeUnipileMail } = require("./transport/mail-unipile.js");

test("LM-24: both Telnyx streaming bodies target the caller leg", () => {
  assert.equal(telnyxDialBody({ connectionId: "c", to: "+1", from: "+2", streamUrl: "wss://x" }).stream_bidirectional_target_legs, "self");
  assert.equal(telnyxStreamingStartBody({ streamUrl: "wss://x" }).stream_bidirectional_target_legs, "self");
});

test("LM-23: webhook subscribes to messages and callbacks; callbacks are answered", async () => {
  const original = global.fetch;
  const calls = [];
  global.fetch = async (url, init) => {
    calls.push({ url, body: JSON.parse(init.body) });
    return { json: async () => ({ ok: true }) };
  };
  try {
    await setWebhook("t", "https://x/telegram", "s");
    await answerCallbackQuery("t", "cb-1", "Saved");
    assert.deepEqual(calls[0].body.allowed_updates, ["message", "callback_query"]);
    assert.match(calls[1].url, /answerCallbackQuery$/);
    assert.deepEqual(calls[1].body, { callback_query_id: "cb-1", text: "Saved" });
  } finally { global.fetch = original; }
});

test("LM-23: parseUpdate preserves message fields and parses callback_query", () => {
  assert.deepEqual(parseUpdate({ message: { chat: { id: 7 }, from: { id: 8 }, text: " /start x " } }), {
    kind: "message", chatId: "7", userId: "8", text: "/start x", isStart: true,
  });
  assert.deepEqual(parseUpdate({ callback_query: { id: "cb", from: { id: 8 }, data: "ask:yes:e1:r1", message: { chat: { id: 7 } } } }), {
    kind: "callback", chatId: "7", userId: "8", data: "ask:yes:e1:r1", callbackQueryId: "cb",
  });
});

test("LM-23: callback router dispatches ask:* and ignores unknown prefixes", async () => {
  const routed = [], logs = [];
  assert.equal(await routeCallbackData("ask:yes:e:r", { ask: async (data) => { routed.push(data); return "ok"; } }), "ok");
  assert.deepEqual(routed, ["ask:yes:e:r"]);
  assert.equal(await routeCallbackData("late:still:t", { late: async (data) => { routed.push(data); return "late"; } }), "late");
  assert.deepEqual(routed, ["ask:yes:e:r", "late:still:t"]);
  assert.deepEqual(await routeCallbackData("leave:no:e", {}, (line) => logs.push(line)), { ignored: true });
  assert.match(logs[0], /unknown callback prefix/);
});

test("LM-3: Unipile searchInbox uses the verified search query parameter", async () => {
  const original = global.fetch;
  let requested = "";
  global.fetch = async (url) => { requested = url; return { json: async () => ({ items: [{ subject: "Venue" }] }) }; };
  try {
    const items = await makeUnipileMail({ accountId: "a", token: "t", dsn: "api.example" }).searchInbox("MUIT 集会");
    assert.equal(items.length, 1);
    assert.equal(new URL(requested).searchParams.get("search"), "MUIT 集会");
  } finally { global.fetch = original; }
});

test("LM-3: search then extraction uses two Gemini calls and Gmail snippets", async () => {
  const bodies = [];
  const raw = async (body) => {
    bodies.push(body);
    if (bodies.length === 1) return { candidates: [{ content: { parts: [{ text: "Official page says Tokyo Hall. Gmail confirms it." }] } }] };
    return { candidates: [{ content: { parts: [{ functionCall: { name: "submit_candidate", args: { found: true, candidate: "Tokyo Hall", source: "gmail" } } }] } }] };
  };
  const out = await agentSearchCandidate({ summary: "MUIT 集会", description: "" }, {
    geminiKey: "k", geminiRaw: raw,
    mail: { ready: () => true, searchInbox: async () => [{ subject: "MUIT", body: "Venue: Tokyo Hall" }] },
  });
  assert.deepEqual(out, { found: true, candidate: "Tokyo Hall", source: "gmail" });
  assert.deepEqual(bodies[0].tools, [{ google_search: {} }]);
  assert.match(bodies[0].contents[0].parts[0].text, /Tokyo Hall/);
  assert.ok(bodies[1].tools[0].functionDeclarations[0].name === "submit_candidate");
  assert.equal(bodies[1].tools.some((t) => t.google_search), false);
});

test("LM-3: candidate found builds the exact closed-question buttons", () => {
  assert.deepEqual(closedAskMessage({ id: "e1", summary: "MUIT 集会" }, "Tokyo Hall", "r1"), {
    text: "📍 “MUIT 集会” は Tokyo Hall で開催ですか？",
    extra: { reply_markup: { inline_keyboard: [[
      { text: "はい", callback_data: "ask:yes:e1:r1" },
      { text: "いいえ", callback_data: "ask:no:e1:r1" },
    ]] } },
  });
});

test("LM-3: yes callback writes persisted candidate; no falls back to free text", async () => {
  const patches = [], messages = [];
  const yes = await handleAskCallback("ask:yes:e1:r1", {
    lookupCandidate: async () => ({ uid: "u1", eventId: "e1", candidate: "Tokyo Hall", summary: "MUIT 集会" }),
    patch: async (...args) => patches.push(args),
    remember: async () => true,
  });
  assert.equal(yes.ok, true);
  assert.deepEqual(patches[0], ["u1", "e1", "Tokyo Hall"]);

  const no = await handleAskCallback("ask:no:e1:r1", {
    chatId: "7", telegramToken: "t", summary: "MUIT 集会",
    sendMessage: async (...args) => { messages.push(args); return { ok: true }; },
  });
  assert.equal(no.fallback, true);
  assert.match(messages[0][2], /Where is “MUIT 集会”/);
});

test("LM-3: no candidate is a silent null so existing open question remains", async () => {
  const out = await agentSearchCandidate({ summary: "造語イベント" }, {
    geminiKey: "k",
    geminiRaw: async (_body, _key) => ({ candidates: [{ content: { parts: [{ text: "No reliable venue." }] } }] }),
    mail: { ready: () => false, searchInbox: async () => { throw new Error("must skip"); } },
  });
  assert.deepEqual(out, { found: false, candidate: "", source: "" });
});
