// scheduler.js — the cloud wake loop. Every 60s: find Life Manager users due for a T-10/T-5 min wake
// and place a Telnyx+Gemini-Charon call whose audio bridges back to THIS service's /ws.
//
// Source of truth:
//   lm_users (Supabase)        — registry: who has a phone + paid + a connected gcal
//   Composio connected_account — the actual Google Calendar OAuth (keyed by the SAME uid)
//   lm_wake_log (Supabase)     — dedup: one call per (uid, event start), survives restarts
"use strict";

const crypto = require("crypto");
const { fetchUpcomingEvents } = require("./lib/events.js");
const { schedulerCohortFilter } = require("./lib/user-selector.js");
const { DEFAULTS: RUNTIME_DEFAULTS, readRuntimePreferences } = require("./lib/runtime-preferences.js");
const { shouldWake, resolveDeparture, isHelperBlock } = require("./lib/wake-filter.js");
const { mentalUserOnce, resolveSleepTarget } = require("./lib/mental-runtime.js");
const { careUserOnce } = require("./lib/care-daily-runtime.js");
const { dietUserOnce } = require("./lib/diet-runtime.js");
const { dietNudgeOnce } = require("./lib/diet-nudge.js");
const { preceptsUserOnce } = require("./lib/precepts-runtime.js");
const { preceptsMirrorOnce } = require("./lib/precepts-mirror.js");
const { readMentalSendState, recordMentalSend } = require("./lib/mental-send-log.js");

// 12c: TROUGH_AFTER_MS (30 min) plus margin — how far back the tick looks for ended events.
const MENTAL_LOOKBACK_MS = 35 * 60000;
const { placeCall } = require("./lib/dial.js");
const { fillTravel, directionsMinutes } = require("./lib/travel.js");
const { formatTravelAutofillMessage } = require("./lib/i18n.js");
const { askTick } = require("./lib/ask.js");
const { onboardNudgeAll } = require("./lib/telegram-onboard.js");
const { sendMessage } = require("./lib/telegram.js");
const { sendLateNotice } = require("./lib/notify.js");
const { langForPhone } = require("./lib/call-language.js");
const { recordDailyComposioPoll } = require("./lib/ledger.js");
const { schedulerPollInterval } = require("./lib/composio-budget.js");
const {
  processLocationLateNotice, getLiveLocation, claimLateEvent,
} = require("./lib/late-notice.js");
const {
  DISCOVERY_WEEK_MS, listDiscoveryUsers, runDiscoveryForUser,
} = require("./lib/feature-discovery.js");

// HMAC over the per-call context so the persistent /ws bridge can prove a connection was minted by
// THIS scheduler (not a stranger draining the Gemini budget) AND that the prompt context wasn't
// tampered in transit. server.js recomputes the same MAC and rejects on mismatch.
function signCtx(parts) {
  const secret = process.env.LM_CALL_SECRET || "";
  return crypto.createHmac("sha256", secret).update(parts.join("\n")).digest("base64url");
}

const TICK_MS = 60 * 1000;
// Escalating wake calls: ring at T-10 (firm) and T-5 (harsh) before EACH event — TWO calls only
// (Dais 2026-06-25: "just call me 10 min before and 5 min before, that's it"), so the user actually
// gets up / leaves. Each (event, level) fires once (deduped).
const WAKE_LEVELS = [
  { min: 10, urgency: "firm" },
  { min: 5, urgency: "harsh" },
];

const SUPA = () => ({ url: process.env.SUPABASE_URL, key: process.env.SUPABASE_SERVICE_ROLE_KEY });

// isHelperBlock now lives in lib/wake-filter.js (shared with the importance filter + leave anchor).

async function supaUsers() {
  const { url, key } = SUPA();
  if (!url || !key) return [];
  const base = `${url}/rest/v1/lm_users?${schedulerCohortFilter()}`;
  const cols = "uid,name,phone,paid,calendar_provider,home_address,gmail_account_id,email,telegram_chat_id,call_language";
  const hdr = { apikey: key, Authorization: `Bearer ${key}` };
  // FAIL-SAFE: try WITH wake_policy; if the column is missing (PostgREST 400) fall back to the base
  // columns rather than returning [] — a missing column must NOT silently disable wakes fleet-wide.
  let r = await fetch(`${base}&select=${cols},wake_policy`, { headers: hdr });
  if (!r.ok) r = await fetch(`${base}&select=${cols}`, { headers: hdr }); // wake_policy → undefined → travel-only
  if (!r.ok) return [];
  const users = await r.json().catch(() => []);
  if (!Array.isArray(users) || users.length === 0) return [];
  const ids = users.map(u => u.uid).filter(Boolean).join(",");
  // call_time_zone rides along because it is the ONLY per-user timezone column that exists anywhere
  // in this schema (lm_users has none). The diet organ resolves each tenant's lunch window from it;
  // without it every tenant would be asked on Tokyo's clock, and the organ chooses silence over that.
  const prefsResponse = await fetch(`${url}/rest/v1/lm_panel_preferences?uid=in.(${encodeURIComponent(ids)})&select=uid,call_enabled,notifications_enabled,daily_automation_enabled,call_time_zone`, { headers: hdr });
  if (!prefsResponse.ok) return users.map(u => ({ ...u, call_enabled: false, notifications_enabled: false, daily_automation_enabled: false }));
  const preferenceRows = await prefsResponse.json().catch(() => null);
  if (!Array.isArray(preferenceRows)) return users.map(u => ({ ...u, call_enabled: false, notifications_enabled: false, daily_automation_enabled: false }));
  const byUid = new Map(preferenceRows.map(row => [row.uid, row]));
  return users.map(u => ({ ...RUNTIME_DEFAULTS, ...u, ...(byUid.get(u.uid) || {}) }));
}

// Returns true if this (uid,event_key) was NOT already called — and records it atomically.
// Relies on the unique(uid,event_key) constraint: a duplicate insert 409s → already called.
async function claimWake(uid, eventKey) {
  const { url, key } = SUPA();
  if (!url || !key) return false;
  const r = await fetch(`${url}/rest/v1/lm_wake_log`, {
    method: "POST",
    headers: { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ uid, event_key: eventKey }),
  });
  return r.status === 201; // 201 = inserted (first time); 409 = duplicate (already called)
}

// Release a claim when placeCall failed, so a LATER tick retries while the event is still in its
// window (claim→dial→unclaim-on-failure — mirrors unclaimTravel in lib/travel.js). Without this, a
// dial failure (e.g. Telnyx balance too low) permanently burns the (uid,event,level) slot: the row
// stays in lm_wake_log forever and claimWake 409s on every future tick even after the fix lands.
async function releaseWake(uid, eventKey) {
  const { url, key } = SUPA();
  if (!url || !key) return;
  await fetch(`${url}/rest/v1/lm_wake_log?uid=eq.${encodeURIComponent(uid)}&event_key=eq.${encodeURIComponent(eventKey)}`, {
    method: "DELETE",
    headers: { apikey: key, Authorization: `Bearer ${key}`, Prefer: "return=minimal" },
  }).catch(() => {});
}

// Low-balance alert (issue#10 root cause: pre-event calls silently never fire when the Telnyx
// balance drops below the $0.50 preflight in lib/dial.js). Ping the admin's Telegram so the balance
// gets topped up instead of the gap going unnoticed. isLowBalanceError/shouldAlertLowBalance are pure
// (matches the testCallAllowed(uid, nowMs) pattern in server.js) so the throttle is unit-testable
// without stubbing fetch/Date. Best-effort like dunningNotify in server.js — NEVER throws.
const LOW_BALANCE_ALERT_COOLDOWN_MS = 6 * 60 * 60 * 1000; // at most 1 alert per 6h
let lastLowBalanceAlertMs = 0;

function isLowBalanceError(errorMsg) {
  return /balance too low/i.test(String(errorMsg || ""));
}

function shouldAlertLowBalance(errorMsg, nowMs, lastAlertMs) {
  return isLowBalanceError(errorMsg) && nowMs - lastAlertMs >= LOW_BALANCE_ALERT_COOLDOWN_MS;
}

async function maybeAlertLowBalance(errorMsg, nowMs = Date.now()) {
  if (!shouldAlertLowBalance(errorMsg, nowMs, lastLowBalanceAlertMs)) return;
  lastLowBalanceAlertMs = nowMs;
  const token = process.env.LM_TELEGRAM_BOT_TOKEN;
  const chatId = process.env.LM_ADMIN_TELEGRAM_CHAT_ID;
  if (!token || !chatId) {
    console.error(`[scheduler] LOW BALANCE (no LM_ADMIN_TELEGRAM_CHAT_ID configured): ${errorMsg}`);
    return;
  }
  await sendMessage(token, chatId, `⚠️ Telnyx balance too low — Life Manager wake calls are NOT firing.\n${errorMsg}`)
    .catch((e) => console.error("[scheduler] low-balance alert send failed", e && e.message));
}

// Resolve the call language for a user row: their EXPLICIT choice (lm_users.call_language, set via the
// /lm toggle) wins; otherwise fall back to the phone country. So a US phone can choose Japanese and a
// Japanese phone can choose English (Dais 2026-06-22).
function langForUser(u) {
  const c = u && u.call_language;
  return c === "ja" || c === "en" ? c : langForPhone(u && u.phone);
}

function buildStreamUrl(ev, urgency, lang, name) {
  const base = (process.env.PUBLIC_WSS || "").replace(/\/$/, "");
  const summary = ev.summary || "";
  const dateTime = ev.startIso || "";
  const location = ev.location || "";
  const urg = urgency || "gentle";
  const lg = lang === "ja" ? "ja" : "en";
  const nm = String(name || "").replace(/[\r\n]/g, " ").slice(0, 60); // address the user by name on the call
  const wakeUid = String(ev.wakeUid || "");
  const wakeEventKey = String(ev.wakeEventKey || "");
  const sig = signCtx([summary, dateTime, location, urg, lg, nm, wakeUid, wakeEventKey]);
  const qs = new URLSearchParams({ summary, dateTime, location, urgency: urg, lang: lg, name: nm, wakeUid, wakeEventKey, sig });
  return `${base}/ws?${qs.toString()}`;
}

// LM-30 runs inside the durable 60s wake tick. A non-expired Telegram live location is the sole gate;
// lm_late_notice_log atomically deduplicates one action per calendar event across restarts.
async function lateNoticeUserOnce(u, nowMs, deps = {}) {
  const now = nowMs !== undefined ? nowMs : Date.now();
  const configuredSupa = SUPA();
  const supaUrl = deps.supaUrl !== undefined ? deps.supaUrl : configuredSupa.url;
  const supaKey = deps.supaKey !== undefined ? deps.supaKey : configuredSupa.key;
  if (!u || !u.uid || !supaUrl || !supaKey) return;
  const dbOpts = { supaUrl, supaKey, nowMs: now, fetchImpl: deps.fetchImpl };
  const location = deps.location !== undefined
    ? deps.location
    : await (deps.getLiveLocation || getLiveLocation)(u.uid, now, dbOpts);
  const events = deps.events || await (deps.fetchUpcomingEvents || fetchUpcomingEvents)(u.uid, {
    nowMs: now, horizonH: 6, apiKey: deps.apiKey || process.env.COMPOSIO_API_KEY,
    calendar: deps.calendar, gmailAccountId: u.gmail_account_id,
  });
  return processLocationLateNotice({
    user: u, location, events, nowMs: now,
    mapsKey: deps.mapsKey || process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY,
    telegramToken: deps.telegramToken !== undefined ? deps.telegramToken : process.env.LM_TELEGRAM_BOT_TOKEN,
    noticeOpts: {
      resendKey: process.env.RESEND_API_KEY, userEmail: u.email, userName: u.name,
    },
  }, {
    routeMinutes: deps.routeMinutes || directionsMinutes,
    claimEvent: deps.claimEvent || ((uid, eventKey) => claimLateEvent(uid, eventKey, dbOpts)),
    sendLateNotice: deps.sendLateNotice || sendLateNotice,
    sendMessage: deps.sendMessage || sendMessage,
  });
}

// ── Per-user single-invocation functions (extracted for Inngest fan-out) ─────
// Each function takes a single user row `u` and performs the loop body for THAT user only.
// The existing tick/travelTick/askTickAll still call these in a for-loop so the in-process
// LIFE_RUN_LOOPS path continues to work unchanged.

// MEN-c wiring. The trigger rule needs a shape the calendar does not hand over directly, so the two
// judgements are made here and stated plainly: an event with a place or people is "important", and one
// that runs 90 minutes or longer is "intense". Location stays "unknown" rather than pretending we can
// tell standing still from travelling — "unknown" never suppresses, "moving" would.
const MENTAL_SEEDS = Object.freeze([
  "I am enough exactly as I am",
  "I choose peace over worry",
  "I release what I cannot control",
  "Today I choose to be kind to myself",
]);

// H2/H4: the diet and precepts triggers only ask whether an event is IN PROGRESS, so they need
// starts and ends and nothing else. An event with no end is given the same 1h assumption mentalDeps
// makes — a missing end must not read as a zero-length event that suppresses nothing.
function inProgressEvents(events) {
  return (Array.isArray(events) ? events : []).map((event) => {
    const startMs = Number(event.startMs);
    const endMs = Number.isFinite(event.endMs) ? Number(event.endMs) : startMs + 60 * 60000;
    return { startMs, endMs };
  }).filter((event) => Number.isFinite(event.startMs) && event.endMs > event.startMs);
}

// The kill switch, spelled the way an operator under pressure actually spells it. `LM_DIET_ENABLED=0`
// was the only accepted form, so `=false` and `=off` silently LEFT THE ORGAN ON — the exact moment
// an off switch must not be pedantic is the moment someone is reaching for it.
const ORGAN_OFF = /^(0|false|off|no)$/i;
function dietEnabled() {
  return !ORGAN_OFF.test(String(process.env.LM_DIET_ENABLED || "").trim());
}

// H4 ORG-precepts: same switch, same spellings, same default-ON. Defaulting a gate to OFF is how an
// organ ships and then quietly never runs, which is indistinguishable from not having shipped it.
function preceptsEnabled() {
  return !ORGAN_OFF.test(String(process.env.LM_PRECEPTS_ENABLED || "").trim());
}

function mentalDeps(u, events, deps = {}) {
  const supa = SUPA();
  const shaped = (Array.isArray(events) ? events : []).map((event) => {
    const startMs = Number(event.startMs);
    const endMs = Number.isFinite(event.endMs) ? Number(event.endMs) : startMs + 60 * 60000;
    return {
      startMs,
      endMs,
      important: Boolean(event.location) || Boolean(event.attendees && event.attendees.length),
      intense: endMs - startMs >= 90 * 60000,
    };
  }).filter((event) => Number.isFinite(event.startMs) && event.endMs > event.startMs);

  return {
    telegramToken: deps.telegramToken !== undefined ? deps.telegramToken : process.env.LM_TELEGRAM_BOT_TOKEN,
    seeds: deps.mentalSeeds || MENTAL_SEEDS,
    sleepTargetMs: Number.isFinite(deps.sleepTargetMs)
      ? deps.sleepTargetMs
      : resolveSleepTarget(process.env.LM_MENTAL_SLEEP_TARGET || "23:30", Date.now(), Number(process.env.LM_MENTAL_UTC_OFFSET_HOURS || 9)),
    fetchUpcomingEvents: async () => shaped,
    getLocationState: deps.getLocationState || (async () => "unknown"),
    sendMessage: deps.sendMessage || sendMessage,
    readSendState: deps.readMentalState || (async (uid, nowMs) => readMentalSendState(uid, nowMs, supa)),
    recordSend: deps.recordMentalSend || ((uid, trigger, messageId) => recordMentalSend(uid, trigger, messageId, supa)),
  };
}

// readMentalSendState / recordMentalSend moved to lib/mental-send-log.js (imported above) — H4 ⑤
// makes lm_mental_send_log a SHARED budget, and a budget only one module can reach is not a budget.
// MENTAL's behaviour is byte-for-byte unchanged: it still calls them non-strict, so an unreadable log
// still reads as "nothing sent yet" for this organ. Precepts calls them strict and stays silent
// instead — see lib/mental-send-log.js for why the two callers differ on purpose.

async function wakeUserOnce(u, nowMs, deps = {}) {
  if (u && u.daily_automation_enabled === false) return;
  const now = nowMs !== undefined ? nowMs : Date.now();
  let events;
  try {
    // LM-7: calendar polling is represented once per UTC day/user. The helper checks today's row
    // in Supabase on every tick; no in-memory counter is used, so restarts preserve aggregation.
    await (deps.recordDailyPoll || recordDailyComposioPoll)(u.uid, { nowMs: now });
    // 6h horizon: a long-travel event AND its [Travel] block must both be visible at the moment we
    // wake 15 min before DEPARTURE, which can be hours before the event itself.
    // 12c: fetch once with a lookback wide enough for the MENTAL trough (an intense block that
    // already ENDED within TROUGH_AFTER_MS). Every non-MENTAL consumer below stays on the
    // strict-future slice, so wake/late behavior is unchanged.
    events = await (deps.fetchUpcomingEvents || fetchUpcomingEvents)(u.uid, {
      nowMs: now, horizonH: 6, lookbackMs: MENTAL_LOOKBACK_MS,
      apiKey: deps.apiKey || process.env.COMPOSIO_API_KEY,
      calendar: deps.calendar, gmailAccountId: u.gmail_account_id,
    });
  } catch {
    return;
  }
  const futureEvents = (events || []).filter((e) => Number(e.startMs) >= now);
  try {
    if (u.notifications_enabled !== false) {
      const late = await (deps.lateNotice || lateNoticeUserOnce)(u, now, { events: futureEvents });
      // The Telegram leg is otherwise unauditable: name the message that was actually delivered.
      if (late && late.telegramMessageId !== undefined) {
        console.log(`[late] uid=${String(u.uid).slice(0, 12)} decision=${late.decision} sent=${!!late.sent} tg_message_id=${late.telegramMessageId}`);
      }
    }
  } catch (e) { console.error(`[late] uid=${String(u && u.uid || "?").slice(0, 12)} err ${e && e.message}`); }
  // MEN-c: the MENTAL organ rides the same 60s tick. It stays silent unless the day itself says now.
  try {
    const mental = await (deps.mental || mentalUserOnce)(u, now, mentalDeps(u, events, deps));
    if (mental && mental.delivered) {
      console.log(`[mental] uid=${String(u.uid).slice(0, 12)} trigger=${mental.trigger} tg_message_id=${mental.telegramMessageId}`);
    }
  } catch (e) { console.error(`[mental] uid=${String(u && u.uid || "?").slice(0, 12)} err ${e && e.message}`); }
  // #69 importance filter: only wake for events the user must TRAVEL to (per their wake_policy),
  // and anchor the 10/5 levels to DEPARTURE (leave time), not the event start — so a 30-min-travel
  // event is called before they must leave. resolveDeparture uses the [Travel] block if present, else
  // computes the leave time inline (never-late even before the 30-min travel loop inserts the block).
  const mapsKey = deps.mapsKey || process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY;
  if (u.call_enabled !== false) {
    for (const ev of futureEvents.filter((e) => shouldWake(e, u.home_address, u.wake_policy))) {
      const depMs = await resolveDeparture(ev, futureEvents, {
        home: u.home_address, mapsKey, nowMs: now, bufferMin: 5,
        directionsFn: deps.directionsMinutes || directionsMinutes,
      });
      const mins = (depMs - now) / 60000;
      for (const lvl of WAKE_LEVELS) {
        // 60s tick → a ~2-min catch window per level; levels are 5 min apart so they never overlap.
        if (mins > lvl.min + 0.5 || mins <= lvl.min - 1.5) continue;
        const eventKey = `${u.uid}|${ev.startIso}|${lvl.min}`;
        const fresh = await (deps.claimWake || claimWake)(u.uid, eventKey);
        if (!fresh) continue; // already called for this (event, level)
        const streamUrl = buildStreamUrl({ ...ev, wakeUid: u.uid, wakeEventKey: eventKey }, lvl.urgency, langForUser(u), u.name);
        let res;
        try {
          res = await (deps.placeCall || placeCall)({ to: u.phone, streamUrl });
        } catch (e) {
          res = { ok: false, error: String((e && e.message) || e) };
        }
        if (res.ok) {
          console.log(`[scheduler] WAKE T-${lvl.min} uid=${u.uid.slice(0, 12)} "${ev.summary}" ccid=${res.ccid}`);
        } else {
          console.error(`[scheduler] dial failed T-${lvl.min} uid=${u.uid.slice(0, 12)}: ${res.error}`);
          // Don't burn the retry: release the claim so the next 60s tick tries again while the event
          // is still in its window (the claim-before-dial order stays intact as the dedup guard).
          await (deps.releaseWake || releaseWake)(u.uid, eventKey);
          await (deps.alertLowBalance || maybeAlertLowBalance)(res.error);
        }
      }
    }
  }
  // 11a/11b: the PHYSICAL organ rides the same 60s tick. careUserOnce holds a durable daily claim
  // in lm_care_scan_log, so despite the 60s cadence there is ONE real scan per user per UTC day —
  // every other tick costs a single row lookup. Isolated exactly like MENTAL above: a care failure
  // must never break wake calls. It runs LAST — after the wake evaluation — because the wake dial
  // has a ~2-min catch window and a slow Places/Supabase chain must never delay it; care has no
  // deadline (any tick today may claim the scan). Still runs for call-disabled users: skipping the
  // wake loop must not skip the PHYSICAL organ. With LM_BOOKING_ENABLED absent this path detects and
  // records candidates only; with the gate ON, careUserOnce also runs the 11c booking leg and the 11d
  // 事後報告 (steel session, Telegram, calendar) inside this same call. The executor holds its own
  // deadline below USER_TICK_TIMEOUT_MS, so a tick abandoned here can never leave the single steel
  // session held open behind it.
  try {
    const care = await (deps.care || careUserOnce)(u, now, { apiKey: deps.apiKey, calendar: deps.calendar });
    if (care && care.status && care.status !== "already_scanned") {
      console.log(`[care] uid=${String(u.uid).slice(0, 12)} status=${care.status}`
        + `${care.category ? ` category=${care.category}` : ""}`
        + `${care.selectedProviderId ? ` selected=${care.selectedProviderId}` : ""}`
        + `${care.chainError ? ` chain_err=${care.chainError}` : ""}`);
    }
  } catch (e) { console.error(`[care] uid=${String(u && u.uid || "?").slice(0, 12)} err ${e && e.message}`); }
  // H2 ORG-diet: the diet organ rides the same 60s tick, LAST — after the time-critical wake dial and
  // after care, because a Places lookup must never sit in front of a call. Both legs hold their own
  // durable claim in lm_diet_log (UNIQUE (uid, day, kind)), so the 120-minute question window and the
  // 30-minute nudge window each produce at most one message however many ticks pass through them.
  //
  // The gate defaults ON (spec H2), and `notifications_enabled` is honoured exactly as the late/mental
  // siblings honour it — the diet organ is nothing but unsolicited messages, so the one switch a user
  // has for "stop messaging me" must cover it. The two legs get SEPARATE try/catch blocks: they share
  // a table but not a fate, and a Places outage in the nudge must not cost the day its question.
  if (dietEnabled() && u.notifications_enabled !== false) {
    let nudgeSentThisTick = false;
    try {
      // getLocationState is passed to BOTH diet legs exactly as mentalDeps passes it to MENTAL: one
      // injected provider, one behaviour. Nothing supplies it in production today, so both organs
      // read the constant "unknown" — the gate is wired, not live, and both files say so.
      const nudge = await (deps.dietNudge || dietNudgeOnce)(u, now, {
        calendarEvents: events, getLocationState: deps.getLocationState,
      });
      if (nudge && nudge.status === "nudged") {
        nudgeSentThisTick = true;
        console.log(`[diet-nudge] uid=${String(u.uid).slice(0, 12)} samples=${nudge.sampleCount}`
          + ` fast=${nudge.fastCount} venue=${nudge.venue ? "yes" : "none"} tg_message_id=${nudge.telegramMessageId}`);
      }
    } catch (e) { console.error(`[diet-nudge] uid=${String(u && u.uid || "?").slice(0, 12)} err ${e && e.message}`); }
    // The two windows overlap (nudge 11:15-11:45, question 11:30-13:30), so on some ticks BOTH legs
    // fire and the user gets two unsolicited messages zero seconds apart — the sermon the thresholds
    // exist to prevent, delivered in one breath. The nudge keeps the tick because it is the
    // time-critical one (it must land before lunch is decided); the question waits for the next tick,
    // which costs 60 seconds out of its own 120-minute window, and only on a day a nudge went out.
    if (!nudgeSentThisTick) {
      try {
        // NOT futureEvents: "is the user mid-meeting right now" is a question only the event that has
        // ALREADY started can answer, and futureEvents drops exactly those. The MENTAL lookback the
        // fetch above already carries is what makes the in-progress event visible here.
        const diet = await (deps.diet || dietUserOnce)(u, now, {
          events: inProgressEvents(events), getLocationState: deps.getLocationState,
        });
        if (diet && (diet.status === "asked" || diet.status === "send_failed")) {
          console.log(`[diet] uid=${String(u.uid).slice(0, 12)} status=${diet.status} day=${diet.day}`);
        }
      } catch (e) { console.error(`[diet] uid=${String(u && u.uid || "?").slice(0, 12)} err ${e && e.message}`); }
    }
  }
  // H4 ORG-precepts: the bedtime organ rides the same 60s tick, after DIET. Both of its legs hold a
  // durable claim in lm_precepts_log (UNIQUE (uid, day, kind)), so the 30-minute bedtime window
  // produces at most one message however many ticks pass through it, and both legs read and write
  // MENTAL's lm_mental_send_log so the evening budget is shared rather than doubled (H4 ⑤).
  //
  // The gate defaults ON (spec H4), `notifications_enabled` is honoured exactly as every other
  // unsolicited-message organ honours it, and the two legs get SEPARATE try/catch blocks: they share
  // a table but not a fate, and a calendar-history outage in the mirror must not cost the night its
  // question.
  if (preceptsEnabled() && u.notifications_enabled !== false) {
    let mirrorSentThisTick = false;
    try {
      // The mirror is evaluated FIRST because it is the rarer and more time-boxed of the two (one
      // Sunday, one window). Its own send records to lm_mental_send_log, which starts the 2h spacing
      // that suppresses the question on every later tick — but not on THIS one, because both legs
      // read their budget before either wrote. mirrorSentThisTick closes that gap: two unsolicited
      // messages zero seconds apart is the sermon these thresholds exist to prevent.
      const mirror = await (deps.preceptsMirror || preceptsMirrorOnce)(u, now, {
        events: inProgressEvents(events), getLocationState: deps.getLocationState,
        apiKey: deps.apiKey, calendar: deps.calendar, gmailAccountId: u.gmail_account_id,
      });
      if (mirror && mirror.status === "mirrored") {
        mirrorSentThisTick = true;
        console.log(`[precepts-mirror] uid=${String(u.uid).slice(0, 12)} day=${mirror.day}`
          + ` answers=${mirror.answerCount} pattern=${mirror.pattern} tg_message_id=${mirror.telegramMessageId}`);
      }
    } catch (e) { console.error(`[precepts-mirror] uid=${String(u && u.uid || "?").slice(0, 12)} err ${e && e.message}`); }
    if (!mirrorSentThisTick) {
      try {
        // NOT futureEvents: "is the user mid-something right now" is a question only the event that
        // has ALREADY started can answer, and futureEvents drops exactly those.
        const precepts = await (deps.precepts || preceptsUserOnce)(u, now, {
          events: inProgressEvents(events), getLocationState: deps.getLocationState,
        });
        if (precepts && (precepts.status === "asked" || precepts.status === "send_failed")) {
          console.log(`[precepts] uid=${String(u.uid).slice(0, 12)} status=${precepts.status} day=${precepts.day}`);
        }
      } catch (e) { console.error(`[precepts] uid=${String(u && u.uid || "?").slice(0, 12)} err ${e && e.message}`); }
    }
  }
}

// forEachUserSafe: process each tenant in ISOLATION (HARD-4). A throw/rejection while handling one user is
// caught + logged per-uid so it NEVER prevents the remaining tenants from being processed this tick. This
// mirrors the production Inngest model (each user is a separate function run); it hardens the in-process
// (LIFE_RUN_LOOPS) path to the same one-tenant-failure-can't-break-others guarantee.
const USER_TICK_TIMEOUT_MS = Number(process.env.LIFE_USER_TICK_TIMEOUT_MS) || 90000;
async function forEachUserSafe(users, label, fn, timeoutMs = USER_TICK_TIMEOUT_MS) {
  for (const u of (users || [])) {
    const uid = (u && u.uid ? String(u.uid) : "?").slice(0, 12);
    try {
      // FIND-002: a per-user TIMEOUT so a HANG (not just a throw) in one tenant's upstream (dial/Gemini with
      // no AbortController) cannot stall the others. The abandoned op may still finish — idempotent via C-H1.
      let timer;
      const guard = new Promise((_, rej) => { timer = setTimeout(() => rej(new Error(`tenant timeout ${timeoutMs}ms`)), timeoutMs); });
      try { await Promise.race([Promise.resolve(fn(u)), guard]); }
      finally { clearTimeout(timer); }
    } catch (e) {
      console.error(`[${label}] uid=${uid} err ${e && e.message}`);
    }
  }
}

// tick/travelTick/askTickAll accept optional injected deps (listUsers + the per-user fn) so a test can drive
// the REAL public loop with a throwing tenant and prove it routes through forEachUserSafe (FIND-001) — a
// future revert to a raw for-loop would then fail the test, not pass silently.
async function tick(deps = {}) {
  const listUsers = deps.listUsers || supaUsers;
  const wake = deps.wake || wakeUserOnce;
  const users = await listUsers();
  const now = deps.now !== undefined ? deps.now : Date.now();
  await forEachUserSafe(users.filter(u => u.daily_automation_enabled !== false && u.call_enabled !== false), "scheduler", (u) => wake(u, now));
}

function startScheduler() {
  if (!process.env.PUBLIC_WSS) {
    console.warn("[scheduler] PUBLIC_WSS not set — calls would have no media bridge URL; loop still runs but won't dial");
  }
  console.log(`[scheduler] started — tick every ${TICK_MS / 1000}s, escalating wakes at T-${WAKE_LEVELS.map((l) => l.min).join("/")}min`);
  let timer;
  const run = async () => {
    try { await tick(); } catch (e) { console.error("[scheduler] tick err", e.message); }
    const intervalMs = await schedulerPollInterval().catch(() => TICK_MS);
    timer = setTimeout(run, intervalMs);
  };
  run();
  return { close: () => clearTimeout(timer) };
}

// ── Travel auto-fill (every 30 min) — keep today+7d filled with [Travel] blocks ─────────────────
const TRAVEL_TICK_MS = 30 * 60 * 1000;

async function travelUserOnce(u, deps = {}) {
  if (u && u.daily_automation_enabled === false) return;
  const apiKey = deps.apiKey || process.env.COMPOSIO_API_KEY;
  const mapsKey = deps.mapsKey || process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY;
  const geminiKey = deps.geminiKey || process.env.GEMINI_API_KEY; // agentic resolve of room-name / unroutable locations
  if (!apiKey || !mapsKey) return;
  const configuredSupa = SUPA();
  const supaUrl = deps.supaUrl !== undefined ? deps.supaUrl : configuredSupa.url;
  const supaKey = deps.supaKey !== undefined ? deps.supaKey : configuredSupa.key;
  try {
    const r = await (deps.fillTravel || fillTravel)(u.uid, {
      apiKey, mapsKey, geminiKey, home: u.home_address,
      nowMs: deps.nowMs === undefined ? Date.now() : deps.nowMs,
      calendar: deps.calendar, supaUrl, supaKey,
      _directionsMinutes: deps.directionsMinutes,
      gmailAccountId: u.gmail_account_id,
    });
    if (r.inserted) console.log(`[travel] uid=${u.uid.slice(0, 12)} inserted=${r.inserted} checked=${r.checked}`);
    const telegramToken = deps.telegramToken !== undefined ? deps.telegramToken : process.env.LM_TELEGRAM_BOT_TOKEN;
    if (u.notifications_enabled !== false && telegramToken && u.telegram_chat_id) {
      for (const report of r.outboundReports || []) {
        try {
          await (deps.sendMessage || sendMessage)(telegramToken, u.telegram_chat_id,
            formatTravelAutofillMessage(report, deps.nowMs === undefined ? Date.now() : deps.nowMs));
        } catch (error) {
          console.error(`[travel] uid=${u.uid.slice(0, 12)} report send failed: ${error && error.message}`);
        }
      }
    }
    return r;
  } catch (e) {
    console.error(`[travel] uid=${u.uid.slice(0, 12)} err ${e.message}`);
  }
}

async function travelTick(deps = {}) {
  const apiKey = process.env.COMPOSIO_API_KEY;
  const mapsKey = process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY;
  if (!apiKey || !mapsKey) return;
  const listUsers = deps.listUsers || supaUsers;
  const travel = deps.travel || travelUserOnce;
  const users = await listUsers();
  await forEachUserSafe(users.filter(u => u.daily_automation_enabled !== false), "travel", travel);
}
function startTravelLoop() {
  console.log(`[travel] started — every ${TRAVEL_TICK_MS / 60000}min, horizon 7d`);
  const run = () => travelTick().catch((e) => console.error("[travel] tick err", e.message));
  run();
  return setInterval(run, TRAVEL_TICK_MS);
}

// ── Ask/reply loop (every 20 min) — ask the user about events missing a location (Telegram or our-domain
// email via Resend); replies arrive on webhooks (/telegram, /inbound-email), not polled here ──
const ASK_TICK_MS = 20 * 60 * 1000;

async function askUserOnce(u) {
  if (u && (u.daily_automation_enabled === false || u.notifications_enabled === false)) return;
  const composioKey = process.env.COMPOSIO_API_KEY;
  const resendKey = process.env.RESEND_API_KEY;                            // our-domain email send
  const mapsKey = process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY; // Places grounding
  const geminiKey = process.env.GEMINI_API_KEY;                            // agentic resolve/read
  const telegramToken = process.env.LM_TELEGRAM_BOT_TOKEN;                 // Telegram ask channel
  const { url: supaUrl, key: supaKey } = SUPA();
  if (!composioKey || !supaUrl || !geminiKey) return;
  // A user is reachable for asks via Telegram OR their email (captured at sign-in) — need at least one.
  if (!u.telegram_chat_id && !u.email) return;
  try {
    const r = await askTick(u.uid, {
      composioKey, userEmail: u.email, resendKey,
      supaUrl, supaKey, mapsKey, geminiKey, home: u.home_address,
      telegramChatId: u.telegram_chat_id, telegramToken,
      gmailAccountId: u.gmail_account_id,
      unipileToken: process.env.UNIPILE_TOKEN,
      unipileDsn: process.env.UNIPILE_DSN,
    });
    if (r.autofilled || r.asked || r.resolved)
      console.log(`[ask] uid=${u.uid.slice(0, 12)} autofilled=${r.autofilled} asked=${r.asked} resolved=${r.resolved} via=${u.telegram_chat_id ? "tg" : "email"}`);
  } catch (e) { console.error(`[ask] uid=${u.uid.slice(0, 12)} err ${e.message}`); }
}

async function askTickAll(deps = {}) {
  const composioKey = process.env.COMPOSIO_API_KEY;
  const { url: supaUrl } = SUPA();
  const geminiKey = process.env.GEMINI_API_KEY;
  if (!composioKey || !supaUrl || !geminiKey) return;
  const listUsers = deps.listUsers || supaUsers;
  const ask = deps.ask || askUserOnce;
  const users = await listUsers();
  await forEachUserSafe(users.filter(u => u.daily_automation_enabled !== false && u.notifications_enabled !== false), "ask", ask);
}
function startAskLoop() {
  console.log(`[ask] started — every ${ASK_TICK_MS / 60000}min`);
  const run = () => askTickAll().catch((e) => console.error("[ask] tick err", e.message));
  run();
  return setInterval(run, ASK_TICK_MS);
}

// ── Interactive Telegram onboarding nudge (every 2 min) — guide linked users to their next step ────
const ONBOARD_TICK_MS = 2 * 60 * 1000;
async function onboardTick() {
  const token = process.env.LM_TELEGRAM_BOT_TOKEN;
  const base = process.env.PUBLIC_BASE || "https://aniccaai.com";
  const { url: supaUrl, key: supaKey } = SUPA();
  if (!token || !supaUrl) return;
  const sent = await onboardNudgeAll({
    token, base, supaUrl, supaKey,
    composioKey: process.env.COMPOSIO_API_KEY,
    geminiKey: process.env.GEMINI_API_KEY,
    uidSecret: process.env.LM_UID_SECRET,
    gmailBase: process.env.LIFE_CALL_PUBLIC_BASE || process.env.PUBLIC_WSS || base,
    gmailConfigured: Boolean(process.env.LM_UID_SECRET && process.env.UNIPILE_DSN &&
      process.env.UNIPILE_TOKEN && process.env.UNIPILE_NOTIFY_SECRET),
  });
  if (sent) console.log(`[onboard] nudged ${sent} Telegram user(s) to their next step`);
}
function startOnboardLoop() {
  console.log(`[onboard] started — every ${ONBOARD_TICK_MS / 60000}min (interactive Telegram guidance)`);
  const run = () => onboardTick().catch((e) => console.error("[onboard] tick err", e.message));
  run();
  return setInterval(run, ONBOARD_TICK_MS);
}

// ── Context-gate feature discovery (weekly) ────────────────────────────────
// The per-user last_discovery_at gate is durable, so process restarts do not
// increase frequency. Each run re-reads live-location freshness before send.
async function discoveryTick(deps = {}) {
  const { url: supaUrl, key: supaKey } = SUPA();
  const token = process.env.LM_TELEGRAM_BOT_TOKEN;
  if (!token || !supaUrl || !supaKey) return;
  const dbOpts = { supaUrl, supaKey, fetchImpl: deps.fetchImpl };
  const listUsers = deps.listUsers || (() => listDiscoveryUsers(dbOpts));
  const discover = deps.discover || ((user, nowMs) => runDiscoveryForUser(user, nowMs, {
    ...dbOpts, token,
  }));
  const users = await listUsers();
  const now = deps.now !== undefined ? deps.now : Date.now();
  await forEachUserSafe(users.filter(user => user.notifications_enabled !== false), "discovery", (user) => discover(user, now));
}

function startDiscoveryLoop() {
  console.log("[discovery] started — weekly, one locked gate per eligible Telegram user");
  const run = () => discoveryTick().catch((error) =>
    console.error("[discovery] tick err", error && error.message));
  run();
  return setInterval(run, DISCOVERY_WEEK_MS);
}

// listPaidUsers: public alias for supaUsers — used by Inngest sweep functions.
const listPaidUsers = supaUsers;

// getUserByUid: re-fetches a single user row by uid for Inngest per-user functions.
// Inngest sweepers fan-out only { uid } (PII-safe); the per-user handler calls this
// to get the full row (phone, home_address, etc.) before invoking the scheduler fn.
// Uses the same column set as supaUsers to keep behaviour identical.
async function getUserByUid(uid) {
  const { url, key } = SUPA();
  if (!url || !key || !uid) return null;
  const cols = "uid,name,phone,paid,calendar_provider,home_address,gmail_account_id,email,telegram_chat_id,call_language";
  const base = `${url}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}&${schedulerCohortFilter()}`;
  const hdr = { apikey: key, Authorization: `Bearer ${key}` };
  let r = await fetch(`${base}&select=${cols},wake_policy`, { headers: hdr });
  if (!r.ok) r = await fetch(`${base}&select=${cols}`, { headers: hdr });
  if (!r.ok) return null;
  const rows = await r.json().catch(() => []);
  const user = Array.isArray(rows) && rows[0] ? rows[0] : null;
  if (!user) return null;
  const prefs = await readRuntimePreferences(uid, { supaUrl: url, supaKey: key, fetchImpl: fetch });
  return prefs ? { ...user, ...prefs } : { ...user, call_enabled: false, notifications_enabled: false, daily_automation_enabled: false };
}

module.exports = {
  startScheduler, startTravelLoop, startAskLoop, startOnboardLoop, startDiscoveryLoop,
  tick, travelTick, askTickAll, onboardTick, discoveryTick,
  // per-user single-invocation functions (for Inngest fan-out + testing)
  wakeUserOnce, travelUserOnce, askUserOnce,
  lateNoticeUserOnce,
  // per-tenant isolation wrapper (HARD-4): one tenant's failure can't break the others' tick
  forEachUserSafe,
  // wake escalation levels (Dais: T-10 firm + T-5 harsh only) — exported so a revert is test-caught
  WAKE_LEVELS,
  // paid-user listing (for Inngest sweep fan-out)
  listPaidUsers,
  // per-uid re-fetch for Inngest per-user functions (PII: sweepers send only uid)
  getUserByUid,
  // utilities used by server.js and tests
  isHelperBlock, buildStreamUrl, langForPhone, langForUser,
  // wake claim ledger (C-H1 dedup) — claim before dial, release on dial failure so a retry can fire
  claimWake, releaseWake,
  // low-balance admin alert (issue#10): pure decision fns + the side-effecting sender
  isLowBalanceError, shouldAlertLowBalance, maybeAlertLowBalance, LOW_BALANCE_ALERT_COOLDOWN_MS,
};
