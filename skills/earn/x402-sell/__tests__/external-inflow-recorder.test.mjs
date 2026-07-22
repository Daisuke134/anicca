import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  USDC_ADDRESS,
  TRANSFER_TOPIC,
  appendUniqueExternalInflows,
  collectVerifiedExternalInflows,
  walletLedgerPath,
} from "../lib/external-inflow-recorder.mjs";

const PAY_TO = "0x1111111111111111111111111111111111111111";
const EXTERNAL = "0x2222222222222222222222222222222222222222";
const SELF = "0x3333333333333333333333333333333333333333";
const FACILITATOR = "0x4444444444444444444444444444444444444444";

const topicAddress = (address) => `0x${address.slice(2).toLowerCase().padStart(64, "0")}`;
const dataUsdc = (units) => `0x${BigInt(units).toString(16).padStart(64, "0")}`;
const hash = (digit) => `0x${digit.repeat(64)}`;

function transferLog({
  tx = hash("a"),
  block = "0x63",
  address = USDC_ADDRESS,
  topic0 = TRANSFER_TOPIC,
  from = EXTERNAL,
  to = PAY_TO,
  units = 50_000n,
} = {}) {
  return {
    address,
    blockNumber: block,
    transactionHash: tx,
    topics: [topic0, topicAddress(from), topicAddress(to)],
    data: dataUsdc(units),
  };
}

function rpcFixture({ candidates, receipts, transactions, finalized = "0x64" }) {
  const calls = [];
  const rpcCall = async (method, params) => {
    calls.push([method, params]);
    if (method === "eth_getBlockByNumber") return { number: finalized };
    if (method === "eth_getLogs") return candidates;
    if (method === "eth_getTransactionReceipt") return receipts.get(String(params[0]).toLowerCase()) ?? null;
    if (method === "eth_getTransactionByHash") return transactions.get(String(params[0]).toLowerCase()) ?? null;
    throw new Error(`unexpected RPC method ${method}`);
  };
  return { calls, rpcCall };
}

test("records only receipt-derived finalized successful Base USDC inbound value", async () => {
  const tx = hash("a");
  const receiptLog = transferLog({ tx, units: 50_000n });
  const candidate = {
    ...receiptLog,
    // These discovery-log fields are deliberately forged. The durable row must be derived from
    // the successful finalized receipt, never from caller/discovery claims.
    topics: [TRANSFER_TOPIC, topicAddress(FACILITATOR), topicAddress(PAY_TO)],
    data: dataUsdc(999_000_000n),
    from: SELF,
    amount: "999999",
    status: "success",
  };
  const { rpcCall, calls } = rpcFixture({
    candidates: [candidate],
    receipts: new Map([[tx, { transactionHash: tx.toUpperCase(), status: "0x1", blockNumber: "0x63", logs: [receiptLog] }]]),
    transactions: new Map([[tx, { hash: tx, from: FACILITATOR }]]),
  });

  const result = await collectVerifiedExternalInflows({
    payTo: PAY_TO,
    fromBlock: 90,
    rpcCall,
    selfWallets: [SELF],
    settledTransactions: new Set([tx.toUpperCase()]),
    amount: "caller-spoof",
    from: SELF,
    status: "caller-spoof",
  });

  assert.equal(result.finalizedBlock, 100);
  assert.deepEqual(result.rows, [{
    tx: tx.toLowerCase(),
    block: 99,
    from: EXTERNAL.toLowerCase(),
    to: PAY_TO.toLowerCase(),
    payTo: PAY_TO.toLowerCase(),
    usdc: 0.05,
    finalized: true,
    status: "success",
    external: true,
  }]);
  assert.deepEqual(calls[0], ["eth_getBlockByNumber", ["finalized", false]]);
  const getLogs = calls.find(([method]) => method === "eth_getLogs");
  assert.equal(getLogs[1][0].address.toLowerCase(), USDC_ADDRESS.toLowerCase());
  assert.deepEqual(getLogs[1][0].topics, [TRANSFER_TOPIC, null, topicAddress(PAY_TO)]);
});

test("rejects failed, unfinalized, malformed, wrong-contract/topic/to receipt logs", async () => {
  const cases = [
    { digit: "1", receipt: { status: "0x0", blockNumber: "0x63", logs: [transferLog()] } },
    { digit: "2", receipt: { status: "0x1", blockNumber: "0x65", logs: [transferLog()] } },
    { digit: "3", receipt: { status: "0x1", blockNumber: "0x63", logs: [transferLog({ address: SELF })] } },
    { digit: "4", receipt: { status: "0x1", blockNumber: "0x63", logs: [transferLog({ topic0: hash("f") })] } },
    { digit: "5", receipt: { status: "0x1", blockNumber: "0x63", logs: [transferLog({ to: SELF })] } },
    { digit: "6", receipt: { status: "0x1", blockNumber: "0x63", logs: [{ ...transferLog(), data: "not-hex" }] } },
  ];
  const candidates = [];
  const receipts = new Map();
  const transactions = new Map();
  for (const item of cases) {
    const tx = hash(item.digit);
    candidates.push(transferLog({ tx }));
    receipts.set(tx, {
      transactionHash: tx,
      ...item.receipt,
      logs: item.receipt.logs.map((log) => ({ ...log, transactionHash: tx })),
    });
    transactions.set(tx, { hash: tx, from: FACILITATOR });
  }

  const { rpcCall } = rpcFixture({ candidates, receipts, transactions });
  const result = await collectVerifiedExternalInflows({
    payTo: PAY_TO,
    fromBlock: 90,
    rpcCall,
    selfWallets: [SELF],
    settledTransactions: new Set(candidates.map((row) => row.transactionHash)),
  });
  assert.deepEqual(result.rows, []);
});

test("excludes SELF_WALLETS transfer senders and self-initiated protocol returns case-insensitively", async () => {
  const senderSelfTx = hash("7");
  const protocolReturnTx = hash("8");
  const senderSelfLog = transferLog({ tx: senderSelfTx, from: SELF.toUpperCase() });
  const protocolReturnLog = transferLog({ tx: protocolReturnTx, from: EXTERNAL });
  const receipts = new Map([
    [senderSelfTx, { transactionHash: senderSelfTx, status: "0x1", blockNumber: "0x63", logs: [senderSelfLog] }],
    [protocolReturnTx, { transactionHash: protocolReturnTx, status: "0x1", blockNumber: "0x63", logs: [protocolReturnLog] }],
  ]);
  const transactions = new Map([
    [senderSelfTx, { hash: senderSelfTx, from: FACILITATOR }],
    [protocolReturnTx, { hash: protocolReturnTx, from: SELF.toUpperCase() }],
  ]);
  const { rpcCall } = rpcFixture({ candidates: [senderSelfLog, protocolReturnLog], receipts, transactions });

  const result = await collectVerifiedExternalInflows({
    payTo: PAY_TO,
    fromBlock: 90,
    rpcCall,
    selfWallets: [SELF],
    settledTransactions: new Set([senderSelfTx, protocolReturnTx]),
  });
  assert.deepEqual(result.rows, []);
});

test("requires matching settled-sale provenance and matches the tx case-insensitively", async () => {
  const tx = hash("9");
  const receiptLog = transferLog({ tx });
  const receipts = new Map([[tx, {
    transactionHash: tx,
    status: "0x1",
    blockNumber: "0x63",
    logs: [receiptLog],
  }]]);
  const transactions = new Map([[tx, { hash: tx, from: FACILITATOR }]]);
  const { rpcCall } = rpcFixture({ candidates: [receiptLog], receipts, transactions });

  const withoutSale = await collectVerifiedExternalInflows({
    payTo: PAY_TO,
    fromBlock: 90,
    rpcCall,
    selfWallets: [SELF],
    settledTransactions: new Set(),
  });
  assert.deepEqual(withoutSale.rows, [], "an arbitrary external USDC gift is not an x402 sale");

  const withSale = await collectVerifiedExternalInflows({
    payTo: PAY_TO,
    fromBlock: 90,
    rpcCall,
    selfWallets: [SELF],
    settledTransactions: new Set([tx.toUpperCase()]),
  });
  assert.equal(withSale.rows.length, 1);
  assert.equal(withSale.rows[0].tx, tx);
});

test("wallet ledger path is lowercase and append is exactly-once by case-insensitive tx", async () => {
  const dir = mkdtempSync(join(tmpdir(), "x402-external-inflow-"));
  const ledgerPath = walletLedgerPath(PAY_TO.toUpperCase(), { stateDir: dir });
  assert.equal(ledgerPath, join(dir, `external-inflows-${PAY_TO.toLowerCase()}.jsonl`));

  const row = {
    tx: hash("a"), block: 99, from: EXTERNAL, to: PAY_TO, payTo: PAY_TO,
    usdc: 0.05, finalized: true, status: "success", external: true,
  };
  writeFileSync(ledgerPath, `${JSON.stringify({ ...row, tx: row.tx.toUpperCase() })}\n`);
  const first = appendUniqueExternalInflows(ledgerPath, [row, { ...row, tx: hash("b") }]);
  const second = appendUniqueExternalInflows(ledgerPath, [{ ...row, tx: hash("B") }]);

  assert.deepEqual(first, { recorded: 1, duplicates: 1 });
  assert.deepEqual(second, { recorded: 0, duplicates: 1 });
  const saved = readFileSync(ledgerPath, "utf8").trim().split("\n").map(JSON.parse);
  assert.equal(saved.length, 2);
  assert.equal(saved[1].tx, hash("b"));
});

test("a competing writer's lock is never removed when this writer fails to acquire it", () => {
  const dir = mkdtempSync(join(tmpdir(), "x402-external-inflow-lock-"));
  const ledgerPath = walletLedgerPath(PAY_TO, { stateDir: dir });
  const lockPath = `${ledgerPath}.lock`;
  writeFileSync(lockPath, "other-writer");

  assert.throws(() => appendUniqueExternalInflows(ledgerPath, []), /EEXIST/);
  assert.equal(existsSync(lockPath), true);
  assert.equal(readFileSync(lockPath, "utf8"), "other-writer");
});

test("watcher invokes durable recorder without replacing verify summary or first-external notification", () => {
  const watcher = readFileSync(new URL("../watch-inflow.sh", import.meta.url), "utf8");
  const recorder = readFileSync(new URL("../record-external-inflow.mjs", import.meta.url), "utf8");
  assert.match(watcher, /node record-external-inflow\.mjs 2/);
  assert.equal((watcher.match(/node record-external-inflow\.mjs 2/g) || []).length, 1);
  assert.match(watcher, /node verify-inflow\.mjs 2/);
  assert.match(watcher, /x402-inflow\$\{TAG/);
  assert.match(watcher, /x402-first-external\$\{TAG/);
  assert.match(watcher, /display notification/);
  assert.doesNotMatch(watcher, /attempts-.*\.jsonl/);
  assert.match(recorder, /X402_PAYTO\s*\|\|\s*['"]0x810f6d61f7606deee2657d3083e150a222bc29c5['"]/);
});
