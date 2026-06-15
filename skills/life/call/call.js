#!/usr/bin/env node
// ~/anicca/skills/life/call/call.js
// B-call skill entrypoint — spec27 WF-B B-call.
//
// Calls the user (Dais) 15 min before each calendar event and talks two-way using
// Gemini Live (voice = Charon, male) bridged over Twilio Media Streams.
//
//   PSTN (μ-law 8kHz)  <--Twilio Media Streams ws-->  bridge  <--Gemini Live ws-->  Charon
//
// The deterministic codec + wire-shape logic lives in ./call-logic.js (TDD-covered,
// mirror of apps/landing/netlify/functions/_lib/call-logic.js). This file is the thin
// I/O layer: Twilio REST dial + the websocket bridge. It is exercised by the verifier's
// REAL dial (HARD 0.24/0.31 — no fake run).
//
// Usage:
//   node call.js --to +818046270314 --event '{"summary":"伊藤歯科","start":{"dateTime":"2026-06-16T09:45:00+09:00"},"location":"表参道"}'
//   node call.js --serve                      # run the Media Streams <-> Gemini bridge ws server
//
// Env (read from ~/.openclaw/.env):
//   GEMINI_API_KEY                  — required (Gemini Live)
//   TWILIO_ACCOUNT_SID/AUTH_TOKEN   — required (Twilio REST)
//   TWILIO_PHONE_NUMBER | TWILIO_FROM — caller id
//   CALL_TO                         — default callee (default +818046270314)
//   GEMINI_LIVE_MODEL               — default gemini-2.0-flash-live-001
//   GEMINI_VOICE                    — default Charon
//   CALL_PUBLIC_WS_URL              — public wss the <Stream> connects to (serve mode)
//   CALL_TWIML_URL                  — public https that returns the Connect/Stream TwiML
//   CALL_BRIDGE_PORT                — local ws port for --serve (default 8787)

"use strict";

const path = require("path");
const fs = require("fs");
const http = require("http");
const {
  twilioMuLawToGeminiPcm16,
  geminiPcm24ToTwilioMuLaw,
  buildGeminiSetup,
  buildGeminiAudioInput,
  buildTwilioMediaFrame,
  buildCallPrompt,
  buildConnectStreamTwiml,
} = require("./call-logic");

// ── Env ───────────────────────────────────────────────────────────────────────

function loadEnv() {
  const envPath = path.join(process.env.HOME, ".openclaw", ".env");
  const raw = fs.existsSync(envPath) ? fs.readFileSync(envPath, "utf8") : "";
  const out = {};
  for (const line of raw.split("\n")) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) out[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
  return out;
}

const ENV = loadEnv();
const get = (k, d) => process.env[k] || ENV[k] || d;

const GEMINI_API_KEY = get("GEMINI_API_KEY", "");
const TWILIO_SID = get("TWILIO_ACCOUNT_SID", "");
const TWILIO_TOKEN = get("TWILIO_AUTH_TOKEN", "");
const TWILIO_FROM = get("TWILIO_PHONE_NUMBER", get("TWILIO_FROM", ""));
const CALL_TO = get("CALL_TO", "+818046270314");
const GEMINI_MODEL = get("GEMINI_LIVE_MODEL", "gemini-2.0-flash-live-001");
const GEMINI_VOICE = get("GEMINI_VOICE", "Charon");
const PUBLIC_WS_URL = get("CALL_PUBLIC_WS_URL", "");
const TWIML_URL = get("CALL_TWIML_URL", "");
const BRIDGE_PORT = parseInt(get("CALL_BRIDGE_PORT", "8787"), 10);
const GEMINI_WS =
  "wss://generativelanguage.googleapis.com/ws/" +
  "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent";

// ── Twilio REST outbound dial (fetch + Basic auth, no twilio SDK) ─────────────

/**
 * Place an outbound call whose audio is connected to our Media Streams bridge.
 * @param {object} o
 * @param {string} o.to     - E.164 callee
 * @param {string} o.from   - E.164 caller id
 * @param {string} o.twimlUrl - public https returning the Connect/Stream TwiML
 * @returns {Promise<object>} Twilio call resource (has .sid)
 */
async function dialOutbound({ to, from, twimlUrl }) {
  if (!TWILIO_SID || !TWILIO_TOKEN) throw new Error("TWILIO_ACCOUNT_SID/AUTH_TOKEN not set");
  if (!from) throw new Error("TWILIO_PHONE_NUMBER/TWILIO_FROM not set");
  if (!twimlUrl) throw new Error("twimlUrl (CALL_TWIML_URL) not set");

  const body = new URLSearchParams({ To: to, From: from, Url: twimlUrl });
  const auth = Buffer.from(`${TWILIO_SID}:${TWILIO_TOKEN}`).toString("base64");
  const res = await fetch(`https://api.twilio.com/2010-04-01/Accounts/${TWILIO_SID}/Calls.json`, {
    method: "POST",
    headers: {
      Authorization: `Basic ${auth}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(`twilio ${res.status} ${JSON.stringify(json)}`);
  return json;
}

// ── Media Streams <-> Gemini Live bridge ──────────────────────────────────────

/**
 * Bridge one Twilio Media Streams socket to a fresh Gemini Live session.
 * Twilio inbound μ-law → Gemini PCM16; Gemini PCM24 → Twilio μ-law.
 * @param {WebSocket} twilioWs - the connected Twilio Media Streams socket
 * @param {string} systemInstruction - Charon's call script
 */
function bridge(twilioWs, systemInstruction) {
  if (!GEMINI_API_KEY) throw new Error("GEMINI_API_KEY not set");
  let streamSid = null;
  const gemini = new WebSocket(`${GEMINI_WS}?key=${GEMINI_API_KEY}`);

  gemini.addEventListener("open", () => {
    gemini.send(JSON.stringify(buildGeminiSetup({
      model: GEMINI_MODEL, voiceName: GEMINI_VOICE, systemInstruction,
    })));
  });

  gemini.addEventListener("message", async (ev) => {
    let msg;
    try {
      const text = typeof ev.data === "string" ? ev.data : await ev.data.text();
      msg = JSON.parse(text);
    } catch { return; }
    const parts = msg.serverContent && msg.serverContent.modelTurn && msg.serverContent.modelTurn.parts;
    if (!Array.isArray(parts) || !streamSid) return;
    for (const p of parts) {
      const inline = p.inlineData || p.inline_data;
      if (inline && inline.data) {
        const muLawB64 = geminiPcm24ToTwilioMuLaw(inline.data);
        twilioWs.send(JSON.stringify(buildTwilioMediaFrame(streamSid, muLawB64)));
      }
    }
  });

  twilioWs.addEventListener("message", (ev) => {
    let data;
    try { data = JSON.parse(typeof ev.data === "string" ? ev.data : ev.data.toString()); }
    catch { return; }
    if (data.event === "start") {
      streamSid = data.start && data.start.streamSid;
    } else if (data.event === "media" && data.media && data.media.payload) {
      if (gemini.readyState === 1 /* OPEN */) {
        const pcm16 = twilioMuLawToGeminiPcm16(data.media.payload);
        gemini.send(JSON.stringify(buildGeminiAudioInput(pcm16)));
      }
    } else if (data.event === "stop") {
      try { gemini.close(); } catch {}
    }
  });

  const closeBoth = () => { try { gemini.close(); } catch {} try { twilioWs.close(); } catch {} };
  twilioWs.addEventListener("close", closeBoth);
  gemini.addEventListener("close", () => { try { twilioWs.close(); } catch {} });
  gemini.addEventListener("error", closeBoth);
}

/**
 * Run the bridge ws server: serves the Connect/Stream TwiML over HTTP and accepts
 * the Media Streams websocket upgrade, bridging each call to Gemini Live.
 * Requires `ws` (Node has a built-in WebSocket client but no server) — present in
 * the landing app; the skill box installs it on demand.
 */
function serve(systemInstruction) {
  const { WebSocketServer } = require("ws");
  const server = http.createServer((req, res) => {
    if (req.method === "POST" || req.url.startsWith("/twiml")) {
      const wsUrl = PUBLIC_WS_URL || `wss://${req.headers.host}/media`;
      res.writeHead(200, { "Content-Type": "text/xml" });
      res.end(buildConnectStreamTwiml(wsUrl));
      return;
    }
    res.writeHead(404); res.end("not found");
  });
  const wss = new WebSocketServer({ server, path: "/media" });
  wss.on("connection", (twilioWs) => bridge(twilioWs, systemInstruction));
  server.listen(BRIDGE_PORT, () => console.log(`[call] bridge listening on :${BRIDGE_PORT} (ws /media)`));
  return server;
}

// ── CLI ───────────────────────────────────────────────────────────────────────

function argVal(flag) {
  const i = process.argv.indexOf(flag);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : null;
}

async function main() {
  const wantsServe = process.argv.includes("--serve");
  const to = argVal("--to") || CALL_TO;
  const eventRaw = argVal("--event");
  let event = {};
  if (eventRaw) { try { event = JSON.parse(eventRaw); } catch { console.error("[call] --event must be JSON"); process.exit(1); } }
  const prompt = buildCallPrompt(event);

  if (wantsServe) {
    serve(prompt);
    return; // long-running
  }

  console.log(`[call] dialing ${to} from ${TWILIO_FROM} — "${event.summary || "(no title)"}"`);
  const call = await dialOutbound({ to, from: TWILIO_FROM, twimlUrl: TWIML_URL });
  console.log(JSON.stringify({ ok: true, callSid: call.sid, status: call.status, to }, null, 2));
}

if (require.main === module) {
  main().catch((err) => { console.error("[call] fatal:", err.message); process.exit(1); });
}

module.exports = { dialOutbound, bridge, serve, buildCallPrompt };
