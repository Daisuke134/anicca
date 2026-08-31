"use strict";

const { createHash } = require("node:crypto");

const { isVerifiedLumaDateInventory } = require("./luma-date-inventory.js");
const { isVerifiedCalendarCandidateGate } = require("./calendar-candidate-gate.js");
const { isVerifiedEventGoalSerendipity } = require("./event-goal-serendipity.js");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,199}$/;
const POLICIES = new WeakSet();
const METHODS = new WeakSet();
const DECISIONS = new WeakSet();
const SEQUENCES = new WeakSet();
const SEQUENCE_DECISIONS = new WeakMap();

function invalid() { throw new Error("Event spend policy invalid"); }
function unavailable() { throw new Error("Event spend policy unavailable"); }

function digest(value) {
  return createHash("sha256").update(String(value), "utf8").digest("hex");
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => (
      `${JSON.stringify(key)}:${stableJson(value[key])}`
    )).join(",")}}`;
  }
  return JSON.stringify(value);
}

async function inspectSavedLumaPaymentMethod(options = {}) {
  if (typeof options.inspect !== "function") invalid();
  let observed;
  try { observed = await options.inspect(); } catch { unavailable(); }
  const binding = String(observed && observed.provider_binding || "").trim();
  if (
    !observed || observed.status !== "saved" || !binding || binding.length > 1_000
    || /[\x00-\x1f\x7f]/.test(binding)
  ) unavailable();
  const method = Object.freeze({
    provider: "luma",
    status: "saved",
    payment_method_ref: `payment-method://luma/saved/${digest(binding)}`,
  });
  METHODS.add(method);
  return method;
}

function limitRow(value) {
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || Object.keys(value).sort().join(",") !== "currency,per_event_minor,rolling_30_day_minor,spent_30_day_minor"
  ) invalid();
  const currency = String(value.currency == null ? "" : value.currency).trim().toUpperCase();
  const amounts = [value.per_event_minor, value.rolling_30_day_minor, value.spent_30_day_minor];
  if (
    !/^[A-Z]{3}$/.test(currency)
    || amounts.some((amount) => !Number.isSafeInteger(amount) || amount < 0)
    || value.spent_30_day_minor > value.rolling_30_day_minor
  ) invalid();
  return Object.freeze({
    currency,
    per_event_minor: value.per_event_minor,
    rolling_30_day_minor: value.rolling_30_day_minor,
    spent_30_day_minor: value.spent_30_day_minor,
  });
}

function createEventSpendPolicy(input = {}) {
  const tenantId = String(input.tenantId == null ? "" : input.tenantId).trim();
  if (!TENANT.test(tenantId) || !Array.isArray(input.limits)) invalid();
  const limits = input.limits.map(limitRow);
  if (new Set(limits.map((limit) => limit.currency)).size !== limits.length) invalid();
  const saved = input.savedPaymentMethod;
  if (limits.length > 0 && (!saved || !METHODS.has(saved))) invalid();
  if (limits.length === 0 && saved != null && !METHODS.has(saved)) invalid();
  const core = {
    tenant_id: tenantId,
    paid_enabled: limits.length > 0,
    saved_payment_method_ref: saved && METHODS.has(saved) ? saved.payment_method_ref : null,
    limits: Object.freeze(limits),
  };
  const policy = Object.freeze({
    event_spend_policy_id: `event-spend-policy:${digest(stableJson(core))}`,
    ...core,
  });
  POLICIES.add(policy);
  return policy;
}

function isVerifiedEventSpendPolicy(value) {
  return Boolean(value && typeof value === "object" && POLICIES.has(value));
}

function authorizeEventSpend(input = {}) {
  const policy = input.policy;
  const inventory = input.dateInventory;
  if (!isVerifiedEventSpendPolicy(policy) || !isVerifiedLumaDateInventory(inventory)) invalid();
  const eventRef = String(input.eventRef == null ? "" : input.eventRef).trim();
  const event = inventory.days.flatMap((day) => day.events).find((candidate) => candidate.event_ref === eventRef);
  if (!event) invalid();
  let allowed = false;
  let reason;
  let paymentMode = "none";
  let paymentMethodRef = null;
  let remainingAfterMinor = null;
  if (event.ticket_price_status === "free" && event.ticket_price_minor === 0) {
    allowed = true;
    reason = "free";
  } else if (event.ticket_price_status !== "paid") {
    reason = "price_unknown";
  } else if (!policy.paid_enabled) {
    reason = "paid_disabled";
  } else {
    const limit = policy.limits.find((candidate) => candidate.currency === event.ticket_currency);
    if (!limit) {
      reason = "currency_not_allowed";
    } else if (event.ticket_price_minor > limit.per_event_minor) {
      reason = "per_event_cap_exceeded";
    } else if (event.ticket_price_minor > limit.rolling_30_day_minor - limit.spent_30_day_minor) {
      reason = "rolling_cap_exceeded";
    } else {
      allowed = true;
      reason = "paid_policy_allowed";
      paymentMode = "saved";
      paymentMethodRef = policy.saved_payment_method_ref;
      remainingAfterMinor = limit.rolling_30_day_minor - limit.spent_30_day_minor - event.ticket_price_minor;
    }
  }
  const core = {
    event_spend_policy_id: policy.event_spend_policy_id,
    inventory_snapshot_id: inventory.inventory_snapshot_id,
    event_ref: event.event_ref,
    allowed,
    reason,
    amount_minor: event.ticket_price_minor,
    currency: event.ticket_currency,
    payment_mode: paymentMode,
    payment_method_ref: paymentMethodRef,
    remaining_after_minor: remainingAfterMinor,
  };
  const decision = Object.freeze({
    event_spend_decision_id: `event-spend-decision:${digest(stableJson(core))}`,
    ...core,
  });
  DECISIONS.add(decision);
  return decision;
}

function isVerifiedEventSpendDecision(value) {
  return Boolean(value && typeof value === "object" && DECISIONS.has(value));
}

function authorizeEventSpendEffect(input = {}) {
  const decision = input.decision;
  const detail = input.eventDetail;
  if (
    !isVerifiedEventSpendDecision(decision)
    || !detail || typeof detail !== "object" || Array.isArray(detail)
    || decision.allowed !== true
    || detail.event_ref !== decision.event_ref
  ) invalid();
  if (
    detail.ticket_price_status === "free"
    && detail.ticket_price_minor === 0
    && decision.amount_minor === 0
    && decision.payment_mode === "none"
  ) return Object.freeze({ mode: "free", event_spend_decision_id: decision.event_spend_decision_id });
  if (
    detail.ticket_price_status === "paid"
    && Number.isSafeInteger(detail.ticket_price_minor)
    && detail.ticket_price_minor > 0
    && detail.ticket_price_minor === decision.amount_minor
    && detail.ticket_currency === decision.currency
    && decision.payment_mode === "saved"
    && /^payment-method:\/\/luma\/saved\/[0-9a-f]{64}$/.test(String(decision.payment_method_ref || ""))
  ) return Object.freeze({ mode: "saved", event_spend_decision_id: decision.event_spend_decision_id });
  invalid();
}

function buildEventSpendSequence(input = {}) {
  const policy = input.policy;
  const inventory = input.dateInventory;
  const gate = input.calendarGate;
  const goal = input.goalDecision;
  if (
    !isVerifiedEventSpendPolicy(policy)
    || !isVerifiedLumaDateInventory(inventory)
    || !isVerifiedCalendarCandidateGate(gate)
    || !isVerifiedEventGoalSerendipity(goal)
    || gate.status !== "evaluated"
    || gate.inventory_snapshot_id !== inventory.inventory_snapshot_id
    || goal.inventory_snapshot_id !== inventory.inventory_snapshot_id
    || gate.date !== goal.date
  ) invalid();
  const day = inventory.days.find((candidate) => candidate.date === gate.date);
  if (!day || day.inventory_status !== "complete" || gate.candidates.length !== day.events.length) invalid();
  const events = new Map(day.events.map((event) => [event.event_ref, event]));
  const eligible = new Map();
  for (const row of gate.candidates) {
    if (!events.has(row.event_ref) || eligible.has(row.event_ref)) invalid();
    eligible.set(row.event_ref, row.eligible === true);
  }
  if (eligible.size !== events.size) invalid();

  const free = [];
  const paid = [];
  const skipped = [];
  const sequenceDecisions = new Map();
  const reservedByCurrency = new Map();
  for (const ranked of goal.ranked_events) {
    const event = events.get(ranked.event_ref);
    if (!event) invalid();
    if (!eligible.get(event.event_ref)) {
      skipped.push(Object.freeze({ event_ref: event.event_ref, reason: "calendar_conflict" }));
      continue;
    }
    const decision = authorizeEventSpend({ policy, dateInventory: inventory, eventRef: event.event_ref });
    if (!decision.allowed) {
      skipped.push(Object.freeze({ event_ref: event.event_ref, reason: decision.reason }));
      continue;
    }
    if (decision.payment_mode === "saved") {
      const alreadyReserved = reservedByCurrency.get(decision.currency) || 0;
      if (decision.remaining_after_minor < alreadyReserved) {
        skipped.push(Object.freeze({ event_ref: event.event_ref, reason: "rolling_sequence_cap_exceeded" }));
        continue;
      }
      reservedByCurrency.set(decision.currency, alreadyReserved + decision.amount_minor);
    }
    const row = Object.freeze({
      event_ref: event.event_ref,
      canonical_url: event.canonical_url,
      event_spend_decision_id: decision.event_spend_decision_id,
      payment_mode: decision.payment_mode,
    });
    sequenceDecisions.set(event.event_ref, decision);
    (decision.payment_mode === "none" ? free : paid).push(row);
  }
  const core = {
    event_spend_policy_id: policy.event_spend_policy_id,
    inventory_snapshot_id: inventory.inventory_snapshot_id,
    calendar_gate_id: gate.calendar_gate_id,
    goal_serendipity_id: goal.goal_serendipity_id,
    date: gate.date,
    ordered_candidates: Object.freeze([...free, ...paid]),
    skipped: Object.freeze(skipped),
  };
  const sequence = Object.freeze({
    event_spend_sequence_id: `event-spend-sequence:${digest(stableJson(core))}`,
    ...core,
  });
  SEQUENCES.add(sequence);
  SEQUENCE_DECISIONS.set(sequence, sequenceDecisions);
  return sequence;
}

function isVerifiedEventSpendSequence(value) {
  return Boolean(value && typeof value === "object" && SEQUENCES.has(value));
}

function eventSpendDecisionForSequence(sequence, eventRef) {
  if (!isVerifiedEventSpendSequence(sequence)) invalid();
  const decision = SEQUENCE_DECISIONS.get(sequence).get(String(eventRef));
  if (!isVerifiedEventSpendDecision(decision)) invalid();
  return decision;
}

module.exports = {
  authorizeEventSpend,
  authorizeEventSpendEffect,
  buildEventSpendSequence,
  createEventSpendPolicy,
  inspectSavedLumaPaymentMethod,
  eventSpendDecisionForSequence,
  isVerifiedEventSpendDecision,
  isVerifiedEventSpendPolicy,
  isVerifiedEventSpendSequence,
};
