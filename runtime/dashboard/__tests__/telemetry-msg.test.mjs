// Tests the REAL telemetry message builder (telemetry-msg.mjs) the poster uses — shape + key-safety
// (REQ-12) on the actual artifact, not a replica (resolves FIND-009). Pure module = no network on import.
// Run: node --test runtime/dashboard/__tests__/telemetry-msg.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildTelemetryMsg, MSG_KEYS } from "../telemetry-msg.mjs";

const FAKE_PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";

function inputs(extra = {}) {
  return {
    id: "0xA3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21", ts: 1782700000, host: "anicca-a3cdd4", geo: "JP",
    funding: "human", env: "local", brain: "proxy", model_live: "free/glm-4.7", model_tier: "free",
    net_worth_usd: 15.37, daily_revenue_usd: 0, monthly_revenue_usd: -0.7, revenue_by_source: { yield: -0.7 },
    burn_day_usd: 0, runway_days: 999, status: "alive", breakdown: { liquid: 15.37 },
    log: [{ ts: 1, kind: "narrate", note: "" }], ...extra,
  };
}

test("buildTelemetryMsg: lowercases id, carries funding/env/brain, mirrors revenue_mo_usd", () => {
  const { obj } = buildTelemetryMsg(inputs());
  assert.equal(obj.id, "0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21"); // lowercased
  assert.equal(obj.funding, "human"); assert.equal(obj.env, "local"); assert.equal(obj.brain, "proxy");
  assert.equal(obj.revenue_mo_usd, obj.monthly_revenue_usd); // back-compat mirror
  assert.deepEqual(obj.log, [{ ts: 1, kind: "narrate", note: "" }]);
});

test("buildTelemetryMsg: key-set is EXACTLY the fixed allowlist (no secret-bearing key)", () => {
  const { obj, msg } = buildTelemetryMsg(inputs());
  assert.deepEqual(Object.keys(obj).sort(), [...MSG_KEYS].sort());
  // even if a private key were passed in as an extra field, it must not appear in the output
  const { msg: msg2 } = buildTelemetryMsg(inputs({ privateKey: FAKE_PK, secret: "x" }));
  assert.ok(!msg2.includes(FAKE_PK), "private key must never reach the signed message");
  assert.ok(!msg2.includes('"secret"'), "stray secret key must not pass through");
  assert.ok(!msg.includes(FAKE_PK));
});

test("buildTelemetryMsg: defaults (status/runway/geo) when omitted", () => {
  const { obj } = buildTelemetryMsg(inputs({ status: undefined, runway_days: undefined, geo: undefined }));
  assert.equal(obj.status, "alive"); assert.equal(obj.runway_days, 999); assert.equal(obj.geo, "JP");
});
