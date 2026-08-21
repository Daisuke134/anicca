import assert from "node:assert/strict";
import { test } from "node:test";
import {
  receiptKey,
  reconcilePendingReceipts,
  reconcileLedger,
  summarizeRealizedRevenue,
} from "./money-truth.mjs";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";

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
  const corrections = await reconcilePendingReceipts(rows, async () => "0x1");
  assert.deepEqual(corrections, [{ tx: TX, status: "0x1" }]);
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
  assert.equal(summarizeRealizedRevenue([row], corrections).external_net_usdc, 0);
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

test("reconcileLedger appends a successful correction once and returns the verified summary", async () => {
  const dir = await mkdtemp(join(tmpdir(), "money-truth-"));
  const ledger = join(dir, "earn-ledger.jsonl");
  const corrections = join(dir, "receipt-reconciliations.jsonl");
  await writeFile(ledger, `${JSON.stringify({ tx: TX, source: "gig", net_usdc: 0.02, external: true, status: "null" })}\n`);

  const first = await reconcileLedger({
    ledgerPath: ledger,
    correctionPath: corrections,
    fetchReceipt: async () => "0x1",
    nowTs: 100,
  });
  assert.equal(first.persisted_corrections, 1);
  assert.equal(first.summary.external_net_usdc, 0.02);

  const second = await reconcileLedger({
    ledgerPath: ledger,
    correctionPath: corrections,
    fetchReceipt: async () => { throw new Error("must not refetch a terminal correction"); },
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
  const result = await reconcileLedger({ ledgerPath: ledger, correctionPath: corrections, fetchReceipt: async () => null });
  assert.equal(result.persisted_corrections, 0);
  assert.equal(result.summary.unverified_external_rows, 1);
});
