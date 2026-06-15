const { test } = require("node:test");
const assert = require("node:assert");
const { Wallet } = require("ethers");
const { canonicalMessage, verifyTelemetry } = require("../telemetry-verify");

const pk = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"; // test key
const w = new Wallet(pk);
const addr = w.address.toLowerCase();

function obj(ts, over = {}) {
  return { id: addr, ts, host: "akash", geo: "US", model_live: "x", model_tier: "free",
    net_worth_usd: 1, revenue_mo_usd: 0, burn_day_usd: 0.1, runway_days: 10, status: "alive", ...over };
}

test("accepts a fresh, correctly-signed, monotonic message", async () => {
  const now = Math.floor(Date.now() / 1000); const msg = canonicalMessage(obj(now));
  const sig = await w.signMessage(msg);
  const r = verifyTelemetry(msg, sig, { now, lastTs: 0 });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.payload.id, addr);
});

test("accepts python-style whole-number floats (5.0 / 0.0) — the prod bug class", async () => {
  const now = Math.floor(Date.now() / 1000);
  // EXACTLY what python json.dumps(...,separators=(',',':')) emits for whole-dollar balances:
  const msg = `{"id":"${addr}","ts":${now},"host":"akash","geo":"US","model_live":"x","model_tier":"free","net_worth_usd":5.0,"revenue_mo_usd":0.0,"burn_day_usd":0,"runway_days":10,"status":"alive"}`;
  const sig = await w.signMessage(msg);
  const r = verifyTelemetry(msg, sig, { now, lastTs: 0 });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.payload.net_worth_usd, 5);
  assert.strictEqual(r.payload.revenue_mo_usd, 0);
});

test("rejects malformed json", () => {
  const r = verifyTelemetry("{not json", "0x00", { now: 1, lastTs: 0 });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "bad_json");
});

test("rejects a schema violation", async () => {
  const msg = JSON.stringify({ id: "nope" });
  const sig = await w.signMessage(msg);
  const r = verifyTelemetry(msg, sig, { now: 1, lastTs: 0 });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "schema");
});

test("rejects a wrong signer", async () => {
  const now = Math.floor(Date.now() / 1000);
  const msg = canonicalMessage(obj(now, { id: "0x000000000000000000000000000000000000dead" }));
  const sig = await w.signMessage(msg); // signed by w, but id claims the dead addr
  const r = verifyTelemetry(msg, sig, { now, lastTs: 0 });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "signer_mismatch");
});

test("rejects a bad signature", () => {
  const now = Math.floor(Date.now() / 1000); const msg = canonicalMessage(obj(now));
  const r = verifyTelemetry(msg, "0xdeadbeef", { now, lastTs: 0 });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "bad_signature");
});

test("rejects a stale ts (>60s old)", async () => {
  const now = Math.floor(Date.now() / 1000); const msg = canonicalMessage(obj(now - 120));
  const sig = await w.signMessage(msg);
  const r = verifyTelemetry(msg, sig, { now, lastTs: 0 });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "stale");
});

test("rejects a replay (ts <= lastTs)", async () => {
  const now = Math.floor(Date.now() / 1000); const msg = canonicalMessage(obj(now));
  const sig = await w.signMessage(msg);
  const r = verifyTelemetry(msg, sig, { now, lastTs: now });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "replay");
});
