#!/usr/bin/env node
// call-bridge.test.js — C1 (VCSDD life-manager-cost-connect-reliability): barge-in unit test.
// Gemini Live native-audio emits serverContent.interrupted:true when the caller speaks over Charon
// (server-side VAD). routeGeminiMessage must surface this so server.js can flush Telnyx's queued
// playback ({event:"clear"}). RED today: routeGeminiMessage has no `interrupted` branch.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  routeGeminiMessage,
  buildTelnyxMediaFrame,
  decideGeminiEnd,
  carrierActionForGeminiKind,
} = require("./call-bridge.cjs");

test("routeGeminiMessage: serverContent.interrupted → {kind:'interrupted'}, no audio frame sent", () => {
  const state = { streamSid: "abc123", outFrames: 0, setupComplete: true };
  const sent = [];
  const spySend = (o) => sent.push(o);

  const r = routeGeminiMessage({ serverContent: { interrupted: true } }, state, spySend, buildTelnyxMediaFrame);

  assert.deepEqual(r, { kind: "interrupted", frames: 0 });
  assert.equal(sent.length, 0); // no audio (or any) frame forwarded to the carrier for an interrupt message
});

test("carrierActionForGeminiKind: interrupted → {event:'clear'}; anything else → null", () => {
  assert.deepEqual(carrierActionForGeminiKind("interrupted"), { event: "clear" });
  assert.equal(carrierActionForGeminiKind("audio"), null);
  assert.equal(carrierActionForGeminiKind("setupComplete"), null);
  assert.equal(carrierActionForGeminiKind("other"), null);
});

test("decideGeminiEnd: reconnect ONCE on a pre-audio transient failure, then end cleanly (no infinite loop)", () => {
  // First socket end, before any audio, carrier still up → reconnect.
  assert.equal(decideGeminiEnd({ gotAudio: false, reconnects: 0, carrierOpen: true }), "reconnect");
  // The paired ws error→close double-fire OR a second failure: reconnects already 1 → close (never a 2nd retry).
  assert.equal(decideGeminiEnd({ gotAudio: false, reconnects: 1, carrierOpen: true }), "close");
  // Drop AFTER audio started → the call was live; do NOT reconnect, end cleanly.
  assert.equal(decideGeminiEnd({ gotAudio: true, reconnects: 0, carrierOpen: true }), "close");
  // Carrier already gone → nothing to reconnect for.
  assert.equal(decideGeminiEnd({ gotAudio: false, reconnects: 0, carrierOpen: false }), "close");
});
