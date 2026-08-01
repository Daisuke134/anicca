"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { planEventSpending } = require("./event-spend-policy.js");

const policy = {
  policy_ref: "spend-policy://dais-local/events-v1",
  payment_method_ref: "payment-method://vault/events-primary",
  enabled: true,
  currency: "JPY",
  per_event_limit_minor: 300000,
  rolling_limit_minor: 500000,
  rolling_spent_minor: 100000,
};

function event(slug, price) {
  return { event_ref: `luma-event://event/${slug}`, price_minor: price, currency: "JPY" };
}

test("free events move ahead while relative priority stays stable", () => {
  const result = planEventSpending({
    policy,
    candidates: [event("paid-a", 100000), event("free-a", 0), event("paid-b", 50000), event("free-b", 0)],
  });
  assert.deepEqual(result.decisions.map(({ event_ref }) => event_ref), [
    "luma-event://event/free-a", "luma-event://event/free-b",
    "luma-event://event/paid-a", "luma-event://event/paid-b",
  ]);
  assert.deepEqual(result.decisions.slice(0, 2).map(({ action }) => action), ["register_free", "register_free"]);
});

test("paid event inside saved policy is autonomous and never asks per-event approval", () => {
  const result = planEventSpending({ policy, candidates: [event("paid", 250000)] });
  assert.deepEqual(result.decisions[0], {
    event_ref: "luma-event://event/paid",
    action: "purchase_with_saved_method",
    price_minor: 250000,
    currency: "JPY",
    policy_ref: policy.policy_ref,
    payment_method_ref: policy.payment_method_ref,
    approval_required: false,
  });
});

test("per-event and rolling limits block automatically without requesting approval", () => {
  const result = planEventSpending({
    policy,
    candidates: [event("per-event-high", 350000), event("within", 250000), event("rolling-high", 200000)],
  });
  assert.deepEqual(result.decisions.map(({ action }) => action), [
    "skip_policy", "purchase_with_saved_method", "skip_policy",
  ]);
  assert.deepEqual(result.decisions.filter(({ action }) => action === "skip_policy").map(({ approval_required }) => approval_required), [false, false]);
  assert.equal(result.authorized_spend_minor, 250000);
  assert.equal(result.rolling_remaining_minor, 150000);
});

test("missing saved method, disabled policy, and currency mismatch fail closed", () => {
  for (const changed of [
    { ...policy, payment_method_ref: "" },
    { ...policy, enabled: false },
  ]) {
    const result = planEventSpending({ policy: changed, candidates: [event("paid", 1000)] });
    assert.equal(result.decisions[0].action, "skip_policy");
    assert.equal(result.decisions[0].approval_required, false);
  }
  const mismatch = planEventSpending({ policy, candidates: [{ ...event("usd", 1000), currency: "USD" }] });
  assert.equal(mismatch.decisions[0].reason, "currency_mismatch");
});
