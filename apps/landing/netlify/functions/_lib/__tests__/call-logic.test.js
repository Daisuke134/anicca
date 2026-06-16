const { test } = require("node:test");
const assert = require("node:assert");
const {
  muLawDecodeSample,
  muLawEncodeSample,
  muLawBufToPcm16,
  pcm16BufToMuLaw,
  resamplePcm16,
  twilioMuLawToGeminiPcm16,
  geminiPcm24ToTwilioMuLaw,
  buildGeminiSetup,
  buildGeminiAudioInput,
  buildTwilioMediaFrame,
  buildCallPrompt,
  buildConnectStreamTwiml,
  LIVE_MODEL,
  geminiLiveWsUrl,
  buildGeminiTurn,
  parseGeminiAudio,
  buildTelnyxMediaFrame,
  parseTelnyxStart,
  telnyxDialBody,
  telnyxStreamingStartBody,
} = require("../call-logic");

// ── 1. μ-law encode(decode(x)) is the identity for every byte (G.711) ─────────
// The sole exception is 0x7F (negative-zero alias): it decodes to 0, and zero
// canonically re-encodes to 0xFF (positive zero). That collapse is the defined
// G.711 behaviour, not a codec bug — so we assert identity for the other 255 and
// the canonical zero collapse for 0x7F.
test("muLaw encode(decode(u)) is the identity for every byte except the -0 alias", () => {
  for (let u = 0; u < 256; u++) {
    const pcm = muLawDecodeSample(u);
    const back = muLawEncodeSample(pcm);
    if (u === 0x7f) {
      assert.strictEqual(back, 0xff, "negative-zero (0x7F) canonicalizes to +0 (0xFF)");
    } else {
      assert.strictEqual(back, u, `byte ${u} round-tripped to ${back}`);
    }
  }
});

// ── 2. μ-law silence vectors (G.711: 0xFF and 0x7F both decode near zero) ──────
test("muLaw silence bytes decode to ~0 PCM", () => {
  assert.strictEqual(muLawDecodeSample(0xff), 0); // +0
  assert.strictEqual(muLawDecodeSample(0x7f), 0); // -0
  // sign bit 0x80 => negative range, cleared => positive range
  assert.ok(muLawDecodeSample(0x00) < 0, "0x00 is a large negative magnitude");
  assert.ok(muLawDecodeSample(0x80) > 0, "0x80 is a large positive magnitude");
});

// ── 3. whole-buffer transcode lengths ─────────────────────────────────────────
test("muLawBufToPcm16 doubles bytes; pcm16BufToMuLaw halves bytes", () => {
  const mu = Buffer.from([0xff, 0x00, 0x7f, 0x80]); // 4 μ-law bytes
  const pcm = muLawBufToPcm16(mu);
  assert.strictEqual(pcm.length, 8); // 4 samples * 2 bytes
  const backMu = pcm16BufToMuLaw(pcm);
  assert.strictEqual(backMu.length, 4); // 4 samples * 1 byte
});

// ── 4. resample 8k -> 16k roughly doubles sample count ────────────────────────
test("resamplePcm16 8000 -> 16000 produces ~2x samples", () => {
  const inSamples = 80; // 10ms @ 8k
  const buf = Buffer.alloc(inSamples * 2); // silence
  for (let i = 0; i < inSamples; i++) buf.writeInt16LE((i % 100) * 10 - 500, i * 2);
  const out = resamplePcm16(buf, 8000, 16000);
  const outSamples = out.length / 2;
  assert.ok(Math.abs(outSamples - inSamples * 2) <= 2, `got ${outSamples}`);
});

// ── 5. resample 24k -> 8k roughly thirds sample count ─────────────────────────
test("resamplePcm16 24000 -> 8000 produces ~1/3 samples", () => {
  const inSamples = 240; // 10ms @ 24k
  const buf = Buffer.alloc(inSamples * 2);
  for (let i = 0; i < inSamples; i++) buf.writeInt16LE(((i * 37) % 1000) - 500, i * 2);
  const out = resamplePcm16(buf, 24000, 8000);
  const outSamples = out.length / 2;
  assert.ok(Math.abs(outSamples - inSamples / 3) <= 2, `got ${outSamples}`);
});

// ── 6. Twilio μ-law -> Gemini PCM16: base64 in/out, ~4x byte growth ───────────
test("twilioMuLawToGeminiPcm16 grows bytes ~4x (n -> 2n -> up2 -> 4n)", () => {
  const muN = 160; // 20ms @ 8k μ-law
  const inB64 = Buffer.alloc(muN, 0xff).toString("base64");
  const outB64 = twilioMuLawToGeminiPcm16(inB64);
  const outBytes = Buffer.from(outB64, "base64").length;
  assert.ok(Math.abs(outBytes - muN * 4) <= 8, `expected ~${muN * 4}, got ${outBytes}`);
});

// ── 7. Gemini PCM24 -> Twilio μ-law: shrinks to ~1/6 ──────────────────────────
test("geminiPcm24ToTwilioMuLaw shrinks ~6x (24k pcm16 -> 8k μ-law)", () => {
  const samples24 = 240; // 10ms @ 24k
  const pcm = Buffer.alloc(samples24 * 2);
  for (let i = 0; i < samples24; i++) pcm.writeInt16LE(((i * 53) % 2000) - 1000, i * 2);
  const inB64 = pcm.toString("base64");
  const outB64 = geminiPcm24ToTwilioMuLaw(inB64);
  const outBytes = Buffer.from(outB64, "base64").length;
  const inBytes = samples24 * 2; // 480
  assert.ok(Math.abs(outBytes - inBytes / 6) <= 3, `expected ~${inBytes / 6}, got ${outBytes}`);
});

// ── 8. Gemini setup message shape (Charon voice, AUDIO modality) ──────────────
test("buildGeminiSetup carries model, AUDIO modality, and Charon voice", () => {
  const m = buildGeminiSetup({
    model: "gemini-2.0-flash-live-001",
    voiceName: "Charon",
    systemInstruction: "You are Anicca.",
  });
  assert.strictEqual(m.setup.model, "models/gemini-2.0-flash-live-001");
  assert.deepStrictEqual(m.setup.generationConfig.responseModalities, ["AUDIO"]);
  assert.strictEqual(
    m.setup.generationConfig.speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName,
    "Charon"
  );
  assert.strictEqual(m.setup.systemInstruction.parts[0].text, "You are Anicca.");
});

test("buildGeminiSetup accepts a bare model id and still prefixes models/", () => {
  const m = buildGeminiSetup({ model: "models/x", voiceName: "Charon", systemInstruction: "" });
  assert.strictEqual(m.setup.model, "models/x"); // already-prefixed is left intact
});

// ── 9. Gemini realtime audio input shape ──────────────────────────────────────
test("buildGeminiAudioInput wraps base64 PCM16 with 16kHz mime", () => {
  const m = buildGeminiAudioInput("QUJD");
  assert.strictEqual(m.realtimeInput.audio.data, "QUJD");
  assert.strictEqual(m.realtimeInput.audio.mimeType, "audio/pcm;rate=16000");
});

// ── 10. Twilio outbound media frame shape ─────────────────────────────────────
test("buildTwilioMediaFrame builds an outbound media frame", () => {
  const f = buildTwilioMediaFrame("MZ123", "cGF5");
  assert.strictEqual(f.event, "media");
  assert.strictEqual(f.streamSid, "MZ123");
  assert.strictEqual(f.media.payload, "cGF5");
});

// ── 11. Call prompt content (null-safe) ───────────────────────────────────────
test("buildCallPrompt mentions the event title, start time, and a leave cue", () => {
  const p = buildCallPrompt({
    summary: "伊藤歯科",
    start: { dateTime: "2026-06-16T09:45:00+09:00" },
    location: "表参道",
  });
  assert.ok(p.includes("伊藤歯科"), "has title");
  assert.ok(p.includes("09:45") || p.includes("9:45"), "has start time");
  assert.ok(/leave|出発|出て|出かけ/i.test(p), "has a leave cue");
});

test("buildCallPrompt is null-safe when fields are missing", () => {
  const p = buildCallPrompt({});
  assert.strictEqual(typeof p, "string");
  assert.ok(p.length > 0);
});

// ── 12. Connect/Stream TwiML ──────────────────────────────────────────────────
test("buildConnectStreamTwiml emits a Connect+Stream TwiML and XML-escapes the url", () => {
  const xml = buildConnectStreamTwiml("wss://x.example/ws?a=1&b=2");
  assert.ok(xml.startsWith("<?xml"), "xml prolog");
  assert.ok(xml.includes("<Connect>"), "Connect verb");
  assert.ok(xml.includes("<Stream "), "Stream noun");
  assert.ok(xml.includes('url="wss://x.example/ws?a=1&amp;b=2"'), "url present and & escaped");
  assert.ok(!xml.includes("a=1&b=2"), "raw ampersand must be escaped");
});

// ── 13. Live model default (the wire-bug fix) ─────────────────────────────────
test("buildGeminiSetup defaults to the verified-working live model when none given", () => {
  const m = buildGeminiSetup({ voiceName: "Charon", systemInstruction: "" });
  // NOT the dead gemini-2.0-flash-live-001 that the bidi API rejects with CLOSE 1008.
  assert.strictEqual(m.setup.model, `models/${LIVE_MODEL}`);
  assert.notStrictEqual(m.setup.model, "models/gemini-2.0-flash-live-001");
  assert.ok(/native-audio/.test(LIVE_MODEL), "live model is a native-audio bidi model");
});

// ── 14. Gemini Live websocket URL ─────────────────────────────────────────────
test("geminiLiveWsUrl builds the BidiGenerateContent wss endpoint with the key", () => {
  const url = geminiLiveWsUrl("AIza-KEY/with+chars");
  assert.ok(url.startsWith("wss://generativelanguage.googleapis.com/ws/"), "wss host");
  assert.ok(url.includes("GenerativeService.BidiGenerateContent"), "bidi method");
  assert.ok(url.includes("key=AIza-KEY%2Fwith%2Bchars"), "key url-encoded");
});

// ── 15. Opening-turn message shape ────────────────────────────────────────────
test("buildGeminiTurn wraps text as a complete user turn", () => {
  const t = buildGeminiTurn("time to leave");
  assert.strictEqual(t.clientContent.turns[0].role, "user");
  assert.strictEqual(t.clientContent.turns[0].parts[0].text, "time to leave");
  assert.strictEqual(t.clientContent.turnComplete, true);
});

// ── 16. Audio extraction from server messages ─────────────────────────────────
test("parseGeminiAudio pulls inlineData audio chunks and ignores non-audio messages", () => {
  const withAudio = {
    serverContent: { modelTurn: { parts: [{ inlineData: { data: "QUJD" } }, { text: "hi" }] } },
  };
  assert.deepStrictEqual(parseGeminiAudio(withAudio), ["QUJD"]);
  assert.deepStrictEqual(parseGeminiAudio({ setupComplete: {} }), []);
  assert.deepStrictEqual(parseGeminiAudio({}), []);
  assert.deepStrictEqual(parseGeminiAudio(null), []);
});

// ── 17. Telnyx outbound media frame = documented {event:media,media:{payload}} (NO stream_id) ──
test("buildTelnyxMediaFrame matches Telnyx docs shape (no stream_id)", () => {
  const f = buildTelnyxMediaFrame("ignored", "QUJD");
  assert.strictEqual(f.event, "media");
  assert.strictEqual(f.media.payload, "QUJD");
  assert.ok(!("stream_id" in f), "outbound frame must omit stream_id per Telnyx docs");
});
// ── 17b. streaming_start contingency body ──
test("telnyxStreamingStartBody carries rtp+PCMU+inbound_track", () => {
  const b = telnyxStreamingStartBody({ streamUrl: "wss://x/ws" });
  assert.strictEqual(b.stream_bidirectional_mode, "rtp");
  assert.strictEqual(b.stream_bidirectional_codec, "PCMU");
  assert.strictEqual(b.stream_track, "inbound_track");
});

// ── 18. parseTelnyxStart pulls stream_id + call_control_id ─────────────────────
test("parseTelnyxStart: extracts stream_id and call_control_id from start frame", () => {
  const start = {
    event: "start",
    stream_id: "STREAM-1",
    start: { call_control_id: "v2:CCID", media_format: { encoding: "PCMU", sample_rate: 8000 } },
  };
  const r = parseTelnyxStart(start);
  assert.strictEqual(r.streamId, "STREAM-1");
  assert.strictEqual(r.callControlId, "v2:CCID");
  // non-start / null are safe
  assert.deepStrictEqual(parseTelnyxStart({ event: "media" }), {});
  assert.deepStrictEqual(parseTelnyxStart(null), {});
});

// ── 19. telnyxDialBody requests bidirectional RTP PCMU streaming ───────────────
test("telnyxDialBody: outbound /v2/calls body with bidirectional rtp + PCMU", () => {
  const b = telnyxDialBody({
    connectionId: "2982013078364751402",
    to: "+818046270314",
    from: "+14322234204",
    streamUrl: "wss://x.trycloudflare.com/ws",
  });
  assert.strictEqual(b.connection_id, "2982013078364751402");
  assert.strictEqual(b.to, "+818046270314");
  assert.strictEqual(b.from, "+14322234204");
  assert.strictEqual(b.stream_url, "wss://x.trycloudflare.com/ws");
  assert.strictEqual(b.stream_track, "inbound_track");
  assert.strictEqual(b.stream_bidirectional_mode, "rtp");
  assert.strictEqual(b.stream_bidirectional_codec, "PCMU");
});
