"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const { buildFunderRegistry } = require("./funder-registry.js");
const { appendFunderRegistryEntries } = require("./funder-registry-store.js");

const SQL = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-02-lm-funder-registry.sql"), "utf8");

function fixtures() {
  return {
    tenantId: "dais-local",
    observedAt: "2026-08-02T00:00:00.000Z",
    portfolio: { version: 1, updated_at: "2026-05-07", funders: [
      { id: "yc-w26", spec: "yc-w26.json", priority: 1 },
      { id: "grant", spec: "grant.json", priority: 2 },
    ] },
    specs: [
      { id: "yc-w26", name: "YC W26", url: "https://apply.ycombinator.com/home", funder_type: "accelerator", verified: true, currency: "USD", amount_range: { min: 125000, max: 500000 }, deadline_kind: "biannual", next_deadline: "2026-09-15", captcha: null, auth: { kind: "session_cookie" } },
      { id: "grant", name: "Builder Grant", url: "https://example.org/grant", funder_type: "grant", verified: false, currency: "USD", amount_range: { min: 50000, max: 100000 }, deadline_kind: "rolling", next_deadline: null, captcha: "recaptcha-v2", auth: { kind: "none" } },
    ],
  };
}

test("legacy entries become ordered stale claims that all require current re-verification", () => {
  const registry = buildFunderRegistry(fixtures());
  assert.equal(registry.entries.length, 2);
  assert.deepEqual(registry.entries.map(({ funder_id }) => funder_id), ["yc-w26", "grant"]);
  assert.equal(registry.entries.every(({ verification_status }) => verification_status === "needs_reverification"), true);
  assert.equal(registry.entries[0].automation_gate, "review_required");
  assert.equal(registry.entries[1].automation_gate, "captcha_blocked");
  assert.equal(registry.entries[0].legacy_claims.fact_status, "stale_claim");
  assert.equal(registry.entries[0].legacy_claims.verified, true);
  assert.match(registry.registry_digest, /^[0-9a-f]{64}$/);
});

test("portfolio/spec mismatch, duplicate priority, unsafe URL, and unknown type fail closed", () => {
  const base = fixtures();
  assert.throws(() => buildFunderRegistry({ ...base, specs: base.specs.slice(0, 1) }), /set/i);
  assert.throws(() => buildFunderRegistry({ ...base, portfolio: { ...base.portfolio, funders: base.portfolio.funders.map((row) => ({ ...row, priority: 1 })) } }), /priority/i);
  assert.throws(() => buildFunderRegistry({ ...base, specs: [{ ...base.specs[0], url: "http://evil.test" }, base.specs[1]] }), /URL/i);
  assert.throws(() => buildFunderRegistry({ ...base, specs: [{ ...base.specs[0], funder_type: "bank" }, base.specs[1]] }), /type/i);
});

test("migration creates append-only tenant registry with service-only RLS", () => {
  assert.match(SQL, /CREATE TABLE IF NOT EXISTS public\.lm_funder_registry_snapshots/i);
  assert.match(SQL, /PRIMARY KEY \(tenant_id, registry_id\)/i);
  assert.match(SQL, /verification_status text NOT NULL CHECK/i);
  assert.match(SQL, /ENABLE ROW LEVEL SECURITY/i);
  assert.match(SQL, /REVOKE ALL .* FROM PUBLIC/i);
  assert.doesNotMatch(SQL, /UPDATE public\.lm_funder_registry_snapshots/i);
});

test("store appends exact revision and never overwrites a prior snapshot", async () => {
  const registry = buildFunderRegistry(fixtures());
  const calls = [];
  const saved = await appendFunderRegistryEntries(registry, { query: async (sql, params) => {
    calls.push({ sql, params });
    return { rows: [{ registry_id: params[1] }] };
  } });
  assert.equal(saved.length, 2);
  assert.equal(calls.every(({ sql }) => /ON CONFLICT \(tenant_id, registry_id\) DO NOTHING/i.test(sql)), true);
  assert.equal(calls.every(({ sql }) => !/UPDATE/i.test(sql)), true);
  assert.equal(calls[0].params[0], "dais-local");
});
