"use strict";

const { roundedScoreValue } = require("./panel-score-semantics.js");

const SCORE_NAMES = Object.freeze(["daily", "physical", "mental", "financial"]);
const SCORE_LABELS = Object.freeze({
  daily: "DAILY",
  physical: "PHYSICAL",
  mental: "MENTAL",
  financial: "FINANCIAL",
});
const SCORE_PERIOD_KINDS = Object.freeze({
  daily: "rolling_7_days",
  physical: "rolling_30_days",
  mental: "rolling_7_days",
  financial: "calendar_month",
});
const SCORE_COMPONENT_KEYS = Object.freeze({
  daily: Object.freeze(["timezone", "excluded_unknown_count", "eligible_events", "resolved_events", "required_succeeded", "required_failed", "required_pending", "context_unnecessary", "optional_ignored"]),
  physical: Object.freeze(["timezone", "excluded_unknown_count", "detected_needs", "confirmed_booking", "confirmed_completion", "unresolved_needs", "search_candidate_unconfirmed"]),
  mental: Object.freeze(["timezone", "excluded_unknown_count", "deduplicated_triggers", "delivered_within_cap", "suppression_honored", "correction_persisted", "cap_overflow", "unresolved_triggers"]),
  financial: Object.freeze(["timezone", "excluded_unknown_count", "currency", "gross_income_minor", "realized_loss_minor", "fee_minor", "user_transfer_minor", "excluded_rows", "net_clamped"]),
});
const SCORE_COMPONENT_LABELS = Object.freeze({
  daily: Object.freeze({
    excluded_unknown_count: "対象外にした不明データ",
    eligible_events: "対象の予定",
    resolved_events: "対応できた予定",
    required_succeeded: "必要な対応の完了",
    required_failed: "必要な対応の未完了",
    required_pending: "確認待ちの対応",
    context_unnecessary: "追加対応が不要",
    optional_ignored: "任意対応の見送り",
  }),
  physical: Object.freeze({
    excluded_unknown_count: "対象外にした不明データ",
    detected_needs: "見つかった身体ケア",
    confirmed_booking: "確認できた予約",
    confirmed_completion: "確認できた完了",
    unresolved_needs: "未対応の身体ケア",
    search_candidate_unconfirmed: "未確認の候補",
  }),
  mental: Object.freeze({
    excluded_unknown_count: "対象外にした不明データ",
    deduplicated_triggers: "確認対象のきっかけ",
    delivered_within_cap: "通知できたきっかけ",
    suppression_honored: "通知を控えたきっかけ",
    correction_persisted: "反映した修正",
    cap_overflow: "上限を超えた通知",
    unresolved_triggers: "未対応のきっかけ",
  }),
  financial: Object.freeze({
    excluded_unknown_count: "対象外にした不明データ",
    currency: "通貨",
    gross_income_minor: "確認済みの収入（最小通貨単位）",
    realized_loss_minor: "確定した損失（最小通貨単位）",
    fee_minor: "手数料（最小通貨単位）",
    user_transfer_minor: "ユーザー送金（最小通貨単位）",
    excluded_rows: "対象外の記録",
    net_clamped: "マイナス補正",
  }),
});

function scoreAsDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) || date.toISOString() !== value ? null : date;
}

function scoreExactKeys(value, expected) {
  const actual = Object.keys(value).sort();
  const wanted = expected.slice().sort();
  return actual.length === wanted.length && actual.every(function (key, index) { return key === wanted[index]; });
}

function scoreNonNegativeInteger(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function validScoreComponents(name, components, status) {
  const keys = SCORE_COMPONENT_KEYS[name];
  if (!keys || !scoreExactKeys(components, keys) || typeof components.timezone !== "string" || !components.timezone) return false;
  if (name !== "financial") return keys.filter(function (key) { return key !== "timezone"; }).every(function (key) { return scoreNonNegativeInteger(components[key]); });
  if (!scoreNonNegativeInteger(components.excluded_unknown_count) || !scoreNonNegativeInteger(components.excluded_rows) || typeof components.net_clamped !== "boolean") return false;
  const amounts = ["gross_income_minor", "realized_loss_minor", "fee_minor", "user_transfer_minor"];
  if (status === "invalid_data") return components.currency === null && amounts.every(function (key) { return components[key] === null; });
  if (!(components.currency === null || /^[A-Z]{3}$/.test(components.currency)) || !amounts.every(function (key) { return scoreNonNegativeInteger(components[key]); })) return false;
  return status !== "measured" || /^[A-Z]{3}$/.test(String(components.currency || ""));
}

function scoreComponentRatio(name, components) {
  if (name === "daily") return [components.resolved_events, components.eligible_events];
  if (name === "physical") return [components.confirmed_booking + components.confirmed_completion, components.detected_needs];
  if (name === "mental") return [components.delivered_within_cap + components.suppression_honored + components.correction_persisted, components.deduplicated_triggers];
  const gross = components.gross_income_minor;
  return [Math.max(0, gross - components.realized_loss_minor - components.fee_minor), gross];
}

function validScoreOrgan(name, organ) {
  if (!organ || typeof organ !== "object" || !["measured", "insufficient_data", "invalid_data"].includes(organ.status)) return false;
  if (!scoreExactKeys(organ, ["status", "value", "period", "numerator", "denominator", "reason", "source_outcome_ids", "components"])) return false;
  if (!organ.period || !scoreExactKeys(organ.period, ["kind", "start_at", "end_at"]) || organ.period.kind !== SCORE_PERIOD_KINDS[name]) return false;
  const periodStart = scoreAsDate(organ.period.start_at);
  const periodEnd = scoreAsDate(organ.period.end_at);
  if (!periodStart || !periodEnd || periodStart >= periodEnd) return false;
  if (typeof organ.reason !== "string" || !organ.reason.trim() || !organ.components || typeof organ.components !== "object" || Array.isArray(organ.components)) return false;
  if (!Array.isArray(organ.source_outcome_ids) || organ.source_outcome_ids.some(function (ref) { return !/^outcome:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(ref)); })) return false;
  if (new Set(organ.source_outcome_ids).size !== organ.source_outcome_ids.length || organ.source_outcome_ids.some(function (ref, index) { return index > 0 && ref < organ.source_outcome_ids[index - 1]; })) return false;
  if (!validScoreComponents(name, organ.components, organ.status)) return false;
  if (organ.status === "measured") {
    if (!Number.isInteger(organ.value) || organ.value < 0 || organ.value > 100 || !scoreNonNegativeInteger(organ.numerator) || !Number.isSafeInteger(organ.denominator) || organ.denominator <= 0 || organ.numerator > organ.denominator) return false;
    const componentRatio = scoreComponentRatio(name, organ.components);
    return organ.numerator === componentRatio[0] && organ.denominator === componentRatio[1] && organ.value === roundedScoreValue(organ.numerator, organ.denominator);
  }
  if (organ.status === "insufficient_data") {
    const componentRatio = scoreComponentRatio(name, organ.components);
    return organ.value === null && organ.numerator === 0 && organ.denominator === 0 && componentRatio[1] === 0;
  }
  return organ.value === null && organ.numerator === null && organ.denominator === null;
}

module.exports = {
  SCORE_COMPONENT_KEYS,
  SCORE_COMPONENT_LABELS,
  SCORE_LABELS,
  SCORE_NAMES,
  SCORE_PERIOD_KINDS,
  scoreAsDate,
  scoreComponentRatio,
  scoreExactKeys,
  scoreNonNegativeInteger,
  validScoreComponents,
  validScoreOrgan,
};
