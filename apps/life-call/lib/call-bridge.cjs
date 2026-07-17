#!/usr/bin/env node
// call-bridge.js — the REAL Twilio Media Streams <-> Gemini Live (Charon) ws bridge
// (spec27c B-call). Twilio connects here via <Connect><Stream>; we open a second ws to
// Gemini Live, transcode every frame with the TESTED pure logic (call-logic.js), and
// relay audio both ways. Charon (male voice) speaks the next-event guidance.
//
// NO FAKE RUN (HARD 0.24): this opens real sockets and moves real audio. The pure
// message-routing core (routeTwilioMessage / routeGeminiMessage) is exported for tests
// with a fake socket; the network plumbing is the thin shell at the bottom.
//
// Run modes:
//   node call-bridge.js --health            self-check (call-logic loads, exit 0), no listen
//   node call-bridge.js --port 8787         start the ws server on :8787 (path /ws)
"use strict";

const path = require("path");
const http = require("http");

const LIB = path.join(__dirname, "call-logic.js");  // consolidated into ~/anicca/skills/life/call/lib
const {
  LIVE_MODEL,
  geminiLiveWsUrl,
  buildGeminiSetup,
  buildGeminiAudioInput,
  buildGeminiTurn,
  parseGeminiAudio,
  parseGeminiTranscripts,
  buildTwilioMediaFrame,
  buildTelnyxMediaFrame,
  parseTelnyxStart,
  buildCallPrompt,
  twilioMuLawToGeminiPcm16,
  geminiPcm24ToTwilioMuLaw,
} = require(LIB);

// ── Pure routing core (testable with a fake socket) ───────────────────────────

/**
 * Handle one parsed Twilio Media Streams message. Mutates `state` (streamSid),
 * forwards transcoded audio into the Gemini socket via `geminiSend`.
 * @param {object} msg - parsed Twilio frame ({event, start?, media?})
 * @param {object} state - { streamSid, inFrames }
 * @param {(o:object)=>void} geminiSend - send a JSON message to Gemini
 * @returns {string} the event kind handled ("start"|"media"|"stop"|"connected"|"mark"|"other")
 */
function routeTwilioMessage(msg, state, geminiSend) {
  const event = msg && msg.event;
  if (event === "start") {
    state.streamSid = (msg.start && msg.start.streamSid) || msg.streamSid || state.streamSid;
    return "start";
  }
  if (event === "media" && msg.media && msg.media.payload) {
    const pcm16b64 = twilioMuLawToGeminiPcm16(msg.media.payload);
    geminiSend(buildGeminiAudioInput(pcm16b64));
    state.inFrames = (state.inFrames || 0) + 1;
    return "media";
  }
  if (event === "stop") return "stop";
  if (event === "connected") return "connected";
  if (event === "mark") return "mark";
  return "other";
}

/**
 * Handle one parsed Telnyx Media Streaming message. Mutates `state` (streamSid),
 * forwards transcoded audio into the Gemini socket via `geminiSend`. Telnyx uses the
 * same μ-law payloads as Twilio; only the frame field names differ (`stream_id`).
 * @param {object} msg - parsed Telnyx frame ({event, start?, media?, stream_id?})
 * @param {object} state - { streamSid, inFrames }
 * @param {(o:object)=>void} geminiSend - send a JSON message to Gemini
 * @returns {string} the event kind handled ("start"|"media"|"stop"|"connected"|"mark"|"dtmf"|"other")
 */
function routeTelnyxMessage(msg, state, geminiSend) {
  const event = msg && msg.event;
  if (event === "start") {
    const s = parseTelnyxStart(msg);
    if (s.streamId) state.streamSid = s.streamId; // unify on streamSid internally
    if (s.callControlId) state.callControlId = s.callControlId;
    return "start";
  }
  if (event === "media" && msg.media && msg.media.payload) {
    // Only feed the caller's (inbound) audio to Gemini. In both_tracks the outbound track is
    // Charon's own playback; forwarding it back creates an echo/feedback loop.
    const track = msg.media.track;
    if (track && track !== "inbound") return "media-skip";
    const pcm16b64 = twilioMuLawToGeminiPcm16(msg.media.payload);
    geminiSend(buildGeminiAudioInput(pcm16b64));
    state.inFrames = (state.inFrames || 0) + 1;
    return "media";
  }
  if (event === "stop") return "stop";
  if (event === "connected") return "connected";
  if (event === "mark") return "mark";
  if (event === "dtmf") return "dtmf";
  return "other";
}

/**
 * Handle one parsed Gemini Live server message. For each audio chunk, transcode to
 * μ-law and forward a provider media frame via `providerSend`. The `frameFor`
 * builder maps (streamId, μ-law-b64) → the provider's wire frame (Twilio or Telnyx),
 * so the same Charon-audio path serves both carriers.
 * @param {object} msg - parsed Gemini server message
 * @param {object} state - { streamSid, outFrames, setupComplete }
 * @param {(o:object)=>void} providerSend - send a JSON message to the caller's carrier
 * @param {(streamId:string,b64MuLaw:string)=>object} [frameFor] - frame builder (default Twilio)
 * @returns {{kind:string, frames:number}} kind + #frames emitted
 */
function routeGeminiMessage(msg, state, providerSend, frameFor) {
  const buildFrame = frameFor || buildTwilioMediaFrame;
  if (msg && msg.setupComplete) {
    state.setupComplete = true;
    return { kind: "setupComplete", frames: 0 };
  }
  // C1 (VCSDD life-manager-cost-connect-reliability): barge-in. Gemini Live native-audio sets
  // serverContent.interrupted:true when server-side VAD detects the caller speaking over Charon.
  // The caller (server.js) then flushes the carrier's queued playback ({event:"clear"}); no audio
  // frame is forwarded for this message.
  if (msg && msg.serverContent && msg.serverContent.interrupted) {
    return { kind: "interrupted", frames: 0 };
  }
  const chunks = parseGeminiAudio(msg);
  let frames = 0;
  for (const b64Pcm24 of chunks) {
    const mu = geminiPcm24ToTwilioMuLaw(b64Pcm24);
    providerSend(buildFrame(state.streamSid, mu));
    frames += 1;
  }
  state.outFrames = (state.outFrames || 0) + frames;
  return { kind: frames ? "audio" : "other", frames };
}

/**
 * The Gemini setup message for a call about `event` (Charon voice, AUDIO).
 * @param {object} event - GCal-shaped event
 * @param {string} [model]
 */
function geminiSetupForEvent(event, urgency, lang, name, model) {
  return buildGeminiSetup({
    model: model || LIVE_MODEL,
    voiceName: "Charon",
    systemInstruction: buildCallPrompt(event, urgency, lang, name),
  });
}

// decideGeminiEnd: when a Gemini Live socket ends, decide whether to reconnect ONCE (a transient
// failure BEFORE any audio) or end the call cleanly. Pure → unit-testable without a real socket.
// Guards against the ws error→close double-fire (the caller also uses a per-socket `ended` flag).
function decideGeminiEnd({ gotAudio, reconnects, carrierOpen, maxReconnects = 1 }) {
  if (!gotAudio && reconnects < maxReconnects && carrierOpen) return "reconnect";
  return "close";
}

// carrierActionForGeminiKind: map a routeGeminiMessage result kind to the Telnyx carrier control frame
// to send (or null). Barge-in = on "interrupted" flush the carrier's queued playback with {event:"clear"}.
function carrierActionForGeminiKind(kind) {
  return kind === "interrupted" ? { event: "clear" } : null;
}

// makeGeminiEndHandler: build the end-handler for ONE Gemini socket. ws fires `error` THEN `close` for a
// single failure, so the returned handler acts AT MOST ONCE (the `ended` flag collapses the pair), then
// either reconnects once (a pre-audio transient failure) or ends the call. Effects are injected so the
// exact `ended`-flag + reconnect wiring that caused the iteration-6 hangup is unit-testable without a real
// socket. `getReconnects`/`incReconnects` operate on the CALL-scoped counter so a reconnect happens ≤1×.
function makeGeminiEndHandler({ getGotAudio, getReconnects, incReconnects, carrierOpen, onReconnect, onClose, log }) {
  let ended = false;
  return (reason) => {
    if (ended) return;
    ended = true;
    if (log) log(reason);
    const decision = decideGeminiEnd({
      gotAudio: getGotAudio(),
      reconnects: getReconnects(),
      carrierOpen: carrierOpen(),
    });
    if (decision === "reconnect") {
      incReconnects();
      onReconnect();
      return;
    }
    onClose(); // never silence, never a clip — end the call cleanly
  };
}

module.exports = {
  routeTwilioMessage,
  routeTelnyxMessage,
  routeGeminiMessage,
  geminiSetupForEvent,
  buildTelnyxMediaFrame,
  decideGeminiEnd,
  carrierActionForGeminiKind,
  makeGeminiEndHandler,
};

// ── Network shell (only runs when invoked directly) ───────────────────────────

function parseArgs(argv) {
  const a = {
    health: false,
    port: Number(process.env.PORT) || 8787,
    event: null,
    provider: process.env.BRIDGE_PROVIDER || "twilio",
  };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--health") a.health = true;
    else if (argv[i] === "--port") a.port = Number(argv[++i]);
    else if (argv[i] === "--event") a.event = JSON.parse(argv[++i]);
    else if (argv[i] === "--urgency") a.urgency = String(argv[++i] || "");
    else if (argv[i] === "--provider") a.provider = String(argv[++i] || "twilio").toLowerCase();
  }
  return a;
}

function startServer({ port, event, provider, urgency }) {
  const isTelnyx = String(provider).toLowerCase() === "telnyx";
  const routeCarrier = isTelnyx ? routeTelnyxMessage : routeTwilioMessage;
  const carrierFrameFor = isTelnyx ? buildTelnyxMediaFrame : buildTwilioMediaFrame;
  // Lazy-require ws so --health works without it being needed.
  const WebSocket = require("ws");
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    console.error("[bridge] GEMINI_API_KEY missing");
    process.exit(1);
  }
  // The event Charon talks about. NO fake "dentist" default — a real call carries a real event;
  // a missing event degrades to a generic "your next appointment" in buildCallPrompt, never a lie.
  const callEvent = event || null;

  // Public host of THIS bridge (set by the runner to the tunnel host) so the
  // inbound-answer TwiML can <Connect><Stream> back to our own /ws.
  const PUBLIC_WSS = process.env.BRIDGE_PUBLIC_WSS || "";

  const server = http.createServer((req, res) => {
    const u = (req.url || "").split("?")[0];
    if (u === "/twiml-answer") {
      // The answering (inbound) leg: stream its audio to our bridge so Gemini hears
      // it and Charon speaks back. Used when we dial a number whose voice webhook is
      // this bridge (self-answered E2E proof).
      const wsUrl = PUBLIC_WSS || `wss://localhost/ws`;
      const twiml = require(LIB).buildConnectStreamTwiml(wsUrl);
      res.writeHead(200, { "content-type": "text/xml" });
      res.end(twiml);
      return;
    }
    res.writeHead(200, { "content-type": "text/plain" });
    res.end("anicca call-bridge ok\n");
  });
  const wss = new WebSocket.Server({ server, path: "/ws" });

  wss.on("connection", (carrierWs) => {
    console.log(`[bridge] carrier connected provider=${isTelnyx ? "telnyx" : "twilio"}`);
    const state = { streamSid: null, inFrames: 0, outFrames: 0, setupComplete: false };

    const gemini = new WebSocket(geminiLiveWsUrl(apiKey));
    const carrierSend = (o) => {
      if (carrierWs.readyState === WebSocket.OPEN) carrierWs.send(JSON.stringify(o));
    };
    const geminiSend = (o) => {
      if (gemini.readyState === WebSocket.OPEN) gemini.send(JSON.stringify(o));
    };

    gemini.on("open", () => {
      console.log("[bridge] Gemini connected");
      geminiSend(geminiSetupForEvent(callEvent, urgency));
    });
    gemini.on("message", (data) => {
      let msg;
      try {
        msg = JSON.parse(data.toString());
      } catch {
        return;
      }
      const r = routeGeminiMessage(msg, state, carrierSend, carrierFrameFor);
      if (r.kind === "setupComplete") {
        console.log("[bridge] EVENT setupComplete");
        // Kick Charon to speak the opening line immediately.
        geminiSend(buildGeminiTurn("Begin the call now with your opening line."));
      }
      // Surface both-side transcripts so call quality (did Charon answer the user?) is auditable.
      const t = parseGeminiTranscripts(msg);
      if (t.input) console.error(`[transcript] USER: ${t.input}`);
      if (t.output) console.error(`[transcript] CHARON: ${t.output}`);
      if (r.frames) console.log(`[bridge] EVENT gemini_audio frames=${state.outFrames}`);
    });
    gemini.on("error", (e) => console.error("[bridge] gemini err", e.message));
    gemini.on("close", () => console.log("[bridge] gemini closed"));

    carrierWs.on("message", (data) => {
      let msg;
      try {
        msg = JSON.parse(data.toString());
      } catch {
        return;
      }
      const kind = routeCarrier(msg, state, geminiSend);
      if (kind === "start") console.log(`[bridge] EVENT twilio_start sid=${state.streamSid}`);
      if (kind === "media" && state.inFrames % 100 === 0)
        console.log(`[bridge] EVENT twilio_media frames=${state.inFrames}`);
      if (kind === "stop") {
        console.log(`[bridge] EVENT twilio_stop in=${state.inFrames} out=${state.outFrames}`);
        try {
          gemini.close();
        } catch {}
      }
    });
    carrierWs.on("close", () => {
      console.log(`[bridge] carrier closed in=${state.inFrames} out=${state.outFrames}`);
      try {
        gemini.close();
      } catch {}
    });
  });

  server.listen(port, () => console.log(`[bridge] listening ${port} path=/ws`));
}

if (require.main === module) {
  const a = parseArgs(process.argv.slice(2));
  if (a.health) {
    // Prove call-logic loads + the live model is the fixed one.
    console.log(`[bridge] health ok model=${LIVE_MODEL}`);
    process.exit(0);
  }
  startServer(a);
}
