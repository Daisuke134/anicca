"use strict";

const assert = require("node:assert/strict");
const { mkdtempSync, writeFileSync } = require("node:fs");
const { tmpdir } = require("node:os");
const { join } = require("node:path");
const test = require("node:test");

const {
  USDC_ADDRESS,
  TRANSFER_TOPIC,
  findLedgerPaths,
  processLedgers,
} = require("./record-x402-sales.js");

const PAY_TO = "0x810f6d61f7606deee2657d3083e150a222bc29c5";
const PAYER = "0x1111111111111111111111111111111111111111";
const TX_INITIATOR = "0x3333333333333333333333333333333333333333";
const TX = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const BLOCK = 34123456;

function sale(overrides = {}) {
  return {
    source: "the402",
    source_sale_id: "the402:order-42",
    offer_id: "forecast/weekly",
    tx: TX,
    block: BLOCK,
    from: PAYER,
    to: PAY_TO,
    payTo: PAY_TO,
    usdc: 0.5,
    usdc_atomic: "500000",
    finalized: true,
    status: "success",
    external: true,
    observed_at: "2026-07-27T13:31:59.000Z",
    ...overrides,
  };
}

function topicAddress(value) {
  return `0x${value.slice(2).padStart(64, "0")}`;
}

function rpcFixture(overrides = {}) {
  const responses = {
    eth_chainId: "0x2105",
    eth_getBlockByNumber: { number: `0x${(BLOCK + 20).toString(16)}` },
    eth_getTransactionReceipt: {
      status: "0x1",
      transactionHash: TX,
      blockNumber: `0x${BLOCK.toString(16)}`,
      logs: [{
        address: USDC_ADDRESS,
        transactionHash: TX,
        topics: [TRANSFER_TOPIC, topicAddress(PAYER), topicAddress(PAY_TO)],
        data: "0x7a120",
      }],
    },
    eth_getTransactionByHash: { hash: TX, from: TX_INITIATOR },
    ...overrides,
  };
  const calls = [];
  return {
    calls,
    rpcCall: async (method) => {
      calls.push(method);
      return responses[method];
    },
  };
}

function ledger(lines) {
  const dir = mkdtempSync(join(tmpdir(), "lm-x402-"));
  const path = join(dir, `external-inflows-${PAY_TO}.jsonl`);
  writeFileSync(path, `${lines.join("\n")}${lines.length ? "\n" : ""}`);
  return { dir, path };
}

test("an empty state directory is a healthy zero-row run with no RPC or write", async () => {
  const dir = mkdtempSync(join(tmpdir(), "lm-x402-empty-"));
  const writes = [];
  const rpc = rpcFixture();
  const result = await processLedgers({
    ledgerPaths: findLedgerPaths(dir),
    selfWallets: [PAY_TO],
    rpcCall: rpc.rpcCall,
    recordSale: async (row) => writes.push(row),
  });

  assert.deepEqual(result, {
    ledgers_seen: 0,
    lines_seen: 0,
    invalid: 0,
    chain_rejected: 0,
    blocked_subcent: 0,
    recorded: 0,
    duplicates: 0,
    transactions: [],
  });
  assert.equal(rpc.calls.length, 0);
  assert.equal(writes.length, 0);
});

test("a finalized exact USDC transfer is reverified and delegated once", async () => {
  const source = ledger([JSON.stringify(sale())]);
  const rpc = rpcFixture();
  const writes = [];
  const result = await processLedgers({
    ledgerPaths: [source.path],
    selfWallets: [PAY_TO],
    rpcCall: rpc.rpcCall,
    recordSale: async (row, options) => {
      writes.push({ row, options });
      return { ok: true, duplicate: false, entry_key: `x402:${row.tx}:income` };
    },
  });

  assert.equal(result.recorded, 1);
  assert.equal(result.duplicates, 0);
  assert.deepEqual(result.transactions, [TX]);
  assert.equal(writes.length, 1);
  assert.deepEqual(writes[0].options.ownedPayTos, [PAY_TO]);
  assert.deepEqual(rpc.calls, [
    "eth_chainId",
    "eth_getBlockByNumber",
    "eth_getTransactionReceipt",
    "eth_getTransactionByHash",
  ]);
});

test("malformed rows and fractional-cent sales never touch chain or database", async () => {
  const source = ledger([
    "{bad-json",
    JSON.stringify(sale({ usdc: 0.001, usdc_atomic: "1000" })),
  ]);
  const rpc = rpcFixture();
  let writes = 0;
  const result = await processLedgers({
    ledgerPaths: [source.path],
    selfWallets: [PAY_TO],
    rpcCall: rpc.rpcCall,
    recordSale: async () => {
      writes += 1;
      return { ok: true, duplicate: false };
    },
  });

  assert.equal(result.lines_seen, 2);
  assert.equal(result.invalid, 1);
  assert.equal(result.blocked_subcent, 1);
  assert.equal(rpc.calls.length, 0);
  assert.equal(writes, 0);
});

test("wrong chain, pending receipt, transfer mismatch, and self initiator fail closed", async () => {
  const cases = [
    { eth_chainId: "0x89" },
    { eth_getBlockByNumber: { number: `0x${(BLOCK - 1).toString(16)}` } },
    {
      eth_getTransactionReceipt: {
        status: "0x1",
        transactionHash: TX,
        blockNumber: `0x${BLOCK.toString(16)}`,
        logs: [],
      },
    },
    { eth_getTransactionByHash: { hash: TX, from: PAY_TO } },
  ];

  for (const override of cases) {
    const source = ledger([JSON.stringify(sale())]);
    let writes = 0;
    const result = await processLedgers({
      ledgerPaths: [source.path],
      selfWallets: [PAY_TO],
      rpcCall: rpcFixture(override).rpcCall,
      recordSale: async () => {
        writes += 1;
        return { ok: true };
      },
    });
    assert.equal(result.chain_rejected, 1);
    assert.equal(writes, 0);
  }
});

test("a Supabase uniqueness retry is exposed as a duplicate, not new revenue", async () => {
  const source = ledger([JSON.stringify(sale())]);
  const result = await processLedgers({
    ledgerPaths: [source.path],
    selfWallets: [PAY_TO],
    rpcCall: rpcFixture().rpcCall,
    recordSale: async () => ({
      ok: true,
      duplicate: true,
      entry_key: `x402:${TX}:income`,
    }),
  });

  assert.equal(result.recorded, 0);
  assert.equal(result.duplicates, 1);
  assert.deepEqual(result.transactions, [TX]);
});

test("ledger receiver is bound by its canonical external-inflows filename", async () => {
  const source = ledger([JSON.stringify(sale({ payTo: PAYER, to: PAYER }))]);
  let writes = 0;
  const result = await processLedgers({
    ledgerPaths: [source.path],
    selfWallets: [PAY_TO],
    rpcCall: rpcFixture().rpcCall,
    recordSale: async () => {
      writes += 1;
      return { ok: true };
    },
  });

  assert.equal(result.invalid, 1);
  assert.equal(writes, 0);
});
