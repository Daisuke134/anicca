// LM-5 late-notice decision core + thin Supabase helpers.
// All timing decisions consume persisted lm_wake_log values; there are no process timers.
"use strict";

const crypto = require("crypto");
const { isReplyToken } = require("./reply-token.js");
const { getCalendar } = require("./transport/index.js");

const FALLBACK_MS = 10 * 60 * 1000;

function parseWakeEventKey(eventKey) {
  const parts = String(eventKey || "").split("|");
  if (parts.length !== 3 || !parts[0] || Number.isNaN(Date.parse(parts[1]))) return null;
  const level = Number(parts[2]);
  if (!Number.isInteger(level)) return null;
  return { uid: parts[0], startIso: parts[1], level };
}

function t0EventKey(eventKey) {
  const parsed = parseWakeEventKey(eventKey);
  return parsed ? `${parsed.uid}|${parsed.startIso}|0` : null;
}

function shouldSendT0(t5Row, nowMs, t0Exists) {
  const parsed = parseWakeEventKey(t5Row && t5Row.event_key);
  return Boolean(parsed && parsed.level === 5 && t5Row.answered_at && !t0Exists && parsed.startIso && Date.parse(parsed.startIso) <= nowMs);
}

function shouldFallback(t0Row, nowMs) {
  const parsed = parseWakeEventKey(t0Row && t0Row.event_key);
  const calledMs = Date.parse(t0Row && t0Row.called_at);
  return Boolean(parsed && parsed.level === 0 && Number.isFinite(calledMs) &&
    !t0Row.answered_at && !t0Row.notified_late_at && nowMs - calledMs >= FALLBACK_MS);
}

// Short opaque token without a new DB column: bind the persisted event_key to the existing call secret.
// The callback's chat id resolves uid first; only that uid's DB rows are compared, in constant time.
function lateToken(eventKey, secret) {
  if (!eventKey || !secret) return "";
  return crypto.createHmac("sha256", secret).update(String(eventKey)).digest().subarray(0, 16).toString("base64url");
}

function tokenMatches(a, b) {
  const aa = Buffer.from(String(a || ""));
  const bb = Buffer.from(String(b || ""));
  return aa.length > 0 && aa.length === bb.length && crypto.timingSafeEqual(aa, bb);
}

function lateQuestion(summary, token) {
  return {
    text: `⏰ “${summary || "次の予定"}” — 出た？`,
    extra: { reply_markup: { inline_keyboard: [[
      { text: "出た", callback_data: `late:ok:${token}` },
      { text: "まだ", callback_data: `late:still:${token}` },
    ]] } },
  };
}

function parseLateCallback(data) {
  const m = /^late:(ok|still):([A-Za-z0-9_-]{16,64})$/.exec(String(data || ""));
  return m && isReplyToken(m[2]) ? { action: m[1], token: m[2] } : null;
}

function runningLateText(summary) {
  return `running late to ${String(summary || "").trim() || "the event"}`;
}

function pendingT0Keys(rows, nowMs) {
  return (rows || []).filter((row) => {
    const parsed = parseWakeEventKey(row && row.event_key);
    const calledMs = Date.parse(row && row.called_at);
    return parsed && parsed.level === 0 && Number.isFinite(calledMs) && calledMs <= nowMs &&
      nowMs - calledMs <= FALLBACK_MS && !row.answered_at && !row.notified_late_at;
  }).map((row) => row.event_key);
}

async function processWakeRows(input, deps) {
  const { user, rows, nowMs, secret } = input;
  const existing = new Set((rows || []).map((row) => row.event_key));
  for (const row of (rows || [])) {
    const key = t0EventKey(row.event_key);
    if (!shouldSendT0(row, nowMs, key && existing.has(key)) || !user.telegram_chat_id || !secret) continue;
    if (!await deps.claimPrompt(user.uid, key)) continue;
    const parsed = parseWakeEventKey(key);
    const summary = await deps.summaryFor(user.uid, parsed.startIso);
    const sent = await deps.sendQuestion(user.telegram_chat_id, lateQuestion(summary, lateToken(key, secret)));
    if (!sent || sent.ok === false) await deps.releasePrompt(user.uid, key);
  }
  for (const row of (rows || [])) {
    if (!shouldFallback(row, nowMs)) continue;
    const parsed = parseWakeEventKey(row.event_key);
    const summary = await deps.summaryFor(user.uid, parsed.startIso);
    await deps.deliver({
      uid: user.uid, eventKey: row.event_key, summary, chatId: user.telegram_chat_id,
      noticeOpts: input.noticeOpts || {}, requireUnanswered: true,
    });
  }
}

async function deliverLateNotice(input, deps) {
  const claimed = await deps.claimNotified(input.uid, input.eventKey, { requireUnanswered: input.requireUnanswered === true });
  if (!claimed) return { notified: false, deduped: true };
  let result = { sent: false };
  try {
    result = await deps.sendLateNotice(input.uid, runningLateText(input.summary), input.noticeOpts || {});
  } catch {
    result = { sent: false };
  }
  if (!result || !result.sent) {
    if (input.chatId) await deps.sendMessage(input.token, input.chatId,
      "遅刻連絡先が見つからなかったため、メールは送信しませんでした。");
    return { notified: true, sent: false, reason: "no_destination" };
  }
  return { notified: true, sent: true, result };
}

async function handleLateCallback(input, deps) {
  const parsed = parseLateCallback(input.data);
  if (!parsed) return { ok: false, ignored: true };
  const row = (input.rows || []).find((candidate) => {
    const key = parseWakeEventKey(candidate && candidate.event_key);
    return key && key.uid === input.uid && key.level === 0 && tokenMatches(parsed.token, lateToken(candidate.event_key, input.secret));
  });
  if (!row) return { ok: false, reason: "unknown_token" };
  if (parsed.action === "ok") {
    await deps.markAnswered(input.uid, row.event_key);
    return { ok: true, action: "ok" };
  }
  const key = parseWakeEventKey(row.event_key);
  const summary = await deps.summaryFor(input.uid, key.startIso);
  const result = await deps.deliver({
    uid: input.uid, eventKey: row.event_key, summary, chatId: input.chatId,
    token: input.telegramToken, noticeOpts: input.noticeOpts || {}, requireUnanswered: false,
  });
  await deps.markAnswered(input.uid, row.event_key);
  return { ok: true, action: "still", notified: result.notified === true };
}

function supaHeaders(key, prefer) {
  return { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json", ...(prefer ? { Prefer: prefer } : {}) };
}

async function listWakeRows(uid, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey || !uid) return [];
  const url = `${opts.supaUrl}/rest/v1/lm_wake_log?uid=eq.${encodeURIComponent(uid)}&select=uid,event_key,called_at,answered_at,notified_late_at`;
  const r = await f(url, { headers: supaHeaders(opts.supaKey) });
  if (!r.ok) return [];
  const rows = await r.json().catch(() => []);
  return Array.isArray(rows) ? rows : [];
}

async function claimPrompt(uid, eventKey, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey) return false;
  const r = await f(`${opts.supaUrl}/rest/v1/lm_wake_log`, {
    method: "POST", headers: supaHeaders(opts.supaKey, "return=minimal"),
    body: JSON.stringify({ uid, event_key: eventKey }),
  });
  return r.status === 201;
}

async function releasePrompt(uid, eventKey, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey) return false;
  const url = `${opts.supaUrl}/rest/v1/lm_wake_log?uid=eq.${encodeURIComponent(uid)}&event_key=eq.${encodeURIComponent(eventKey)}`;
  const r = await f(url, { method: "DELETE", headers: supaHeaders(opts.supaKey, "return=minimal") }).catch(() => null);
  return Boolean(r && r.ok);
}

async function markAnswered(uid, eventKey, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey) return false;
  const url = `${opts.supaUrl}/rest/v1/lm_wake_log?uid=eq.${encodeURIComponent(uid)}&event_key=eq.${encodeURIComponent(eventKey)}&answered_at=is.null&select=event_key`;
  const r = await f(url, {
    method: "PATCH", headers: supaHeaders(opts.supaKey, "return=representation"),
    body: JSON.stringify({ answered_at: new Date(opts.nowMs || Date.now()).toISOString() }),
  });
  if (!r.ok) return false;
  const rows = await r.json().catch(() => []);
  return Array.isArray(rows) && rows.length > 0;
}

async function claimNotified(uid, eventKey, claimOpts = {}, opts = {}) {
  const f = opts.fetchImpl || fetch;
  if (!opts.supaUrl || !opts.supaKey) return false;
  const unanswered = claimOpts.requireUnanswered ? "&answered_at=is.null" : "";
  const url = `${opts.supaUrl}/rest/v1/lm_wake_log?uid=eq.${encodeURIComponent(uid)}&event_key=eq.${encodeURIComponent(eventKey)}&notified_late_at=is.null${unanswered}&select=event_key`;
  const r = await f(url, {
    method: "PATCH", headers: supaHeaders(opts.supaKey, "return=representation"),
    body: JSON.stringify({ notified_late_at: new Date(opts.nowMs || Date.now()).toISOString() }),
  });
  if (!r.ok) return false;
  const rows = await r.json().catch(() => []);
  return Array.isArray(rows) && rows.length > 0;
}

async function eventSummaryFor(uid, startIso, opts = {}) {
  if (!uid || !startIso) return "the event";
  const startMs = Date.parse(startIso);
  if (!Number.isFinite(startMs)) return "the event";
  try {
    const calendar = opts.calendar || getCalendar({ apiKey: opts.composioKey });
    const items = await calendar.listEventsRaw(uid, {
      timeMin: new Date(startMs - 60 * 1000).toISOString(),
      timeMax: new Date(startMs + 60 * 1000).toISOString(), maxResults: 10,
    });
    const match = (items || []).find((item) => Date.parse(item && item.start && item.start.dateTime) === startMs);
    return match && match.summary ? match.summary : "the event";
  } catch {
    return "the event";
  }
}

module.exports = {
  FALLBACK_MS,
  parseWakeEventKey, t0EventKey, shouldSendT0, shouldFallback,
  lateToken, lateQuestion, parseLateCallback, runningLateText, pendingT0Keys,
  processWakeRows, deliverLateNotice, handleLateCallback,
  listWakeRows, claimPrompt, releasePrompt, markAnswered, claimNotified, eventSummaryFor,
};
