#!/usr/bin/env node
// call-bridge.test.js — C1 (VCSDD life-manager-cost-connect-reliability): barge-in unit test.
// Gemini Live native-audio emits serverContent.interrupted:true when the caller speaks over Charon
// (server-side VAD). routeGeminiMessage must surface this so server.js can flush Telnyx's queued
// playback ({event:"clear"}). RED today: routeGeminiMessage has no `interrupted` branch.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { routeGeminiMessage, buildTelnyxMediaFrame } = require("./call-bridge.cjs");

test("routeGeminiMessage: serverContent.interrupted → {kind:'interrupted'}, no audio frame sent", () => {
  const state = { streamSid: "abc123", outFrames: 0, setupComplete: true };
  const sent = [];
  const spySend = (o) => sent.push(o);

  const r = routeGeminiMessage({ serverContent: { interrupted: true } }, state, spySend, buildTelnyxMediaFrame);

  assert.deepEqual(r, { kind: "interrupted", frames: 0 });
  assert.equal(sent.length, 0); // no audio (or any) frame forwarded to the carrier for an interrupt message
});
