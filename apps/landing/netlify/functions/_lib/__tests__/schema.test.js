const { test } = require("node:test");
const assert = require("node:assert");
const { validate } = require("../telemetry-schema");

const valid = { id: "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21", ts: 1781450000, host: "akash",
  geo: "US", model_live: "auto", model_tier: "free", net_worth_usd: 0.0059, revenue_mo_usd: 0,
  burn_day_usd: 0, runway_days: 999, status: "alive" };

test("accepts a valid payload", () => {
  const r = validate(valid);
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.payload.id, valid.id);
});
test("rejects a bad wallet id", () => {
  assert.strictEqual(validate({ ...valid, id: "nope" }).ok, false);
});
test("rejects negative runway", () => {
  assert.strictEqual(validate({ ...valid, runway_days: -1 }).ok, false);
});
test("rejects a bad model_tier", () => {
  assert.strictEqual(validate({ ...valid, model_tier: "gpt" }).ok, false);
});
test("rejects null", () => {
  assert.strictEqual(validate(null).ok, false);
});
