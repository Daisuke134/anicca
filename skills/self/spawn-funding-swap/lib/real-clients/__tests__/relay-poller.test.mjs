// VCSDD spawn-funding-swap Phase 2a (sprint-2, RED). PROP-039/PROP-040 — lib/real-clients/relay-poller.mjs.
// fetchImpl is always mocked and every wait window is injected at test scale (milliseconds, never the
// real 60s default) so this suite runs fast with zero real network/timing dependency (NFR-6). Written
// against a file that does NOT exist yet -- every test below MUST fail (module-not-found) until Phase 2b.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRealRelayPoller } from "../relay-poller.mjs";

const TX_HASH = "0xdeadbeef";

test("PROP-039: numeric chainId + a receipt with status 0x1 on the first poll resolves 'confirmed'", async () => {
  const poller = createRealRelayPoller({
    fetchImpl: async (url, init) => {
      const body = JSON.parse(init.body);
      assert.equal(body.method, "eth_getTransactionReceipt");
      assert.deepEqual(body.params, [TX_HASH]);
      return { ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: { status: "0x1" } }) };
    },
    pollIntervalMs: 5,
  });
  assert.equal(await poller.waitForConfirmation(8453, TX_HASH, 1000), "confirmed");
});

test("PROP-039: numeric chainId + a receipt with status 0x0 resolves 'reverted'", async () => {
  const poller = createRealRelayPoller({ fetchImpl: async () => ({ ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: { status: "0x0" } }) }), pollIntervalMs: 5 });
  assert.equal(await poller.waitForConfirmation(8453, TX_HASH, 1000), "reverted");
});

test("PROP-039: numeric chainId + no receipt ever landing before timeoutMs resolves 'pending'", async () => {
  const poller = createRealRelayPoller({ fetchImpl: async () => ({ ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: null }) }), pollIntervalMs: 5 });
  assert.equal(await poller.waitForConfirmation(8453, TX_HASH, 30), "pending");
});

test("PROP-039: numeric chainId + falsy txHash resolves 'pending' immediately (nothing to poll)", async () => {
  const poller = createRealRelayPoller({ fetchImpl: async () => { throw new Error("must not be called"); } });
  assert.equal(await poller.waitForConfirmation(8453, null, 1000), "pending");
});

// FIND-007 fix (impl review iter1): both string-chainId tests below now inject an explicit fetchImpl
// that THROWS if ever called -- the string-chainId branch is a pure setTimeout-based wait (never touches
// fetchImpl in this implementation), but PROP-049's tightened scan now REQUIRES every createRealXxx()
// call in this directory to inject a transport seam, closing the gap where a FUTURE change to the
// string-chainId branch that DID reach the network would go undetected by a bare construction.
const NEVER_CALLED_FETCH = async () => { throw new Error("must not be called"); };

test("PROP-040: string chainId (relay-only leg) resolves 'confirmed' once the injected settle window fully elapses within timeoutMs", async () => {
  const poller = createRealRelayPoller({ relaySettleWaitMs: 10, fetchImpl: NEVER_CALLED_FETCH });
  assert.equal(await poller.waitForConfirmation("akashnet-2", null, 1000), "confirmed");
});

test("PROP-040: string chainId resolves 'pending' when timeoutMs is smaller than the settle window", async () => {
  const poller = createRealRelayPoller({ relaySettleWaitMs: 1000, fetchImpl: NEVER_CALLED_FETCH });
  assert.equal(await poller.waitForConfirmation("akashnet-2", null, 10), "pending");
});

test("PROP-040: the EVM-vs-Cosmos branch is selected by typeof chainId, not a specific chain-id string match", async () => {
  const poller = createRealRelayPoller({
    fetchImpl: async () => ({ ok: true, json: async () => ({ jsonrpc: "2.0", id: 1, result: { status: "0x1" } }) }),
    relaySettleWaitMs: 5,
    pollIntervalMs: 5,
  });
  // A numeric chainId that happens to look unusual still takes the EVM/receipt-poll branch.
  assert.equal(await poller.waitForConfirmation(999999, TX_HASH, 1000), "confirmed");
});
