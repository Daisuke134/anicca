"use strict";

const {
  containsSensitiveDisplayValue,
  formatCurrencyAmount,
  safeDate,
  safeHttpsLink,
} = require("./panel-display-policy.js");

const SAFE_TIMELINE_SENTENCE = "予定の詳細を安全に表示できず、次はカレンダーで開始時刻を確認してください。";
const SCORE_ORGANS = Object.freeze(["daily", "physical", "mental", "financial"]);
const SCORE_STATUSES = new Set(["measured", "insufficient_data", "invalid_data"]);
const SCORE_PERIOD_KINDS = Object.freeze({
  daily: "rolling_7_days",
  physical: "rolling_30_days",
  mental: "rolling_7_days",
  financial: "calendar_month",
});
const SCORE_COMPONENT_KEYS = Object.freeze({
  daily: ["timezone", "excluded_unknown_count", "eligible_events", "resolved_events", "required_succeeded", "required_failed", "required_pending", "context_unnecessary", "optional_ignored"],
  physical: ["timezone", "excluded_unknown_count", "detected_needs", "confirmed_booking", "confirmed_completion", "unresolved_needs", "search_candidate_unconfirmed"],
  mental: ["timezone", "excluded_unknown_count", "deduplicated_triggers", "delivered_within_cap", "suppression_honored", "correction_persisted", "cap_overflow", "unresolved_triggers"],
  financial: ["timezone", "excluded_unknown_count", "currency", "gross_income_minor", "realized_loss_minor", "fee_minor", "user_transfer_minor", "excluded_rows", "net_clamped"],
});
const CONNECTION_NAMES = Object.freeze(["calendar", "telegram", "location", "call", "email", "wallet"]);
const CONNECTION_STATES = new Set(["connected", "action_required", "error", "unavailable"]);
const CONTROL_NAMES = Object.freeze(["delegation", "physical_automation", "mental_automation", "financial_automation"]);

class PanelSectionUnavailableError extends Error {
  constructor(section) {
    super("section_unavailable");
    this.name = "PanelSectionUnavailableError";
    this.code = "section_unavailable";
    this.section = section;
  }
}

function fail(section) {
  throw new PanelSectionUnavailableError(section);
}

function record(value) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function exactKeys(value, keys) {
  if (!record(value)) return false;
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  return actual.length === expected.length
    && actual.every((key, index) => key === expected[index]);
}

function validTimeZone(value) {
  if (typeof value !== "string" || containsSensitiveDisplayValue(value)) return false;
  try {
    new Intl.DateTimeFormat("en", { timeZone: value }).format(0);
    return true;
  } catch {
    return false;
  }
}

function clockText(value, timeZone) {
  const parsed = Date.parse(String(value || ""));
  if (!Number.isFinite(parsed)) return null;
  return new Intl.DateTimeFormat("ja-JP", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(parsed));
}

function timelineStatus(decision) {
  return Object.freeze({
    offline: "カレンダーで確認",
    travel: "移動準備",
    ready: "準備完了",
    question: "確認が必要",
  })[decision] || "確認が必要";
}

function projectTimeline(candidate) {
  if (
    !record(candidate)
    || !/^\d{4}-\d{2}-\d{2}$/.test(String(candidate.date || ""))
    || !validTimeZone(candidate.timezone)
    || !Array.isArray(candidate.events)
    || !Array.isArray(candidate.calls)
  ) fail("timeline");

  const items = [];
  for (const event of candidate.events) {
    if (!record(event)) fail("timeline");
    const hostile = containsSensitiveDisplayValue(event);
    const time = clockText(event.start_at, candidate.timezone);
    items.push({
      sentence: hostile || !time
        ? SAFE_TIMELINE_SENTENCE
        : `${time}開始の予定です。詳細はカレンダーで確認してください。`,
      status: hostile ? "確認が必要" : timelineStatus(event.interpretation && event.interpretation.decision),
    });
  }
  for (const call of candidate.calls) {
    if (!record(call)) fail("timeline");
    const time = clockText(call.called_at, candidate.timezone);
    const answered = typeof call.answered_at === "string" && Number.isFinite(Date.parse(call.answered_at));
    items.push({
      sentence: time
        ? `${time}の電話は${answered ? "応答済み" : "未応答"}です。`
        : "電話の状態を安全に表示できませんでした。",
      status: answered ? "応答済み" : "未応答",
    });
  }
  return { date: candidate.date, timezone: candidate.timezone, items };
}

function financialAmount(row) {
  const currency = typeof row.currency === "string" ? row.currency : "USD";
  if (row.amount != null) return formatCurrencyAmount(row.amount, currency);
  if (row.amount_minor != null) return formatCurrencyAmount(Number(row.amount_minor) / 100, currency);
  if (row.est_usd != null) return formatCurrencyAmount(row.est_usd, "USD");
  return null;
}

function ledgerItem(row, label) {
  if (!record(row)) return {
    label,
    date: "日付不明",
    amount: "金額不明",
    link: null,
  };
  const linkSource = row.link || row.on_chain_url || row.transaction_url || row.href || null;
  return {
    label,
    date: safeDate(row.ts || row.date || row.created_at) || "日付不明",
    amount: financialAmount(row) || "金額不明",
    link: safeHttpsLink(linkSource),
  };
}

function projectLedger(candidate) {
  if (
    !record(candidate)
    || !Array.isArray(candidate.apiCostEntries)
    || !Array.isArray(candidate.financialEntries)
  ) fail("ledger");
  const apiItems = candidate.apiCostEntries.map((row) => ledgerItem(row, "API利用料"));
  const financialItems = candidate.financialEntries.map((row) => ledgerItem(row, "収支"));
  const total = candidate.apiCostEntries.reduce((sum, row) => {
    const amount = Number(record(row) ? row.est_usd : NaN);
    return Number.isFinite(amount) ? sum + amount : sum;
  }, 0);
  return {
    api_cost: {
      no_data: apiItems.length === 0,
      total: formatCurrencyAmount(total, "USD"),
      items: apiItems,
    },
    financial: {
      no_data: financialItems.length === 0,
      items: financialItems,
    },
  };
}

function validNumberOrNull(value) {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function validComponentValue(value) {
  return value === null
    || typeof value === "boolean"
    || (typeof value === "number" && Number.isFinite(value) && value >= 0)
    || (typeof value === "string" && value.length <= 100 && !containsSensitiveDisplayValue(value));
}

function validScoreOrgan(name, value) {
  if (!exactKeys(value, ["status", "value", "period", "numerator", "denominator", "reason", "source_outcome_ids", "components"])) return false;
  if (!SCORE_STATUSES.has(value.status) || !validNumberOrNull(value.value) || !validNumberOrNull(value.numerator) || !validNumberOrNull(value.denominator)) return false;
  if (typeof value.reason !== "string" || containsSensitiveDisplayValue(value.reason)) return false;
  if (!exactKeys(value.period, ["kind", "start_at", "end_at"]) || value.period.kind !== SCORE_PERIOD_KINDS[name]) return false;
  if (!Number.isFinite(Date.parse(value.period.start_at)) || !Number.isFinite(Date.parse(value.period.end_at))) return false;
  if (!Array.isArray(value.source_outcome_ids) || value.source_outcome_ids.some((ref) => !/^outcome:[0-9a-f-]{36}$/.test(ref))) return false;
  if (!exactKeys(value.components, SCORE_COMPONENT_KEYS[name])) return false;
  return Object.values(value.components).every(validComponentValue);
}

function validateScores(candidate) {
  if (!exactKeys(candidate, ["organs"]) || !exactKeys(candidate.organs, SCORE_ORGANS)) fail("scores");
  if (containsSensitiveDisplayValue(candidate)) fail("scores");
  for (const organ of SCORE_ORGANS) {
    if (!validScoreOrgan(organ, candidate.organs[organ])) fail("scores");
  }
  return candidate;
}

function validateGates(candidate) {
  if (!exactKeys(candidate, ["gates"]) || !Array.isArray(candidate.gates) || candidate.gates.length !== 2) fail("gates");
  const expectedIds = ["location", "payout"];
  for (let index = 0; index < candidate.gates.length; index += 1) {
    const gate = candidate.gates[index];
    if (
      !exactKeys(gate, ["id", "unlocked", "unlock_method"])
      || gate.id !== expectedIds[index]
      || typeof gate.unlocked !== "boolean"
      || typeof gate.unlock_method !== "string"
      || containsSensitiveDisplayValue(gate.unlock_method)
    ) fail("gates");
  }
  return candidate;
}

function validCallLanguage(value) {
  return value === null || value === "ja" || value === "en";
}

function validSettings(candidate) {
  return exactKeys(candidate, ["call_language", "call_schedule", "connections"])
    && validCallLanguage(candidate.call_language)
    && exactKeys(candidate.call_schedule, ["time_zone", "minutes_before", "wake_policy"])
    && validTimeZone(candidate.call_schedule.time_zone)
    && Array.isArray(candidate.call_schedule.minutes_before)
    && candidate.call_schedule.minutes_before.length === 2
    && candidate.call_schedule.minutes_before[0] === 10
    && candidate.call_schedule.minutes_before[1] === 5
    && new Set(["travel-only", "all-events"]).has(candidate.call_schedule.wake_policy)
    && exactKeys(candidate.connections, ["calendar", "gmail", "telegram"])
    && Object.values(candidate.connections).every((value) => typeof value === "boolean")
    && !containsSensitiveDisplayValue(candidate);
}

function validateSettings(candidate) {
  if (!validSettings(candidate)) fail("settings");
  return candidate;
}

function validConnection(value) {
  if (!record(value)) return false;
  const allowedKeys = new Set(["state", "reason", "actions", "actionLabel"]);
  if (Object.keys(value).some((key) => !allowedKeys.has(key))) return false;
  if (typeof value.state !== "string" || !CONNECTION_STATES.has(value.state)) return false;
  if (typeof value.reason !== "string" || containsSensitiveDisplayValue(value.reason)) return false;
  if (value.actions != null && (!Array.isArray(value.actions) || value.actions.some((action) => typeof action !== "string" || containsSensitiveDisplayValue(action)))) return false;
  if (value.actionLabel != null && (typeof value.actionLabel !== "string" || containsSensitiveDisplayValue(value.actionLabel))) return false;
  return true;
}

function validControlSettings(value) {
  return exactKeys(value, ["call_enabled", "notifications_enabled", "daily_automation_enabled", "call_time_zone", "call_language", "wake_policy"])
    && typeof value.call_enabled === "boolean"
    && typeof value.notifications_enabled === "boolean"
    && typeof value.daily_automation_enabled === "boolean"
    && validTimeZone(value.call_time_zone)
    && validCallLanguage(value.call_language)
    && new Set(["travel-only", "all-events"]).has(value.wake_policy);
}

function validControls(value) {
  if (!exactKeys(value, CONTROL_NAMES)) return false;
  if (!exactKeys(value.delegation, ["state", "reason"]) || value.delegation.state !== "unavailable" || typeof value.delegation.reason !== "string") return false;
  return CONTROL_NAMES.slice(1).every((name) => exactKeys(value[name], ["state"]) && value[name].state === "unavailable");
}

function validateControlCenter(candidate) {
  if (!exactKeys(candidate, ["identity", "context", "connections", "settings", "controls", "csrf"])) fail("control-center");
  if (
    !exactKeys(candidate.identity, ["name", "uidRef"])
    || candidate.identity.name !== "Life Manager user"
    || !/^user:[0-9a-f]{12}$/.test(candidate.identity.uidRef)
    || !exactKeys(candidate.context, ["timeZone", "locationAvailable"])
    || !validTimeZone(candidate.context.timeZone)
    || typeof candidate.context.locationAvailable !== "boolean"
    || !exactKeys(candidate.connections, CONNECTION_NAMES)
    || CONNECTION_NAMES.some((name) => !validConnection(candidate.connections[name]))
    || !validControlSettings(candidate.settings)
    || !validControls(candidate.controls)
    || typeof candidate.csrf !== "string"
    || !candidate.csrf
    || containsSensitiveDisplayValue(candidate)
  ) fail("control-center");
  return candidate;
}

function presentPanelSection(section, candidate) {
  if (section === "timeline") return projectTimeline(candidate);
  if (section === "ledger") return projectLedger(candidate);
  if (section === "scores") return validateScores(candidate);
  if (section === "gates") return validateGates(candidate);
  if (section === "settings") return validateSettings(candidate);
  if (section === "control-center") return validateControlCenter(candidate);
  fail(section);
}

module.exports = {
  PanelSectionUnavailableError,
  SAFE_TIMELINE_SENTENCE,
  presentPanelSection,
};
