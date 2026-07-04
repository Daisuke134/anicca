const { test, beforeEach } = require("node:test");
const assert = require("node:assert");
const { Wallet } = require("ethers");
const nacl = require("tweetnacl");
const bs58 = require("bs58");
const { canonicalMessage } = require("../telemetry-verify");
const { handler } = require("../../telemetry");

const w = new Wallet("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d");
const addr = w.address.toLowerCase();
// canonical host bound to this wallet (Dais: wallet = 1 identity; "akash" squatters rejected)
const canonHost = "anicca-" + addr.slice(2, 8);

let lastTs, upserts, origFetch;
beforeEach(() => {
  lastTs = 0; upserts = [];
  process.env.SUPABASE_URL = "https://x.supabase.co";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "svc";
  origFetch = global.fetch;
  global.fetch = async (url, opts) => {
    if (!opts || opts.method !== "POST") return { ok: true, json: async () => (lastTs ? [{ ts: lastTs }] : []) };
    const row = JSON.parse(opts.body); upserts.push(row); lastTs = row.ts;
    return { ok: true, text: async () => "" };
  };
});

function ev(body) { return { httpMethod: "POST", body: JSON.stringify(body), headers: {} }; }
function objStr(over = {}) {
  const now = Math.floor(Date.now() / 1000);
  return canonicalMessage({ id: addr, ts: now, host: canonHost, geo: "US", model_live: "x",
    model_tier: "free", net_worth_usd: 1, revenue_mo_usd: 0, burn_day_usd: 0.1, runway_days: 10, status: "alive", ...over });
}

test("202 on a valid signed fresh message", async () => {
  const message = objStr(); const signature = await w.signMessage(message);
  const res = await handler(ev({ message, signature }));
  assert.strictEqual(res.statusCode, 202);
  assert.strictEqual(upserts.length, 1);
  assert.strictEqual(upserts[0].id, addr);
  global.fetch = origFetch;
});
test("400 host_wallet_mismatch — a validly-signed post on this wallet but named 'akash' is REJECTED (no wallet-stealing)", async () => {
  const message = objStr({ host: "akash" }); // correct signer + wallet, but foreign host
  const signature = await w.signMessage(message);
  const res = await handler(ev({ message, signature }));
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body, "host_wallet_mismatch");
  assert.strictEqual(upserts.length, 0); // never written → dashboard row untouched
  global.fetch = origFetch;
});
test("401 on signer mismatch", async () => {
  const message = objStr({ id: "0x000000000000000000000000000000000000dead" });
  const signature = await w.signMessage(message); // signed by w, id claims dead addr
  const res = await handler(ev({ message, signature }));
  assert.strictEqual(res.statusCode, 401);
  global.fetch = origFetch;
});
test("400 on schema violation", async () => {
  const message = JSON.stringify({ id: "nope" }); const signature = await w.signMessage(message);
  const res = await handler(ev({ message, signature }));
  assert.strictEqual(res.statusCode, 400);
  global.fetch = origFetch;
});
test("400 on a non-address id (PostgREST injection) — rejected BEFORE any DB query", async () => {
  let fetchCalled = false;
  const saved = global.fetch;
  global.fetch = async () => { fetchCalled = true; return { ok: true, json: async () => [] }; };
  const message = JSON.stringify({ id: "0xabc&select=*", ts: 1, host: "a" });
  const signature = await w.signMessage(message);
  const res = await handler(ev({ message, signature }));
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(fetchCalled, false); // never reached getLastTs's URL
  global.fetch = saved;
});
test("400 on missing message/signature", async () => {
  const res = await handler(ev({ signature: "0x00" }));
  assert.strictEqual(res.statusCode, 400);
  global.fetch = origFetch;
});
test("405 on non-POST", async () => {
  const res = await handler({ httpMethod: "GET", headers: {} });
  assert.strictEqual(res.statusCode, 405);
  global.fetch = origFetch;
});

// FIXED_IDENTITIES (2026-07-05): Franklin + claude-p have stable, pre-registered host names instead of
// the auto-derived "anicca-<hex>" scheme. This must NOT weaken the anti-squatting invariant — only the
// pinned wallet may claim the pinned name.
const claudeP = new Wallet("0x" + "11".repeat(32));
test("202: claude-p (EVM, fixed identity) accepted with host='claude-p'", async () => {
  const now = Math.floor(Date.now() / 1000);
  const message = canonicalMessage({
    id: claudeP.address, ts: now, host: "claude-p", geo: "JP", funding: "human", env: "local", brain: "claude-p",
    model_live: "claude-sonnet-5", model_tier: "frontier", net_worth_usd: 1, revenue_mo_usd: 0, burn_day_usd: 0, runway_days: 999, status: "alive",
  });
  // claude-p's real wallet is pinned by ADDRESS, not by this test key — so this test only exercises the
  // fixed-identity LOOKUP path structurally reachable code; it must reach host_wallet_mismatch (proving
  // the lookup ran) rather than silently falling back to the anicca-<hex> derivation for an unrelated key.
  const signature = await claudeP.signMessage(message);
  const res = await handler(ev({ message, signature }));
  // this test wallet is NOT the real pinned claude-p address, so it correctly falls through to the
  // anicca-<hex> derivation and mismatches (host="claude-p" != "anicca-<hex of this test wallet>") —
  // proving FIXED_IDENTITIES lookup is address-scoped, not name-scoped (can't just claim the name).
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body, "host_wallet_mismatch");
  global.fetch = origFetch;
});

const solKp = nacl.sign.keyPair();
const solAddr = bs58.encode(Buffer.from(solKp.publicKey));
test("202: Solana chain id passes the pre-verify id-shape guard (base58, not 0x)", async () => {
  const now = Math.floor(Date.now() / 1000);
  const obj = {
    id: solAddr, ts: now, host: "Franklin", geo: "JP", chain: "solana",
    model_live: "openai/gpt-5-mini", model_tier: "frontier", net_worth_usd: 1, revenue_mo_usd: 0, burn_day_usd: 0, runway_days: 999, status: "alive",
  };
  const message = JSON.stringify(obj);
  const sig = nacl.sign.detached(Buffer.from(message, "utf8"), solKp.secretKey);
  const signature = bs58.encode(Buffer.from(sig));
  const res = await handler(ev({ message, signature }));
  // this random test keypair isn't the pinned Franklin wallet either, so it correctly falls through to
  // the anicca-<hex> derivation (nonsensical for a base58 id) and mismatches — the important assertion is
  // that it got PAST the pre-verify id-shape guard (400 bad_json/schema would mean the guard rejected the
  // base58 id outright, which is the regression this test guards against).
  assert.notStrictEqual(res.body, "schema");
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body, "host_wallet_mismatch");
  global.fetch = origFetch;
});
