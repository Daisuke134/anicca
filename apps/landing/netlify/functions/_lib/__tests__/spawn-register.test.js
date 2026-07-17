// VCSDD sprint-2 RED — S9: spawn-boot signed upsert.
// FAILS until _lib/spawn-register.js exists with registerSpawn(...) that:
//   - builds canonicalMessage(payload), signs with the given key, verifies signer==id
//   - stamps last_heartbeat (ISO string) using an injectable clock
//   - calls the injected upsertInstance(f) exactly once with id lowercased
//   - throws (and does NOT call the store) if signer != payload.id
const { test } = require("node:test");
const assert = require("node:assert");
const { Wallet } = require("ethers");
const nacl = require("tweetnacl");
const bs58 = require("bs58");
const { canonicalMessage, verifyTelemetry } = require("../telemetry-verify");

const KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d";
const w = new Wallet(KEY);
const ADDR = w.address.toLowerCase();
const NOW_S = Math.floor(Date.now() / 1000);

function basePayload(over = {}) {
  return {
    id: ADDR, ts: NOW_S, host: "akash", geo: "JP", model_live: "glm-4.7", model_tier: "free",
    net_worth_usd: 1, revenue_mo_usd: 0, burn_day_usd: 0.1, runway_days: 10, status: "alive",
    // include every additive signed field so the byte-identity contract is fully exercised:
    tags: ["agent-hackathon"],
    revenue_today_usd: 0,
    revenue_by_source: { gig: 0 },
    log_feed: [{ ts: NOW_S, line: "spawn boot" }],
    ...over,
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

test("S9.1: builds canonicalMessage byte-identical to canonicalMessage(payload) INCLUDING all additive fields (log_feed etc.), signs, verifies OK, returns {message,signature,last_heartbeat}", async () => {
  const { registerSpawn } = require("../spawn-register");
  const p = basePayload();
  const stub = makeStoreStub();
  const iso = new Date(NOW_S * 1000).toISOString();
  const result = await registerSpawn({ privateKey: KEY, payload: p, storeDeps: stub.deps, now: () => iso });
  // byte-identity — must cover tags, revenue_today_usd, revenue_by_source, log_feed
  assert.strictEqual(result.message, canonicalMessage(p));
  const v = verifyTelemetry(result.message, result.signature, { now: NOW_S, lastTs: 0 });
  assert.strictEqual(v.ok, true, `verify must pass, got: ${v.reason}`);
  // return shape
  assert.strictEqual(result.last_heartbeat, iso);
  assert.ok(typeof result.signature === "string" && result.signature.startsWith("0x"));
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

test("S9.2: throws with 'signer' + both address strings and does NOT upload on signer/id mismatch (assertion binds to the invariant, not to any random error)", async () => {
  const { registerSpawn } = require("../spawn-register");
  const wrongId = "0x0000000000000000000000000000000000000001";
  const p = basePayload({ id: wrongId });
  const stub = makeStoreStub();
  await assert.rejects(
    registerSpawn({ privateKey: KEY, payload: p, storeDeps: stub.deps, now: () => new Date().toISOString() }),
    (err) => {
      // must be an Error whose message names the invariant AND both addresses
      assert.ok(err instanceof Error, `expected Error, got ${typeof err}`);
      assert.match(err.message, /signer/, `message must contain literal 'signer', got: ${err.message}`);
      assert.ok(err.message.includes(wrongId), `message must reference the mismatched payload.id ${wrongId}`);
      // signer is the address derived from KEY (case-insensitive substring)
      assert.match(err.message.toLowerCase(), new RegExp(ADDR.slice(2, 10)), `message must include recovered signer address`);
      return true;
    },
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

test("S2-IMPL-FIND-002: rejects malformed additive fields (tags[0] is number) BEFORE touching the store", async () => {
  const { registerSpawn } = require("../spawn-register");
  const p = basePayload({ tags: [123] }); // schema requires strings
  const stub = makeStoreStub();
  await assert.rejects(
    registerSpawn({ privateKey: KEY, payload: p, storeDeps: stub.deps, now: () => new Date().toISOString() }),
    /verifyTelemetry|schema/i,
  );
  assert.strictEqual(stub.calls.length, 0);
});
test("S2-IMPL-FIND-002: rejects revenue_today_usd > revenue_mo_usd BEFORE touching the store", async () => {
  const { registerSpawn } = require("../spawn-register");
  const p = basePayload({ revenue_mo_usd: 5, revenue_today_usd: 9 });
  const stub = makeStoreStub();
  await assert.rejects(
    registerSpawn({ privateKey: KEY, payload: p, storeDeps: stub.deps, now: () => new Date().toISOString() }),
    /verifyTelemetry|schema/i,
  );
  assert.strictEqual(stub.calls.length, 0);
});

// Sprint-6: multi-chain — solana registerSpawn (chain param, ed25519 signer, id NEVER lowercased)
const solKeypair = nacl.sign.keyPair();
const SOL_ADDR = bs58.encode(Buffer.from(solKeypair.publicKey));
const SOL_SECRET_B58 = bs58.encode(Buffer.from(solKeypair.secretKey));

function solPayload(over = {}) {
  return {
    id: SOL_ADDR, chain: "solana", ts: NOW_S, host: "akash", geo: "JP", model_live: "glm-4.7",
    model_tier: "free", net_worth_usd: 1, revenue_mo_usd: 0, burn_day_usd: 0.1, runway_days: 10,
    status: "alive", ...over,
  };
}

test("S6.3: solana registerSpawn signs via ed25519 and verifies OK", async () => {
  const { registerSpawn } = require("../spawn-register");
  const p = solPayload();
  const stub = makeStoreStub();
  const iso = new Date(NOW_S * 1000).toISOString();
  const result = await registerSpawn({ chain: "solana", privateKey: SOL_SECRET_B58, payload: p, storeDeps: stub.deps, now: () => iso });
  assert.strictEqual(result.message, canonicalMessage(p));
  const v = verifyTelemetry(result.message, result.signature, { now: NOW_S, lastTs: 0 });
  assert.strictEqual(v.ok, true, `verify must pass, got: ${v.reason}`);
});

test("S6.3: solana registerSpawn does NOT lowercase the id in the stored row (regression guard)", async () => {
  const { registerSpawn } = require("../spawn-register");
  const p = solPayload();
  const stub = makeStoreStub();
  await registerSpawn({ chain: "solana", privateKey: SOL_SECRET_B58, payload: p, storeDeps: stub.deps, now: () => new Date().toISOString() });
  assert.strictEqual(stub.calls.length, 1);
  assert.strictEqual(stub.calls[0].id, SOL_ADDR); // exact case, not .toLowerCase()
});

test("S6.3: solana registerSpawn rejects a claimed id that doesn't match the signing key", async () => {
  const { registerSpawn } = require("../spawn-register");
  const otherKeypair = nacl.sign.keyPair();
  const wrongId = bs58.encode(Buffer.from(otherKeypair.publicKey));
  const p = solPayload({ id: wrongId });
  const stub = makeStoreStub();
  await assert.rejects(
    registerSpawn({ chain: "solana", privateKey: SOL_SECRET_B58, payload: p, storeDeps: stub.deps, now: () => new Date().toISOString() }),
  );
  assert.strictEqual(stub.calls.length, 0);
});
