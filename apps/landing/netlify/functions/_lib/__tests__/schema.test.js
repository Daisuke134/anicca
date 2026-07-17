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

// Sprint-6: multi-chain (chain field, default 'base' back-compat)
test("chain-absent payload behaves exactly as today (regression)", () => {
  const r = validate(valid);
  assert.strictEqual(r.ok, true);
});
test("chain:'base' explicit is equivalent to absent", () => {
  const r = validate({ ...valid, chain: "base" });
  assert.strictEqual(r.ok, true);
});
test("chain:'solana' accepts a valid base58 id", () => {
  const r = validate({ ...valid, chain: "solana", id: "AJ99EemzNHpkdjpMJ9aXfLthvfQYkjSXUjYrQr3853MN" });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.payload.id, "AJ99EemzNHpkdjpMJ9aXfLthvfQYkjSXUjYrQr3853MN");
});
test("chain:'solana' rejects an 0x-style id", () => {
  const r = validate({ ...valid, chain: "solana", id: "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21" });
  assert.strictEqual(r.ok, false);
});
test("chain:'base' (default) rejects a base58 id (unchanged behavior)", () => {
  const r = validate({ ...valid, id: "AJ99EemzNHpkdjpMJ9aXfLthvfQYkjSXUjYrQr3853MN" });
  assert.strictEqual(r.ok, false);
});
test("chain:'polygon' is a known, accepted value (same 0x id shape as base)", () => {
  const r = validate({ ...valid, chain: "polygon" });
  assert.strictEqual(r.ok, true);
});
test("chain:'polygon-proxy' is a known, accepted value (delegate-signed, always unverified by design)", () => {
  const r = validate({ ...valid, chain: "polygon-proxy" });
  assert.strictEqual(r.ok, true);
});
test("rejects an unknown chain value", () => {
  const r = validate({ ...valid, chain: "ethereum" });
  assert.strictEqual(r.ok, false);
});
test("chain:'solana' rejects an id containing base58-excluded chars (0/O/I/l)", () => {
  const r = validate({ ...valid, chain: "solana", id: "0J99EemzNHpkdjpMJ9aXfLthvfQYkjSXUjYrQr3853MN" });
  assert.strictEqual(r.ok, false);
});
