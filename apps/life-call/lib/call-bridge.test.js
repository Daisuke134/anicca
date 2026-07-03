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
  makeGeminiEndHandler,
} = require("./call-bridge.cjs");

// Build a handler over mutable call-scoped state, capturing the effects the real server.js injects.
function wireEndHandler({ gotAudio = false, reconnects = 0, carrierOpen = true } = {}) {
  const s = { gotAudio, reconnects, carrierOpen, reconnectCalls: 0, closeCalls: 0 };
  const handler = makeGeminiEndHandler({
    getGotAudio: () => s.gotAudio,
    getReconnects: () => s.reconnects,
    incReconnects: () => { s.reconnects++; },
    carrierOpen: () => s.carrierOpen,
    onReconnect: () => { s.reconnectCalls++; },
    onClose: () => { s.closeCalls++; },
  });
  return { handler, s };
}

test("makeGeminiEndHandler: ws error THEN close for ONE socket → reconnect once, carrier NOT closed (iteration-6 bug guard)", () => {
  const { handler, s } = wireEndHandler({ gotAudio: false, reconnects: 0, carrierOpen: true });
  handler("err boom"); // ws `error` fires
  handler("closed");   // the PAIRED `close` fires — must be a no-op (ended flag)
  assert.equal(s.reconnectCalls, 1, "exactly one reconnect");
  assert.equal(s.closeCalls, 0, "the paired close must NOT hang up the call");
  assert.equal(s.reconnects, 1, "counter incremented once");
});

test("makeGeminiEndHandler: a reconnected socket that fails again (reconnects=1) ends the call, no 2nd retry", () => {
  const { handler, s } = wireEndHandler({ gotAudio: false, reconnects: 1, carrierOpen: true });
  handler("err boom2");
  handler("closed");
  assert.equal(s.reconnectCalls, 0, "no second reconnect (≤1 total)");
  assert.equal(s.closeCalls, 1, "call ends cleanly");
});

test("makeGeminiEndHandler: a drop AFTER audio started ends cleanly, never reconnects", () => {
  const { handler, s } = wireEndHandler({ gotAudio: true, reconnects: 0, carrierOpen: true });
  handler("closed");
  assert.equal(s.reconnectCalls, 0);
  assert.equal(s.closeCalls, 1);
});

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
