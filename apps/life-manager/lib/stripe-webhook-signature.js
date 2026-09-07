"use strict";

function stripeWebhookSecrets(env = {}) {
  return [...new Set([
    env.STRIPE_WEBHOOK_SECRET,
    env.STRIPE_TEST_WEBHOOK_SECRET,
  ].map((value) => String(value || "").trim()).filter(Boolean))];
}

function stripeWebhookAllowed(env = {}) {
  if (String(env.STRIPE_DEV || "").trim() === "1") return true;
  return stripeWebhookSecrets(env).length > 0;
}

function constructStripeWebhookEvent(raw, signature, env, stripeClient) {
  const secrets = stripeWebhookSecrets(env);
  if (secrets.length === 0) return stripeClient.webhooks.constructEvent(raw, signature, "");
  let lastError;
  for (const secret of secrets) {
    try {
      return stripeClient.webhooks.constructEvent(raw, signature, secret);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}

module.exports = { constructStripeWebhookEvent, stripeWebhookAllowed, stripeWebhookSecrets };
