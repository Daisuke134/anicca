// lib/compositional-live.test.js — pure helpers for the live adapters (network fns tested in E2E).
"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { pcm16ToWav, parseGroqSSE } = require("./compositional-live.cjs");

test("pcm16ToWav: valid 44-byte header + data, correct sample rate", () => {
  const pcm = Buffer.alloc(320, 1);
  const wav = pcm16ToWav(pcm, 16000);
  assert.equal(wav.slice(0, 4).toString(), "RIFF");
  assert.equal(wav.slice(8, 12).toString(), "WAVE");
  assert.equal(wav.readUInt32LE(24), 16000); // sample rate
  assert.equal(wav.length, 44 + 320);
  assert.equal(wav.readUInt32LE(40), 320); // data size
});

test("parseGroqSSE: extracts content deltas, ignores [DONE] + non-content lines", () => {
  const chunk = [
    'data: {"choices":[{"delta":{"content":"17"}}]}',
    'data: {"choices":[{"delta":{"content":"分です。"}}]}',
    'data: {"choices":[{"delta":{}}]}',
    "data: [DONE]",
    ": keepalive",
  ].join("\n");
  assert.deepEqual(parseGroqSSE(chunk), ["17", "分です。"]);
});

test("parseGroqSSE: tolerates a partial/garbled json line", () => {
  assert.deepEqual(parseGroqSSE('data: {"choices":[{"delta":{"content":"ok"}}]}\ndata: {partial'), ["ok"]);
});
