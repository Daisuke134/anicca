"use strict";

const { isVerifiedRollingEventCoverage } = require("./rolling-event-coverage.js");
const { isVerifiedLumaDateInventory } = require("./luma-date-inventory.js");
const { isVerifiedConnectorCalendarSync } = require("./connector-calendar-sync.js");
const { isVerifiedEventGoalSerendipity } = require("./event-goal-serendipity.js");
const { notifyOpenClaw, parseOpenClawMessageId } = require("./outbound-guardian.js");
const { hashChatId } = require("./telegram.js");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const NEW_EVENT_KEYS = Object.freeze(["calendarSync", "dateInventory", "eventRef", "goalDecision"]);
const UNSAFE = /\{\{|\}\}|\b(?:TODO|TBD|password|cookie|guest[_ -]?key|api[_ -]?key|access[_ -]?token)\b/i;

function invalid() { throw new Error("Connector coverage Telegram invalid"); }

function displayText(value) {
  return String(value).replace(/[<>]/g, "");
}

function safeText(value, max) {
  const result = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  if (!result || result.length > max || UNSAFE.test(result)) invalid();
  return result;
}

function googleCalendarUrl(value) {
  let url;
  try { url = new URL(String(value == null ? "" : value)); } catch { invalid(); }
  if (
    url.protocol !== "https:" || url.hostname !== "calendar.google.com"
    || !url.pathname.startsWith("/calendar/") || url.username || url.password
  ) invalid();
  return url.toString();
}

function jaDate(date) {
  const [year, month, day] = String(date).split("-").map(Number);
  if (!year || !month || !day) invalid();
  return `${year}年${month}月${day}日`;
}

function shortDate(date) {
  const [, month, day] = String(date).split("-").map(Number);
  return `${month}/${day}`;
}

function localDate(instant, timeZone) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(instant)).filter((part) => part.type !== "literal")
    .map((part) => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function jaTimeRange(startAt, endAt, timeZone) {
  const format = (value) => new Intl.DateTimeFormat("ja-JP", {
    timeZone, hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).format(new Date(value));
  return `${format(startAt)}〜${format(endAt)}`;
}

function normalizeNewEvents(coverage, rows) {
  if (!Array.isArray(rows)) invalid();
  const coveredDates = new Set(coverage.days.filter((day) => day.status === "covered_new").map((day) => day.date));
  const seenRefs = new Set();
  const seenDates = new Set();
  const result = rows.map((row) => {
    if (
      !row || typeof row !== "object" || Array.isArray(row)
      || Object.keys(row).sort().join(",") !== [...NEW_EVENT_KEYS].sort().join(",")
      || !isVerifiedLumaDateInventory(row.dateInventory)
      || !isVerifiedConnectorCalendarSync(row.calendarSync)
      || !isVerifiedEventGoalSerendipity(row.goalDecision)
    ) invalid();
    const eventRef = String(row.eventRef == null ? "" : row.eventRef).trim();
    if (
      !eventRef || seenRefs.has(eventRef)
      || row.calendarSync.event_ref !== eventRef
      || row.calendarSync.canonical_event_url == null
      || row.dateInventory.inventory_snapshot_id !== row.goalDecision.inventory_snapshot_id
    ) invalid();
    const event = row.dateInventory.days.flatMap((day) => day.events)
      .find((candidate) => candidate.event_ref === eventRef);
    const goal = row.goalDecision.ranked_events.find((candidate) => candidate.event_ref === eventRef);
    if (!event || !goal || event.canonical_url !== row.calendarSync.canonical_event_url) invalid();
    const date = localDate(event.starts_at, coverage.timezone);
    const coverageDay = coverage.days.find((day) => day.date === date);
    if (
      !coverageDay || coverageDay.status !== "covered_new"
      || !coverageDay.evidence_refs.includes(row.calendarSync.registration_receipt_ref)
      || !coverageDay.evidence_refs.includes(row.calendarSync.calendar_event_ref)
    ) invalid();
    seenRefs.add(eventRef);
    seenDates.add(date);
    return Object.freeze({
      date,
      title: safeText(event.title, 160),
      venue: safeText(event.venue_name || event.venue_address, 160),
      starts_at: event.starts_at,
      ends_at: event.ends_at,
      reason: safeText(goal.goal_reason, 240),
      event_url: event.canonical_url,
      calendar_url: googleCalendarUrl(row.calendarSync.calendar_event_url),
    });
  });
  if (seenDates.size !== coveredDates.size || [...coveredDates].some((date) => !seenDates.has(date))) invalid();
  return result.sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at));
}

function buildConnectorCoverageTelegramMessage(input = {}) {
  const coverage = input.coverage;
  if (!isVerifiedRollingEventCoverage(coverage) || coverage.horizon_days !== 21) invalid();
  const calendar = googleCalendarUrl(input.calendarCoverageUrl);
  const newEvents = normalizeNewEvents(coverage, input.newEvents);
  const lines = [
    coverage.counts.open === 0 ? "✅ 今後3週間のevent予定を確認しました。" : "🔌 Connector 3週間予約状況",
    "",
    `確認期間: ${jaDate(coverage.window_start_date)}〜${jaDate(coverage.window_end_date)}`,
    "対象日: 21日",
    `既存の対面予定: ${coverage.counts.covered_existing}日`,
    `Connectorが新しく予約: ${coverage.counts.covered_new}日`,
    `固定予定で追加不可: ${coverage.counts.unavailable}日`,
    `未処理の空き: ${coverage.counts.open}日`,
  ];
  if (newEvents.length > 0) {
    lines.push("", "今回予約し、確認メールとCalendar登録を照合したevent:");
    for (const [index, event] of newEvents.entries()) {
      lines.push(
        `${index + 1}. ${shortDate(event.date)} ${displayText(event.title)}`,
        `   ${jaTimeRange(event.starts_at, event.ends_at, coverage.timezone)} / ${displayText(event.venue)}`,
        `   理由: ${displayText(event.reason)}`,
        "   イベントページ:",
        `   ${event.event_url}`,
        "   Calendar:",
        `   ${event.calendar_url}`,
      );
    }
  }
  if (coverage.counts.open > 0) {
    const dates = coverage.days.filter((day) => day.status === "open").map((day) => shortDate(day.date));
    lines.push(
      "",
      `空いている日: ${dates.join("、")}`,
      "この日々は終了扱いにしていません。予約が成立するまで探索と申込みを続けています。",
    );
  } else if (coverage.counts.covered_new === 0) {
    lines.push("", "予約できる空き枠が残っていないため、二重予約を作りませんでした。");
  } else {
    lines.push("", "21日間の未処理日はありません。既存予定と移動時間が重なる予約もありません。");
  }
  lines.push("", "3週間のCalendarを開く:", calendar);
  const message = lines.join("\n");
  if (message.length > 4_096 || /runner|bounded|none:/i.test(message)) invalid();
  return message;
}

async function deliverConnectorCoverageTelegram(input = {}, dependencies = {}) {
  const tenant = String(input.tenantId == null ? "" : input.tenantId).trim();
  const target = String(input.telegramTarget == null ? "" : input.telegramTarget).trim();
  if (!TENANT.test(tenant) || !target || input.coverage?.tenant_id !== tenant) invalid();
  const message = buildConnectorCoverageTelegramMessage(input);
  const send = dependencies.send || notifyOpenClaw;
  const response = await send(message, { telegramTarget: target });
  let providerId;
  try { providerId = parseOpenClawMessageId(JSON.stringify(response || {})); }
  catch { throw new Error("Connector coverage Telegram needs a positive message ID"); }
  const observedAt = new Date(Date.parse(
    (dependencies.observedAt || (() => new Date().toISOString()))(),
  )).toISOString();
  if (!Number.isFinite(Date.parse(observedAt))) invalid();
  return Object.freeze({
    kind: "connector_coverage_telegram_delivery",
    provider_id: providerId,
    observed_at: observedAt,
    tenant_id: tenant,
    chat_id_sha256: hashChatId(target),
    coverage_snapshot_id: input.coverage.coverage_snapshot_id,
  });
}

module.exports = {
  buildConnectorCoverageTelegramMessage,
  deliverConnectorCoverageTelegram,
};
