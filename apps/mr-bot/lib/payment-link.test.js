"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { paymentLink } = require("./payment-link.js");

test("paymentLink allows only tenant-scoped buy.stripe.com HTTPS", () => {
  assert.equal(
    paymentLink({ stripePaymentLink: "https://buy.stripe.com/test_mr_bot" }, { uid: "tenant-a" }),
    "https://buy.stripe.com/test_mr_bot?client_reference_id=tenant-a",
  );
  assert.equal(paymentLink({ stripePaymentLink: "https://evil.example/pay" }, { uid: "tenant-a" }), "");
  assert.equal(paymentLink({ stripePaymentLink: "https://buy.stripe.com/test" }, {}), "");
});
