"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { runLumaCandidateSequence } = require("./luma-candidate-loop.js");
const {
  createEventSourceCapabilities,
  executeEventSourceHandoff,
  isVerifiedEventSourceCapabilities,
  isVerifiedEventSourceHandoff,
  planEventSourceHandoff,
} = require("./event-source-handoff.js");

async function exhausted() {
  return runLumaCandidateSequence({
    candidates: [{ event_ref: "luma-event://event/a", canonical_url: "https://luma.com/a" }],
    attempt: async () => ({ status: "not_eligible" }),
  });
}

function connpassEvent(id, overrides = {}) {
  return {
    id,
    title: `Event ${id}`,
    catch: "Public event summary",
    description: "Public event description",
    started_at: "2026-08-05T19:00:00+09:00",
    ended_at: "2026-08-05T21:00:00+09:00",
    event_type: "participation",
    open_status: "open",
    group: { id: 9, subdomain: "tokyo-builders", title: "Tokyo Builders" },
    address: "Tokyo",
    place: "Shibuya Hall",
    ...overrides,
  };
}

test("missing connpass key permits Luma only and produces zero-network open handoff", async () => {
  const capabilities = createEventSourceCapabilities({ connpassApiKey: "" });
  assert.equal(capabilities.sources.luma.coverage_credit, true);
  assert.equal(capabilities.sources.connpass.status, "blocked_missing_key");
  assert.equal(capabilities.sources.connpass.registration_allowed, false);
  assert.equal(capabilities.sources.connpass.coverage_credit, false);
  assert.equal(JSON.stringify(capabilities).includes("apiKey"), false);
  assert.equal(isVerifiedEventSourceCapabilities(capabilities), true);
  assert.equal(isVerifiedEventSourceCapabilities(structuredClone(capabilities)), false);

  const plan = planEventSourceHandoff({
    date: "2026-08-05",
    lumaOutcome: await exhausted(),
    capabilities,
  });
  let networkCalls = 0;
  const result = await executeEventSourceHandoff({
    plan,
    connpassClient: { async searchEvents() { networkCalls += 1; } },
  });
  assert.equal(networkCalls, 0);
  assert.deepEqual(result, {
    handoff_id: result.handoff_id,
    date: "2026-08-05",
    status: "waiting_for_authorized_source",
    coverage_status: "open",
    advisory_candidates: [],
    coverage_credit_count: 0,
    network_call_count: 0,
    next_actions: ["watch_connpass_api_key", "rediscover_luma"],
  });
  assert.equal(isVerifiedEventSourceHandoff(result), true);
  assert.equal(isVerifiedEventSourceHandoff(structuredClone(result)), false);
});

test("valid key enables exhaustive official API GET discovery but never registration or coverage credit", async () => {
  const capabilities = createEventSourceCapabilities({
    connpassApiKey: "fixture-secret-api-key-1234567890",
  });
  assert.equal(capabilities.sources.connpass.status, "official_api_discovery_only");
  const plan = planEventSourceHandoff({
    date: "2026-08-05",
    lumaOutcome: await exhausted(),
    capabilities,
  });
  const calls = [];
  const pages = [
    { results_returned: 2, results_available: 3, results_start: 1, events: [connpassEvent(101), connpassEvent(102)] },
    { results_returned: 1, results_available: 3, results_start: 3, events: [connpassEvent(103, { url: "https://another-group.connpass.com/event/103/", group: { id: 10, subdomain: "another-group", title: "Another" } })] },
  ];
  const result = await executeEventSourceHandoff({
    plan,
    connpassClient: {
      async searchEvents(query) {
        calls.push(query);
        return pages.shift();
      },
    },
  });
  assert.deepEqual(calls, [
    { ymd: ["20260805"], count: 100, order: 2, start: 1 },
    { ymd: ["20260805"], count: 100, order: 2, start: 3 },
  ]);
  assert.equal(result.status, "advisory_candidates_found");
  assert.equal(result.advisory_candidates.length, 3);
  assert.equal(result.advisory_candidates[0].canonical_url, "https://tokyo-builders.connpass.com/event/101/");
  assert.equal(result.advisory_candidates[2].canonical_url, "https://another-group.connpass.com/event/103/");
  assert.equal(result.advisory_candidates.every((row) => (
    row.registration_allowed === false && row.coverage_credit === false
  )), true);
  assert.equal(result.coverage_status, "open");
  assert.equal(result.coverage_credit_count, 0);
  assert.equal(result.network_call_count, 2);
});

test("source error and empty official inventory keep the date open for Luma retry", async () => {
  const capabilities = createEventSourceCapabilities({ connpassApiKey: "fixture-secret-api-key-1234567890" });
  const makePlan = async () => planEventSourceHandoff({ date: "2026-08-05", lumaOutcome: await exhausted(), capabilities });
  const failed = await executeEventSourceHandoff({
    plan: await makePlan(),
    connpassClient: { async searchEvents() { throw new Error("provider down"); } },
  });
  assert.equal(failed.status, "authorized_source_unavailable");
  assert.equal(failed.coverage_status, "open");
  assert.deepEqual(failed.next_actions, ["rediscover_luma", "retry_connpass_api"]);

  const empty = await executeEventSourceHandoff({
    plan: await makePlan(),
    connpassClient: { async searchEvents() { return { results_returned: 0, results_available: 0, results_start: 1, events: [] }; } },
  });
  assert.equal(empty.status, "authorized_source_empty");
  assert.equal(empty.coverage_status, "open");
  assert.deepEqual(empty.next_actions, ["rediscover_luma"]);
});

test("fake provenance, short keys, non-exhausted Luma, and malformed connpass pages fail closed", async () => {
  assert.throws(() => createEventSourceCapabilities({ connpassApiKey: "short" }), /event source handoff invalid/i);
  const capabilities = createEventSourceCapabilities({ connpassApiKey: "fixture-secret-api-key-1234567890" });
  const outcome = await exhausted();
  assert.throws(() => planEventSourceHandoff({
    date: "2026-08-05", lumaOutcome: structuredClone(outcome), capabilities,
  }), /event source handoff invalid/i);
  assert.throws(() => planEventSourceHandoff({
    date: "2026-08-05", lumaOutcome: outcome, capabilities: structuredClone(capabilities),
  }), /event source handoff invalid/i);
  const plan = planEventSourceHandoff({ date: "2026-08-05", lumaOutcome: outcome, capabilities });
  await assert.rejects(executeEventSourceHandoff({
    plan: structuredClone(plan), connpassClient: { async searchEvents() {} },
  }), /event source handoff invalid/i);
  await assert.rejects(executeEventSourceHandoff({
    plan,
    connpassClient: { async searchEvents() { return { results_returned: 1, results_available: 2, results_start: 1, events: [connpassEvent(1)] }; } },
  }), /event source handoff invalid/i);
});
