const { test } = require("node:test");
const assert = require("node:assert");
const store = require("../owners-store");

const cfg = (f) => ({ url: "https://x.supabase.co", key: "svc", f });

test("isEventSeen returns true when a row exists, false when empty", async () => {
  assert.strictEqual(await store.isEventSeen("evt_1", cfg(async () => ({ ok: true, json: async () => [{ event_id: "evt_1" }] }))), true);
  assert.strictEqual(await store.isEventSeen("evt_2", cfg(async () => ({ ok: true, json: async () => [] }))), false);
});

test("markEventSeen POSTs to spawn_events with ignore-duplicates", async () => {
  let captured;
  await store.markEventSeen("evt_9", cfg(async (url, opts) => { captured = { url, opts }; return { ok: true, text: async () => "" }; }));
  assert.ok(captured.url.includes("spawn_events"));
  assert.strictEqual(captured.opts.method, "POST");
  assert.ok(captured.opts.headers.Prefer.includes("ignore-duplicates"));
  assert.strictEqual(JSON.parse(captured.opts.body).event_id, "evt_9");
});

test("upsertOwner POSTs to owners on_conflict=sub_id", async () => {
  let captured;
  await store.upsertOwner({ email: "b@x.io", droplet_id: 7, sub_id: "sub_7", status: "active" },
    cfg(async (url, opts) => { captured = { url, opts }; return { ok: true, text: async () => "" }; }));
  assert.ok(captured.url.includes("on_conflict=sub_id"));
  const row = JSON.parse(captured.opts.body);
  assert.strictEqual(row.sub_id, "sub_7");
  assert.strictEqual(row.droplet_id, 7);
  assert.strictEqual(row.status, "active");
});

test("getOwnerBySub returns the row or null", async () => {
  assert.deepStrictEqual(
    await store.getOwnerBySub("sub_7", cfg(async () => ({ ok: true, json: async () => [{ sub_id: "sub_7", droplet_id: 7 }] }))),
    { sub_id: "sub_7", droplet_id: 7 });
  assert.strictEqual(await store.getOwnerBySub("nope", cfg(async () => ({ ok: true, json: async () => [] }))), null);
});

test("markDestroyed PATCHes status=destroyed for the sub", async () => {
  let captured;
  await store.markDestroyed("sub_7", cfg(async (url, opts) => { captured = { url, opts }; return { ok: true, text: async () => "" }; }));
  assert.strictEqual(captured.opts.method, "PATCH");
  assert.ok(captured.url.includes("sub_id=eq.sub_7"));
  assert.strictEqual(JSON.parse(captured.opts.body).status, "destroyed");
});

test("store ops throw on non-ok supabase response", async () => {
  await assert.rejects(() => store.isEventSeen("e", cfg(async () => ({ ok: false, status: 500, text: async () => "x" }))), /supabase 500/);
});
