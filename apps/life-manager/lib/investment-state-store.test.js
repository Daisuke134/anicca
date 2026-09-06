"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { createInvestmentStateStore, normalizeInvestmentState } = require("./investment-state-store.js");

const UID = "tenant-a";
const STATE = Object.freeze({
  uid: UID,
  lifecycle: "in_review",
  deployment: "cloud",
  mode: "paper",
  paused: false,
  killed: false,
  core_digest: "a".repeat(64),
  receipt_refs: ["provider-receipt://alpaca/application/abc"],
  alpaca_api_key_ref: "secret://alpaca/api-key",
  alpaca_api_secret_ref: "secret://alpaca/api-secret",
});

function response(rows, ok = true) {
  return { ok, json: async () => rows };
}

test("missing tenant state truthfully starts at setup_required", async () => {
  const calls = [];
  const store = createInvestmentStateStore({ supaUrl: "https://db.example", supaKey: "service", fetchImpl: async (...args) => {
    calls.push(args); return response([]);
  } });
  assert.deepEqual(await store.read(UID), { lifecycle: "setup_required" });
  assert.match(calls[0][0], /uid=eq\.tenant-a/);
  assert.doesNotMatch(calls[0][0], /tenant-b/);
});

test("read is exactly tenant scoped and accepts only the persisted allowlist", async () => {
  const store = createInvestmentStateStore({ supaUrl: "https://db.example/", supaKey: "service", fetchImpl: async (url) => {
    assert.match(url, /uid=eq\.tenant-a/);
    return response([STATE]);
  } });
  assert.deepEqual(await store.read(UID), STATE);
});

test("cross-tenant or schema-drift rows fail closed", async () => {
  for (const row of [{ ...STATE, uid: "tenant-b" }, { ...STATE, api_secret: "raw" }]) {
    const store = createInvestmentStateStore({ supaUrl: "https://db.example", supaKey: "service", fetchImpl: async () => response([row]) });
    await assert.rejects(store.read(UID), /invalid|unavailable/);
  }
});

test("upsert sends references only and rejects raw credentials before fetch", async () => {
  const calls = [];
  const store = createInvestmentStateStore({ supaUrl: "https://db.example", supaKey: "service", fetchImpl: async (url, options) => {
    assert.match(url, /on_conflict=uid&select=alpaca_api_key_ref,/);
    assert.doesNotMatch(url, /created_at|updated_at/);
    calls.push(options); return response([STATE]);
  } });
  assert.deepEqual(await store.upsert(UID, STATE), STATE);
  const written = JSON.parse(calls[0].body);
  assert.deepEqual(Object.keys(written).sort(), Object.keys(STATE).sort());
  assert.equal(JSON.stringify(written).includes("raw-secret"), false);
  await assert.rejects(store.upsert(UID, { ...STATE, alpaca_api_secret_ref: "raw-secret" }), /invalid/);
  await assert.rejects(store.upsert(UID, { ...STATE, api_key: "raw-secret" }), /invalid/);
  assert.equal(calls.length, 1);
});

test("invalid lifecycle, deployment, mode, refs, and digests fail closed", () => {
  for (const state of [
    { ...STATE, lifecycle: "unknown" }, { ...STATE, deployment: "both" }, { ...STATE, mode: "enabled" },
    { ...STATE, core_digest: "nope" }, { ...STATE, receipt_refs: ["https://example.com/raw"] },
    { ...STATE, alpaca_api_key_ref: "secret://other/api-key" },
  ]) assert.throws(() => normalizeInvestmentState(state, UID), /invalid/);
});

test("migration is service-only and has no raw credential columns", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-09-06-lm-investment-states.sql"), "utf8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_investment_states/i);
  assert.match(sql, /uid text PRIMARY KEY REFERENCES public\.lm_users\(uid\)/i);
  assert.match(sql, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(sql, /REVOKE ALL ON TABLE public\.lm_investment_states FROM PUBLIC/i);
  assert.match(sql, /GRANT SELECT, INSERT, UPDATE ON TABLE public\.lm_investment_states TO service_role/i);
  assert.doesNotMatch(sql, /\b(api_key|api_secret|password|token)\s+(?:text|jsonb|bytea)\b/i);
});
