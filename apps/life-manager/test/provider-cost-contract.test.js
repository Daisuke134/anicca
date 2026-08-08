"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

function loadLedger() {
  const file = require.resolve("../lib/ledger.js");
  delete require.cache[file];
  return require(file);
}

const BASE = {
  provider: "google_maps",
  sku: "geocoding",
  operation: "address_lookup",
  uid: "u1",
  requestId: "req-1",
  quantity: 1,
  unit: "request",
  pricingVersion: "maps-2026-01",
  estimatedUsd: 0.005,
  metadata: { source: "travel" },
};

test("provider cost migration adds complete dimensions and separate actual status/classification", () => {
  const sql = fs.readFileSync(path.join(__dirname, "../migrations/2026-08-08-lm-provider-cost.sql"), "utf8").toLowerCase();
  for (const field of ["provider", "sku", "operation", "request_id", "pricing_version", "estimated_usd", "actual_billed_usd", "actual_status"]) {
    assert.match(sql, new RegExp(`add column if not exists ${field}`));
  }
  assert.match(sql, /actual_status/);
  assert.match(sql, /cost_classification/);
  assert.match(sql, /actual_status[^;]+known/);
  assert.match(sql, /lm_provider_cost_failures/);
  assert.match(sql, /add column if not exists metadata/);
});

test("voice reservation identity is wired through scheduler, bridge, webhook, and import paths", () => {
  const server = fs.readFileSync(path.join(__dirname, "../server.js"), "utf8");
  const scheduler = fs.readFileSync(path.join(__dirname, "../scheduler.js"), "utf8");
  const imports = fs.readFileSync(path.join(__dirname, "../lib/provider-cost-imports.js"), "utf8");
  assert.match(scheduler, /reservationRequestId/);
  assert.match(server, /reservationRequestId/);
  assert.match(server, /legacyKind:\s*["']telnyx_call["']/);
  assert.match(imports, /reservationRequestId/);
});

test("recordProviderCost records all dimensions and known actual billing", async () => {
  const calls = [];
  const ok = await loadLedger().recordProviderCost({
    ...BASE,
    actualBilledUsd: 0.0042,
    actualStatus: "known",
    costClassification: "measured",
  }, {
    supaUrl: "https://db.example", supaKey: "service",
    fetchImpl: async (...args) => { calls.push(args); return { ok: true, status: 201 }; },
  });
  assert.equal(ok, true);
  assert.equal(calls.length, 1);
  const body = JSON.parse(calls[0][1].body);
  assert.deepEqual(body, {
    uid: "u1",
    provider: "google_maps",
    sku: "geocoding",
    operation: "address_lookup",
    request_id: "req-1",
    quantity: 1,
    unit: "request",
    pricing_version: "maps-2026-01",
    estimated_usd: 0.005,
    actual_billed_usd: 0.0042,
    actual_status: "known",
    cost_classification: "measured",
    est_usd: 0.005,
    metadata: { source: "travel" },
  });
});

test("a new Telnyx 60-second row preserves legacy summary dimensions alongside provider fields", async () => {
  const calls = [];
  const ok = await loadLedger().recordProviderCost({
    provider: "telnyx", sku: "voice", operation: "call_cdr", uid: "u1", requestId: "cdr-summary-1",
    quantity: 60, unit: "seconds", pricingVersion: "telnyx-cdr-test-1", estimatedUsd: null,
    actualBilledUsd: 0.02, actualStatus: "known", costClassification: "measured",
    metadata: { reservationRequestId: "call-reservation-1" },
    legacyKind: "telnyx_call", legacyMeta: { kind: "telnyx_call", reservationRequestId: "call-reservation-1" },
  }, {
    supaUrl: "https://db.example", supaKey: "service",
    fetchImpl: async (...args) => { calls.push(args); return { ok: true, status: 201 }; },
  });
  assert.equal(ok, true);
  const body = JSON.parse(calls[0][1].body);
  assert.equal(body.provider, "telnyx");
  assert.equal(body.operation, "call_cdr");
  assert.equal(body.kind, "telnyx_call");
  assert.equal(body.meta.reservationRequestId, "call-reservation-1");
  const summary = loadLedger().businessSummary(1, [{
    ts: new Date().toISOString(), uid: body.uid, kind: body.kind, quantity: body.quantity, est_usd: body.est_usd,
    provider: body.provider, operation: body.operation,
  }], Date.now());
  assert.equal(summary.calls, 1);
  assert.equal(summary.call_minutes, 1);
});

test("missing provider billing is stored as null/unknown and never coerced to zero", async () => {
  const calls = [];
  const ok = await loadLedger().recordProviderCost({ ...BASE, requestId: "req-unknown" }, {
    supaUrl: "https://db.example", supaKey: "service",
    fetchImpl: async (...args) => { calls.push(args); return { ok: true, status: 201 }; },
  });
  assert.equal(ok, true);
  const body = JSON.parse(calls[0][1].body);
  assert.equal(body.actual_status, "unknown");
  assert.equal(body.cost_classification, "estimated");
  assert.equal(body.actual_billed_usd, null);
  assert.notEqual(body.actual_billed_usd, 0);
  assert.equal(body.estimated_usd, BASE.estimatedUsd);
});

test("invalid actual status or dimensions fail closed without a provider write", async () => {
  let calls = 0;
  const deps = {
    supaUrl: "https://db.example", supaKey: "service",
    fetchImpl: async () => { calls += 1; return { ok: true, status: 201 }; },
  };
  assert.equal(await loadLedger().recordProviderCost({ ...BASE, actualStatus: "fake" }, deps), false);
  assert.equal(await loadLedger().recordProviderCost({ ...BASE, actualStatus: "measured", actualBilledUsd: 0.1 }, deps), false);
  assert.equal(await loadLedger().recordProviderCost({ ...BASE, quantity: -1 }, deps), false);
  assert.equal(await loadLedger().recordProviderCost({ ...BASE, actualStatus: "known" }, deps), false);
  assert.equal(calls, 0);
});

test("ledger write failure emits a structured owner alert/outbox record and returns false", async () => {
  const alerts = [];
  const outbox = [];
  const ok = await loadLedger().recordProviderCost(BASE, {
    supaUrl: "https://db.example", supaKey: "service",
    fetchImpl: async () => ({ ok: false, status: 503 }),
    ownerAlert: async (event) => alerts.push(event),
    outboxStore: { insert: async (event) => { outbox.push(event); return true; } },
    log: () => {},
  });
  assert.equal(ok, false);
  assert.equal(alerts.length, 1);
  assert.equal(outbox.length, 1);
  assert.equal(alerts[0].kind, "provider_cost_ledger_write_failed");
  assert.equal(alerts[0].requestId, "req-1");
  assert.equal(outbox[0].provider, "google_maps");
  assert.equal(outbox[0].error.status, 503);
});
