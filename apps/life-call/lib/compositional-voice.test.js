// lib/compositional-voice.test.js — C1 compositional two-way loop orchestration (control flow, no network).
// Injects stt/llm/tts/send/sendClear seams; asserts the pipeline calls the right things and NEVER opens Live.
"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { createConversation } = require("./compositional-voice.cjs");

// helpers
const loud = () => { const b = Buffer.alloc(320); b.fill(60); return b; };
const quiet = () => Buffer.alloc(320);
function harness(over = {}) {
  const calls = { tts: [], send: 0, sendClear: 0, stt: 0, llm: 0 };
  const c = createConversation({
    event: { summary: "歯医者", location: "新宿デンタル" }, urgency: "firm", lang: "ja", groqKey: "gsk_x",
    tts: async (text) => { calls.tts.push(text); return Buffer.from("AUDIO:" + text); },
    send: async () => { calls.send++; },
    sendClear: async () => { calls.sendClear++; },
    stt: async () => { calls.stt++; return over.transcript !== undefined ? over.transcript : "何分かかる?"; },
    llm: async (_body, _key, onToken) => { calls.llm++; for (const t of (over.llmTokens || ["17分です。", "急いで。"])) await onToken(t); },
    vadOpts: { threshold: 200, silenceMs: 100, frameMs: 20 }, // 5 silent frames = endpoint
    ...over.ctor,
  });
  return { c, calls };
}

test("start(): agent speaks the opening wake line (names event + place), sends audio, Live NOT opened", async () => {
  const { c, calls } = harness();
  await c.start();
  assert.ok(calls.tts.some((t) => /歯医者/.test(t) && /新宿デンタル/.test(t)));
  assert.ok(calls.send >= 1);
  assert.equal(c.liveWsOpened, 0);
});

test("caller utterance → endpoint → STT → LLM → each sentence TTS+send; Live never opened", async () => {
  const { c, calls } = harness();
  await c.pushCallerFrame(loud()); // speech starts
  await c.pushCallerFrame(loud());
  for (let i = 0; i < 6; i++) await c.pushCallerFrame(quiet()); // silence → endpoint
  assert.equal(calls.stt, 1);
  assert.equal(calls.llm, 1);
  assert.deepEqual(calls.tts, ["17分です。", "急いで。"]); // two streamed sentences
  assert.equal(c.liveWsOpened, 0);
});

test("empty transcript (noise) → no LLM call (don't respond to non-speech)", async () => {
  const { c, calls } = harness({ transcript: "" });
  await c.pushCallerFrame(loud());
  for (let i = 0; i < 6; i++) await c.pushCallerFrame(quiet());
  assert.equal(calls.stt, 1);
  assert.equal(calls.llm, 0);
});

test("barge-in: caller speaks while bot is speaking → sendClear called, Live never opened", async () => {
  const { c, calls } = harness();
  // simulate bot speaking then caller barges in
  const p = c.start(); // bot speaking
  await c.pushCallerFrame(loud()); // caller speech while speaking → barge-in
  await p;
  assert.ok(calls.sendClear >= 1);
  assert.equal(c.liveWsOpened, 0);
});

test("liveWsOpened is ALWAYS 0 (no path opens Gemini Live)", async () => {
  const { c } = harness();
  await c.start();
  await c.pushCallerFrame(loud());
  for (let i = 0; i < 6; i++) await c.pushCallerFrame(quiet());
  assert.equal(c.liveWsOpened, 0);
});
