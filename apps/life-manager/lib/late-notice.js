// LM-30 location-gated late notice decision core + Supabase helpers.
// A fresh Telegram live location is the only gate. The scheduler observes and reports; it never asks.
"use strict";

const { isHelperBlock } = require("./wake-filter.js");

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

async function claimLateEvent(uid, key, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey || !uid || !key) return false;
  const response = await f(`${opts.supaUrl}/rest/v1/lm_late_notice_log`, {
    method: "POST", headers: supaHeaders(opts.supaKey, "return=minimal"),
    body: JSON.stringify({ uid, event_key: key }),
  }).catch(() => null);
  return Boolean(response && response.status === 201);
}

// Wake-call answer telemetry remains useful to the authenticated Telnyx webhook even though it no
// longer unlocks or triggers a late notice. No new T-0 rows are created by this helper.
async function markAnswered(uid, key, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey || !uid || !key) return false;
  const url = `${opts.supaUrl}/rest/v1/lm_wake_log?uid=eq.${encodeURIComponent(uid)}&event_key=eq.${encodeURIComponent(key)}&answered_at=is.null&select=event_key`;
  const response = await f(url, {
    method: "PATCH", headers: supaHeaders(opts.supaKey, "return=representation"),
    body: JSON.stringify({ answered_at: new Date(opts.nowMs || Date.now()).toISOString() }),
  }).catch(() => null);
  if (!response || !response.ok) return false;
  const rows = await response.json().catch(() => []);
  return Array.isArray(rows) && rows.length > 0;
}

module.exports = {
  NO_DESTINATION_MESSAGE, MAIL_FAILURE_MESSAGE,
  evaluateLateArrival, formatLateSuccessMessage, externalAttendees,
  processLocationLateNotice, upsertLiveLocation, getLiveLocation, claimLateEvent, markAnswered,
};
