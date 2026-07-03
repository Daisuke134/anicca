// VCSDD Phase 2a RED — R9: additive fields are type-checked; existing rows still valid.
// FAILS until GREEN extends telemetry-schema.validate.
const { test } = require("node:test");
const assert = require("node:assert");
const { validate } = require("../telemetry-schema");

const ok = () => ({ id: "0x" + "a".repeat(40), ts: 1, host: "h", geo: "US", model_live: "m",
  model_tier: "free", net_worth_usd: 1, revenue_mo_usd: 1, burn_day_usd: 0.1, runway_days: 1, status: "alive" });

test("R9: existing valid row still validates (back-compat)", () => {
  assert.strictEqual(validate(ok()).ok, true);
});
test("R9: non-array tags => ok:false", () => {
  assert.strictEqual(validate({ ...ok(), tags: "nope" }).ok, false);
});
test("R9: revenue_today_usd > revenue_mo_usd => ok:false", () => {
  assert.strictEqual(validate({ ...ok(), revenue_mo_usd: 5, revenue_today_usd: 9 }).ok, false);
});
test("R9: NEGATIVE revenue_by_source value => ok:true (per-source PnL can be a loss — verified against live 2026-07-04, row 0xa3cd… had bluechip:-0.433)", () => {
  assert.strictEqual(validate({ ...ok(), revenue_by_source: { bluechip: -0.433, aave: -0.005, gig: 0.206 } }).ok, true);
});
test("R9: NON-FINITE revenue_by_source value => ok:false (NaN/Infinity still rejected)", () => {
  assert.strictEqual(validate({ ...ok(), revenue_by_source: { gig: Number.NaN } }).ok, false);
  assert.strictEqual(validate({ ...ok(), revenue_by_source: { gig: Number.POSITIVE_INFINITY } }).ok, false);
});
test("R9: revenue_by_source string value => ok:false (type check still enforced)", () => {
  assert.strictEqual(validate({ ...ok(), revenue_by_source: { gig: "1.5" } }).ok, false);
});
test("R9: well-formed additive fields => ok:true", () => {
  assert.strictEqual(validate({ ...ok(), tags: ["agent-hackathon"], revenue_mo_usd: 5, revenue_today_usd: 2, revenue_by_source: { gig: 5 } }).ok, true);
});
