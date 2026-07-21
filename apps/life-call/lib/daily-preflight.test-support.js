"use strict";

// Tests only: production CLI and production modules never import this collector-DI harness.
const { validateEmailProof, validateTelegramProof } = require("./daily-preflight.js");

async function collectControlledL3ForTest({ mode, nowMs, collectors } = {}) {
  if (mode !== "controlled-l3") throw new Error("controlled_mode_required");
  if (!collectors || typeof collectors.telegram !== "function" || typeof collectors.email !== "function") {
    throw new Error("collector_registry_invalid");
  }
  const [telegram, email] = await Promise.all([collectors.telegram(), collectors.email()]);
  return Object.freeze({ telegram: validateTelegramProof(telegram, nowMs), email: validateEmailProof(email, nowMs) });
}

async function collectTelegramControlledForTest({ roundTrip, getWebhookInfo, sleep = () => Promise.resolve(), now = Date.now, maxPolls = 3 } = {}) {
  if (typeof roundTrip !== "function" || typeof getWebhookInfo !== "function") throw new Error("telegram_collector_unavailable");
  const trip = await roundTrip();
  const samples = [];
  let finalInfo;
  for (let index = 0; index < maxPolls; index += 1) {
    finalInfo = await getWebhookInfo();
    samples.push(finalInfo && finalInfo.pending_update_count);
    if (samples.at(-1) === 0) break;
    if (index + 1 < maxPolls) await sleep();
  }
  return {
    attempted: true, verified: trip && trip.verified === true,
    checkedAt: new Date(now()).toISOString(), requestMessageRef: trip && trip.requestMessageRef,
    replyMessageRef: trip && trip.replyMessageRef, exactUrl: finalInfo && finalInfo.exactUrl === true,
    allowedUpdates: finalInfo && finalInfo.allowed_updates,
    providerError: Boolean(finalInfo && finalInfo.providerError),
    pendingUpdateCount: samples.at(-1), pendingUpdateSamples: samples,
  };
}

module.exports = { collectControlledL3ForTest, collectTelegramControlledForTest };
