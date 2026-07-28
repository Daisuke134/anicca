"use strict";

const DECISION_KEYS = Object.freeze([
  "action_kind",
  "browser_required",
  "explicit_request",
  "goal",
  "locale",
  "requires_kyc",
  "requires_login",
  "reversible",
  "zero_cost",
]);

const RESERVED_MESSAGE = /^(?:\/|feedback\s*[:：]|フィードバック\s*[:：])/i;

function invalid() {
  throw new Error("browser decision schema invalid");
}

function validateBrowserDecision(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) invalid();
  if (Object.keys(value).sort().join(",") !== [...DECISION_KEYS].sort().join(",")) invalid();
  for (const key of [
    "browser_required",
    "explicit_request",
    "reversible",
    "zero_cost",
    "requires_kyc",
    "requires_login",
  ]) {
    if (typeof value[key] !== "boolean") invalid();
  }
  if (typeof value.action_kind !== "string" || !value.action_kind.trim() || value.action_kind.length > 100) invalid();
  if (typeof value.goal !== "string" || !value.goal.trim() || value.goal.length > 1000) invalid();
  if (!["en", "ja"].includes(value.locale)) invalid();
  return Object.freeze({ ...value, goal: value.goal.trim(), action_kind: value.action_kind.trim() });
}

function rejectionReason(decision) {
  if (!decision.explicit_request || !decision.browser_required) return "not_explicitly_actionable";
  if (!decision.zero_cost) return "financial_or_paid_action";
  if (decision.requires_kyc) return "kyc_or_identity_gate";
  if (!decision.reversible) return "irreversible_action";
  return null;
}

async function classifyBrowserTask(text, deps = {}) {
  const input = String(text || "").trim();
  if (RESERVED_MESSAGE.test(input)) {
    return { accepted: false, reason: "reserved_message_shape" };
  }
  if (!input) {
    return { accepted: false, reason: "not_explicitly_actionable" };
  }
  if (typeof deps.infer !== "function") throw new Error("browser classifier inference unavailable");
  const decision = validateBrowserDecision(await deps.infer(input));
  const reason = rejectionReason(decision);
  if (reason) return { accepted: false, reason };
  return {
    accepted: true,
    reason: "explicit_reversible_zero_cost_browser_task",
    goal: decision.goal,
    actionKind: decision.action_kind,
    locale: decision.locale,
    requiresLogin: decision.requires_login,
  };
}

module.exports = {
  classifyBrowserTask,
  validateBrowserDecision,
};
