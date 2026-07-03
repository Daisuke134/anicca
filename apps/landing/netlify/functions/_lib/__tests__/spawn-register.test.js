// VCSDD sprint-2 RED — S9: spawn-boot signed upsert.
// FAILS until _lib/spawn-register.js exists with registerSpawn(...) that:
//   - builds canonicalMessage(payload), signs with the given key, verifies signer==id
//   - stamps last_heartbeat (ISO string) using an injectable clock
//   - calls the injected upsertInstance(f) exactly once with id lowercased
//   - throws (and does NOT call the store) if signer != payload.id
const { test } = require("node:test");
const assert = require("node:assert");
const { Wallet } = require("ethers");
const { canonicalMessage, verifyTelemetry } = require("../telemetry-verify");

const KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d";
const w = new Wallet(KEY);
const ADDR = w.address.toLowerCase();
const NOW_S = Math.floor(Date.now() / 1000);

function basePayload(over = {}) {
  return {
    id: ADDR, ts: NOW_S, host: "akash", geo: "JP", model_live: "glm-4.7", model_tier: "free",
    net_worth_usd: 1, revenue_mo_usd: 0, burn_day_usd: 0.1, runway_days: 10, status: "alive",
    tags: ["agent-hackathon"], ...over,
  };
}

function makeStoreStub() {
  const calls = [];
  return {
    calls,
    deps: {
      url: "https://x.supabase.co",
      key: "svc",
      f: async (_u, opts) => { if (opts && opts.method === "POST") calls.push(JSON.parse(opts.body)); return { ok: true, text: async () => "" }; },
    },
  };
}

test("S9.1: builds canonicalMessage byte-identical to canonicalMessage(payload), signs, verifies OK", async () => {
  const { registerSpawn } = require("../spawn-register");
  const p = basePayload();
  const stub = makeStoreStub();
  const clock = () => new Date(NOW_S * 1000).toISOString();
  const result = await registerSpawn({ privateKey: KEY, payload: p, storeDeps: stub.deps, now: clock });
  assert.strictEqual(result.message, canonicalMessage(p));
  const v = verifyTelemetry(result.message, result.signature, { now: NOW_S, lastTs: 0 });
  assert.strictEqual(v.ok, true, `verify must pass, got: ${v.reason}`);
});

test("S9.1: calls upsertInstance exactly once with id lowercased", async () => {
  const { registerSpawn } = require("../spawn-register");
  const upperId = "0x" + ADDR.slice(2).toUpperCase();
  const p = basePayload({ id: upperId });
  const stub = makeStoreStub();
  await registerSpawn({ privateKey: KEY, payload: p, storeDeps: stub.deps, now: () => new Date().toISOString() });
  assert.strictEqual(stub.calls.length, 1);
  assert.strictEqual(stub.calls[0].id, ADDR); // lowercased
});

test("S9.2: throws and does NOT upload when payload.id != signer address", async () => {
  const { registerSpawn } = require("../spawn-register");
  const p = basePayload({ id: "0x0000000000000000000000000000000000000001" });
  const stub = makeStoreStub();
  await assert.rejects(
    registerSpawn({ privateKey: KEY, payload: p, storeDeps: stub.deps, now: () => new Date().toISOString() }),
    /signer|mismatch|id/i,
  );
  assert.strictEqual(stub.calls.length, 0, "must not touch the store on signer mismatch");
});

test("S9.3: stamps last_heartbeat ISO string in the upsert body", async () => {
  const { registerSpawn } = require("../spawn-register");
  const p = basePayload();
  const stub = makeStoreStub();
  const iso = "2026-07-04T10:00:00.000Z";
  await registerSpawn({ privateKey: KEY, payload: p, storeDeps: stub.deps, now: () => iso });
  assert.strictEqual(stub.calls[0].last_heartbeat, iso);
  assert.ok(!Number.isNaN(Date.parse(stub.calls[0].last_heartbeat)));
});
