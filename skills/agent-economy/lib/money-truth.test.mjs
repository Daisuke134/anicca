import assert from "node:assert/strict";
import { test } from "node:test";
import {
  receiptKey,
  reconcilePendingReceipts,
  reconcileLedger,
  reconcileRevenueReceipts,
  summarizeRealizedRevenue,
} from "./money-truth.mjs";
import { normalizeRevenueReceipt } from "./revenue-receipt.mjs";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const TX = "0x436143c136183fbf164d884bda7cf9608b0b5ac7b6243f797d4d2e72ccc23d58";

test("reconciles a delayed 0x1 receipt and counts the real external net", async () => {
  const rows = [{
    wallet: "0x3eccad24794ca298d25378e9902a251322ea8749",
    source: "gig",
    earn_usdc: 0.02,
    cost_usdc: 0,
    net_usdc: 0.02,
    tx: TX,
    status: "null",
    external: true,
  }];
  const corrections = await reconcilePendingReceipts(rows, async () => ({
    verified: true,
    status: "0x1",
    evidence: { chain_id: 8453, tx_hash: TX, log_index: 0 },
  }));
  assert.deepEqual(corrections, [{ tx: TX, status: "0x1", verified: true, evidence: { chain_id: 8453, tx_hash: TX, log_index: 0 } }]);
  assert.deepEqual(summarizeRealizedRevenue(rows, corrections), {
    external_net_usdc: 0.02,
    verified_external_rows: 1,
    unverified_external_rows: 0,
    excluded_rows: 0,
  });
});

test("receipt timeout stays unverified and contributes no revenue", async () => {
  const row = { source: "gig", net_usdc: 0.02, earn_usdc: 0.02, tx: TX, status: "null", external: true };
  const corrections = await reconcilePendingReceipts([row], async () => null);
  assert.deepEqual(corrections, [{ tx: TX, status: null }]);
  assert.equal(summarizeRealizedRevenue([row], []).external_net_usdc, 0);
});

test("plain status=0x1 callback is not accepted without verified transfer proof", async () => {
  const row = { source: "gig", net_usdc: 0.02, earn_usdc: 0.02, tx: TX, status: "0x1", external: true };
  const corrections = await reconcilePendingReceipts([row], async () => "0x1");
  assert.deepEqual(corrections, [{ tx: TX, status: null }]);
  assert.equal(summarizeRealizedRevenue([row], []).external_net_usdc, 0);
});

test("self, test, and non-external rows never become external revenue", async () => {
  const rows = [
    { source: "x402", net_usdc: 1, tx: "0xself", status: "0x1", external: false },
    { source: "test-payment", net_usdc: 2, tx: "0xtest", status: "0x1", external: true, test: true },
    { source: "swap-eth-usdc", net_usdc: 3, tx: "0xswap", status: "0x1", external: true },
  ];
  const result = summarizeRealizedRevenue(rows, []);
  assert.deepEqual(result, {
    external_net_usdc: 0,
    verified_external_rows: 0,
    unverified_external_rows: 0,
    excluded_rows: 3,
  });
});

test("receiptKey supports EVM, Solana, and Hyperliquid proof identities", () => {
  assert.equal(receiptKey({ tx: TX }), TX);
  assert.equal(receiptKey({ sig: "sol-signature" }), "sig:sol-signature");
  assert.equal(receiptKey({ chain: "hyperliquid", fill_tid: 99 }), "hyperliquid:99");
  assert.equal(receiptKey({ source: "narrate" }), null);
});

test("canonical v2 proof suppresses the matching legacy tx row without suppressing distinct txs", () => {
  const canonical = revenueReceipt({ gross: "1.000000", fee: "0", proof: { chain_id: 8453, tx_hash: REVENUE_TX, log_index: 0, verified: true } });
  const legacy = { tx: REVENUE_TX, source: "gig", net_usdc: 1, external: true, status: "0x1" };
  const correction = {
    tx: REVENUE_TX,
    status: "0x1",
    verified: true,
    evidence: { chain_id: 8453, tx_hash: REVENUE_TX, log_index: 0 },
  };
  const distinct = revenueReceipt({ gross: "1.000000", fee: "0", proof: { chain_id: 8453, tx_hash: `0x${"66".repeat(32)}`, log_index: 0, verified: true } });
  const result = summarizeRealizedRevenue([legacy, canonical, distinct], [correction]);
  assert.equal(result.external_net_usdc, 2);
  assert.equal(result.verified_external_rows, 2);
});

test("cross-dedupe uses normalized chain+tx: same chain suppresses", () => {
  const canonical = revenueReceipt({ gross: "1.000000", fee: "0", proof: { chain_id: 8453, tx_hash: REVENUE_TX, log_index: 0, verified: true } });
  const legacy = { tx: REVENUE_TX, chain_id: 8453, source: "gig", net_usdc: 1, external: true, status: "0x1" };
  const correction = { tx: REVENUE_TX, status: "0x1", verified: true, evidence: { chain_id: 8453, tx_hash: REVENUE_TX, log_index: 0 } };
  const result = summarizeRealizedRevenue([legacy, canonical], [correction]);
  assert.equal(result.external_net_usdc, 1);
  assert.equal(result.verified_external_rows, 1);
});

test("cross-dedupe uses normalized chain+tx: unknown legacy chain suppresses fail-closed", () => {
  const canonical = revenueReceipt({ gross: "1.000000", fee: "0", proof: { chain_id: 8453, tx_hash: REVENUE_TX, log_index: 0, verified: true } });
  const legacy = { tx: REVENUE_TX, source: "gig", net_usdc: 1, external: true, status: "0x1" };
  const correction = { tx: REVENUE_TX, status: "0x1", verified: true, evidence: { chain_id: 8453, tx_hash: REVENUE_TX, log_index: 0 } };
  const result = summarizeRealizedRevenue([legacy, canonical], [correction]);
  assert.equal(result.external_net_usdc, 1);
  assert.equal(result.verified_external_rows, 1);
});

test("cross-dedupe uses normalized chain+tx: known different chain preserves legacy row", () => {
  const canonical = revenueReceipt({ gross: "1.000000", fee: "0", proof: { chain_id: 8453, tx_hash: REVENUE_TX, log_index: 0, verified: true } });
  const legacy = { tx: REVENUE_TX, chain_id: 1, source: "gig", net_usdc: 1, external: true, status: "0x1" };
  const correction = { tx: REVENUE_TX, status: "0x1", verified: true, evidence: { chain_id: 1, tx_hash: REVENUE_TX, log_index: 0 } };
  const result = summarizeRealizedRevenue([legacy, canonical], [correction]);
  assert.equal(result.external_net_usdc, 2);
  assert.equal(result.verified_external_rows, 2);
});

test("reconcileLedger appends a successful correction once and returns the verified summary", async () => {
  const dir = await mkdtemp(join(tmpdir(), "money-truth-"));
  const ledger = join(dir, "earn-ledger.jsonl");
  const corrections = join(dir, "receipt-reconciliations.jsonl");
  await writeFile(ledger, `${JSON.stringify({ tx: TX, source: "gig", net_usdc: 0.02, external: true, status: "null" })}\n`);

  const first = await reconcileLedger({
    ledgerPath: ledger,
    correctionPath: corrections,
    verifyReceipt: async () => ({
      verified: true,
      status: "0x1",
      chain_id: 8453,
      tx_hash: TX,
      transfer: {
        contract: "0x833589fcd6edb6e08f4c7c32d4f71b54bdA02913",
        payer: "0x1111111111111111111111111111111111111111",
        recipient: "0x2222222222222222222222222222222222222222",
        amount_atomic: "20000",
        log_index: 0,
      },
    }),
    nowTs: 100,
  });
  assert.equal(first.persisted_corrections, 1);
  assert.equal(first.summary.external_net_usdc, 0.02);
  const correctionRow = JSON.parse((await readFile(corrections, "utf8")).trim());
  assert.deepEqual(correctionRow.evidence, {
    chain_id: 8453,
    tx_hash: TX,
    contract: "0x833589fcd6edb6e08f4c7c32d4f71b54bdA02913",
    payer: "0x1111111111111111111111111111111111111111",
    recipient: "0x2222222222222222222222222222222222222222",
    amount_atomic: "20000",
    log_index: 0,
  });

  const second = await reconcileLedger({
    ledgerPath: ledger,
    correctionPath: corrections,
    verifyReceipt: async () => { throw new Error("must not refetch a terminal correction"); },
    nowTs: 101,
  });
  assert.equal(second.persisted_corrections, 0);
  assert.equal((await readFile(corrections, "utf8")).trim().split("\n").length, 1);
});

test("reconcileLedger does not persist a null receipt, so the next wake can retry", async () => {
  const dir = await mkdtemp(join(tmpdir(), "money-truth-"));
  const ledger = join(dir, "earn-ledger.jsonl");
  const corrections = join(dir, "receipt-reconciliations.jsonl");
  await writeFile(ledger, `${JSON.stringify({ tx: TX, source: "gig", net_usdc: 0.02, external: true, status: "null" })}\n`);
  const result = await reconcileLedger({ ledgerPath: ledger, correctionPath: corrections, verifyReceipt: async () => null });
  assert.equal(result.persisted_corrections, 0);
  assert.equal(result.summary.unverified_external_rows, 1);
});

const REVENUE_TX = `0x${"22".repeat(32)}`;
const EXTERNAL_PAYER = "0x1111111111111111111111111111111111111111";
const INSTANCE_RECIPIENT = "0x2222222222222222222222222222222222222222";
const revenueReceipt = (overrides = {}) => normalizeRevenueReceipt({
  provider: "x402",
  payer: EXTERNAL_PAYER,
  recipient: INSTANCE_RECIPIENT,
  gross: "2.000000",
  fee: "0.100000",
  refund: "0",
  asset: "USDC",
  proof: { chain_id: 8453, tx_hash: REVENUE_TX, log_index: 0, verified: true },
  terminal_state: "settled",
  occurred_at: "2026-08-27T00:00:00.000Z",
  ...overrides,
});

test("reconcileRevenueReceipts appends one canonical positive row and replay is zero", async () => {
  const dir = await mkdtemp(join(tmpdir(), "money-truth-revenue-"));
  const journalPath = join(dir, "revenue-journal.jsonl");
  const receipt = revenueReceipt();
  const first = await reconcileRevenueReceipts({ journalPath, receipts: [receipt], nowTs: 100 });
  assert.equal(first.accepted, 1);
  assert.equal(first.duplicates, 0);
  assert.equal(first.summary.external_net_usdc, 1.9);
  const second = await reconcileRevenueReceipts({ journalPath, receipts: [receipt], nowTs: 101 });
  assert.equal(second.accepted, 0);
  assert.equal(second.duplicates, 1);
  assert.equal((await readFile(journalPath, "utf8")).trim().split("\n").length, 1);
});

test("reconcileRevenueReceipts includes a signed negative refund correction", async () => {
  const dir = await mkdtemp(join(tmpdir(), "money-truth-revenue-"));
  const journalPath = join(dir, "revenue-journal.jsonl");
  await reconcileRevenueReceipts({ journalPath, receipts: [revenueReceipt()], nowTs: 100 });
  const correction = revenueReceipt({
    gross: "0",
    fee: "0",
    refund: "0.500000",
    terminal_state: "refunded",
    proof: { chain_id: 8453, tx_hash: `0x${"33".repeat(32)}`, log_index: 0, verified: true },
  });
  const result = await reconcileRevenueReceipts({ journalPath, receipts: [correction], nowTs: 101 });
  assert.equal(result.accepted, 1);
  assert.equal(result.summary.external_net_usdc, 1.4);
});

test("reconcileRevenueReceipts rejects self-payment and unverified receipts without appending", async () => {
  const dir = await mkdtemp(join(tmpdir(), "money-truth-revenue-"));
  const journalPath = join(dir, "revenue-journal.jsonl");
  await assert.rejects(
    () => reconcileRevenueReceipts({ journalPath, receipts: [revenueReceipt({ payer: INSTANCE_RECIPIENT })] }),
    /self|payer/i,
  );
  await assert.rejects(
    () => reconcileRevenueReceipts({ journalPath, receipts: [{ provider: "x402", terminal_state: "settled" }] }),
    /receipt|provider|proof/i,
  );
  assert.equal((await readFile(journalPath, "utf8").catch(() => "")).trim(), "");
});

test("empty selfPayers does not mask provided selfWallets", async () => {
  const dir = await mkdtemp(join(tmpdir(), "money-truth-revenue-"));
  const journalPath = join(dir, "revenue-journal.jsonl");
  const payer = "0x9999999999999999999999999999999999999999";
  await assert.rejects(
    () => reconcileRevenueReceipts({ journalPath, receipts: [revenueReceipt({ payer })], selfWallets: [payer] }),
    /self|payer/i,
  );
});

test("reconcileRevenueReceipts always re-normalizes a forged canonical marker", async () => {
  const dir = await mkdtemp(join(tmpdir(), "money-truth-revenue-"));
  const journalPath = join(dir, "revenue-journal.jsonl");
  const forged = { ...revenueReceipt(), signed_net: 999, idempotency_key: revenueReceipt().idempotency_key };
  await assert.rejects(() => reconcileRevenueReceipts({ journalPath, receipts: [forged] }), /ARITHMETIC_MISMATCH|canonical|idempotency/i);
});

test("reconcileRevenueReceipts refuses a stored v1 row instead of re-appending it as v2", async () => {
  const dir = await mkdtemp(join(tmpdir(), "money-truth-revenue-"));
  const journalPath = join(dir, "revenue-journal.jsonl");
  const old = { ...revenueReceipt(), schema_version: 1, idempotency_key: `revenue:v1:${"a".repeat(64)}` };
  await writeFile(journalPath, `${JSON.stringify(old)}\n`);
  await assert.rejects(() => reconcileRevenueReceipts({ journalPath, receipts: [revenueReceipt()] }), /unsupported|version/i);
  assert.equal((await readFile(journalPath, "utf8")).trim().split("\n").length, 1);
});

test("reconcileRevenueReceipts fails closed on corrupt JSONL and serializes concurrent appends", async () => {
  const dir = await mkdtemp(join(tmpdir(), "money-truth-revenue-"));
  const corruptPath = join(dir, "corrupt.jsonl");
  await writeFile(corruptPath, "{not-json}\n");
  await assert.rejects(() => reconcileRevenueReceipts({ journalPath: corruptPath, receipts: [revenueReceipt()] }), /corrupt|json/i);

  const journalPath = join(dir, "concurrent.jsonl");
  const receipt = revenueReceipt({ proof: { chain_id: 8453, tx_hash: `0x${"44".repeat(32)}`, log_index: 0, verified: true } });
  const results = await Promise.all([
    reconcileRevenueReceipts({ journalPath, receipts: [receipt] }),
    reconcileRevenueReceipts({ journalPath, receipts: [receipt] }),
  ]);
  assert.equal(results.reduce((sum, result) => sum + result.accepted, 0), 1);
  assert.equal((await readFile(journalPath, "utf8")).trim().split("\n").length, 1);
});

test("standalone reconcile CLI uses the strict row verifier, never status-only receiptStatus", async () => {
  const source = await readFile(new URL("../reconcile-receipts.mjs", import.meta.url), "utf8");
  assert.match(source, /verifyLedgerRow/);
  assert.match(source, /verifyEvmReceipt/);
  assert.doesNotMatch(source, /receiptStatus/);
});

test("standalone reconcile CLI consumes a canonical receipt journal without external effects", async () => {
  const dir = await mkdtemp(join(tmpdir(), "money-truth-cli-"));
  const ledgerPath = join(dir, "earn-ledger.jsonl");
  const correctionPath = join(dir, "receipt-reconciliations.jsonl");
  await writeFile(ledgerPath, `${JSON.stringify(revenueReceipt({
    proof: { provider_receipt_id: "cli-flow-1", verified: true },
  }))}\n`);
  const { stdout } = await execFileAsync(process.execPath, ["skills/agent-economy/reconcile-receipts.mjs", ledgerPath, correctionPath], {
    cwd: process.cwd(),
    timeout: 5_000,
    env: { ...process.env },
  });
  const result = JSON.parse(stdout.trim());
  assert.equal(result.persisted_corrections, 0);
  assert.equal(result.summary.external_net_usdc, 1.9);
});
