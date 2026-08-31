"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { buildRollingEventCoverage } = require("./rolling-event-coverage.js");
const { runLumaCandidateSequence } = require("./luma-candidate-loop.js");
const {
  createEventSourceCapabilities, executeEventSourceHandoff, planEventSourceHandoff,
} = require("./event-source-handoff.js");
const {
  buildEventProviderDateInventory, isVerifiedEventProviderDateInventory,
} = require("./event-provider-date-inventory.js");

const FIXTURE_CONNPASS_API_KEY = ["connpass", "test", "key", "0".repeat(16)].join("-");

async function fixture() {
  const coverage = buildRollingEventCoverage({
    tenantId: "dais-local", timeZone: "Asia/Tokyo",
    now: "2026-08-01T16:00:00.000Z", resolvedDays: [],
  });
  const lumaOutcome = await runLumaCandidateSequence({ candidates: [], attempt: async () => {} });
  const capabilities = createEventSourceCapabilities({ connpassApiKey: FIXTURE_CONNPASS_API_KEY });
  const plan = planEventSourceHandoff({ date: "2026-08-05", lumaOutcome, capabilities });
  const handoff = await executeEventSourceHandoff({
    plan,
    connpassClient: { async searchEvents() { return {
      results_returned: 1, results_available: 1, results_start: 1,
      events: [{
        id: 101, title: "Connpass Night", catch: "Public", description: "Public details",
        started_at: "2026-08-05T19:00:00+09:00", ended_at: "2026-08-05T21:00:00+09:00",
        place: "Shibuya Hall", address: "Shibuya, Tokyo", group: { subdomain: "tokyo-builders" },
      }],
    }; } },
  });
  return { coverage, handoff };
}

test("builds one immutable Connpass inventory from verified eligible handoff candidates", async () => {
  const { coverage, handoff } = await fixture();
  const inventory = buildEventProviderDateInventory({
    coverage, handoff, eligibleCandidates: handoff.advisory_candidates,
    now: "2026-08-02T01:00:00.000Z",
  });
  assert.equal(isVerifiedEventProviderDateInventory(inventory), true);
  assert.equal(isVerifiedEventProviderDateInventory(structuredClone(inventory)), false);
  assert.equal(inventory.provider, "connpass");
  assert.equal(inventory.coverage_snapshot_id, coverage.coverage_snapshot_id);
  assert.equal(inventory.days.find((day) => day.date === "2026-08-05").events[0].event_ref, "connpass-event://event/101");
  assert.equal(JSON.stringify(inventory).includes("fixture-secret"), false);
  assert.equal(Object.isFrozen(inventory.days), true);
});

test("rejects forged handoffs, non-eligible candidates, and coverage drift", async () => {
  const { coverage, handoff } = await fixture();
  assert.throws(() => buildEventProviderDateInventory({
    coverage, handoff: structuredClone(handoff), eligibleCandidates: [],
    now: "2026-08-02T01:00:00.000Z",
  }), /provider date inventory invalid/i);
  assert.throws(() => buildEventProviderDateInventory({
    coverage, handoff, eligibleCandidates: [{ ...handoff.advisory_candidates[0], event_ref: "connpass-event://event/999" }],
    now: "2026-08-02T01:00:00.000Z",
  }), /provider date inventory invalid/i);
});
