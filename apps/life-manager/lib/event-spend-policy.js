"use strict";

const EVENT_REF = /^[a-z][a-z0-9+.-]*:\/\/[^\s]{3,500}$/i;
const POLICY_REF = /^spend-policy:\/\/[a-z0-9._/-]{3,200}$/i;
const PAYMENT_REF = /^payment-method:\/\/vault\/[a-z0-9._-]{3,200}$/i;

function validMoney(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function planEventSpending(input = {}) {
  if (!Array.isArray(input.candidates)) throw new Error("event spending candidates invalid");
  const seen = new Set();
  const candidates = input.candidates.map((candidate) => {
    const eventRef = String(candidate && candidate.event_ref || "").trim();
    const currency = String(candidate && candidate.currency || "").trim();
    if (!EVENT_REF.test(eventRef) || seen.has(eventRef) || !validMoney(candidate && candidate.price_minor) || !/^[A-Z]{3}$/.test(currency)) {
      throw new Error("event spending candidate invalid");
    }
    seen.add(eventRef);
    return Object.freeze({ event_ref: eventRef, price_minor: candidate.price_minor, currency });
  });
  const ordered = candidates.filter(({ price_minor: price }) => price === 0)
    .concat(candidates.filter(({ price_minor: price }) => price > 0));

  const policy = input.policy && typeof input.policy === "object" ? input.policy : {};
  const policyRef = String(policy.policy_ref || "").trim();
  const paymentRef = String(policy.payment_method_ref || "").trim();
  const policyCurrency = String(policy.currency || "").trim();
  const monetaryPolicyValid = validMoney(policy.per_event_limit_minor)
    && validMoney(policy.rolling_limit_minor)
    && validMoney(policy.rolling_spent_minor)
    && policy.rolling_spent_minor <= policy.rolling_limit_minor;
  if (policy.enabled === true && !monetaryPolicyValid) throw new Error("event spending policy invalid");
  let authorizedSpend = 0;
  const decisions = [];
  for (const candidate of ordered) {
    if (candidate.price_minor === 0) {
      decisions.push(Object.freeze({
        event_ref: candidate.event_ref,
        action: "register_free",
        price_minor: 0,
        currency: candidate.currency,
        approval_required: false,
      }));
      continue;
    }
    let reason = "";
    if (policy.enabled !== true || !POLICY_REF.test(policyRef)) reason = "policy_unavailable";
    else if (!PAYMENT_REF.test(paymentRef)) reason = "saved_payment_unavailable";
    else if (candidate.currency !== policyCurrency) reason = "currency_mismatch";
    else if (candidate.price_minor > policy.per_event_limit_minor) reason = "per_event_limit_exceeded";
    else if (policy.rolling_spent_minor + authorizedSpend + candidate.price_minor > policy.rolling_limit_minor) reason = "rolling_limit_exceeded";
    if (reason) {
      decisions.push(Object.freeze({
        event_ref: candidate.event_ref,
        action: "skip_policy",
        price_minor: candidate.price_minor,
        currency: candidate.currency,
        reason,
        approval_required: false,
      }));
      continue;
    }
    authorizedSpend += candidate.price_minor;
    decisions.push(Object.freeze({
      event_ref: candidate.event_ref,
      action: "purchase_with_saved_method",
      price_minor: candidate.price_minor,
      currency: candidate.currency,
      policy_ref: policyRef,
      payment_method_ref: paymentRef,
      approval_required: false,
    }));
  }
  const remaining = monetaryPolicyValid
    ? policy.rolling_limit_minor - policy.rolling_spent_minor - authorizedSpend
    : null;
  return Object.freeze({
    schema_version: 1,
    decisions: Object.freeze(decisions),
    authorized_spend_minor: authorizedSpend,
    rolling_remaining_minor: remaining,
  });
}

module.exports = { planEventSpending };
