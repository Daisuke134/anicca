import assert from "node:assert/strict";
import { test } from "node:test";
import { summarizeEconomyStatus } from "./status.mjs";

const NOW = Date.parse("2026-08-21T00:00:00Z");

test("status sums verified external net, compute, and shelter costs over the last 30 days", () => {
  const result = summarizeEconomyStatus({
    nowMs: NOW,
    earnRows: [
      { ts: Math.floor((NOW - 2 * 86400000) / 1000), source: "gig", net_usdc: 15, external: true, tx: "0x1", status: "0x1" },
      { ts: Math.floor((NOW - 40 * 86400000) / 1000), source: "gig", net_usdc: 99, external: true, tx: "0x2", status: "0x1" },
    ],
    corrections: [],
    computeRows: [
      { ts: (NOW - 3 * 86400000) / 1000, cost_usd: 6 },
      { ts: (NOW - 40 * 86400000) / 1000, cost_usd: 99 },
    ],
    shelterRows: [{ ts: NOW - 4 * 86400000, settledLeaseCostUsd: 4 }],
    liquidRunwayDays: 30,
    humanPaidInference30d: 0,
  });
  assert.equal(result.external_realized_net_30d, 15);
  assert.equal(result.compute_cost_30d, 6);
  assert.equal(result.shelter_cost_30d, 4);
  assert.equal(result.graduation.eligible, true);
});

test("status keeps graduation ineligible when runway or human-fuel evidence is missing", () => {
  const result = summarizeEconomyStatus({
    nowMs: NOW,
    earnRows: [{ ts: NOW / 1000, source: "gig", net_usdc: 15, external: true, tx: "0x1", status: "0x1" }],
    corrections: [],
    computeRows: [{ ts: NOW / 1000, cost_usd: 6 }],
    shelterRows: [{ ts: NOW, settledLeaseCostUsd: 4 }],
  });
  assert.equal(result.graduation.eligible, false);
  assert.equal(result.graduation.reason, "invalid-input");
});

