// lib/voice-cheap.test.js — C1 RED. Cheap wake-call path: a pre-synthesized ONE-WAY guidance clip
// (cheap text line → edge-tts → μ-law → Telnyx) is the DEFAULT; a two-way Gemini Live session is opened
// ONLY on caller interaction (escalation). INVARIANT (measurable, Goal 1): the default path never opens
// the Gemini Live ws. Pure logic only.
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const { buildWakeLine, planVoice, chooseTts, TTS_ORDER } = require("./voice-cheap.js"); // missing → RED

const EV = { title: "歯医者", place: "新宿デンタル", urgency: "firm" };
const ROUTE = { line: "中央線快速", durationMin: 17 };

test("buildWakeLine (ja): names event + place + route + urgency, one line", () => {
  const s = buildWakeLine(EV, ROUTE, "firm", "ja");
  assert.match(s, /歯医者/);
  assert.match(s, /新宿デンタル/);
  assert.match(s, /中央線快速/);
  assert.equal(s.includes("\n"), false);
});

test("buildWakeLine (en): harsh urgency is more insistent than firm", () => {
  const firm = buildWakeLine({ title: "Dentist", place: "Shinjuku Dental" }, { line: "Chuo line" }, "firm", "en");
  const harsh = buildWakeLine({ title: "Dentist", place: "Shinjuku Dental" }, { line: "Chuo line" }, "harsh", "en");
  assert.match(firm, /Dentist/);
  assert.match(harsh, /now/i);
  assert.notEqual(firm, harsh);
});

test("planVoice: default (no interaction) = one-way, Live ws NOT opened", () => {
  const p = planVoice({ callerSpoke: false, keypad: null });
  assert.equal(p.mode, "oneway");
  assert.equal(p.opensLiveWs, false); // ← Goal 1 invariant
});

test("planVoice: caller speaks OR presses key → live escalation (billed, rare)", () => {
  assert.equal(planVoice({ callerSpoke: true }).mode, "live_escalation");
  assert.equal(planVoice({ callerSpoke: true }).opensLiveWs, true);
  assert.equal(planVoice({ keypad: "1" }).opensLiveWs, true);
});

test("chooseTts: fallback order edge-tts → kokoro → piper → live; picks first available", () => {
  assert.deepEqual(TTS_ORDER, ["edge-tts", "kokoro", "piper", "live"]);
  assert.equal(chooseTts({ "edge-tts": true, kokoro: true }), "edge-tts");
  assert.equal(chooseTts({ "edge-tts": false, kokoro: true }), "kokoro");
  assert.equal(chooseTts({ "edge-tts": false, kokoro: false, piper: false, live: true }), "live");
  assert.equal(chooseTts({}), null); // nothing available → caller must not dial a silent call
});

test("buildWakeLine (ja): harsh differs from firm — FIND-005", () => {
  const firm = buildWakeLine(EV, ROUTE, "firm", "ja");
  const harsh = buildWakeLine(EV, ROUTE, "harsh", "ja");
  assert.notEqual(firm, harsh);
  assert.match(harsh, /今すぐ/);
});
