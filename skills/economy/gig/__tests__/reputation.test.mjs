// node:test — lib/reputation.mjs (franklin-reputation-gasless G2, RED phase). buildFeedbackArgs is pure
// (no network) -- unit-tested directly. giveFeedback/getReputationSummary's real network calls are
// exercised through the real viem writeContract/readContract functions but those are only invoked with
// injected fake wallet/public clients here (no real testnet funds, no real network round-trip) --
// consistent with gig.mjs's own DI convention for lib/escrow.mjs and lib/identity.mjs.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  buildFeedbackArgs,
  giveFeedback,
  getReputationSummary,
  GIG_COMPLETE_TAG1,
  POSITIVE_FEEDBACK_VALUE,
  NEGATIVE_FEEDBACK_VALUE,
} from "../lib/reputation.mjs";

// ============ buildFeedbackArgs (pure) ============

test("buildFeedbackArgs: positive outcome -> +100 value, gig-complete tag", () => {
  const args = buildFeedbackArgs({ agentId: "42", positive: true, gigId: "7" });
  assert.equal(args[0], 42n, "agentId is coerced to BigInt");
  assert.equal(args[1], POSITIVE_FEEDBACK_VALUE);
  assert.equal(args[2], 0, "valueDecimals defaults to 0 (whole-number reputation points)");
  assert.equal(args[3], GIG_COMPLETE_TAG1);
});

test("buildFeedbackArgs: negative outcome (reject) -> -100 value", () => {
  const args = buildFeedbackArgs({ agentId: "42", positive: false, gigId: "7" });
  assert.equal(args[1], NEGATIVE_FEEDBACK_VALUE);
});

test("buildFeedbackArgs: same gigId always produces the same feedbackHash (deterministic, no randomness)", () => {
  const a = buildFeedbackArgs({ agentId: "1", positive: true, gigId: "gig-123" });
  const b = buildFeedbackArgs({ agentId: "1", positive: true, gigId: "gig-123" });
  assert.equal(a[7], b[7]);
});

test("buildFeedbackArgs: different gigIds produce different feedbackHash", () => {
  const a = buildFeedbackArgs({ agentId: "1", positive: true, gigId: "gig-123" });
  const b = buildFeedbackArgs({ agentId: "1", positive: true, gigId: "gig-456" });
  assert.notEqual(a[7], b[7]);
});

test("buildFeedbackArgs: throws (loudly, at build time) when agentId is missing -- never silently gives feedback for agentId=undefined", () => {
  assert.throws(() => buildFeedbackArgs({ agentId: null, positive: true, gigId: "1" }));
});

// ============ giveFeedback / getReputationSummary (network calls, dependency-injected) ============

test("giveFeedback: on writeContract success + confirmed receipt, returns ok:true with the real tx hash", async () => {
  const fakeWalletClient = { writeContract: async () => "0xfeedbacktx1" };
  const fakePublicClient = { waitForTransactionReceipt: async () => ({ status: "success" }) };
  const result = await giveFeedback({
    signerPrivateKey: "0x" + "11".repeat(32),
    agentId: "9",
    positive: true,
    gigId: "gigX",
    walletClientFactory: () => fakeWalletClient,
    publicClientFactory: () => fakePublicClient,
  });
  assert.equal(result.ok, true);
  assert.equal(result.tx, "0xfeedbacktx1");
});

test("★fail-open★ giveFeedback: a reverted feedback tx returns ok:false, never throws", async () => {
  const fakeWalletClient = { writeContract: async () => "0xfeedbacktx2" };
  const fakePublicClient = { waitForTransactionReceipt: async () => ({ status: "reverted" }) };
  const result = await giveFeedback({
    signerPrivateKey: "0x" + "22".repeat(32),
    agentId: "9",
    positive: true,
    gigId: "gigX",
    walletClientFactory: () => fakeWalletClient,
    publicClientFactory: () => fakePublicClient,
  });
  assert.equal(result.ok, false);
});

test("★fail-open★ giveFeedback: a writeContract exception (e.g. 'Self-feedback not allowed' revert) returns {ok:false,reason}, never throws out of the function", async () => {
  const fakeWalletClient = {
    writeContract: async () => {
      throw new Error("Self-feedback not allowed");
    },
  };
  const result = await giveFeedback({
    signerPrivateKey: "0x" + "33".repeat(32),
    agentId: "9",
    positive: true,
    gigId: "gigX",
    walletClientFactory: () => fakeWalletClient,
    publicClientFactory: () => ({}),
  });
  assert.equal(result.ok, false);
  assert.match(result.reason, /Self-feedback/);
});

test("getReputationSummary: refuses (ok:false) with empty clientAddresses WITHOUT making a network call -- the contract itself reverts on empty array (verified against ReputationRegistryUpgradeable.sol getSummary), so we fail fast instead of wasting a call", async () => {
  let called = false;
  const result = await getReputationSummary({
    agentId: "9",
    clientAddresses: [],
    publicClientFactory: () => {
      called = true;
      return { readContract: async () => [0n, 0n, 0] };
    },
  });
  assert.equal(result.ok, false);
  assert.equal(called, false, "must never construct a client for a call we already know will revert");
});

test("getReputationSummary: on success, returns count/summaryValue/decimals as plain numbers", async () => {
  const fakePublicClient = { readContract: async () => [3n, 250n, 0] };
  const result = await getReputationSummary({
    agentId: "9",
    clientAddresses: ["0xClient00000000000000000000000000000001"],
    publicClientFactory: () => fakePublicClient,
  });
  assert.equal(result.ok, true);
  assert.equal(result.count, 3);
  assert.equal(result.summaryValue, 250);
  assert.equal(result.decimals, 0);
});

test("★fail-open★ getReputationSummary: a readContract exception returns {ok:false,reason}, never throws", async () => {
  const result = await getReputationSummary({
    agentId: "9",
    clientAddresses: ["0xClient00000000000000000000000000000001"],
    publicClientFactory: () => ({
      readContract: async () => {
        throw new Error("network down");
      },
    }),
  });
  assert.equal(result.ok, false);
  assert.match(result.reason, /network down/);
});
