// lib/voice-turn.test.js — C1 compositional voice, pure turn-logic (no live key/network).
"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { sentenceSplitter, energyVAD, decideBargeIn, chooseSttProvider, chooseLlmProvider, buildLlmChat } = require("./voice-turn.cjs");

test("sentenceSplitter: emits a sentence as soon as it ends; buffers the rest", () => {
  const s = sentenceSplitter();
  assert.deepEqual(s.push("いま出ないと"), []);          // no terminator yet
  assert.deepEqual(s.push("間に合いません。次は"), ["いま出ないと間に合いません。"]); // 。 flushes
  assert.deepEqual(s.push("中央線です！ほら"), ["次は中央線です！"]);              // ！ flushes
  assert.deepEqual(s.flush(), ["ほら"]);                 // remainder on flush
});

test("sentenceSplitter: English terminators . ? !", () => {
  const s = sentenceSplitter();
  assert.deepEqual(s.push("Leave now. Take the"), ["Leave now."]);
  assert.deepEqual(s.push(" Chuo line?"), ["Take the Chuo line?"]);
});

test("energyVAD: RMS over threshold = speech; silence run past N ms = endpointed", () => {
  const loud = Buffer.alloc(320); loud.fill(60); // nonzero PCM16 bytes → energy
  const quiet = Buffer.alloc(320); // zeros = silence
  const vad = energyVAD({ threshold: 200, silenceMs: 500, frameMs: 20 });
  assert.equal(vad.push(loud).speech, true);
  // 500ms of silence at 20ms/frame = 25 frames → endpointed on the 25th
  let endpointed = false;
  for (let i = 0; i < 25; i++) endpointed = vad.push(quiet).endpointed || endpointed;
  assert.equal(endpointed, true);
});

test("decideBargeIn: speaking + caller speech-start → stop send + Telnyx clear + NO Live", () => {
  assert.deepEqual(decideBargeIn({ botSpeaking: true, callerSpeechStart: true }),
    { stopSend: true, sendClear: true, openLive: false });
  assert.deepEqual(decideBargeIn({ botSpeaking: false, callerSpeechStart: true }),
    { stopSend: false, sendClear: false, openLive: false });
});

test("chooseSttProvider: fail-closed — no key / 429 / timeout → local, NEVER live", () => {
  assert.equal(chooseSttProvider({ groqKey: "gsk_x" }).name, "groq-whisper");
  assert.equal(chooseSttProvider({ groqKey: "" }).name, "faster-whisper-local");
  assert.equal(chooseSttProvider({ groqKey: "gsk_x", lastError: 429 }).name, "faster-whisper-local");
  assert.equal(chooseSttProvider({ groqKey: "gsk_x", lastError: "timeout" }).name, "faster-whisper-local");
  for (const p of ["groqKey", ""]) assert.notEqual(chooseSttProvider({ groqKey: p }).name, "gemini-live");
});

test("chooseLlmProvider: fail-closed — no key / 429 → cheap text fallback, NEVER live", () => {
  assert.equal(chooseLlmProvider({ groqKey: "gsk_x" }).name, "groq-llama");
  assert.equal(chooseLlmProvider({ groqKey: "" }).name, "gemini-flash-text");
  assert.equal(chooseLlmProvider({ groqKey: "gsk_x", lastError: 429 }).name, "gemini-flash-text");
  assert.notEqual(chooseLlmProvider({ groqKey: "" }).name, "gemini-live");
});

test("buildLlmChat: OpenAI-compatible Groq chat body (model, messages, stream)", () => {
  const b = buildLlmChat({ system: "You are Life Manager.", history: [{ role: "user", content: "hi" }], model: "llama-3.1-8b-instant" });
  assert.equal(b.model, "llama-3.1-8b-instant");
  assert.equal(b.stream, true);
  assert.equal(b.messages[0].role, "system");
  assert.equal(b.messages.at(-1).content, "hi");
});
