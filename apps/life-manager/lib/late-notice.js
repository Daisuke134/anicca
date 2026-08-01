// LM-30 location-gated late notice decision core + Supabase helpers.
// A fresh Telegram live location is the only gate. The scheduler observes and reports; it never asks.
"use strict";

const { isHelperBlock } = require("./wake-filter.js");
const { shouldMarkAnswered } = require("./answered.js");
const { hangupCall } = require("./dial.js");

const NO_DESTINATION_MESSAGE = "⚠️ 先方の連絡先が見つからず、遅刻連絡は送れていません";
const MAIL_FAILURE_MESSAGE = "⚠️ 遅刻連絡メールを送信できませんでした";

function evaluateLateArrival({ nowMs, event, travelMinutes, location }) {
  if (!location) return { decision: "location_missing" };
  const expiresMs = Date.parse(location.expires_at || location.expiresAt || "");
  if (!Number.isFinite(expiresMs) || expiresMs <= nowMs) return { decision: "location_expired" };
  if (!event || !Number.isFinite(event.startMs)) return { decision: "no_event" };
  if (!Number.isFinite(travelMinutes) || travelMinutes < 0) return { decision: "route_unavailable" };
  const arrivalMs = nowMs + travelMinutes * 60_000;
  const lateMinutes = Math.max(0, Math.ceil((arrivalMs - event.startMs) / 60_000));
  return { decision: arrivalMs > event.startMs ? "late" : "on_time", arrivalMs, lateMinutes };
}

function offsetMinutes(iso) {
  if (/Z$/i.test(String(iso || ""))) return 0;
  const match = /([+-])(\d{2}):(\d{2})$/.exec(String(iso || ""));
  if (!match) return 0;
  const minutes = Number(match[2]) * 60 + Number(match[3]);
  return match[1] === "-" ? -minutes : minutes;
}

function clockAt(ms, referenceIso) {
  const shifted = new Date(ms + offsetMinutes(referenceIso) * 60_000);
  return `${String(shifted.getUTCHours()).padStart(2, "0")}:${String(shifted.getUTCMinutes()).padStart(2, "0")}`;
}

function roundedEtaMinutes(minutes) {
  return Math.max(5, Math.ceil(minutes / 5) * 5);
}

function formatLateSuccessMessage(event, arrivalMs, lateMinutes) {
  const eta = roundedEtaMinutes(lateMinutes);
  return `📨 現在地から見て${clockAt(event.startMs, event.startIso)}に間に合わないため、先方に「${eta}分ほど遅れます」とメールを送っておきました。次の電車なら${clockAt(arrivalMs, event.startIso)}着です。`;
}

function externalAttendees(event) {
  return (event && Array.isArray(event.attendees) ? event.attendees : [])
    .filter((attendee) => attendee && attendee.email && !attendee.self && !attendee.organizer)
    .map((attendee) => attendee.email);
}

function locationOrigin(location) {
  return `${Number(location.latitude)},${Number(location.longitude)}`;
}

function eventKey(event) {
  return String(event.id || `${event.startIso || event.startMs}|${event.summary || "event"}`);
}

async function processLocationLateNotice(input, deps) {
  const nowMs = input.nowMs === undefined ? Date.now() : input.nowMs;
  const candidates = (input.events || []).filter((candidate) => candidate && !isHelperBlock(candidate.summary) &&
    candidate.location && Number.isFinite(candidate.startMs));
  const gate = evaluateLateArrival({ nowMs, event: candidates[0] || null, travelMinutes: null, location: input.location });
  if (["location_missing", "location_expired", "no_event"].includes(gate.decision)) return gate;

  // Keep the id Telegram hands back: without it the journey's Telegram leg cannot be audited later.
  let telegramMessageId;
  const notifyTelegram = async (text) => {
    if (!input.telegramToken || !input.user.telegram_chat_id) return;
    const sent = await deps.sendMessage(input.telegramToken, input.user.telegram_chat_id, text);
    const id = sent && sent.result && sent.result.message_id;
    if (id !== undefined && id !== null) telegramMessageId = id;
  };
  const withTelegramId = (result) => (telegramMessageId === undefined ? result : { ...result, telegramMessageId });

  // A meeting we already acted on must not hide the rest of the day. Seen in production 2026-07-25:
  // an all-day located event was claimed in the morning and ran until evening, so every later event
  // was unreachable — the old code stopped at the first located event and gave up on a failed claim.
  let deduplicated = false;
  for (const event of candidates) {
    const travelMinutes = await deps.routeMinutes(
      locationOrigin(input.location), event.location, input.mapsKey, event.startMs, nowMs,
    );
    const assessment = evaluateLateArrival({ nowMs, event, travelMinutes, location: input.location });
    if (assessment.decision !== "late") return assessment;

    const fresh = await deps.claimEvent(input.user.uid, eventKey(event));
    if (!fresh) { deduplicated = true; continue; }

    const attendees = externalAttendees(event);
    if (!attendees.length) {
      await notifyTelegram(NO_DESTINATION_MESSAGE);
      return withTelegramId({ ...assessment, notified: true, sent: false, reason: "no_destination" });
    }

    const etaMinutes = roundedEtaMinutes(assessment.lateMinutes);
    let result;
    try {
      result = await deps.sendLateNotice(input.user.uid, event, {
        ...(input.noticeOpts || {}), etaMinutes,
        userEmail: input.user.email, userName: input.user.name,
      });
    } catch (error) {
      result = { sent: false, reason: "send_failed", error: String(error && error.message || error) };
    }
    if (!result || !result.sent) {
      const noDestination = result && result.reason === "no_destination";
      await notifyTelegram(noDestination ? NO_DESTINATION_MESSAGE : MAIL_FAILURE_MESSAGE);
      return withTelegramId({ ...assessment, notified: true, sent: false, reason: noDestination ? "no_destination" : "send_failed" });
    }
    await notifyTelegram(formatLateSuccessMessage(event, assessment.arrivalMs, assessment.lateMinutes));
    return withTelegramId({ ...assessment, notified: true, sent: true, result });
  }
  return deduplicated ? { decision: "late", deduped: true } : gate;
}

function supaHeaders(key, prefer) {
  return {
    apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json",
    ...(prefer ? { Prefer: prefer } : {}),
  };
}

async function upsertLiveLocation(uid, location, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey || !uid || !location ||
      !Number.isFinite(location.latitude) || !Number.isFinite(location.longitude) ||
      !Number.isFinite(location.observedAtMs) || !Number.isFinite(location.expiresAtMs) ||
      location.expiresAtMs <= location.observedAtMs) return false;
  const response = await f(`${opts.supaUrl}/rest/v1/lm_user_locations?on_conflict=uid`, {
    method: "POST",
    headers: supaHeaders(opts.supaKey, "resolution=merge-duplicates,return=minimal"),
    body: JSON.stringify({
      uid,
      latitude: location.latitude,
      longitude: location.longitude,
      telegram_message_id: String(location.messageId || ""),
      source: "telegram_live_location",
      observed_at: new Date(location.observedAtMs).toISOString(),
      expires_at: new Date(location.expiresAtMs).toISOString(),
    }),
  }).catch(() => null);
  return Boolean(response && response.ok);
}

async function getLiveLocation(uid, nowMs = Date.now(), opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey || !uid) return null;
  const url = `${opts.supaUrl}/rest/v1/lm_user_locations?uid=eq.${encodeURIComponent(uid)}&select=uid,latitude,longitude,observed_at,expires_at&limit=1`;
  const response = await f(url, { headers: supaHeaders(opts.supaKey) }).catch(() => null);
  if (!response || !response.ok) return null;
  const rows = await response.json().catch(() => []);
  const row = Array.isArray(rows) && rows[0] ? rows[0] : null;
  return row && Date.parse(row.expires_at) > nowMs ? row : null;
}

// /stop (spec §12.1 row 4): the user's manual disconnect. The uid filter is the tenant boundary — an
// unfiltered DELETE would wipe every user's fix, so the guard refuses to run without one. The Prefer
// header reads back what was removed: the caller reports the true count, and a request we could not
// complete returns null (unknown), never a comforting zero.
async function deleteLiveLocation(uid, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey || !uid) return null;
  const url = `${opts.supaUrl}/rest/v1/lm_user_locations?uid=eq.${encodeURIComponent(uid)}`;
  const response = await f(url, {
    method: "DELETE", headers: supaHeaders(opts.supaKey, "return=representation"),
  }).catch(() => null);
  if (!response || !response.ok) return null;
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) return null;
  return { deleted: rows.length };
}

async function claimLateEvent(uid, key, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey || !uid || !key) return false;
  const response = await f(`${opts.supaUrl}/rest/v1/lm_late_notice_log`, {
    method: "POST", headers: supaHeaders(opts.supaKey, "return=minimal"),
    body: JSON.stringify({ uid, event_key: key }),
  }).catch(() => null);
  return Boolean(response && response.status === 201);
}

// spec §1.3: markAnswered used to answer `false` for BOTH "the PATCH matched zero rows" and "the
// request never landed", and its one caller threw the value away. That is how a rotated Telnyx
// signing key could silence every wake call forever while looking identical to a user who did not
// pick up. Every wake-log write now reports which of the three it was:
//
//   { ok: true,  matched: n>0 }  the write landed and changed n rows
//   { ok: true,  matched: 0   }  the write landed and correctly matched nothing (no such row / latched)
//   { ok: false, matched: 0, error } we never got a successful write — a recording failure
//
// A caller that ignores `error` is ignoring an outage, so call sites log the two apart.
async function patchWakeLog(uid, key, { filter = "", body, ...opts }) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey || !uid || !key) return { ok: false, matched: 0, error: "missing_args" };
  const url = `${opts.supaUrl}/rest/v1/lm_wake_log?uid=eq.${encodeURIComponent(uid)}` +
    `&event_key=eq.${encodeURIComponent(key)}${filter}&select=event_key`;
  const response = await f(url, {
    method: "PATCH", headers: supaHeaders(opts.supaKey, "return=representation"),
    body: JSON.stringify(body),
  }).catch((e) => ({ __threw: (e && e.message) || "fetch failed" }));
  if (response && response.__threw) return { ok: false, matched: 0, error: response.__threw };
  if (!response || !response.ok) return { ok: false, matched: 0, error: `http_${(response && response.status) || "unknown"}` };
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) return { ok: false, matched: 0, error: "unreadable_response" };
  return { ok: true, matched: rows.length };
}

// Wake-call answer telemetry remains useful to the authenticated Telnyx webhook even though it no
// longer unlocks or triggers a late notice. No new T-0 rows are created by this helper.
// The answered_at=is.null filter is a latch, not a lookup: the FIRST human proof wins and later
// events must not rewrite the moment the user picked up. That is why amd_result is a separate write
// below rather than an extra field here — fusing them would force this latch onto a column whose
// rule is the opposite (last observation wins, always recorded).
async function markAnswered(uid, key, opts = {}) {
  return patchWakeLog(uid, key, {
    ...opts,
    filter: "&answered_at=is.null",
    body: { answered_at: new Date(opts.nowMs || Date.now()).toISOString() },
  });
}

// spec §3 row 2: persist what AMD actually said, on EVERY detection. Unfiltered by answered_at on
// purpose (see above), and the value is stored verbatim — folding not_sure into machine, or dropping
// it, would put it straight back into the NULL bucket that means "we never heard anything".
async function recordAmdResult(uid, key, opts = {}) {
  const result = typeof opts.result === "string" ? opts.result.trim() : "";
  if (!result) return { ok: false, matched: 0, error: "missing_result" };
  return patchWakeLog(uid, key, { ...opts, body: { amd_result: result } });
}

// The whole of what a call.machine.detection.ended means for the wake row, in one testable place:
// record the raw result always, latch answered_at only for a human, and hang up on anything AMD
// says is not a human. server.js owns the transport (signature, decode, HTTP reply); this owns the
// decision, so the outcomes are provable without booting the server or reaching for global fetch.
//
// spec §3 row 2b / §5.2.1 — why the hangup lives here and why it is second:
//   * Measured, this service never hung up at all: `hangup_source` was `callee` on all 43 correlated
//     events, so every voicemail ran to the carrier's 120s recording limit at ~$0.05 of Gemini Live.
//     17 machines against 3 humans, and four straight days of nothing but voicemail.
//   * `not_sure` hangs up too. Telnyx's docs recommend treating it as human; the measured ratio says
//     otherwise, and the asymmetry settles it — being wrong here costs one missed nudge, being wrong
//     the other way costs two minutes of paid speech into a recording nobody plays back.
//   * A result we could not read at all (empty/missing) hangs up on NOBODY. That is not an AMD
//     verdict, it is a payload we failed to parse, and hanging up on it would turn one Telnyx schema
//     change into "no wake call ever completes again" — the silent-total-failure class of §1.3.
//   * The record is written FIRST. The hangup is a cost saving; amd_result is the evidence that tells
//     a voicemail apart from a webhook that never arrived, and it must not be hostage to Telnyx.
//
// `hangup` mirrors `answered`'s vocabulary: null = deliberately not attempted, { ok:false, error } =
// we meant to and could not, which is a thing to log rather than a thing to skip.
async function applyAmdDetection(uid, key, opts = {}) {
  const result = typeof opts.result === "string" ? opts.result.trim() : "";
  const amd = await recordAmdResult(uid, key, opts);
  if (shouldMarkAnswered({ amdEnabled: true, signal: "amd", result })) {
    return { result, amd, answered: await markAnswered(uid, key, opts), hangup: null };
  }
  if (!result) return { result, amd, answered: null, hangup: null };
  const hangup = await hangupCall(opts.callControlId, {
    fetchImpl: opts.fetchImpl, apiKey: opts.telnyxApiKey,
  });
  return { result, amd, answered: null, hangup };
}

module.exports = {
  NO_DESTINATION_MESSAGE, MAIL_FAILURE_MESSAGE,
  evaluateLateArrival, formatLateSuccessMessage, externalAttendees,
  processLocationLateNotice, upsertLiveLocation, getLiveLocation, deleteLiveLocation, claimLateEvent,
  markAnswered, recordAmdResult, applyAmdDetection,
};
