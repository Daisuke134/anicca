// VCSDD anicca-agent-spawn, sprint-2, contract-review round 2 (resolves FIND-001/002/003a). Direct
// unit coverage for spawn-orchestrator.mjs's two newly-exported pieces:
//  - defaultDeploy: REQ-304's funding-gate wiring (evaluateAkashFundingGate called before ANY
//    deploy-akash.sh invocation, never invoking it at all when the gate is not ready).
//  - assertRealEvmAddress: REQ-201's hard SHALL that a generated EVM address is not gen-wallet.sh's
//    own documented sha256 fallback, detected by an independent keccak re-derivation (viem).
import { test } from "node:test";
import assert from "node:assert/strict";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";
import { defaultDeploy, assertRealEvmAddress, shelterCostUsdFromSettledPrice } from "../spawn-orchestrator.mjs";

// ---------------------------------------------------------------------------
// PROP-304b/c/d/f (Round 2 additions, resolves FIND-001/002): defaultDeploy calls
// evaluateAkashFundingGate before invoking deploy-akash.sh; a not-ready gate (after both passes)
// fails cleanly, with deploy-akash.sh never invoked at all.
// ---------------------------------------------------------------------------

test("defaultDeploy: non-akash target is rejected exactly as before -- the funding gate is never even evaluated", async () => {
  const result = await defaultDeploy({ target: "nosana", childId: "anicca-cTEST" }, {
    queryBalanceAkt: async () => { throw new Error("must not be called for a non-akash target"); },
  });
  assert.equal(result.ok, false);
  assert.match(result.error, /no deploy path implemented/);
});

test("defaultDeploy: funding gate ready on the FIRST pass -> deploy-akash.sh is invoked, bridge never attempted", async () => {
  let bridgeCalls = 0;
  let deployCalls = 0;
  const result = await defaultDeploy(
    { target: "akash", childId: "anicca-cTEST" },
    {
      queryBalanceAkt: async () => 30, // >= spawn_cost_akt(25) + buffer_akt(1), per spawn-child/config.json
      attemptBridge: async () => { bridgeCalls += 1; },
      runDeployAkash: async (childId) => {
        deployCalls += 1;
        return JSON.stringify({ dseq: `dseq-${childId}`, priceAmount: "5", priceDenom: "uact" });
      },
    }
  );
  assert.equal(bridgeCalls, 0, "a ready first pass must never attempt the bridge");
  assert.equal(deployCalls, 1);
  assert.equal(result.ok, true);
  assert.equal(result.leaseId, "dseq-anicca-cTEST");
  assert.equal(result.shelterCostUsd, 0.000005, "FIND-002/PROP-303c: uact settled price converts to USD via the fixed 1e-6 peg (AEP-76)");
});

test("defaultDeploy: funding gate not ready after BOTH passes -> deploy-akash.sh is NEVER invoked, fails cleanly", async () => {
  let deployCalls = 0;
  let bridgeCalls = 0;
  const result = await defaultDeploy(
    { target: "akash", childId: "anicca-cTEST" },
    {
      queryBalanceAkt: async () => 2, // stays insufficient even after the bridge attempt
      attemptBridge: async () => { bridgeCalls += 1; },
      runDeployAkash: async () => { deployCalls += 1; return JSON.stringify({ dseq: "dseq-should-never-happen", priceAmount: "5", priceDenom: "uact" }); },
    }
  );
  assert.equal(bridgeCalls, 1, "an insufficient first pass must trigger exactly one bridge attempt");
  assert.equal(deployCalls, 0, "deploy-akash.sh must NEVER be invoked when the funding gate is not ready");
  assert.equal(result.ok, false);
  assert.match(result.error, /REQ-304 funding gate not ready/);
});

test("defaultDeploy: funding gate not ready on first pass, ready after the bridge lands funds on the second pass -> deploy proceeds", async () => {
  let queryCount = 0;
  let deployCalls = 0;
  const result = await defaultDeploy(
    { target: "akash", childId: "anicca-cTEST" },
    {
      queryBalanceAkt: async () => { queryCount += 1; return queryCount === 1 ? 2 : 30; },
      attemptBridge: async () => {},
      runDeployAkash: async () => {
        deployCalls += 1;
        return JSON.stringify({ dseq: "dseq-after-bridge", priceAmount: "10000", priceDenom: "uact" });
      },
    }
  );
  assert.equal(queryCount, 2, "balanceAkt must be freshly re-queried for each of the (at most two) passes");
  assert.equal(deployCalls, 1);
  assert.equal(result.ok, true);
  assert.equal(result.leaseId, "dseq-after-bridge");
  assert.equal(result.shelterCostUsd, 0.01);
});

test("defaultDeploy: a deploy-akash.sh failure (post-funding-gate) is still reported as before", async () => {
  const result = await defaultDeploy(
    { target: "akash", childId: "anicca-cTEST" },
    {
      queryBalanceAkt: async () => 30,
      attemptBridge: async () => {},
      runDeployAkash: async () => { throw new Error("no open bids for dseq"); },
    }
  );
  assert.equal(result.ok, false);
  assert.match(result.error, /deploy-akash.sh failed/);
});

test("defaultDeploy: deploy-akash.sh's stdout is not valid JSON -> fails cleanly, never crashes/fabricates a leaseId (fail-closed on a malformed output shape)", async () => {
  const result = await defaultDeploy(
    { target: "akash", childId: "anicca-cTEST" },
    {
      queryBalanceAkt: async () => 30,
      attemptBridge: async () => {},
      runDeployAkash: async () => "not-json-777",
    }
  );
  assert.equal(result.ok, false);
  assert.match(result.error, /deploy-akash\.sh produced invalid output/);
});

// ---------------------------------------------------------------------------
// FIND-002/PROP-303c: shelterCostUsdFromSettledPrice's pure uact->USD conversion.
// ---------------------------------------------------------------------------

test("shelterCostUsdFromSettledPrice: a real uact settled price converts via the fixed AEP-76 1e-6 USD peg, never a fetched spot price", () => {
  assert.equal(shelterCostUsdFromSettledPrice({ priceAmount: "10000", priceDenom: "uact" }), 0.01);
  assert.equal(shelterCostUsdFromSettledPrice({ priceAmount: "5", priceDenom: "uact" }), 0.000005);
});

test("shelterCostUsdFromSettledPrice: any denom other than uact fails closed to null (never prices the wrong asset)", () => {
  assert.equal(shelterCostUsdFromSettledPrice({ priceAmount: "10000", priceDenom: "uakt" }), null);
  assert.equal(shelterCostUsdFromSettledPrice({ priceAmount: "10000", priceDenom: undefined }), null);
});

test("shelterCostUsdFromSettledPrice: a non-numeric/negative amount fails closed to null, never NaN/negative", () => {
  assert.equal(shelterCostUsdFromSettledPrice({ priceAmount: "not-a-number", priceDenom: "uact" }), null);
  assert.equal(shelterCostUsdFromSettledPrice({ priceAmount: "-5", priceDenom: "uact" }), null);
});

// ---------------------------------------------------------------------------
// PROP-201a (Round 2 additions, resolves FIND-003a): assertRealEvmAddress.
// ---------------------------------------------------------------------------

test("assertRealEvmAddress: a genuine keccak256-derived address (viem-generated) passes", () => {
  const privateKey = generatePrivateKey();
  const address = privateKeyToAccount(privateKey).address;
  assert.doesNotThrow(() => assertRealEvmAddress({ address, privateKey }));
});

test("assertRealEvmAddress: case-insensitive comparison (checksummed vs lowercase) still passes", () => {
  const privateKey = generatePrivateKey();
  const address = privateKeyToAccount(privateKey).address;
  assert.doesNotThrow(() => assertRealEvmAddress({ address: address.toLowerCase(), privateKey }));
});

test("assertRealEvmAddress: the documented sha256-fallback shape (address that does not re-derive from the private key) is REJECTED", () => {
  const privateKey = generatePrivateKey();
  const realAddress = privateKeyToAccount(privateKey).address;
  // Simulate gen-wallet.sh's own sha256 fallback: a same-shape (0x + 40 hex) address that is NOT the
  // real keccak256-derived address for this private key -- exactly what the fallback branch produces.
  const fallbackShapeAddress = "0x" + "ab".repeat(20);
  assert.notEqual(fallbackShapeAddress.toLowerCase(), realAddress.toLowerCase());
  assert.throws(
    () => assertRealEvmAddress({ address: fallbackShapeAddress, privateKey }),
    /fails independent keccak re-derivation/
  );
});
