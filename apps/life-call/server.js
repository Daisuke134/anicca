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
  carrierActionForGeminiKind,
  makeGeminiEndHandler,
} = require("./lib/call-bridge.cjs");
const {
  geminiLiveWsUrl,
  buildGeminiTurn,
  parseGeminiTranscripts,
} = require("./lib/call-logic.js");
const { startScheduler, startTravelLoop, startAskLoop, startOnboardLoop, buildStreamUrl, langForPhone } = require("./scheduler.js");
const { openingTurnForLang } = require("./lib/call-language.js");
const { maybeStartLoops } = require("./lib/maybe-start-loops.js");
const { serve: inngestServe } = require("inngest/node"); // raw Node http server (NOT express) → use the node adapter
const { inngest } = require("./inngest/client.js");
const { functions: inngestFunctions } = require("./inngest/functions.js");
const inngestHandler = inngestServe({ client: inngest, functions: inngestFunctions });
const { placeCall, startRecording } = require("./lib/dial.js");
const { parseUpdate, sendMessage, answerCallbackQuery, routeCallbackData } = require("./lib/telegram.js");
const { resolveTelegramReply } = require("./lib/telegram-reply.js");
const { handleInboundReply, handleAskCallback, parseInboundRecipient } = require("./lib/ask.js");
const { isReplyToken } = require("./lib/reply-token.js");
const {
  sendStage, rowByChatId, setStage, saveField, handleOnboardingText, handleGmailCallback,
  applyTelegramProfileName, backfillIfCalendarCompleted,
} = require("./lib/telegram-onboard.js");
const { signedGmailConnectUrl, createHostedGmailLink } = require("./lib/gmail-onboard.js");
const { classifyLate, sendLateNotice } = require("./lib/notify.js");
const {
  handleLateCallback, listWakeRows, markAnswered, claimNotified,
  eventSummaryFor, deliverLateNotice, pendingT0Keys,
} = require("./lib/late-notice.js");
const { claimEvent, unclaimEvent, applyBilling } = require("./lib/billing.js");
const { recordCost } = require("./lib/ledger.js");
const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY || "sk_test_placeholder"); // apiKey unused by constructEvent
const SUPA_URL = process.env.SUPABASE_URL, SUPA_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const COMPOSIO_KEY = process.env.COMPOSIO_API_KEY;
const RESEND_API_KEY = process.env.RESEND_API_KEY || ""; // our-domain email send (asks + late-notice)
const LM_INBOUND_SECRET = process.env.LM_INBOUND_SECRET || ""; // shared secret in the Resend inbound webhook URL

const LM_TG_TOKEN = process.env.LM_TELEGRAM_BOT_TOKEN || "";
const LM_TG_SECRET = process.env.LM_TELEGRAM_WEBHOOK_SECRET || "";
const PUBLIC_BASE = process.env.PUBLIC_BASE || "https://aniccaai.com";
const GMAIL_ROUTE_BASE = process.env.LIFE_CALL_PUBLIC_BASE || process.env.PUBLIC_WSS || PUBLIC_BASE;
const GMAIL_ONBOARD_CONFIGURED = Boolean(
  process.env.LM_UID_SECRET && process.env.UNIPILE_DSN && process.env.UNIPILE_TOKEN && process.env.UNIPILE_NOTIFY_SECRET,
);

// inngestServeAllowed: pure helper — returns true when the /api/inngest route may serve requests.
// In dev (INNGEST_DEV=1) it always returns true; in prod it requires INNGEST_SIGNING_KEY.
// Exported for testing (FIND-005).
function inngestServeAllowed(env) {
  const isDev = String((env || {}).INNGEST_DEV || "").trim() === "1";
  if (isDev) return true;
  return Boolean((env || {}).INNGEST_SIGNING_KEY);
}

// stripeWebhookAllowed: mirrors inngestServeAllowed — dev (STRIPE_DEV=1) serves without a secret; prod
// requires STRIPE_WEBHOOK_SECRET else 503 fail-closed (REQ-41). Exported-shape pure helper for testing.
function stripeWebhookAllowed(env) {
  const isDev = String((env || {}).STRIPE_DEV || "").trim() === "1";
  if (isDev) return true;
  return Boolean((env || {}).STRIPE_WEBHOOK_SECRET);
}

// dunningNotify(uid): best-effort ONE message when a subscription goes past_due (REQ-40). Telegram if we
// have the user's chat, else logged (email is a later enhancement). NEVER throws (dunning must not 500 the webhook).
async function dunningNotify(uid) {
  try {
    if (!SUPA_URL || !SUPA_KEY) return;
    const r = await fetch(`${SUPA_URL}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}&select=telegram_chat_id,email`,
      { headers: { apikey: SUPA_KEY, Authorization: `Bearer ${SUPA_KEY}` } });
    const d = await r.json().catch(() => []);
    const row = Array.isArray(d) && d[0] ? d[0] : null;
    const msg = "⚠️ Your Life Manager payment didn't go through. Update your card to keep your wake calls active.";
    if (row && row.telegram_chat_id && LM_TG_TOKEN) await sendMessage(LM_TG_TOKEN, row.telegram_chat_id, msg);
    else console.log("[stripe] dunning (no telegram channel) uid=", uid, "email=", row && row.email);
  } catch (e) { console.error("[stripe] dunning err", e.message); }
}

const LM_UID_SECRET = process.env.LM_UID_SECRET || "";
function verifyUid(uid, sig) {
  if (!LM_UID_SECRET || !uid || !sig) return false;
  const expected = crypto.createHmac("sha256", LM_UID_SECRET).update(uid).digest("base64url");
  const a = Buffer.from(String(sig)), b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
// SERVER-SIDE rate-limit for /test-call. The dashboard "Call me now" button disables after one tap, but
// that gate is client-side ONLY — a page reload resets it, so a user could otherwise spam billed Charon
// calls. Every test call is real money, so we enforce the limit here (single always-on process → a Map is
// authoritative). Cooldown stops reload-spam; the daily cap bounds total cost per user.
const TEST_CALL_COOLDOWN_MS = 10 * 60 * 1000; // 1 test call per uid per 10 min
const TEST_CALL_DAILY_MAX = 5;                // hard ceiling per uid per rolling 24h
const _testCallLog = new Map();               // uid -> [epoch ms]
function testCallAllowed(uid, now = Date.now()) {
  const arr = (_testCallLog.get(uid) || []).filter((t) => now - t < 24 * 3600 * 1000);
  const last = arr[arr.length - 1];
  if (last !== undefined && now - last < TEST_CALL_COOLDOWN_MS) {
    return { ok: false, retryAfter: Math.ceil((TEST_CALL_COOLDOWN_MS - (now - last)) / 1000) };
  }
  if (arr.length >= TEST_CALL_DAILY_MAX) return { ok: false, retryAfter: 3600 };
  arr.push(now);
  _testCallLog.set(uid, arr);
  return { ok: true };
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
// readRawBody: collect the EXACT bytes as a Buffer (no utf8 string concat, which corrupts multi-byte chars
// split across chunks → Stripe signature mismatch). Used for the Stripe webhook where constructEvent must
// hash the raw bytes (FIND-005).
function readRawBody(req) {
  return new Promise((resolve) => {
    const chunks = []; let len = 0;
    req.on("data", (c) => { chunks.push(c); len += c.length; if (len > 1e5) req.destroy(); });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", () => resolve(Buffer.alloc(0)));
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
  const wakeUid = (q.get("wakeUid") || "").slice(0, 100);
  const wakeEventKey = (q.get("wakeEventKey") || "").slice(0, 300);
  const sig = q.get("sig") || "";

  const secret = process.env.LM_CALL_SECRET || "";
  const expected = crypto.createHmac("sha256", secret).update([summary, dateTime, location, urgency, lang, name, wakeUid, wakeEventKey].join("\n")).digest("base64url");
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (!secret || a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;

  return { event: { summary, start: { dateTime }, location }, urgency, lang, name, wakeUid, wakeEventKey };
}

const server = http.createServer((req, res) => {
  const path = (req.url || "").split("?")[0];
  if (path === "/health" || path === "/") {
    res.writeHead(200, { "content-type": "application/json" });
    // `build` lets any deploy be verified from outside (curl /health) — proves new code is live.
    res.end(JSON.stringify({ ok: true, service: "life-call", ws: "/ws", build: "lm6-ledger-v1" }));
    return;
  }
  // GET /gmail-connect — signed Telegram deep link into the existing real Unipile hosted-auth flow.
  // A provider/config failure is an explicit error; this route never claims Gmail was connected.
  if (path === "/gmail-connect") {
    if (req.method !== "GET") { res.writeHead(405); res.end("method"); return; }
    (async () => {
      const q = new URL(req.url, "http://x").searchParams;
      const uid = q.get("uid") || "";
      if (!verifyUid(uid, q.get("sig") || "")) { res.writeHead(403); res.end("bad uid signature"); return; }
      const redirect = await createHostedGmailLink(uid, {
        dsn: process.env.UNIPILE_DSN, token: process.env.UNIPILE_TOKEN,
        notifySecret: process.env.UNIPILE_NOTIFY_SECRET,
        publicBase: PUBLIC_BASE,
      });
      if (!redirect) { res.writeHead(503); res.end("Gmail connection is temporarily unavailable"); return; }
      res.writeHead(302, { Location: redirect }); res.end();
    })().catch((error) => { console.error("[gmail-onboard]", error.message); res.writeHead(503); res.end("Gmail connection is temporarily unavailable"); });
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
        // Cost guard: enforce the one-time/cooldown SERVER-SIDE (client gate resets on reload). 429 = too soon.
        const rl = testCallAllowed(body.uid);
        if (!rl.ok) return reply(429, { error: "rate_limited", retryAfter: rl.retryAfter });
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
          if (u.kind === "callback") {
            await answerCallbackQuery(LM_TG_TOKEN, u.callbackQueryId, "Received");
            await routeCallbackData(u.data, { ask: (data) => handleAskCallback(data, {
                chatId: u.chatId, telegramToken: LM_TG_TOKEN,
                supaUrl: SUPA_URL, supaKey: SUPA_KEY, composioKey: COMPOSIO_KEY,
              }), gmail: async (data) => {
                const row = await rowByChatId(u.chatId, SUPA_URL, SUPA_KEY);
                return handleGmailCallback(data, row, {
                  token: LM_TG_TOKEN, chatId: u.chatId, base: PUBLIC_BASE,
                  supaUrl: SUPA_URL, supaKey: SUPA_KEY,
                });
              }, late: async (data) => {
                const row = await rowByChatId(u.chatId, SUPA_URL, SUPA_KEY);
                if (!row) return { ok: false, reason: "unlinked_chat" };
                const dbOpts = { supaUrl: SUPA_URL, supaKey: SUPA_KEY };
                const rows = await listWakeRows(row.uid, dbOpts);
                return handleLateCallback({
                  uid: row.uid, chatId: u.chatId, data, rows,
                  secret: process.env.LM_CALL_SECRET || "", telegramToken: LM_TG_TOKEN,
                  noticeOpts: {
                    composioKey: COMPOSIO_KEY, geminiKey: GEMINI_KEY, resendKey: RESEND_API_KEY,
                    userEmail: row.email, userName: row.name,
                  },
                }, {
                  markAnswered: (uid, eventKey) => markAnswered(uid, eventKey, dbOpts),
                  summaryFor: (uid, startIso) => eventSummaryFor(uid, startIso, { composioKey: COMPOSIO_KEY }),
                  deliver: (input) => deliverLateNotice(input, {
                    claimNotified: (uid, eventKey, claimOpts) => claimNotified(uid, eventKey, claimOpts, dbOpts),
                    sendLateNotice, sendMessage,
                  }),
                });
              } });
            res.writeHead(200); res.end("ok");
            return;
          }
          const row = await rowByChatId(u.chatId, SUPA_URL, SUPA_KEY); // null until they link via /lm
          const gmailConnectUrl = row && GMAIL_ONBOARD_CONFIGURED
            ? signedGmailConnectUrl(row.uid, GMAIL_ROUTE_BASE, LM_UID_SECRET) : "";
          const opts = {
            token: LM_TG_TOKEN, base: PUBLIC_BASE, supaUrl: SUPA_URL, supaKey: SUPA_KEY, gmailConnectUrl,
            composioKey: COMPOSIO_KEY, geminiKey: GEMINI_KEY,
          };
          if (u.isStart) {
            // Name comes from the Telegram profile; calendar/pay are taps and phone is the only typed ask.
            const profile = { first_name: u.firstName, last_name: u.lastName };
            const effective = applyTelegramProfileName(row, profile);
            if (row && !row.name && effective.name) await saveField(row.uid, { name: effective.name }, SUPA_URL, SUPA_KEY);
            await backfillIfCalendarCompleted(row, opts);
            const announced = await sendStage(LM_TG_TOKEN, u.chatId, effective, PUBLIC_BASE, { profile, gmailConnectUrl });
            if (row) await setStage(row.uid, announced, SUPA_URL, SUPA_KEY);
          } else if (u.text) {
            // Any Telegram message inside a T-0 response window counts as a response and suppresses
            // the DB-driven 10-minute fallback. Each row update is conditional on answered_at NULL.
            if (row) {
              const dbOpts = { supaUrl: SUPA_URL, supaKey: SUPA_KEY };
              const wakeRows = await listWakeRows(row.uid, dbOpts);
              for (const eventKey of pendingT0Keys(wakeRows, Date.now()))
                await markAnswered(row.uid, eventKey, dbOpts);
            }
            // Native steps (name/phone) capture the typed value; web steps re-nudge; "done" → reply.
            const result = await handleOnboardingText(u.chatId, u.text, row, opts);
            if (result === "done") {
              // Onboarded → a free-text message is either "I'm running late …" (notify a stakeholder)
              // or a reply to a location ask. Classify, then route.
              const late = await classifyLate(u.text, GEMINI_KEY);
              if (late.isLate) {
                const n = await sendLateNotice(row.uid, u.text, {
                  composioKey: COMPOSIO_KEY, geminiKey: GEMINI_KEY, resendKey: RESEND_API_KEY,
                  userEmail: row.email, userName: row.name, etaMinutes: late.etaMinutes,
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
  // POST /inbound-email?s=<secret> — Resend Inbound webhook. A web user replied to our "where is X?" email
  // (To: reply+<token>@reply.aniccaai.com). Auth = the shared secret in the URL; we pull the token out of the
  // recipient, resolve it to (uid,event) via lm_ask_log, extract the location the user gave, and patch the
  // calendar + remember it. We never read the user's Gmail — this is OUR inbound domain. Always 200 (so the
  // provider doesn't retry); a bad/unknown token is a no-op.
  if (path === "/inbound-email") {
    if (req.method !== "POST") { res.writeHead(405); res.end("method"); return; }
    (async () => {
      try {
        const q = new URL(req.url, "http://x").searchParams;
        if (!LM_INBOUND_SECRET || q.get("s") !== LM_INBOUND_SECRET) { res.writeHead(403); res.end("forbidden"); return; }
        const body = JSON.parse((await readBody(req)) || "{}");
        const { token, text } = parseInboundRecipient(body); // pure, unit-tested across Resend payload shapes
        if (!isReplyToken(token)) { res.writeHead(200); res.end("no-token"); return; } // not one of ours → ignore
        const r = await handleInboundReply(token, text, { composioKey: COMPOSIO_KEY, geminiKey: GEMINI_KEY, supaUrl: SUPA_URL, supaKey: SUPA_KEY });
        console.log(`[inbound-email] token=${token.slice(0, 8)} ok=${r.ok} ${r.ok ? `${(r.uid || "").slice(0, 12)} → ${r.location}` : r.reason}`);
        res.writeHead(200); res.end(r.ok ? "patched" : "noop");
      } catch (e) { console.error("[inbound-email] err", e.message); res.writeHead(200); res.end("err"); }
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
  // POST /api/stripe/webhook — Stripe billing lifecycle = source of truth for lm_users.paid (HARD-3).
  // Verify the signature over the RAW body (REQ-35), dedup by event.id (REQ-36), then apply entitlement.
  // FAIL-CLOSED in prod when STRIPE_WEBHOOK_SECRET is missing (REQ-41).
  if (path === "/api/stripe/webhook") {
    if (req.method !== "POST") { res.writeHead(405); res.end("method"); return; }
    if (!stripeWebhookAllowed(process.env)) {
      res.writeHead(503, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: "stripe webhook secret not configured", service: "life-call" }));
      return;
    }
    (async () => {
      const raw = await readRawBody(req); // EXACT bytes (Buffer) for signature verification (FIND-005)
      let event;
      try {
        event = stripe.webhooks.constructEvent(raw, req.headers["stripe-signature"], process.env.STRIPE_WEBHOOK_SECRET || "");
      } catch (e) {
        console.error("[stripe] bad signature", e.message);
        res.writeHead(400); res.end("invalid signature"); return; // REQ-35: reject, no billing side effect
      }
      const claimed = await claimEvent(event.id, event.type, SUPA_URL, SUPA_KEY); // REQ-36 idempotency
      if (!claimed) { res.writeHead(200); res.end("duplicate"); return; }         // duplicate delivery → ack, no re-apply
      try {
        const result = await applyBilling(event, { supaUrl: SUPA_URL, supaKey: SUPA_KEY, notify: dunningNotify });
        console.log("[stripe]", event.type, JSON.stringify(result));
        res.writeHead(200); res.end("ok");
      } catch (e) {
        console.error("[stripe] apply failed", e.message);
        // FIND-006: release the claim so Stripe's redelivery re-processes. If THIS also fails, the event
        // stays claimed → the transition would stick; log a RECONCILE marker (writes are idempotent SETs).
        const released = await unclaimEvent(event.id, SUPA_URL, SUPA_KEY);
        if (!released) console.error("[stripe] RECONCILE: unclaim failed for", event.id, "— manual replay needed");
        res.writeHead(500); res.end("apply failed");
      }
    })();
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
  const { event, urgency, lang, name, wakeUid, wakeEventKey } = ctx;
  console.log(`[bridge] carrier connected urgency=${urgency} live=${liveCalls}`);
  const state = { streamSid: null, inFrames: 0, outFrames: 0, setupComplete: false };

  // C1 (VCSDD life-manager-cost-connect-reliability): Gemini Live is the DEFAULT — every answered call
  // is a two-way Charon conversation from the first second (no one-way clip). `liveWsOpened` is the
  // measurable Goal-1 invariant (now ≥1 on EVERY answered call, the inverse of the old escalation-only
  // invariant).
  let gemini = null;
  let callStartedAtMs = null;
  let liveWsOpened = 0;
  let gotAudio = false;       // has Gemini emitted any audio yet on this call?
  let geminiReconnects = 0;   // one-retry guard for a pre-audio socket drop
  const carrierSend = (o) => { if (carrierWs.readyState === WebSocket.OPEN) carrierWs.send(JSON.stringify(o)); };
  const geminiSend = (o) => { if (gemini && gemini.readyState === WebSocket.OPEN) gemini.send(JSON.stringify(o)); };

  // Open the Gemini Live bridge (billed, ~$0.023/min). Called on the Telnyx `start` frame (call
  // answered) — this IS the default path now, not an escalation. If the socket drops before any audio
  // was heard, retry ONCE; a second pre-audio failure ends the call cleanly (never silence, never a
  // clip fallback).
  function openGeminiLive() {
    if (gemini) return;
    liveWsOpened++;
    console.log(`[bridge] opening Gemini Live live_ws_opened=${liveWsOpened}`);
    gemini = new WebSocket(geminiLiveWsUrl(GEMINI_KEY));
    const geminiStartedAtMs = Date.now();
    let geminiCostRecorded = false;
    gemini.on("open", () => geminiSend(geminiSetupForEvent(event, urgency, lang, name)));
    gemini.on("message", (data) => {
      let msg;
      try { msg = JSON.parse(data.toString()); } catch { return; }
      const r = routeGeminiMessage(msg, state, carrierSend, buildTelnyxMediaFrame);
      if (r.kind === "setupComplete") geminiSend(buildGeminiTurn(openingTurnForLang(lang)));
      if (r.kind === "audio") gotAudio = true;
      // Barge-in: the caller spoke over Charon (Gemini server-VAD). Flush Telnyx's queued playback so
      // the caller is heard immediately instead of talked over.
      const carrierAction = carrierActionForGeminiKind(r.kind);
      if (carrierAction) carrierSend(carrierAction); // barge-in: flush Telnyx queued playback
      if (DEBUG_TRANSCRIPTS) {
        const t = parseGeminiTranscripts(msg);
        if (t.input) console.error(`[transcript] USER: ${t.input}`);
        if (t.output) console.error(`[transcript] CHARON: ${t.output}`);
      }
    });
    // ws fires `error` THEN `close` for a SINGLE failure — the factory's `ended` flag collapses the pair
    // (else the paired close would hang up the call right after the reconnect socket opened). One retry
    // only, for a pre-audio transient failure; otherwise end the call cleanly (never silence, never a clip).
    const onGeminiEnd = makeGeminiEndHandler({
      getGotAudio: () => gotAudio,
      getReconnects: () => geminiReconnects,
      incReconnects: () => { geminiReconnects++; },
      carrierOpen: () => carrierWs.readyState === WebSocket.OPEN,
      onReconnect: () => { gemini = null; openGeminiLive(); },
      onClose: () => { try { carrierWs.close(); } catch {} },
      log: (reason) => console.log(`[bridge] gemini ${reason} gotAudio=${gotAudio} reconnects=${geminiReconnects}`),
    });
    gemini.on("error", (e) => onGeminiEnd(`err ${e.message}`));
    gemini.on("close", () => {
      if (!geminiCostRecorded) {
        geminiCostRecorded = true;
        const quantity = Math.max(0, (Date.now() - geminiStartedAtMs) / 1000);
        // Duration proxy from spec §13's measured ~$0.023/min. Google bills Live API by actual
        // token usage, not wall time (https://ai.google.dev/gemini-api/docs/live-api/best-practices#pricing-billing),
        // but this bridge does not receive billable token totals, so the ledger stores this explicit estimate.
        recordCost({ uid: wakeUid || null, kind: "gemini_live", quantity, unit: "seconds",
          estUsd: quantity / 60 * 0.023, meta: { reconnect: geminiReconnects } });
      }
      onGeminiEnd("closed");
    });
  }

  carrierWs.on("message", (data) => {
    let msg;
    try { msg = JSON.parse(data.toString()); } catch { return; }
    const kind = routeTelnyxMessage(msg, state, geminiSend);
    if (kind === "start") {
      if (callStartedAtMs == null) callStartedAtMs = Date.now();
      // Telnyx emits media `start` only after the call is active; dial.js already uses this same signal
      // for record_start because an unanswered/ringing call rejects that action. It is therefore the
      // existing answered approximation for the exact wake row carried in the signed stream context.
      if (wakeUid && wakeEventKey) markAnswered(wakeUid, wakeEventKey, {
        supaUrl: SUPA_URL, supaKey: SUPA_KEY,
      }).catch((e) => console.error(`[bridge] answered_at update failed: ${e && e.message}`));
      if (state.callControlId && !state.recordStarted) {
        state.recordStarted = true;
        startRecording(state.callControlId).then((r) => {
          if (r.ok) console.log(`[bridge] recording started ccid=${state.callControlId}`);
          else console.error(`[bridge] record_start FAILED: ${r.error}`);
        });
      }
      if (!gemini) openGeminiLive(); // DEFAULT: two-way Gemini Live from second 1
    }
    if (kind === "dtmf") console.log("[bridge] DTMF ignored (Gemini Live already open)");
    if (kind === "stop" && gemini) { try { gemini.close(); } catch {} }
  });
  let released = false;
  const release = () => { if (!released) { released = true; liveCalls = Math.max(0, liveCalls - 1); } };
  carrierWs.on("close", () => {
    release();
    console.log(`[bridge] carrier closed in=${state.inFrames} out=${state.outFrames} live_ws_opened=${liveWsOpened} live=${liveCalls}`);
    if (callStartedAtMs != null) {
      const quantity = Math.max(0, (Date.now() - callStartedAtMs) / 1000);
      recordCost({ uid: wakeUid || null, kind: "telnyx_call", quantity, unit: "seconds",
        estUsd: quantity / 60 * 0.002, meta: { stream_id: state.streamSid || null } });
    }
    if (gemini) { try { gemini.close(); } catch {} }
  });
  carrierWs.on("error", release);
});

// Only bind to the port when this file is run directly (not when required by tests).
// This allows test files to import inngestServeAllowed without starting the HTTP server.
if (require.main === module) {
  server.listen(PORT, () => {
    console.log(`[life-call] listening ${PORT} ws=/ws build=lm6-ledger-v1`);
    // SINGLE-WRITER (B3): run the scheduler loops in-process ONLY when LIFE_RUN_LOOPS!=="false".
    // The /ws Telnyx⇄Gemini-Live voice bridge + /test-call + /telegram endpoints are ALWAYS on regardless.
    // As an OpenClaw voice daemon, set LIFE_RUN_LOOPS=false so the cron-COMMAND jobs (B2) own the loops.
    const loops = maybeStartLoops(process.env, { startScheduler, startTravelLoop, startAskLoop, startOnboardLoop });
    console.log(`[life-call] ${loops.started ? "loops ON (standalone)" : "VOICE DAEMON (loops OFF)"} — ${loops.reason}`);
  });
}

// redeploy trigger 010026

// Export pure helpers for unit tests (FIND-005).
module.exports = { inngestServeAllowed, testCallAllowed, TEST_CALL_COOLDOWN_MS, TEST_CALL_DAILY_MAX };
