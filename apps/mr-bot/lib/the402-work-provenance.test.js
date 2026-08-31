"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { classifyThe402Revenue } = require("./the402-work-provenance.js");

const TX = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

function inflow(overrides = {}) {
  return {
    source: "the402",
    source_sale_id: "the402:settlement_42",
    offer_id: "svc_research",
    tx: TX,
    usdc_atomic: "1000000",
    ...overrides,
  };
}

function settlement(overrides = {}) {
  return {
    settlement_id: "settlement_42",
    status: "settled",
    tx_hash: TX,
    provider_amount_usd: "1.00",
    service_id: "svc_research",
    job_id: "job_42",
    posting_id: "post_42",
    ...overrides,
  };
}

function job(overrides = {}) {
  return {
    id: "job_42",
    posting_id: "post_42",
    service_id: "svc_research",
    status: "completed",
    ...overrides,
  };
}

test("classifies a uniquely matched terminal settlement and job as work", () => {
  assert.deepEqual(classifyThe402Revenue(inflow(), {
    earnings: { recent_settlements: [settlement()] },
    jobs: { jobs: [job()] },
  }), {
    kind: "work",
    settlementId: "settlement_42",
    jobId: "job_42",
    postingId: "post_42",
  });
});

test("classifies a matched settlement without job or posting provenance as a direct sale", () => {
  assert.deepEqual(classifyThe402Revenue(inflow(), {
    earnings: {
      recent_settlements: [settlement({ job_id: undefined, posting_id: undefined })],
    },
    jobs: { jobs: [] },
  }), {
    kind: "sale",
    settlementId: "settlement_42",
    jobId: null,
    postingId: null,
  });
});

test("rejects missing, ambiguous, or economically mismatched settlements", () => {
  const cases = [
    { earnings: { recent_settlements: [] }, jobs: { jobs: [] } },
    {
      earnings: { recent_settlements: [settlement(), settlement()] },
      jobs: { jobs: [job()] },
    },
    {
      earnings: { recent_settlements: [settlement({ tx_hash: `0x${"b".repeat(64)}` })] },
      jobs: { jobs: [job()] },
    },
    {
      earnings: { recent_settlements: [settlement({ provider_amount_usd: "1.01" })] },
      jobs: { jobs: [job()] },
    },
    {
      earnings: { recent_settlements: [settlement({ service_id: "svc_other" })] },
      jobs: { jobs: [job()] },
    },
    {
      earnings: {
        recent_settlements: [settlement({ offer_id: "svc_conflict" })],
      },
      jobs: { jobs: [job()] },
    },
  ];
  for (const evidence of cases) {
    assert.deepEqual(classifyThe402Revenue(inflow(), evidence), {
      kind: "rejected",
      reason: "settlement_mismatch",
    });
  }
});

test("rejects work-shaped settlements without one matching terminal job", () => {
  const cases = [
    [],
    [job({ status: "in_progress" })],
    [job({ service_id: "svc_other" })],
    [job(), job()],
  ];
  for (const jobs of cases) {
    assert.deepEqual(classifyThe402Revenue(inflow(), {
      earnings: { recent_settlements: [settlement()] },
      jobs: { jobs },
    }), {
      kind: "rejected",
      reason: "job_mismatch",
    });
  }
});

test("requires terminal settlement status and rejects untrusted source syntax", () => {
  assert.deepEqual(classifyThe402Revenue(inflow(), {
    earnings: { recent_settlements: [settlement({ status: "pending" })] },
    jobs: { jobs: [job()] },
  }), {
    kind: "rejected",
    reason: "settlement_mismatch",
  });
  assert.deepEqual(classifyThe402Revenue(inflow({ source: "manual" }), {
    earnings: { recent_settlements: [settlement()] },
    jobs: { jobs: [job()] },
  }), {
    kind: "rejected",
    reason: "invalid_inflow",
  });
});
