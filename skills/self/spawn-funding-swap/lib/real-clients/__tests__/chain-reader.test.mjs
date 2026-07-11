// VCSDD spawn-funding-swap Phase 2a (sprint-2, RED). PROP-032..PROP-035 — lib/real-clients/chain-reader.mjs.
// Every transport boundary (execFileImpl, fetchImpl) is mocked; NO real network/subprocess call is ever
// made from this file (NFR-6). Written against a file that does NOT exist yet as of this commit -- every
// test below MUST fail (module-not-found) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRealChainReader } from "../chain-reader.mjs";

const TEST_ENV = { AKASH_NODE: "https://fake-node.example:443", AKASH_CHAIN_ID: "fake-chain-1", AKASH_CLI: "fake-akash-cli" };
const BASE_ADDRESS = "0x1234567890123456789012345678901234567890";

function fakeFetch(handler) {
  return async (url, init) => handler(url, init);
}

test("PROP-032: getAkashBalance parses a mocked `akash query bank balances -o json` stdout into the uakt bigint", async () => {
  const reader = createRealChainReader({
    env: TEST_ENV,
    execFileImpl: async (cmd, args) => {
      assert.equal(cmd, "fake-akash-cli");
      assert.deepEqual(args, ["query", "bank", "balances", "akash1abc", "--node", TEST_ENV.AKASH_NODE, "--chain-id", TEST_ENV.AKASH_CHAIN_ID, "-o", "json"]);
      return { stdout: JSON.stringify({ balances: [{ denom: "uakt", amount: "26000000" }] }) };
    },
  });
  const balance = await reader.getAkashBalance("akash1abc");
  assert.equal(balance, 26_000_000n);
  assert.equal(typeof balance, "bigint");
});

test("PROP-032: getAkashBalance returns 0n when no uakt entry is present (genuinely-zero, not an error)", async () => {
  const reader = createRealChainReader({
    env: TEST_ENV,
    execFileImpl: async () => ({ stdout: JSON.stringify({ balances: [{ denom: "uusdc", amount: "5" }] }) }),
  });
  assert.equal(await reader.getAkashBalance("akash1abc"), 0n);
});

test("PROP-032: getAkashBalance returns 0n for an empty balances array", async () => {
  const reader = createRealChainReader({ env: TEST_ENV, execFileImpl: async () => ({ stdout: JSON.stringify({ balances: [] }) }) });
  assert.equal(await reader.getAkashBalance("akash1abc"), 0n);
});

test("PROP-033: getAkashBalance throws when AKASH_NODE is unset (fail-closed, never queries an ambient default node)", async () => {
  const reader = createRealChainReader({ env: { AKASH_CHAIN_ID: "fake-chain-1" }, execFileImpl: async () => { throw new Error("must not be called"); } });
  await assert.rejects(() => reader.getAkashBalance("akash1abc"), /AKASH_NODE/);
});

test("PROP-033: getAkashBalance throws when AKASH_CHAIN_ID is unset", async () => {
  const reader = createRealChainReader({ env: { AKASH_NODE: "https://fake-node.example:443" }, execFileImpl: async () => { throw new Error("must not be called"); } });
  await assert.rejects(() => reader.getAkashBalance("akash1abc"), /AKASH_CHAIN_ID/);
});

test("PROP-032: getAkashBalance throws on unparseable CLI stdout (fail-closed, never returns a silently-wrong 0n on a parse error)", async () => {
  const reader = createRealChainReader({ env: TEST_ENV, execFileImpl: async () => ({ stdout: "not json" }) });
  await assert.rejects(() => reader.getAkashBalance("akash1abc"));
});

test("PROP-034: getBaseUsdc returns the RAW eth_call result as a bigint (never /1e6-scaled)", async () => {
  const reader = createRealChainReader({
    fetchImpl: fakeFetch(async (url, init) => {
      const body = JSON.parse(init.body);
      assert.equal(body.method, "eth_call");
      assert.equal(body.params[0].to, "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913");
      assert.ok(body.params[0].data.startsWith("0x70a08231"));
      return { ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: "0x000000000000000000000000000000000000000000000000000000000e4e1c" }) };
    }),
  });
  const balance = await reader.getBaseUsdc(BASE_ADDRESS);
  assert.equal(balance, 937500n);
  assert.equal(typeof balance, "bigint");
});

test("PROP-034: getBaseGas returns the RAW eth_getBalance wei result as a bigint", async () => {
  const reader = createRealChainReader({
    fetchImpl: fakeFetch(async (url, init) => {
      const body = JSON.parse(init.body);
      assert.equal(body.method, "eth_getBalance");
      return { ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: "0x2386f26fc10000" }) }; // 0.01 ETH in wei
    }),
  });
  assert.equal(await reader.getBaseGas(BASE_ADDRESS), 10_000_000_000_000_000n);
});

test("PROP-034: getBaseUsdc throws on a non-2xx RPC response (fail-closed)", async () => {
  const reader = createRealChainReader({ fetchImpl: fakeFetch(async () => ({ ok: false, status: 500 })) });
  await assert.rejects(() => reader.getBaseUsdc(BASE_ADDRESS));
});

test("PROP-034: getBaseUsdc throws on an invalid address", async () => {
  const reader = createRealChainReader({ fetchImpl: fakeFetch(async () => { throw new Error("must not be called"); }) });
  await assert.rejects(() => reader.getBaseUsdc("not-an-address"));
});

test("PROP-035: getBaseTxStatusByNonce returns 'confirmed' when the mined-tx-count is strictly greater than the queried nonce", async () => {
  const reader = createRealChainReader({
    fetchImpl: fakeFetch(async (url, init) => {
      const body = JSON.parse(init.body);
      assert.equal(body.method, "eth_getTransactionCount");
      assert.deepEqual(body.params, [BASE_ADDRESS, "latest"]);
      return { ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: "0x5" }) }; // count = 5
    }),
  });
  assert.equal(await reader.getBaseTxStatusByNonce(BASE_ADDRESS, 3n), "confirmed");
  assert.equal(await reader.getBaseTxStatusByNonce(BASE_ADDRESS, 4n), "confirmed");
});

test("PROP-035: getBaseTxStatusByNonce returns 'not-found' when the mined-tx-count is NOT strictly greater than the queried nonce", async () => {
  const reader = createRealChainReader({ fetchImpl: fakeFetch(async () => ({ ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: "0x5" }) })) });
  assert.equal(await reader.getBaseTxStatusByNonce(BASE_ADDRESS, 5n), "not-found");
  assert.equal(await reader.getBaseTxStatusByNonce(BASE_ADDRESS, 6n), "not-found");
});
