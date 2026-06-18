// apps/life-call/server.js — Life Manager CLOUD wake-call service (Railway, always-on).
//
// Two things in one process:
//   1. A PERSISTENT Gemini-Charon bridge at  wss://<svc>.up.railway.app/ws  — multi-call, with
//      per-call context read from the WS upgrade URL query (?summary=&dateTime=&location=&urgency=).
//      Telnyx streams the call's RTP here; we bridge it bidirectionally to Gemini Live (voice Charon).
//   2. The 60-second SCHEDULER (scheduler.js) that finds users due for a T-15min wake and dials them
//      with stream_url pointing back at THIS service's /ws.
//
// Unlike the local runner-telnyx.mjs (ephemeral cloudflared tunnel + one bridge per call), this is a
// stable always-on server: Railway gives a permanent public wss, so no cloudflared, no Mac-mini.
"use strict";

const http = require("http");
const { URL } = require("url");
const WebSocket = require("ws");
const {
  routeTelnyxMessage,
  routeGeminiMessage,
  geminiSetupForEvent,
  buildTelnyxMediaFrame,
} = require("./lib/call-bridge.cjs");
const {
  geminiLiveWsUrl,
  buildGeminiTurn,
  parseGeminiTranscripts,
} = require("./lib/call-logic.js");
const { startScheduler } = require("./scheduler.js");

const PORT = Number(process.env.PORT) || 8788;
const GEMINI_KEY = process.env.GEMINI_API_KEY;

// Build a GCal-shaped event ({summary,start:{dateTime},location}) + urgency from the /ws query.
// This is the per-call context — each Telnyx media stream carries its own, so a persistent
// multi-call bridge never leaks one caller's event into another's prompt.
function ctxFromReq(req) {
  let q;
  try {
    q = new URL(req.url, "http://x").searchParams;
  } catch {
    q = new URLSearchParams();
  }
  const event = {
    summary: q.get("summary") || "",
    start: { dateTime: q.get("dateTime") || "" },
    location: q.get("location") || "",
  };
  const urgency = q.get("urgency") || "gentle";
  return { event, urgency };
}

const server = http.createServer((req, res) => {
  const path = (req.url || "").split("?")[0];
  if (path === "/health" || path === "/") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ ok: true, service: "life-call", ws: "/ws" }));
    return;
  }
  res.writeHead(404);
  res.end("not found");
});

const wss = new WebSocket.Server({ server, path: "/ws" });

wss.on("connection", (carrierWs, req) => {
  if (!GEMINI_KEY) {
    console.error("[bridge] GEMINI_API_KEY missing — closing call");
    try { carrierWs.close(); } catch {}
    return;
  }
  const { event, urgency } = ctxFromReq(req);
  console.log(`[bridge] carrier connected event="${event.summary}" urgency=${urgency}`);
  const state = { streamSid: null, inFrames: 0, outFrames: 0, setupComplete: false };

  const gemini = new WebSocket(geminiLiveWsUrl(GEMINI_KEY));
  const carrierSend = (o) => { if (carrierWs.readyState === WebSocket.OPEN) carrierWs.send(JSON.stringify(o)); };
  const geminiSend = (o) => { if (gemini.readyState === WebSocket.OPEN) gemini.send(JSON.stringify(o)); };

  gemini.on("open", () => {
    console.log("[bridge] Gemini connected");
    geminiSend(geminiSetupForEvent(event, urgency)); // per-call Charon prompt
  });
  gemini.on("message", (data) => {
    let msg;
    try { msg = JSON.parse(data.toString()); } catch { return; }
    const r = routeGeminiMessage(msg, state, carrierSend, buildTelnyxMediaFrame);
    if (r.kind === "setupComplete") {
      console.log("[bridge] setupComplete");
      geminiSend(buildGeminiTurn("Begin the call now with your opening line."));
    }
    const t = parseGeminiTranscripts(msg);
    if (t.input) console.error(`[transcript] USER: ${t.input}`);
    if (t.output) console.error(`[transcript] CHARON: ${t.output}`);
  });
  gemini.on("error", (e) => console.error("[bridge] gemini err", e.message));
  gemini.on("close", () => console.log("[bridge] gemini closed"));

  carrierWs.on("message", (data) => {
    let msg;
    try { msg = JSON.parse(data.toString()); } catch { return; }
    const kind = routeTelnyxMessage(msg, state, geminiSend);
    if (kind === "stop") { try { gemini.close(); } catch {} }
  });
  carrierWs.on("close", () => {
    console.log(`[bridge] carrier closed in=${state.inFrames} out=${state.outFrames}`);
    try { gemini.close(); } catch {}
  });
});

server.listen(PORT, () => {
  console.log(`[life-call] listening ${PORT} ws=/ws`);
  startScheduler(); // begin the 60s wake loop once the bridge is up
});
