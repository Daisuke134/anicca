"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  taskMarketLedgerEntry,
  verifyTaskMarketAwardOnBase,
  processTaskMarketTasks,
} = require("./taskmarket-work-ledger.js");

const WORKER = "0xd7Db94062AFec8a86F70250B931C77619acf8937";
const REQUESTER = "0xa4d897959211c8e565F862080913b45Cc761Ac6A";
const ESCROW = "0xddc6cc3e4d11c1f3527b867c7dad4ed9869c33f7";
const USDC = "0x833589fCD6eDb6E08f4C7C32D4f71b54bdA02913";
const TASK_ID = `0x${"ab".repeat(32)}`;
const TX = `0x${"cd".repeat(32)}`;
const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";

function topic(address) {
  return `0x${address.toLowerCase().slice(2).padStart(64, "0")}`;
}

function task(overrides = {}) {
  return {
    id: TASK_ID,
    requester: REQUESTER,
    status: "completed",
    mode: "bounty",
    selfAward: false,
    awardCount: 1,
    awards: [award()],
    ...overrides,
  };
}

function award(overrides = {}) {
  return {
    workerAddress: WORKER,
    workerAgentId: "60023",
    rank: 1,
    isPrimary: true,
    grossAmount: "2500000",
    workerPayment: "2312500",
    platformFee: "187500",
    settlementTxHash: TX,
    settledAt: "2026-07-28T06:00:00.000Z",
    ...overrides,
  };
}

function receipt(overrides = {}) {
  return {
    status: "0x1",
    transactionHash: TX,
    blockNumber: "0x64",
    logs: [{
      address: USDC,
      transactionHash: TX,
      topics: [TRANSFER_TOPIC, topic(ESCROW), topic(WORKER)],
      data: "0x234934",
    }],
    ...overrides,
  };
}

function rpcFor(rcpt = receipt(), { chainId = "0x2105", finalized = "0x65" } = {}) {
  return async (method) => {
    if (method === "eth_chainId") return chainId;
    if (method === "eth_getBlockByNumber") return { number: finalized };
    if (method === "eth_getTransactionReceipt") return rcpt;
    throw new Error(`unexpected ${method}`);
  };
}

test("builds a conservative, exactly-once WORK row from the verified worker payment", () => {
  const row = taskMarketLedgerEntry(task(), award(), {
    workerAddress: WORKER,
    selfWallets: [WORKER],
    receiptBlock: 100,
  });
  assert.equal(row.entry_key, `taskmarket:${TASK_ID}:${TX}:income`);
  assert.equal(row.kind, "financial_external_income");
  assert.equal(row.amount_minor, 231);
  assert.equal(row.source, "taskmarket_work");
  assert.equal(row.meta.usdc_atomic, "2312500");
  assert.equal(row.meta.excluded_dust_atomic, "2500");
  assert.equal(row.meta.requester, REQUESTER.toLowerCase());
  assert.equal(row.meta.receipt_block, 100);
});

test("rejects uncompleted, self-awarded, foreign-worker, and self-requester claims", () => {
  const options = { workerAddress: WORKER, selfWallets: [WORKER], receiptBlock: 100 };
  assert.throws(() => taskMarketLedgerEntry(task({ status: "open" }), award(), options), /completed/);
  assert.throws(() => taskMarketLedgerEntry(task({ selfAward: true }), award(), options), /self-award/);
  assert.throws(() => taskMarketLedgerEntry(task(), award({ workerAddress: REQUESTER }), options), /owned worker/);
  assert.throws(() => taskMarketLedgerEntry(task({ requester: WORKER }), award(), options), /self wallet/);
});

test("requires internally consistent exact award amounts and settlement fields", () => {
  const options = { workerAddress: WORKER, selfWallets: [WORKER], receiptBlock: 100 };
  assert.throws(() => taskMarketLedgerEntry(task(), award({ grossAmount: "2499999" }), options), /sum/);
  const subcent = award({ grossAmount: "197499", workerPayment: "9999" });
  assert.throws(() => taskMarketLedgerEntry(task({ awards: [subcent] }), subcent, options), /one cent/);
  assert.throws(() => taskMarketLedgerEntry(task(), award({ settlementTxHash: "bad" }), options), /transaction/);
});

test("verifies a finalized exact native-USDC transfer to the worker", async () => {
  const verified = await verifyTaskMarketAwardOnBase(task(), award(), {
    workerAddress: WORKER,
    selfWallets: [WORKER],
    rpcCall: rpcFor(),
  });
  assert.deepEqual(verified, { ok: true, receiptBlock: 100 });
});

test("rejects wrong chain, premature, failed, wrong amount, wrong receiver, and duplicate transfers", async () => {
  const options = { workerAddress: WORKER, selfWallets: [WORKER] };
  assert.equal((await verifyTaskMarketAwardOnBase(task(), award(), { ...options, rpcCall: rpcFor(receipt(), { chainId: "0x1" }) })).ok, false);
  assert.equal((await verifyTaskMarketAwardOnBase(task(), award(), { ...options, rpcCall: rpcFor(receipt(), { finalized: "0x63" }) })).ok, false);
  assert.equal((await verifyTaskMarketAwardOnBase(task(), award(), { ...options, rpcCall: rpcFor(receipt({ status: "0x0" })) })).ok, false);
  const wrongAmount = receipt();
  wrongAmount.logs[0].data = "0x1";
  assert.equal((await verifyTaskMarketAwardOnBase(task(), award(), { ...options, rpcCall: rpcFor(wrongAmount) })).ok, false);
  const wrongReceiver = receipt();
  wrongReceiver.logs[0].topics[2] = topic(REQUESTER);
  assert.equal((await verifyTaskMarketAwardOnBase(task(), award(), { ...options, rpcCall: rpcFor(wrongReceiver) })).ok, false);
  const duplicate = receipt();
  duplicate.logs.push({ ...duplicate.logs[0] });
  assert.equal((await verifyTaskMarketAwardOnBase(task(), award(), { ...options, rpcCall: rpcFor(duplicate) })).ok, false);
});

test("open task is a truthful no-op and a verified award is duplicate safe", async () => {
  const writes = [];
  const open = await processTaskMarketTasks({
    taskIds: [TASK_ID],
    workerAddress: WORKER,
    selfWallets: [WORKER],
    fetchTask: async () => task({ status: "open", awardCount: 0, awards: [] }),
    rpcCall: rpcFor(),
    recordEntry: async (row) => { writes.push(row); return { ok: true, duplicate: false }; },
  });
  assert.equal(open.recorded, 0);
  assert.equal(open.pending, 1);
  assert.equal(writes.length, 0);

  const first = await processTaskMarketTasks({
    taskIds: [TASK_ID],
    workerAddress: WORKER,
    selfWallets: [WORKER],
    fetchTask: async () => task(),
    rpcCall: rpcFor(),
    recordEntry: async (row) => { writes.push(row); return { ok: true, duplicate: false }; },
  });
  assert.equal(first.recorded, 1);
  assert.equal(writes.length, 1);

  const duplicate = await processTaskMarketTasks({
    taskIds: [TASK_ID],
    workerAddress: WORKER,
    selfWallets: [WORKER],
    fetchTask: async () => task(),
    rpcCall: rpcFor(),
    recordEntry: async () => ({ ok: true, duplicate: true }),
  });
  assert.equal(duplicate.duplicates, 1);
  assert.equal(duplicate.recorded, 0);
});
