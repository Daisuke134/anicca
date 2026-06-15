const { test } = require("node:test");
const assert = require("node:assert");
const {
  routeTwilioMessage,
  routeGeminiMessage,
  geminiSetupForEvent,
} = require("../call-bridge.cjs");

// ── 1. Twilio start frame captures the streamSid ──────────────────────────────
test("routeTwilioMessage: start frame records streamSid", () => {
  const state = {};
  const sent = [];
  const kind = routeTwilioMessage(
    { event: "start", start: { streamSid: "MZ-abc" } },
    state,
    (o) => sent.push(o)
  );
  assert.strictEqual(kind, "start");
  assert.strictEqual(state.streamSid, "MZ-abc");
  assert.strictEqual(sent.length, 0, "start sends nothing to Gemini");
});

// ── 2. Twilio media frame -> transcoded Gemini realtimeInput ──────────────────
test("routeTwilioMessage: media frame forwards a Gemini audio input", () => {
  const state = { streamSid: "MZ-abc" };
  const sent = [];
  // 160 μ-law bytes (20ms @ 8k) base64
  const payload = Buffer.alloc(160, 0xff).toString("base64");
  const kind = routeTwilioMessage(
    { event: "media", media: { payload } },
    state,
    (o) => sent.push(o)
  );
  assert.strictEqual(kind, "media");
  assert.strictEqual(state.inFrames, 1);
  assert.strictEqual(sent.length, 1);
  assert.ok(sent[0].realtimeInput.audio.data, "carries transcoded base64 PCM16");
  assert.strictEqual(sent[0].realtimeInput.audio.mimeType, "audio/pcm;rate=16000");
});

// ── 3. Twilio stop / connected / unknown are classified, send nothing ─────────
test("routeTwilioMessage: stop/connected/unknown classified without forwarding", () => {
  const sent = [];
  const push = (o) => sent.push(o);
  assert.strictEqual(routeTwilioMessage({ event: "stop" }, {}, push), "stop");
  assert.strictEqual(routeTwilioMessage({ event: "connected" }, {}, push), "connected");
  assert.strictEqual(routeTwilioMessage({ event: "weird" }, {}, push), "other");
  assert.strictEqual(sent.length, 0);
});

// ── 4. Gemini setupComplete flips state, emits no frames ──────────────────────
test("routeGeminiMessage: setupComplete sets flag, no Twilio frames", () => {
  const state = { streamSid: "MZ-abc" };
  const sent = [];
  const r = routeGeminiMessage({ setupComplete: {} }, state, (o) => sent.push(o));
  assert.strictEqual(r.kind, "setupComplete");
  assert.strictEqual(state.setupComplete, true);
  assert.strictEqual(sent.length, 0);
});

// ── 5. Gemini audio chunk -> transcoded Twilio media frame(s) ─────────────────
test("routeGeminiMessage: audio chunk forwards a Twilio media frame", () => {
  const state = { streamSid: "MZ-abc" };
  const sent = [];
  // 240 PCM24 samples (10ms) -> base64
  const pcm = Buffer.alloc(240 * 2);
  for (let i = 0; i < 240; i++) pcm.writeInt16LE(((i * 53) % 2000) - 1000, i * 2);
  const msg = {
    serverContent: { modelTurn: { parts: [{ inlineData: { data: pcm.toString("base64") } }] } },
  };
  const r = routeGeminiMessage(msg, state, (o) => sent.push(o));
  assert.strictEqual(r.kind, "audio");
  assert.strictEqual(r.frames, 1);
  assert.strictEqual(state.outFrames, 1);
  assert.strictEqual(sent[0].event, "media");
  assert.strictEqual(sent[0].streamSid, "MZ-abc");
  assert.ok(sent[0].media.payload, "carries transcoded μ-law payload");
});

// ── 6. Bidirectional round-trip with two fake sockets ─────────────────────────
test("bridge moves audio BOTH ways through fake sockets", () => {
  const state = { streamSid: "MZ-xyz" };
  const toGemini = [];
  const toTwilio = [];
  // Twilio -> Gemini
  routeTwilioMessage(
    { event: "media", media: { payload: Buffer.alloc(160, 0x7f).toString("base64") } },
    state,
    (o) => toGemini.push(o)
  );
  // Gemini -> Twilio
  const pcm = Buffer.alloc(480 * 2);
  routeGeminiMessage(
    { serverContent: { modelTurn: { parts: [{ inlineData: { data: pcm.toString("base64") } }] } } },
    state,
    (o) => toTwilio.push(o)
  );
  assert.ok(toGemini.length >= 1, "user audio reached Gemini (uplink)");
  assert.ok(toTwilio.length >= 1, "Charon audio reached Twilio (downlink)");
});

// ── 7. setup message uses Charon + the live model + the event's prompt ─────────
test("geminiSetupForEvent: Charon voice, live model, event-aware prompt", () => {
  const setup = geminiSetupForEvent({
    summary: "伊藤歯科",
    start: { dateTime: "2026-06-16T09:45:00+09:00" },
    location: "表参道",
  });
  assert.strictEqual(
    setup.setup.generationConfig.speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName,
    "Charon"
  );
  assert.ok(/native-audio/.test(setup.setup.model), "live native-audio model");
  assert.ok(setup.setup.systemInstruction.parts[0].text.includes("伊藤歯科"), "event title in prompt");
});
