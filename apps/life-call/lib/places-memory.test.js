"use strict";
// PHASE C / PC-1 — per-user location memory (C3 ask→remember). Run: node --test lib/places-memory.test.js
const { test } = require("node:test");
const assert = require("node:assert");
const { placeKey, recallPlace, rememberPlace } = require("./places-memory.js");

// ── placeKey: deterministic normalization (REQ-47) ──────
test("placeKey: lowercase + collapse whitespace + trim", () => {
  assert.strictEqual(placeKey("  Lunch   With  Mai "), "lunch with mai");
  assert.strictEqual(placeKey("おばあちゃんの家"), "おばあちゃんの家");
  assert.strictEqual(placeKey("1on1\twith  X"), "1on1 with x");
});
test("placeKey: empty/null → '' (no key)", () => {
  assert.strictEqual(placeKey(""), "");
  assert.strictEqual(placeKey(null), "");
  assert.strictEqual(placeKey(undefined), "");
});
test("placeKey: same summary with different casing/spacing maps to the SAME key (recurring-event recall)", () => {
  assert.strictEqual(placeKey("Lunch with Mai"), placeKey("lunch  with mai"));
});

// ── recallPlace (REQ-45) ──────
test("recallPlace: row found → its address", async () => {
  const f = async (url) => { assert.match(url, /lm_user_places\?uid=eq\.u1&phrase=eq\./); return { ok: true, json: async () => [{ address: "Shibuya Hikarie" }] }; };
  assert.strictEqual(await recallPlace("u1", "lunch with mai", "http://s", "k", f), "Shibuya Hikarie");
});
test("recallPlace: no row → null", async () => {
  assert.strictEqual(await recallPlace("u1", "lunch with mai", "http://s", "k", async () => ({ ok: true, json: async () => [] })), null);
});
test("recallPlace: missing phrase/uid/creds → null (never queries)", async () => {
  const boom = async () => { throw new Error("should not query"); };
  assert.strictEqual(await recallPlace("u1", "", "http://s", "k", boom), null);
  assert.strictEqual(await recallPlace("", "p", "http://s", "k", boom), null);
  assert.strictEqual(await recallPlace("u1", "p", "", "", boom), null);
});
test("recallPlace: TTL (FIND-002) adds an updated_at filter so stale memory expires; ttlDays=0 disables it", async () => {
  let withTtl, noTtl;
  await recallPlace("u1", "p", "http://s", "k", async (u) => { withTtl = u; return { ok: true, json: async () => [] }; }, 30);
  await recallPlace("u1", "p", "http://s", "k", async (u) => { noTtl = u; return { ok: true, json: async () => [] }; }, 0);
  assert.match(withTtl, /updated_at=gt\./, "ttlDays>0 → recall only fresh memory");
  assert.doesNotMatch(noTtl, /updated_at/, "ttlDays=0 → no time bound");
});

// ── rememberPlace (REQ-46) ──────
test("rememberPlace: upsert (POST merge-duplicates) → true on 201/200/204", async () => {
  const calls = [];
  const f = async (url, opts) => { calls.push({ url, opts }); return { status: 201 }; };
  assert.strictEqual(await rememberPlace("u1", "おばあちゃんの家", "Nerima 1-2-3", "http://s", "k", f), true);
  assert.match(calls[0].url, /lm_user_places/);
  assert.match(calls[0].url, /on_conflict=uid,phrase/); // must target the unique constraint or a 2nd write 409s
  assert.strictEqual(calls[0].opts.method, "POST");
  assert.match(calls[0].opts.headers.Prefer, /merge-duplicates/);
  const body = JSON.parse(calls[0].opts.body);
  assert.strictEqual(body.uid, "u1"); assert.strictEqual(body.phrase, "おばあちゃんの家"); assert.strictEqual(body.address, "Nerima 1-2-3");
});
test("rememberPlace: missing address/phrase/creds → false (no-op)", async () => {
  const boom = async () => { throw new Error("should not write"); };
  assert.strictEqual(await rememberPlace("u1", "p", "", "http://s", "k", boom), false);
  assert.strictEqual(await rememberPlace("u1", "", "addr", "http://s", "k", boom), false);
  assert.strictEqual(await rememberPlace("u1", "p", "addr", "", "", boom), false);
});
