#!/usr/bin/env node
// call-bridge.test.js — C1 (VCSDD life-manager-cost-connect-reliability): barge-in unit test.
// Gemini Live native-audio emits serverContent.interrupted:true when the caller speaks over Charon
// (server-side VAD). routeGeminiMessage must surface this so server.js can flush Telnyx's queued
// playback ({event:"clear"}). RED today: routeGeminiMessage has no `interrupted` branch.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events");
const {
  routeGeminiMessage,
  buildTelnyxMediaFrame,
  decideGeminiEnd,
  carrierActionForGeminiKind,
  makeGeminiEndHandler,
  attachGeminiUsageTracking,
} = require("./call-bridge.cjs");

const USAGE_CONTEXT = { owner_id: "u1", financial_unit_id: "life_manager_saas", request_model: "models/gemini-2.5-flash-native-audio-preview-09-2025", live_session_id: "a".repeat(32) };
const USAGE_OPTIONS = { storeOptions: { supaUrl: "https://supa.invalid", supaKey: "service" } };
const usageMessage = (n) => ({ usageMetadata: { promptTokenCount: n, responseTokenCount: n, totalTokenCount: n } });
const emitUsage = (socket, message) => socket.emit("message", Buffer.from(JSON.stringify(message)));

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

test("attachGeminiUsageTracking: ignores non-usage and serializes ordered captures", async () => {
  const socket = new EventEmitter(), seen = [], first = usageMessage(1), second = usageMessage(2);
  const recorder = attachGeminiUsageTracking({ socket, context: USAGE_CONTEXT, options: USAGE_OPTIONS, capture: async (message, context, options) => seen.push({ message, context, options }) });
  emitUsage(socket, { serverContent: {} }); emitUsage(socket, first); emitUsage(socket, second);
  const result = await recorder.settle();
  assert.deepEqual(seen, [{ message: first, context: { ...USAGE_CONTEXT, usage_sequence: 0 }, options: USAGE_OPTIONS }, { message: second, context: { ...USAGE_CONTEXT, usage_sequence: 1 }, options: USAGE_OPTIONS }]);
  assert.deepEqual(result, { seen: 2, stored: 2, failed: 0, complete: true }); assert.equal(Object.isFrozen(result), true);
});

test("attachGeminiUsageTracking: counts one rejection, never retries/logs, and zero is incomplete", async () => {
  const socket = new EventEmitter(), calls = []; let logs = 0; const original = console.log; console.log = () => { logs++; };
  try {
    const recorder = attachGeminiUsageTracking({ socket, context: USAGE_CONTEXT, options: USAGE_OPTIONS, capture: async message => { calls.push(message); if (calls.length === 1) throw new Error("sentinel"); } });
    emitUsage(socket, usageMessage(1)); emitUsage(socket, usageMessage(2));
    assert.deepEqual(await recorder.settle(), { seen: 2, stored: 1, failed: 1, complete: false });
    const empty = attachGeminiUsageTracking({ socket: new EventEmitter(), context: USAGE_CONTEXT, options: USAGE_OPTIONS, capture: async () => {} });
    assert.deepEqual(await empty.settle(), { seen: 0, stored: 0, failed: 0, complete: false }); assert.equal(calls.length, 2); assert.equal(logs, 0);
  } finally { console.log = original; }
});

test("attachGeminiUsageTracking: close ends synchronously, fallback waits for deferred settlement and isolates reconnect", async () => {
  const run = async (context, outcomes) => {
    const socket = new EventEmitter(), pending = [], ends = [], fallbacks = [], calls = [];
    const recorder = attachGeminiUsageTracking({ socket, context, options: USAGE_OPTIONS, capture: (message, actual, options) => new Promise((resolve, reject) => pending.push({ message, actual, options, resolve, reject })), onEnd: () => ends.push("end"), onFallback: result => fallbacks.push(result) });
    outcomes.forEach((_, i) => emitUsage(socket, usageMessage(i + 1))); socket.emit("close"); assert.deepEqual(ends, ["end"]); assert.equal(fallbacks.length, 0);
    for (let i = 0; i < outcomes.length; i++) { while (!pending[i]) await Promise.resolve(); calls.push(pending[i]); outcomes[i] ? pending[i].resolve() : pending[i].reject(new Error("sentinel")); }
    const result = await recorder.settle(); await Promise.resolve(); return { result, calls, fallbacks };
  };
  const zero = await run({ ...USAGE_CONTEXT, live_session_id: "0".repeat(32) }, []);
  const all = await run(USAGE_CONTEXT, [true, true]); const partial = await run(USAGE_CONTEXT, [true, false]);
  assert.equal(zero.fallbacks.length, 1); assert.deepEqual(zero.result, { seen: 0, stored: 0, failed: 0, complete: false }); assert.equal(all.fallbacks.length, 0); assert.equal(partial.fallbacks.length, 1); assert.deepEqual(partial.result, { seen: 2, stored: 1, failed: 1, complete: false });
  const next = await run({ ...USAGE_CONTEXT, live_session_id: "b".repeat(32) }, [true]); assert.equal(next.calls[0].actual.usage_sequence, 0); assert.equal(next.calls[0].actual.live_session_id, "b".repeat(32)); assert.strictEqual(next.calls[0].options, USAGE_OPTIONS);
});
