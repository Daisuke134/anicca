import assert from "node:assert/strict";
import { test } from "node:test";
import { summarizeEconomyStatus } from "./status.mjs";
import { normalizeRevenueReceipt } from "./lib/revenue-receipt.mjs";
import { reconcileRevenueReceipts } from "./lib/money-truth.mjs";
import { mkdtemp, readFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";

const NOW = Date.parse("2026-08-21T00:00:00Z");
const VERIFIED = normalizeRevenueReceipt({
  provider: "gig",
  payer: "0x1111111111111111111111111111111111111111",
  recipient: "0x2222222222222222222222222222222222222222",
  gross: "15.000000",
  fee: "0",
  refund: "0",
  asset: "USDC",
  proof: { chain_id: 8453, tx_hash: `0x${"55".repeat(32)}`, log_index: 0, verified: true },
  terminal_state: "settled",
  occurred_at: "2026-08-19T00:00:00.000Z",
});

test("status sums verified external net, compute, and shelter costs over the last 30 days", () => {
  const result = summarizeEconomyStatus({
    nowMs: NOW,
    earnRows: [
      VERIFIED,
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

test("status-only status=0x1 rows contribute zero by default", () => {
  const result = summarizeEconomyStatus({
    nowMs: NOW,
    earnRows: [{ ts: NOW / 1000, source: "gig", net_usdc: 15, external: true, tx: "0x1", status: "0x1" }],
    corrections: [],
    computeRows: [],
    shelterRows: [],
  });
  assert.equal(result.external_realized_net_30d, 0);
  assert.equal(result.verified_external_rows_30d, 0);
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

test("canonical receipt journal rows are consumed by status", async () => {
  const dir = await mkdtemp(join(tmpdir(), "agent-economy-status-"));
  const journalPath = join(dir, "revenue-journal.jsonl");
  await reconcileRevenueReceipts({ journalPath, receipts: [normalizeRevenueReceipt({
    ...VERIFIED,
    gross: "2.000000",
    proof: { provider_receipt_id: "status-flow-1", verified: true },
    idempotency_key: undefined,
    signed_net: undefined,
  })] });
  const rows = (await readFile(journalPath, "utf8")).trim().split("\n").map((line) => JSON.parse(line));
  const result = summarizeEconomyStatus({ nowMs: NOW, earnRows: rows, corrections: [], computeRows: [], shelterRows: [] });
  assert.equal(result.external_realized_net_30d, 2);
  assert.equal(result.verified_external_rows_30d, 1);
});
