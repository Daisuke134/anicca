"use strict";

const crypto = require("node:crypto");
const assert = require("node:assert/strict");

function digest(value) {
  const canonical = JSON.stringify(value, (_key, item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return item;
    return Object.fromEntries(Object.keys(item).sort().map((key) => [key, item[key]]));
  });
  return crypto.createHash("sha256").update(canonical).digest("hex");
}

function runParityCore(fixture) {
  const decision = fixture && fixture.no_trade;
  const account = fixture && fixture.observation && fixture.observation.account;
  if (!decision || decision.candidate_ref !== "NO_TRADE" || decision.approved !== false
    || decision.gate !== "model_no_trade" || !account
    || ![decision.reason, decision.observed_at, account.cash, account.equity]
      .every((value) => typeof value === "string" && value.length > 0)) {
    throw new Error("investment parity input invalid");
  }
  const core = { decision: "NO_TRADE",
    report: { cash: account.cash, equity: account.equity, reason: decision.reason },
    risk: { approved: false, effect_permission: "none", gate: "model_no_trade" } };
  const coreDigest = digest(core);
  return Object.freeze({ ...core, core_digest: coreDigest,
    idempotency_key: crypto.createHash("sha256")
      .update(`investment-parity\n${decision.observed_at}\n${coreDigest}`).digest("hex") });
}

function assertLocalCloudParity(actual, expected) {
  try { assert.deepStrictEqual(actual, expected); }
  catch { throw new Error("investment local/cloud parity mismatch"); }
  return actual;
}

module.exports = { runParityCore, assertLocalCloudParity };
