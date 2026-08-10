#!/usr/bin/env node
// call-bridge.test.js — C1 (VCSDD life-manager-cost-connect-reliability): barge-in unit test.
// Gemini Live native-audio emits serverContent.interrupted:true when the caller speaks over Charon
// (server-side VAD). routeGeminiMessage must surface this so server.js can flush Telnyx's queued
// playback ({event:"clear"}). RED today: routeGeminiMessage has no `interrupted` branch.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events"), fs = require("node:fs"), path = require("node:path");
const {
  routeGeminiMessage,
  buildTelnyxMediaFrame,
  decideGeminiEnd,
  carrierActionForGeminiKind,
  makeGeminiEndHandler,
  attachGeminiUsageTracking,
} = require("./call-bridge.cjs");

const USAGE_CONTEXT = { owner_id: "u1", financial_unit_id: "life_manager_saas", request_model: "models/gemini-2.5-flash-native-audio-preview-09-2025", live_session_id: "a".repeat(32) }, USAGE_OPTIONS = { storeOptions: { supaUrl: "https://supa.invalid", supaKey: "service" } };
const usageMessage = (n) => ({ usageMetadata: { promptTokenCount: n, responseTokenCount: n, totalTokenCount: n } }), emitUsage = (socket, message) => socket.emit("message", Buffer.from(JSON.stringify(message)));
const serverSource = () => fs.readFileSync(path.join(__dirname, "../server.js"), "utf8");
async function trapConsole(run) {
  const names = ["log", "error", "warn"], originals = names.map(name => console[name]), logs = []; names.forEach((name, i) => { console[name] = (...args) => logs.push(args); });
  try { return await run(logs); } finally { names.forEach((name, i) => { console[name] = originals[i]; }); }
}

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

test("attachGeminiUsageTracking: ordered serialization and fixed context", async () => { const socket = new EventEmitter(), pending = [], first = usageMessage(1), second = usageMessage(2), recorder = attachGeminiUsageTracking({ socket, context: USAGE_CONTEXT, options: USAGE_OPTIONS, capture: (message, context, options) => new Promise(resolve => pending.push({ message, context, options, resolve })) }); emitUsage(socket, { serverContent: {} }); emitUsage(socket, first); emitUsage(socket, second); await Promise.resolve(); assert.equal(pending.length, 1); assert.deepEqual(pending[0].message, first); assert.deepEqual(pending[0].context, { ...USAGE_CONTEXT, usage_sequence: 0 }); assert.strictEqual(pending[0].options, USAGE_OPTIONS); pending[0].resolve(); while (pending.length < 2) await Promise.resolve(); assert.equal(pending[1].context.usage_sequence, 1); pending[1].resolve(); const result = await recorder.settle(); assert.deepEqual(result, { seen: 2, stored: 2, failed: 0, complete: true }); assert.equal(Object.isFrozen(result), true); });

test("attachGeminiUsageTracking: failure continuation and zero are incomplete", async () => await trapConsole(async logs => { const socket = new EventEmitter(), calls = [], recorder = attachGeminiUsageTracking({ socket, context: USAGE_CONTEXT, options: USAGE_OPTIONS, capture: async message => { calls.push(message); if (calls.length === 1) throw new Error("sentinel"); } }); emitUsage(socket, usageMessage(1)); emitUsage(socket, usageMessage(2)); assert.deepEqual(await recorder.settle(), { seen: 2, stored: 1, failed: 1, complete: false }); const empty = attachGeminiUsageTracking({ socket: new EventEmitter(), context: USAGE_CONTEXT, options: USAGE_OPTIONS, capture: async () => {} }); assert.deepEqual(await empty.settle(), { seen: 0, stored: 0, failed: 0, complete: false }); assert.equal(calls.length, 2); assert.deepEqual(logs, []); }));

test("attachGeminiUsageTracking: close/fallback/reconnect lifecycle", async () => { const run = async (context, outcomes) => { const socket = new EventEmitter(), pending = [], ends = [], fallbacks = [], recorder = attachGeminiUsageTracking({ socket, context, options: USAGE_OPTIONS, capture: (message, actual, options) => new Promise((resolve, reject) => pending.push({ message, actual, options, resolve, reject })), onEnd: () => ends.push("end"), onFallback: result => fallbacks.push(result) }); outcomes.forEach((_, i) => emitUsage(socket, usageMessage(i + 1))); socket.emit("close"); assert.deepEqual(ends, ["end"]); assert.equal(fallbacks.length, 0); for (let i = 0; i < outcomes.length; i++) { while (!pending[i]) await Promise.resolve(); outcomes[i] ? pending[i].resolve() : pending[i].reject(new Error("capture sentinel")); } const result = await recorder.settle(); await Promise.resolve(); return { result, fallbacks }; }; const zero = await run({ ...USAGE_CONTEXT, live_session_id: "0".repeat(32) }, []), all = await run(USAGE_CONTEXT, [true, true]), partial = await run(USAGE_CONTEXT, [true, false]); assert.equal(zero.fallbacks.length, 1); assert.deepEqual(zero.result, { seen: 0, stored: 0, failed: 0, complete: false }); assert.equal(all.fallbacks.length, 0); assert.equal(partial.fallbacks.length, 1); assert.deepEqual(partial.result, { seen: 2, stored: 1, failed: 1, complete: false }); const closedSocket = new EventEmitter(), closed = attachGeminiUsageTracking({ socket: closedSocket, context: USAGE_CONTEXT, options: USAGE_OPTIONS, capture: () => { throw new Error("post-close sentinel"); } }); closedSocket.emit("close"); emitUsage(closedSocket, usageMessage(9)); assert.deepEqual(await closed.settle(), { seen: 0, stored: 0, failed: 0, complete: false }); const escaped = [], onUnhandled = error => escaped.push(error); let consumed = false; process.on("unhandledRejection", onUnhandled); try { await trapConsole(async logs => { const socket = new EventEmitter(), thenable = { then(resolve, reject) { consumed = true; reject(new Error("fallback sentinel")); } }, recorder = attachGeminiUsageTracking({ socket, context: USAGE_CONTEXT, options: USAGE_OPTIONS, capture: async () => {}, onFallback: () => thenable }); socket.emit("close"); await recorder.settle(); await new Promise(resolve => setImmediate(resolve)); assert.equal(consumed, true); assert.deepEqual(logs, []); }); } finally { process.removeListener("unhandledRejection", onUnhandled); } assert.deepEqual(escaped, []); const oldSocket = new EventEmitter(), newSocket = new EventEmitter(), oldPending = [], newPending = [], old = attachGeminiUsageTracking({ socket: oldSocket, context: USAGE_CONTEXT, options: USAGE_OPTIONS, capture: (message, context) => new Promise(resolve => oldPending.push({ message, context, resolve })) }), next = attachGeminiUsageTracking({ socket: newSocket, context: { ...USAGE_CONTEXT, live_session_id: "b".repeat(32) }, options: USAGE_OPTIONS, capture: (message, context) => new Promise(resolve => newPending.push({ message, context, resolve })) }); emitUsage(oldSocket, usageMessage(1)); await Promise.resolve(); assert.equal(oldPending.length, 1); oldSocket.emit("close"); emitUsage(oldSocket, usageMessage(99)); emitUsage(newSocket, usageMessage(1)); await Promise.resolve(); assert.equal(oldPending.length, 1); assert.equal(newPending.length, 1); assert.equal(newPending[0].context.usage_sequence, 0); oldPending[0].resolve(); newPending[0].resolve(); await Promise.all([old.settle(), next.settle()]); });

test("server source contract: owner propagation and close-time fallback snapshot", () => { const source = serverSource(), seam = source.indexOf("attachGeminiUsageTracking({"), start = source.indexOf("onFallback:", seam), end = source.indexOf("recordCost(", start), fallback = source.slice(start, end); assert.match(source, /buildStreamUrl\(\{\s*\.\.\.ev,\s*wakeUid:\s*body\.uid\s*\},\s*urgency,\s*lang,\s*u\.name\)/); assert.match(source, /onEnd:\s*\(\)\s*=>\s*\{[\s\S]*?geminiDurationSeconds\s*=\s*Math\.max\([\s\S]*?onGeminiEnd\("closed"\);?\s*\}/); assert.match(source, /onFallback:\s*\(\)\s*=>\s*\{[^}]*const quantity\s*=\s*geminiDurationSeconds\s*===\s*null\s*\?\s*0\s*:\s*geminiDurationSeconds/s); assert.ok(seam >= 0 && start > seam && end > start); assert.doesNotMatch(fallback, /Date\.now\(/); });
