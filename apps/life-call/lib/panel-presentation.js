"use strict";

const {
  containsSensitiveDisplayValue,
  formatCurrencyAmount,
  safeDate,
  safeHttpsLink,
} = require("./panel-display-policy.js");
const {
  SCORE_NAMES,
  validScoreOrgan,
} = require("./panel-score-display-contract.js");

const SAFE_TIMELINE_SENTENCE = "予定の詳細を安全に表示できず、次はカレンダーで開始時刻を確認してください。";
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

function validDisplayText(value) {
  return typeof value === "string"
    && value.trim().length > 0
    && value.length <= 1000
    && !containsSensitiveDisplayValue(value);
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

function validateScores(candidate) {
  if (!exactKeys(candidate, ["organs"]) || !exactKeys(candidate.organs, SCORE_NAMES)) fail("scores");
  if (containsSensitiveDisplayValue(candidate)) fail("scores");
  for (const organ of SCORE_NAMES) {
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
      || !validDisplayText(gate.unlock_method)
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
  if (!validDisplayText(value.reason)) return false;
  if (
    Object.hasOwn(value, "actions")
    && (!Array.isArray(value.actions) || value.actions.some((action) => !validDisplayText(action)))
  ) return false;
  if (Object.hasOwn(value, "actionLabel") && !validDisplayText(value.actionLabel)) return false;
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
  if (!exactKeys(value.delegation, ["state", "reason"]) || value.delegation.state !== "unavailable" || !validDisplayText(value.delegation.reason)) return false;
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
    || !validDisplayText(candidate.csrf)
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
