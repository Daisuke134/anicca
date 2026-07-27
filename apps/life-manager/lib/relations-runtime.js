"use strict";

const { fetchCalendarHistory } = require("./events.js");
const { extractCalendarInteractions } = require("./relation-calendar.js");
const { detectRelationCadence } = require("./relation-detector.js");
const { formatRelationSuggestion } = require("./i18n.js");
const { sendMessage } = require("./telegram.js");
const { readMentalSendState, recordMentalSend } = require("./mental-send-log.js");
const { localDay, localMinuteOfDay, resolveUserTzOffsetH } = require("./user-tz.js");

const HISTORY_MS = 548 * 86400000;
const WEEK_MS = 7 * 86400000;
const MIN_MENTAL_GAP_MS = 2 * 60 * 60 * 1000;
const DAILY_MENTAL_CAP = 3;
const WINDOW_START_MINUTE = 18 * 60 + 30;
const WINDOW_END_MINUTE = 19 * 60;
const TZ_ENV_KEYS = Object.freeze(["LM_RELATIONS_UTC_OFFSET_HOURS"]);

function supaBase(url) {
  return String(url).replace(/\/$/, "");
}

function headers(key, extra) {
  return { apikey: key, Authorization: `Bearer ${key}`, ...extra };
}

async function scanExists(uid, day, supa, fetchImpl) {
  const query = `uid=eq.${encodeURIComponent(uid)}&day=eq.${encodeURIComponent(day)}`
    + "&kind=eq.scan&select=id&limit=1";
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_relations_log?${query}`, {
    headers: headers(supa.supaKey),
  });
  if (!response || !response.ok) throw new Error(`relations scan lookup failed (${response ? response.status : "no response"})`);
  const rows = await response.json();
  if (!Array.isArray(rows)) throw new Error("relations scan lookup returned no rows array");
  return rows.length > 0;
}

async function readAttemptState(uid, nowMs, supa, fetchImpl) {
  const since = new Date(nowMs - WEEK_MS).toISOString();
  const query = `uid=eq.${encodeURIComponent(uid)}&kind=eq.suggestion_attempt`
    + `&attempted_at=gte.${encodeURIComponent(since)}&select=attempted_at&order=attempted_at.desc`;
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_relations_log?${query}`, {
    headers: headers(supa.supaKey),
  });
  if (!response || !response.ok) throw new Error(`relations attempt lookup failed (${response ? response.status : "no response"})`);
  const rows = await response.json();
  if (!Array.isArray(rows)) throw new Error("relations attempt lookup returned no rows array");
  const times = rows.map((row) => Date.parse(row.attempted_at))
    .filter((value) => Number.isFinite(value) && value >= nowMs - WEEK_MS && value <= nowMs);
  return { lastAttemptMs: times.length ? Math.max(...times) : null };
}

async function appendRow(row, supa, fetchImpl) {
  const response = await fetchImpl(`${supaBase(supa.supaUrl)}/rest/v1/lm_relations_log`, {
    method: "POST",
    headers: headers(supa.supaKey, { "Content-Type": "application/json", Prefer: "return=minimal" }),
    body: JSON.stringify(row),
  }).catch(() => null);
  if (response && response.status === 201) return true;
  if (response && response.status === 409) return false;
  throw new Error(`relations log insert failed (${response ? response.status : "no response"})`);
}

function piiFreeDetections(candidates) {
  return candidates.map((candidate) => ({
    person_key: candidate.personKey,
    source: candidate.source,
    personal_interval_days: candidate.personalIntervalDays,
    days_since: candidate.daysSince,
    overdue_days: candidate.overdueDays,
    overdue_ratio: candidate.overdueRatio,
    decision: candidate.decision,
    decision_reason: candidate.decisionReason,
  }));
}

function hasActiveEvent(events, nowMs) {
  return (Array.isArray(events) ? events : []).some((event) =>
    Number(event.startMs) <= nowMs && Number(event.endMs) > nowMs);
}

async function relationsUserOnce(u, nowMs, deps = {}) {
  const supa = {
    supaUrl: deps.supaUrl || process.env.SUPABASE_URL,
    supaKey: deps.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY,
  };
  const chatId = String((u && u.telegram_chat_id) || "");
  if (!u || !u.uid || !chatId || u.notifications_enabled === false || !supa.supaUrl || !supa.supaKey) {
    return { status: "skipped" };
  }

  const offsetH = resolveUserTzOffsetH(deps, u, nowMs, TZ_ENV_KEYS);
  if (offsetH === null) return { status: "suppressed", reason: "no-timezone" };
  const minute = localMinuteOfDay(nowMs, offsetH);
  if (minute < WINDOW_START_MINUTE || minute >= WINDOW_END_MINUTE) {
    return { status: "suppressed", reason: "outside-window" };
  }

  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  const day = localDay(nowMs, offsetH);
  if (await (deps.scanExists || scanExists)(u.uid, day, supa, fetchImpl)) {
    return { status: "already_scanned" };
  }

  const history = await (deps.fetchHistory || fetchCalendarHistory)(u.uid, {
    nowMs,
    historyMs: HISTORY_MS,
    apiKey: deps.apiKey,
    calendar: deps.calendar,
    gmailAccountId: deps.gmailAccountId || u.gmail_account_id,
  });
  const interactions = extractCalendarInteractions(history, {
    secret: deps.hashSecret || process.env.LM_RELATIONS_HASH_SECRET,
  });
  const detection = detectRelationCadence({ nowMs, interactions });
  const scanClaimed = await (deps.appendRow || appendRow)({
    uid: u.uid,
    day,
    kind: "scan",
    interaction_count: detection.interactionCount,
    detections: piiFreeDetections(detection.candidates),
  }, supa, fetchImpl);
  if (!scanClaimed) return { status: "already_scanned" };

  const candidate = detection.candidates.find((item) => item.decision === "act");
  if (!candidate) return { status: "abstained", interactionCount: detection.interactionCount };

  const attemptState = await (deps.readAttemptState || readAttemptState)(u.uid, nowMs, supa, fetchImpl);
  if (Number.isFinite(attemptState.lastAttemptMs) && attemptState.lastAttemptMs >= nowMs - WEEK_MS) {
    return { status: "suppressed", reason: "weekly-spacing" };
  }
  const mentalState = await (deps.readMentalSendState || readMentalSendState)(
    u.uid, nowMs, supa, fetchImpl, { strict: true },
  );
  if (Number(mentalState.sentTodayCount) >= DAILY_MENTAL_CAP) {
    return { status: "suppressed", reason: "mental-daily-cap-reached" };
  }
  if (Number.isFinite(mentalState.lastSentMs) && nowMs - mentalState.lastSentMs < MIN_MENTAL_GAP_MS) {
    return { status: "suppressed", reason: "too-soon-after-mental-send" };
  }
  if (hasActiveEvent(deps.events, nowMs)) return { status: "suppressed", reason: "active-event" };
  const locationState = deps.getLocationState
    ? await deps.getLocationState(u.uid, nowMs)
    : "unknown";
  if (locationState !== "still") return { status: "suppressed", reason: `location-${locationState || "unknown"}` };

  const attemptedAt = new Date(nowMs).toISOString();
  const claimed = await (deps.appendRow || appendRow)({
    uid: u.uid,
    day,
    kind: "suggestion_attempt",
    person_key: candidate.personKey,
    attempted_at: attemptedAt,
  }, supa, fetchImpl);
  if (!claimed) return { status: "already_attempted" };

  const text = formatRelationSuggestion(candidate);
  const sent = await (deps.sendMessage || sendMessage)(
    deps.telegramToken !== undefined ? deps.telegramToken : process.env.LM_TELEGRAM_BOT_TOKEN,
    chatId,
    text,
  );
  if (!sent || !sent.ok) return { status: "send_failed", day };
  const messageId = sent.result && sent.result.message_id;
  await (deps.appendRow || appendRow)({
    uid: u.uid,
    day,
    kind: "delivery",
    person_key: candidate.personKey,
    delivered_at: attemptedAt,
    telegram_message_id: String(messageId),
  }, supa, fetchImpl);
  const budgeted = await (deps.recordMentalSend || recordMentalSend)(
    u.uid, "relations", messageId, supa, fetchImpl,
  );
  return { status: "suggested", day, telegramMessageId: messageId, budgeted };
}

module.exports = {
  relationsUserOnce,
  scanExists,
  readAttemptState,
  appendRow,
  piiFreeDetections,
  HISTORY_MS,
  WEEK_MS,
};
