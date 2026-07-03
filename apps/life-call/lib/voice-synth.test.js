// lib/voice-synth.test.js — C1 unit (pure parts). The real edge-tts+ffmpeg synth is exercised in the
// no-mock E2E (a real call); here we lock the framing + voice-pick logic.
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { chunkMuLawToFrames, voiceForLang } = require("./voice-synth.cjs");

test("chunkMuLawToFrames: 160-byte (20ms) frames, base64, last partial kept", () => {
  const buf = Buffer.alloc(370, 7); // 2 full frames + 50-byte tail
  const frames = chunkMuLawToFrames(buf, 160);
  assert.equal(frames.length, 3);
  assert.equal(Buffer.from(frames[0], "base64").length, 160);
  assert.equal(Buffer.from(frames[2], "base64").length, 50);
});

test("chunkMuLawToFrames: empty buffer → no frames", () => {
  assert.deepEqual(chunkMuLawToFrames(Buffer.alloc(0)), []);
});

test("voiceForLang: ja → Japanese voice, else English", () => {
  assert.equal(voiceForLang("ja"), "ja-JP-NanamiNeural");
  assert.equal(voiceForLang("ja-JP"), "ja-JP-NanamiNeural");
  assert.equal(voiceForLang("en"), "en-US-GuyNeural");
  assert.equal(voiceForLang(undefined), "en-US-GuyNeural");
});
