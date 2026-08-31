"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  handoffTaskMarketAwards,
  atomicToUsdc,
} = require("./taskmarket-award-handoff.js");

const WORKER = "0xd7Db94062AFec8a86F70250B931C77619acf8937";
const DESTINATION = "0x477EeE969ccfdc0e959F38cE8B83e372FC0262ad";
const TX = `0x${"12".repeat(32)}`;
const AWARD_TX = `0x${"34".repeat(32)}`;
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";

function ledger(overrides = {}) {
  return {
    ok: true,
    worker_address: WORKER.toLowerCase(),
    recorded: 1,
    duplicates: 0,
    transactions: [AWARD_TX],
    ...overrides,
  };
}

function jsonResponse(body, { ok = true, status = 200 } = {}) {
  return {
    ok,
    status,
    async text() { return JSON.stringify(body); },
  };
}

function topicAddress(value) {
  return `0x${value.slice(2).toLowerCase().padStart(64, "0")}`;
}

function receipt(amountAtomic = "4625000") {
  return {
    status: "0x1",
    transactionHash: TX,
    blockNumber: "0x64",
    logs: [{
      address: USDC,
      transactionHash: TX,
      topics: [
        TRANSFER_TOPIC,
        topicAddress(WORKER),
        topicAddress(DESTINATION),
      ],
      data: `0x${BigInt(amountAtomic).toString(16)}`,
    }],
  };
}

test("formats atomic USDC without floating-point conversion", () => {
  assert.equal(atomicToUsdc("1"), "0.000001");
  assert.equal(atomicToUsdc("4625000"), "4.625000");
  assert.equal(atomicToUsdc("1000000"), "1.000000");
});

test("does not inspect a wallet or mutate TaskMarket before an owned award exists", async () => {
  const result = await handoffTaskMarketAwards({
    ledgerResult: ledger({ recorded: 0, transactions: [] }),
    workerAddress: WORKER,
    destination: DESTINATION,
  }, {
    fetchImpl: async () => { throw new Error("fetch must not run"); },
    execFileImpl: async () => { throw new Error("CLI must not run"); },
    rpcCall: async () => { throw new Error("RPC must not run"); },
  });
  assert.deepEqual(result, {
    ok: true,
    status: "noop",
    reason: "no_verified_award",
    verified_awards: 0,
  });
});

test("retries a duplicate verified award and proves one exact finalized USDC handoff", async () => {
  const calls = [];
  const result = await handoffTaskMarketAwards({
    ledgerResult: ledger({ recorded: 0, duplicates: 1 }),
    workerAddress: WORKER,
    destination: DESTINATION,
  }, {
    fetchImpl: async (url) => {
      assert.match(url, /withdrawal-address/);
      return jsonResponse({ withdrawalAddress: DESTINATION });
    },
    execFileImpl: async (file, args, options) => {
      calls.push({ file, args, options });
      if (args.join(" ") === "wallet balance") {
        return {
          stdout: JSON.stringify({
            ok: true,
            data: {
              address: WORKER,
              balanceBaseUnits: "4625000",
              balanceUsdc: "4.625000",
            },
          }),
          stderr: "",
        };
      }
      assert.deepEqual(args, ["withdraw", "4.625000"]);
      return {
        stdout: JSON.stringify({
          ok: true,
          data: {
            txHash: TX,
            amountBaseUnits: "4625000",
            to: DESTINATION,
          },
        }),
        stderr: "",
      };
    },
    rpcCall: async (method) => {
      if (method === "eth_chainId") return "0x2105";
      if (method === "eth_getTransactionReceipt") return receipt();
      if (method === "eth_getBlockByNumber") return { number: "0x65" };
      throw new Error(`unexpected RPC method ${method}`);
    },
    sleep: async () => {},
  });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].file, "/opt/homebrew/bin/taskmarket");
  assert.equal(calls[1].file, "/opt/homebrew/bin/taskmarket");
  assert.equal(calls[1].args.includes(WORKER), false);
  assert.equal(calls[1].args.includes(DESTINATION), false);
  assert.equal(result.status, "transferred");
  assert.equal(result.amount_atomic, "4625000");
  assert.equal(result.tx_hash, TX);
  assert.equal(result.to, DESTINATION.toLowerCase());
  assert.equal(result.block_number, "100");
  assert.equal(result.verified_awards, 1);
});

test("zero balance after a verified duplicate is an idempotent no-op", async () => {
  let cliCalls = 0;
  const result = await handoffTaskMarketAwards({
    ledgerResult: ledger({ recorded: 0, duplicates: 1 }),
    workerAddress: WORKER,
    destination: DESTINATION,
  }, {
    fetchImpl: async () => jsonResponse({ withdrawalAddress: DESTINATION }),
    execFileImpl: async () => {
      cliCalls += 1;
      return {
        stdout: JSON.stringify({
          ok: true,
          data: { address: WORKER, balanceBaseUnits: "0", balanceUsdc: "0.000000" },
        }),
        stderr: "",
      };
    },
    rpcCall: async () => { throw new Error("RPC must not run"); },
  });
  assert.equal(cliCalls, 1);
  assert.equal(result.status, "noop");
  assert.equal(result.reason, "worker_balance_zero");
});

test("fails closed on wrong destination, malformed evidence, or a mismatched receipt", async () => {
  await assert.rejects(() => handoffTaskMarketAwards({
    ledgerResult: ledger(),
    workerAddress: WORKER,
    destination: DESTINATION,
  }, {
    fetchImpl: async () => jsonResponse({
      withdrawalAddress: "0x1111111111111111111111111111111111111111",
    }),
    execFileImpl: async () => { throw new Error("CLI must not run"); },
  }), /destination does not match/);

  await assert.rejects(() => handoffTaskMarketAwards({
    ledgerResult: ledger({ transactions: [] }),
    workerAddress: WORKER,
    destination: DESTINATION,
  }), /transaction evidence/);

  await assert.rejects(() => handoffTaskMarketAwards({
    ledgerResult: ledger(),
    workerAddress: WORKER,
    destination: DESTINATION,
  }, {
    fetchImpl: async () => jsonResponse({ withdrawalAddress: DESTINATION }),
    execFileImpl: async (_file, args) => {
      if (args[0] === "wallet") {
        return {
          stdout: JSON.stringify({
            ok: true,
            data: { address: WORKER, balanceBaseUnits: "4625000", balanceUsdc: "4.625000" },
          }),
          stderr: "",
        };
      }
      return {
        stdout: JSON.stringify({
          ok: true,
          data: { txHash: TX, amountBaseUnits: "4625000", to: DESTINATION },
        }),
        stderr: "",
      };
    },
    rpcCall: async (method) => {
      if (method === "eth_chainId") return "0x2105";
      if (method === "eth_getTransactionReceipt") return receipt("1");
      if (method === "eth_getBlockByNumber") return { number: "0x65" };
      throw new Error("unexpected RPC");
    },
    sleep: async () => {},
  }), /exactly one matching/);
});
