const { test } = require("node:test");
const assert = require("node:assert");
const { getLastTs, upsertInstance } = require("../telemetry-store");

const cfg = { url: "https://x.supabase.co", key: "svc" };

test("getLastTs returns 0 when no row", async () => {
  const f = async () => ({ ok: true, json: async () => [] });
  assert.strictEqual(await getLastTs("0xABC", { ...cfg, f }), 0);
});
test("getLastTs returns the existing ts and queries lowercased id", async () => {
  let calledUrl = "";
  const f = async (u) => { calledUrl = u; return { ok: true, json: async () => [{ ts: 123 }] }; };
  assert.strictEqual(await getLastTs("0xABC", { ...cfg, f }), 123);
  assert.ok(calledUrl.includes("id=eq.0xabc"));
});
test("upsertInstance POSTs a lowercased row with merge-duplicates", async () => {
  let opts = null, url = "";
  const f = async (u, o) => { url = u; opts = o; return { ok: true, text: async () => "" }; };
  await upsertInstance({ id: "0xABC", ts: 5, net_worth_usd: 5 }, { ...cfg, f });
  const sent = JSON.parse(opts.body);
  assert.strictEqual(sent.id, "0xabc");                 // lowercased
  assert.ok(opts.headers.Prefer.includes("merge-duplicates"));
  assert.ok(url.includes("on_conflict=id"));
});
test("upsertInstance throws on a non-ok response", async () => {
  const f = async () => ({ ok: false, status: 409, text: async () => "conflict" });
  await assert.rejects(() => upsertInstance({ id: "0xabc", ts: 1 }, { ...cfg, f }), /supabase 409/);
});
