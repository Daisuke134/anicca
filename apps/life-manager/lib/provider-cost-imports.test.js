"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  importTelnyxCdrs,
  importRailwayAllocations,
  importSupabaseAllocations,
  importScheduledMeasurements,
  runScheduledProviderCostImports,
} = require("./provider-cost-imports.js");
const { recordProviderCost } = require("./ledger.js");

function recorder() {
  const events = [];
  return {
    events,
    deps: { recordProviderCost: async (event) => { events.push(event); return true; } },
  };
}

test("Telnyx CDR import stores measured cost and keeps a missing CDR amount unknown", async () => {
  const r = recorder();
  const result = await importTelnyxCdrs([
    { id: "cdr-1", call_control_id: "cc-1", billed_duration: 90, cost: { amount: "0.037", currency: "USD" } },
    { id: "cdr-2", call_control_id: "cc-2", billed_duration: 30 },
  ], { uid: "u1", ...r.deps });
  assert.deepEqual(result, { attempted: 2, recorded: 2, failed: 0 });
  assert.equal(r.events[0].actualStatus, "known");
  assert.equal(r.events[0].actualBilledUsd, 0.037);
  assert.equal(r.events[1].actualStatus, "unknown");
  assert.equal(r.events[1].actualBilledUsd, null);
});

test("Telnyx import propagates a row reservation id to the CDR settlement event", async () => {
  const r = recorder();
  await importTelnyxCdrs([
    { id: "cdr-reservation", call_control_id: "cc-reservation", billed_duration: 60,
      reservation_request_id: "call-reservation-1", cost: { amount: "0.02", currency: "USD" } },
  ], { uid: "u1", ...r.deps });
  assert.equal(r.events[0].metadata.reservationRequestId, "call-reservation-1");
});

test("Railway and Supabase allocation imports preserve owner measurements", async () => {
  const r = recorder();
  await importRailwayAllocations([{ period: "2026-08-08", amount_usd: "1.25" }], { uid: "u1", ...r.deps });
  await importSupabaseAllocations([{ period_key: "2026-08-08", amount_usd: "0.40" }], { uid: "u1", ...r.deps });
  assert.deepEqual(r.events.map((event) => [event.provider, event.actualBilledUsd]), [
    ["railway", 1.25], ["supabase", 0.4],
  ]);
  assert.ok(r.events.every((event) => event.actualStatus === "known"));
});

test("a failed scheduled measurement import returns failure and emits no synthetic zero row", async () => {
  const r = recorder();
  const result = await importScheduledMeasurements("railway", async () => { throw new Error("usage API down"); }, {
    uid: "u1", ...r.deps,
  });
  assert.equal(result.attempted, 0);
  assert.equal(result.recorded, 0);
  assert.equal(result.failed, 1);
  assert.equal(r.events.length, 0);
  assert.match(result.error, /usage API down/);
});

test("a replayed Telnyx import with a provider uniqueness conflict is recorded, not failed", async () => {
  const result = await importTelnyxCdrs([
    { id: "cdr-replay", call_control_id: "cc-replay", billed_duration: 60, cost: { amount: "0.02", currency: "USD" } },
  ], {
    uid: "u1", recordProviderCost,
    supaUrl: "https://db.example", supaKey: "service",
    fetchImpl: async () => ({ ok: false, status: 409, json: async () => ({ code: "23505" }) }),
  });
  assert.deepEqual(result, { attempted: 1, recorded: 1, failed: 0 });
});

test("production import runner invokes Telnyx, Railway, and Supabase loaders and reports each result", async () => {
  const r = recorder();
  const loaded = [];
  const result = await runScheduledProviderCostImports({
    loaders: {
      telnyx: async () => { loaded.push("telnyx"); return [{ id: "cdr-run", cost: { amount: "0.01", currency: "USD" } }]; },
      railway: async () => { loaded.push("railway"); return [{ period: "2026-08-08", amount_usd: "0.20" }]; },
      supabase: async () => { loaded.push("supabase"); return [{ period: "2026-08-08", amount_usd: "0.10" }]; },
    },
    options: { uid: "u1", ...r.deps },
  });
  assert.deepEqual(loaded, ["telnyx", "railway", "supabase"]);
  assert.deepEqual(result.map((item) => item.provider), ["telnyx", "railway", "supabase"]);
  assert.ok(result.every((item) => item.receipt.recorded === 1 && item.receipt.failed === 0));
});
