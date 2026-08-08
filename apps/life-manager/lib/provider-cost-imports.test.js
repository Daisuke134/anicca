"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  importTelnyxCdrs,
  importRailwayAllocations,
  importSupabaseAllocations,
  importScheduledMeasurements,
} = require("./provider-cost-imports.js");

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
