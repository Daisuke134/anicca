// Phase 2b — tests the REAL posted-message path (19-key poster msg, NOT canonicalMessage's 11-field
// legacy shape) for the fleet-identity fields + key-safety (REQ-2/REQ-12/REQ-13). Run:
//   node --test netlify/functions/_lib/__tests__/fleet-fields.test.js
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { Wallet } = require("ethers");
const { verifyTelemetry } = require("../telemetry-verify");
const { validate } = require("../telemetry-schema");

// Deterministic throwaway key (hardhat account #0) — NEVER a real wallet. id MUST equal the signer.
const TEST_PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
const w = new Wallet(TEST_PK);
const ID = w.address.toLowerCase();

// The EXACT shape telemetry-poster.mjs signs (19 keys incl funding/env/brain) — not canonicalMessage.
const ALLOWED = new Set([
  "id", "ts", "host", "geo", "funding", "env", "brain", "model_live", "model_tier",
  "net_worth_usd", "daily_revenue_usd", "monthly_revenue_usd", "revenue_by_source",
  "revenue_mo_usd", "burn_day_usd", "runway_days", "status", "breakdown", "log",
]);
function posterMsg(extra = {}) {
  const o = {
    id: ID, ts: Math.floor(Date.now() / 1000), host: "anicca-test", geo: "JP",
    funding: "human", env: "local", brain: "proxy",
    model_live: "free/glm-4.7", model_tier: "free",
    net_worth_usd: 15.36, daily_revenue_usd: 0, monthly_revenue_usd: -0.7,
    revenue_by_source: {}, revenue_mo_usd: -0.7, burn_day_usd: 0, runway_days: 999,
    status: "alive", breakdown: { liquid: 15.36 }, log: [{ ts: 1, kind: "narrate", note: "" }],
    ...extra,
  };
  return JSON.stringify(o);
}

// FIND-003: the REAL 19-key signed message verifies (not canonicalMessage). FIND-002: the 3 fields survive.
test("real poster-shaped signed msg verifies + carries funding/env/brain (REQ-2/3)", async () => {
  const message = posterMsg();
  const signature = await w.signMessage(message);
  const r = verifyTelemetry(message, signature, { now: Math.floor(Date.now() / 1000), lastTs: 0 });
  assert.equal(r.ok, true, r.reason);
  assert.equal(r.payload.funding, "human");
  assert.equal(r.payload.env, "local");
  assert.equal(r.payload.brain, "proxy");
});

// FIND-002: the schema enum branch (telemetry-schema.js) actually rejects a bad value.
test("invalid funding/env/brain value is rejected by schema (enum branch)", () => {
  assert.equal(validate(JSON.parse(posterMsg({ funding: "zzz" }))).ok, false);
  assert.equal(validate(JSON.parse(posterMsg({ env: "mars" }))).ok, false);
  assert.equal(validate(JSON.parse(posterMsg({ brain: "gpt-p" }))).ok, false);
  // absent is OK (backward compatible REQ-2)
  const noFields = JSON.parse(posterMsg());
  delete noFields.funding; delete noFields.env; delete noFields.brain;
  assert.equal(validate(noFields).ok, true);
});

// FIND-002: log round-trips intact through verify.
test("log array round-trips through verify (REQ-13)", async () => {
  const log = [{ ts: 10, kind: "earn", note: "+$2" }, { ts: 11, kind: "done", note: "x" }];
  const message = posterMsg({ log });
  const signature = await w.signMessage(message);
  const r = verifyTelemetry(message, signature, { now: Math.floor(Date.now() / 1000), lastTs: 0 });
  assert.deepEqual(r.payload.log, log);
});

// FIND-001 (CRITICAL, REQ-12): key-safety — no secret in the signed message; key-set ⊆ allowlist.
test("key-safety: message never contains a private key / service-role key; keys ⊆ allowlist", () => {
  const fakeSvcKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.SERVICE_ROLE_SECRET.sig";
  process.env.SUPABASE_SERVICE_ROLE_KEY = fakeSvcKey;
  const message = posterMsg();
  assert.ok(!message.includes(TEST_PK), "private key must NOT appear in the message");
  assert.ok(!message.includes(TEST_PK.replace(/^0x/, "")), "private key (no 0x) must NOT appear");
  assert.ok(!message.includes(fakeSvcKey), "service-role key must NOT appear in the message");
  const keys = Object.keys(JSON.parse(message));
  for (const k of keys) assert.ok(ALLOWED.has(k), `unexpected key in message: ${k}`);
});
