const { test, beforeEach } = require("node:test");
const assert = require("node:assert");
const { Wallet } = require("ethers");
const { canonicalMessage } = require("../telemetry-verify");
const { handler } = require("../../telemetry");

const w = new Wallet("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d");
const addr = w.address.toLowerCase();

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
  return canonicalMessage({ id: addr, ts: now, host: "akash", geo: "US", model_live: "x",
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
