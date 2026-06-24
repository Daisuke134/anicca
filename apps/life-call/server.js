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
const crypto = require("crypto");
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
const { startScheduler, startTravelLoop, startAskLoop, startOnboardLoop, buildStreamUrl, langForPhone } = require("./scheduler.js");
const { maybeStartLoops } = require("./lib/maybe-start-loops.js");
const { serve: inngestServe } = require("inngest/node"); // raw Node http server (NOT express) → use the node adapter
const { inngest } = require("./inngest/client.js");
const { functions: inngestFunctions } = require("./inngest/functions.js");
const inngestHandler = inngestServe({ client: inngest, functions: inngestFunctions });
const { placeCall, startRecording } = require("./lib/dial.js");
const { parseUpdate, sendMessage } = require("./lib/telegram.js");
const { resolveTelegramReply } = require("./lib/telegram-reply.js");
const { sendStage, rowByChatId, setStage, handleOnboardingText } = require("./lib/telegram-onboard.js");
const { classifyLate, sendLateNotice } = require("./lib/notify.js");
const SUPA_URL = process.env.SUPABASE_URL, SUPA_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const COMPOSIO_KEY = process.env.COMPOSIO_API_KEY, UNIPILE_TOKEN = process.env.UNIPILE_TOKEN, UNIPILE_DSN = process.env.UNIPILE_DSN;

const LM_TG_TOKEN = process.env.LM_TELEGRAM_BOT_TOKEN || "";
const LM_TG_SECRET = process.env.LM_TELEGRAM_WEBHOOK_SECRET || "";
const PUBLIC_BASE = process.env.PUBLIC_BASE || "https://aniccaai.com";

// inngestServeAllowed: pure helper — returns true when the /api/inngest route may serve requests.
// In dev (INNGEST_DEV=1) it always returns true; in prod it requires INNGEST_SIGNING_KEY.
// Exported for testing (FIND-005).
function inngestServeAllowed(env) {
  const isDev = String((env || {}).INNGEST_DEV || "").trim() === "1";
  if (isDev) return true;
  return Boolean((env || {}).INNGEST_SIGNING_KEY);
}

const LM_UID_SECRET = process.env.LM_UID_SECRET || "";
function verifyUid(uid, sig) {
  if (!LM_UID_SECRET || !uid || !sig) return false;
  const expected = crypto.createHmac("sha256", LM_UID_SECRET).update(uid).digest("base64url");
  const a = Buffer.from(String(sig)), b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
async function userForUid(uid) {
  const url = process.env.SUPABASE_URL, key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return null;
  // phone (to dial) + call_language (user-chosen call language, may be null → fall back to phone) +
  // name (so the call can address them by name).
  const r = await fetch(`${url}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}&select=phone,call_language,name`,
    { headers: { apikey: key, Authorization: `Bearer ${key}` } });
  const d = await r.json().catch(() => []);
  return Array.isArray(d) && d[0] ? d[0] : null;
}
function readBody(req) {
  return new Promise((resolve) => {
    let b = ""; req.on("data", (c) => { b += c; if (b.length > 1e5) req.destroy(); });
    req.on("end", () => resolve(b)); req.on("error", () => resolve(""));
  });
}

const PORT = Number(process.env.PORT) || 8788;
const GEMINI_KEY = process.env.GEMINI_API_KEY;
const DEBUG_TRANSCRIPTS = process.env.DEBUG_TRANSCRIPTS === "1";
const MAX_CONCURRENT = Number(process.env.MAX_CONCURRENT_CALLS) || 8;
const VALID_URGENCY = new Set(["gentle", "firm", "harsh"]);
let liveCalls = 0;

// Build a GCal-shaped event ({summary,start:{dateTime},location}) + urgency from the /ws query —
// AND authenticate it. Each Telnyx media stream carries its own signed context; an unsigned or
// tampered connection is rejected before any Gemini socket opens (no budget drain, no prompt
// injection). Returns null when the HMAC (over summary|dateTime|location|urgency, keyed by
// LM_CALL_SECRET) does not verify.
function ctxFromReq(req) {
  let q;
  try {
    q = new URL(req.url, "http://x").searchParams;
  } catch {
    return null;
  }
  const summary = (q.get("summary") || "").slice(0, 200);
  const dateTime = (q.get("dateTime") || "").slice(0, 40);
  const location = (q.get("location") || "").slice(0, 200);
  let urgency = q.get("urgency") || "gentle";
  if (!VALID_URGENCY.has(urgency)) urgency = "gentle";
  let lang = q.get("lang");
  if (lang !== "ja" && lang !== "en") lang = "en"; // call language follows the user (JP→ja, else en)
  const name = (q.get("name") || "").slice(0, 60); // who to address on the call (already sanitized when signed)
  const sig = q.get("sig") || "";

  const secret = process.env.LM_CALL_SECRET || "";
  const expected = crypto.createHmac("sha256", secret).update([summary, dateTime, location, urgency, lang, name].join("\n")).digest("base64url");
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (!secret || a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;

  return { event: { summary, start: { dateTime }, location }, urgency, lang, name };
}

const server = http.createServer((req, res) => {
  const path = (req.url || "").split("?")[0];
  if (path === "/health" || path === "/") {
    res.writeHead(200, { "content-type": "application/json" });
    // `build` lets any deploy be verified from outside (curl /health) — proves new code is live.
    res.end(JSON.stringify({ ok: true, service: "life-call", ws: "/ws", build: "converse-v1" }));
    return;
  }
  // POST /test-call {uid,sig} — the dashboard "Call me now" button. Auth'd by the same HMAC uid+sig
  // the /lm app already holds; we look up the user's phone and place an immediate Charon call so they
  // hear, right then, that the wake calls work. CORS-open for aniccaai.com (the static /lm page).
  if (path === "/test-call") {
    res.setHeader("Access-Control-Allow-Origin", "https://aniccaai.com");
    res.setHeader("Access-Control-Allow-Headers", "content-type");
    res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
    if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }
    if (req.method !== "POST") { res.writeHead(405); res.end("method"); return; }
    (async () => {
      const reply = (code, obj) => { res.writeHead(code, { "content-type": "application/json" }); res.end(JSON.stringify(obj)); };
      try {
        const body = JSON.parse((await readBody(req)) || "{}");
        if (!verifyUid(body.uid, body.sig)) return reply(403, { error: "bad uid signature" });
        const u = await userForUid(body.uid);
        const phone = u && u.phone;
        if (!phone) return reply(400, { error: "no phone on file" });
        // Call language = the user's CHOICE (lm_users.call_language, set via the /lm toggle) if present,
        // else fall back to the phone country (+81 → ja, else en). Dais 2026-06-22.
        const lang = (u.call_language === "ja" || u.call_language === "en") ? u.call_language : langForPhone(phone);
        // Caller may pass a REAL event (summary/location/urgency) so the call + its recording are
        // postable content — NEVER hardcode "test" (the assistant reads the summary aloud). Default = a
        // real morning nudge in the USER's language, not a "test" label.
        const ev = {
          summary: (body.summary || (lang === "ja" ? "次のご予定" : "your next appointment")).toString().slice(0, 200),
          startIso: body.dateTime || new Date(Date.now() + 15 * 60000).toISOString(),
          location: (body.location || "").toString().slice(0, 200),
        };
        const urgency = ["gentle", "firm", "harsh"].includes(body.urgency) ? body.urgency : "gentle";
        const streamUrl = buildStreamUrl(ev, urgency, lang, u.name);
        const result = await placeCall({ to: phone, streamUrl });
        return reply(result.ok ? 200 : 502, result);
      } catch (e) {
        return reply(502, { error: String(e) });
      }
    })();
    return;
  }
  // POST /telegram — the Life Manager bot webhook. Telegram echoes our secret in a header; reject
  // anything that doesn't match (so strangers can't post fake updates). /start hands the user to the
  // web onboarding (deep-linked with their chat id); any other text is treated as a reply to a
  // pending location ask and routed to the calendar.
  if (path === "/telegram") {
    if (req.method !== "POST") { res.writeHead(405); res.end("method"); return; }
    // Fail CLOSED: no secret configured → reject. Constant-time compare to avoid timing leaks.
    const hdr = String(req.headers["x-telegram-bot-api-secret-token"] || "");
    const ok = LM_TG_SECRET.length > 0 && hdr.length === LM_TG_SECRET.length &&
      crypto.timingSafeEqual(Buffer.from(hdr), Buffer.from(LM_TG_SECRET));
    if (!ok) { res.writeHead(401); res.end("unauthorized"); return; }
    (async () => {
      try {
        const update = JSON.parse((await readBody(req)) || "{}");
        const u = parseUpdate(update);
        if (u && LM_TG_TOKEN) {
          const row = await rowByChatId(u.chatId, SUPA_URL, SUPA_KEY); // null until they link via /lm
          const opts = { token: LM_TG_TOKEN, base: PUBLIC_BASE, supaUrl: SUPA_URL, supaKey: SUPA_KEY };
          if (u.isStart) {
            // Guided onboarding: send the user's CURRENT step (asks for name first if brand-new).
            const announced = await sendStage(LM_TG_TOKEN, u.chatId, row, PUBLIC_BASE);
            if (row) await setStage(row.uid, announced, SUPA_URL, SUPA_KEY);
          } else if (u.text) {
            // Native steps (name/phone) capture the typed value; web steps re-nudge; "done" → reply.
            const result = await handleOnboardingText(u.chatId, u.text, row, opts);
            if (result === "done") {
              // Onboarded → a free-text message is either "I'm running late …" (notify a stakeholder)
              // or a reply to a location ask. Classify, then route.
              const late = await classifyLate(u.text, GEMINI_KEY);
              if (late.isLate) {
                const n = await sendLateNotice(row.uid, u.text, {
                  composioKey: COMPOSIO_KEY, geminiKey: GEMINI_KEY, unipileToken: UNIPILE_TOKEN,
                  unipileDsn: UNIPILE_DSN, accountId: row.gmail_account_id, userName: row.name, etaMinutes: late.etaMinutes,
                });
                await sendMessage(LM_TG_TOKEN, u.chatId,
                  n.sent ? `✅ Let <b>${n.to}</b> know you're ${n.etaMinutes ? `~${n.etaMinutes} min ` : ""}late to “${n.event}”.`
                         : "I couldn't find an upcoming event with someone to notify. Which meeting did you mean?");
              } else {
                const res2 = await resolveTelegramReply(u.chatId, u.text);
                await sendMessage(LM_TG_TOKEN, u.chatId,
                  res2.filled ? `✅ Got it — set “${res2.event}” to ${res2.location}.`
                              : "Thanks! If that was an event location, reply to my question and I'll add it.");
              }
            }
          }
        }
      } catch (e) { console.error("[telegram] err", e.message); }
      res.writeHead(200); res.end("ok"); // always 200 fast so Telegram doesn't retry
    })();
    return;
  }
  // POST/GET /api/inngest — Inngest durable function endpoint (always mounted, independent of LIFE_RUN_LOOPS).
  // Inngest cloud calls this to register functions and dispatch events. In dev, INNGEST_DEV=1 syncs with
  // the local Inngest dev server. In prod, INNGEST_SIGNING_KEY authenticates incoming requests.
  // FAIL-CLOSED: in production (INNGEST_DEV not "1"), if INNGEST_SIGNING_KEY is missing we return 503
  // rather than serve unauthenticated — matching the fail-closed convention of /telegram and /ws.
  // In dev (INNGEST_DEV=1) we serve without a signing key so the local dev server can sync.
  // Both the in-process LIFE_RUN_LOOPS path and the Inngest path coexist; C-H1 (claimWake/claimTravel)
  // makes concurrent executions race-safe so running both simultaneously is harmless.
  if (path === "/api/inngest") {
    if (!inngestServeAllowed(process.env)) {
      res.writeHead(503, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: "inngest signing key not configured", service: "life-call" }));
      return;
    }
    return inngestHandler(req, res);
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
  // Auth gate: reject unsigned/tampered upgrades BEFORE opening a Gemini socket (cost + injection).
  const ctx = ctxFromReq(req);
  if (!ctx) {
    console.error("[bridge] rejected unauthenticated /ws connection");
    try { carrierWs.close(1008, "unauthorized"); } catch {}
    return;
  }
  if (liveCalls >= MAX_CONCURRENT) {
    console.error(`[bridge] at capacity (${liveCalls}/${MAX_CONCURRENT}) — rejecting`);
    try { carrierWs.close(1013, "busy"); } catch {}
    return;
  }
  liveCalls++;
  const { event, urgency, lang, name } = ctx;
  console.log(`[bridge] carrier connected urgency=${urgency} live=${liveCalls}`);
  const state = { streamSid: null, inFrames: 0, outFrames: 0, setupComplete: false };

  const gemini = new WebSocket(geminiLiveWsUrl(GEMINI_KEY));
  const carrierSend = (o) => { if (carrierWs.readyState === WebSocket.OPEN) carrierWs.send(JSON.stringify(o)); };
  const geminiSend = (o) => { if (gemini.readyState === WebSocket.OPEN) gemini.send(JSON.stringify(o)); };

  gemini.on("open", () => {
    console.log("[bridge] Gemini connected");
    geminiSend(geminiSetupForEvent(event, urgency, lang, name)); // per-call prompt (language + name follow the user)
  });
  gemini.on("message", (data) => {
    let msg;
    try { msg = JSON.parse(data.toString()); } catch { return; }
    const r = routeGeminiMessage(msg, state, carrierSend, buildTelnyxMediaFrame);
    if (r.kind === "setupComplete") {
      console.log("[bridge] setupComplete");
      geminiSend(buildGeminiTurn("Begin the call now with your opening line."));
    }
    if (DEBUG_TRANSCRIPTS) {
      const t = parseGeminiTranscripts(msg); // PII (user speech) — off unless explicitly enabled
      if (t.input) console.error(`[transcript] USER: ${t.input}`);
      if (t.output) console.error(`[transcript] CHARON: ${t.output}`);
    }
  });
  gemini.on("error", (e) => console.error("[bridge] gemini err", e.message));
  gemini.on("close", () => console.log("[bridge] gemini closed"));

  carrierWs.on("message", (data) => {
    let msg;
    try { msg = JSON.parse(data.toString()); } catch { return; }
    const kind = routeTelnyxMessage(msg, state, geminiSend);
    // Call is ANSWERED the moment the media `start` frame arrives → record_start is valid NOW
    // (firing it right after dial fails: the call was still ringing). Once per call; log result.
    if (kind === "start" && state.callControlId && !state.recordStarted) {
      state.recordStarted = true;
      startRecording(state.callControlId).then((r) => {
        if (r.ok) console.log(`[bridge] recording started ccid=${state.callControlId}`);
        else console.error(`[bridge] record_start FAILED: ${r.error}`);
      });
    }
    if (kind === "stop") { try { gemini.close(); } catch {} }
  });
  let released = false;
  const release = () => { if (!released) { released = true; liveCalls = Math.max(0, liveCalls - 1); } };
  carrierWs.on("close", () => {
    release();
    console.log(`[bridge] carrier closed in=${state.inFrames} out=${state.outFrames} live=${liveCalls}`);
    try { gemini.close(); } catch {}
  });
  carrierWs.on("error", release);
});

// Only bind to the port when this file is run directly (not when required by tests).
// This allows test files to import inngestServeAllowed without starting the HTTP server.
if (require.main === module) {
  server.listen(PORT, () => {
    console.log(`[life-call] listening ${PORT} ws=/ws build=agentic-ask-worldwide-v2`);
    // SINGLE-WRITER (B3): run the scheduler loops in-process ONLY when LIFE_RUN_LOOPS!=="false".
    // The /ws Telnyx⇄Gemini-Live voice bridge + /test-call + /telegram endpoints are ALWAYS on regardless.
    // As an OpenClaw voice daemon, set LIFE_RUN_LOOPS=false so the cron-COMMAND jobs (B2) own the loops.
    const loops = maybeStartLoops(process.env, { startScheduler, startTravelLoop, startAskLoop, startOnboardLoop });
    console.log(`[life-call] ${loops.started ? "loops ON (standalone)" : "VOICE DAEMON (loops OFF)"} — ${loops.reason}`);
  });
}

// redeploy trigger 010026

// Export pure helpers for unit tests (FIND-005).
module.exports = { inngestServeAllowed };
