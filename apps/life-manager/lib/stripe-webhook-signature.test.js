"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { constructStripeWebhookEvent, stripeWebhookAllowed, stripeWebhookSecrets } = require("./stripe-webhook-signature.js");

test("accepts a separate test-mode signing secret without replacing live", () => {
  assert.equal(stripeWebhookAllowed({ STRIPE_TEST_WEBHOOK_SECRET: "whsec_test" }), true);
  assert.deepEqual(stripeWebhookSecrets({
    STRIPE_WEBHOOK_SECRET: " whsec_live ",
    STRIPE_TEST_WEBHOOK_SECRET: "whsec_test",
  }), ["whsec_live", "whsec_test"]);

  const attempts = [];
  const event = constructStripeWebhookEvent(
    Buffer.from("payload"),
    "signature",
    { STRIPE_WEBHOOK_SECRET: "whsec_live", STRIPE_TEST_WEBHOOK_SECRET: "whsec_test" },
    { webhooks: { constructEvent(_raw, _signature, secret) {
      attempts.push(secret);
      if (secret === "whsec_test") return { id: "evt_test" };
      throw new Error("signature mismatch");
    } } },
  );
  assert.equal(event.id, "evt_test");
  assert.deepEqual(attempts, ["whsec_live", "whsec_test"]);
});

test("fails closed when every configured secret rejects the signature", () => {
  assert.throws(() => constructStripeWebhookEvent(
    Buffer.from("payload"),
    "signature",
    { STRIPE_WEBHOOK_SECRET: "whsec_live", STRIPE_TEST_WEBHOOK_SECRET: "whsec_test" },
    { webhooks: { constructEvent() { throw new Error("signature mismatch"); } } },
  ), /signature mismatch/);
});
