// node:test — is_self_funded(agent) join gate (spec .vcsdd/features/anicca-agent-economy §1.2/§3 P0).
// RED phase: this file is written BEFORE ../is-self-funded.mjs exists, so the import itself
// is the first failing assertion (module not found). GREEN = implement to make all pass.
import { test } from "node:test";
import assert from "node:assert/strict";
import { isSelfFunded, selfFundedReasons } from "../is-self-funded.mjs";

// ---------------------------------------------------------------------------
// (a)+(b)+(c) all satisfied -> citizen, gate PASSES.
// ---------------------------------------------------------------------------
test("fresh own-wallet-fueled spawn: own EVM wallet + ClawRouter own-wallet fuel + zero human deps -> PASS", () => {
  const agent = {
    wallet: { evm: true, solana: false },
    fuel: { provider: "clawrouter-own-wallet" },
    humanDependencies: [],
  };
  assert.equal(isSelfFunded(agent), true);
  assert.deepEqual(selfFundedReasons(agent), []);
});

test("automaton (anicca-a3cdd4): ClawRouter own-wallet fuel, own Base EVM wallet -> PASS", () => {
  assert.equal(
    isSelfFunded({
      wallet: { evm: true, solana: false },
      fuel: { provider: "clawrouter-own-wallet" },
      humanDependencies: [],
    }),
    true,
  );
});

test("Franklin: x402 self-settled fuel, own Solana wallet -> PASS", () => {
  assert.equal(
    isSelfFunded({
      wallet: { evm: false, solana: true },
      fuel: { provider: "x402" },
      humanDependencies: [],
    }),
    true,
  );
});

test("fresh spawn on a genuinely free model, own Solana wallet -> PASS", () => {
  assert.equal(
    isSelfFunded({
      wallet: { evm: false, solana: true },
      fuel: { provider: "free-model" },
      humanDependencies: [],
    }),
    true,
  );
});

// ---------------------------------------------------------------------------
// (b) violation: human-billed fuel -> gate FAILS even with a real own wallet.
// ---------------------------------------------------------------------------
test("claude-p-like agent: own wallet present but fuel = anthropic-subscription (human-funded) -> FAIL", () => {
  const agent = {
    wallet: { evm: true, solana: true },
    fuel: { provider: "anthropic-subscription" },
    humanDependencies: [],
  };
  assert.equal(isSelfFunded(agent), false);
  assert.ok(selfFundedReasons(agent).some((r) => r.startsWith("fuel-not-own-funded")));
});

test("human-card-billed fuel -> FAIL (not a citizen, regardless of wallet)", () => {
  assert.equal(
    isSelfFunded({
      wallet: { evm: true, solana: true },
      fuel: { provider: "human-card" },
      humanDependencies: [],
    }),
    false,
  );
});

// ---------------------------------------------------------------------------
// (a) violation: no wallet at all -> gate FAILS regardless of fuel.
// ---------------------------------------------------------------------------
test("agent with no wallet: own-funded fuel but wallet.evm/solana both false -> FAIL", () => {
  const agent = {
    wallet: { evm: false, solana: false },
    fuel: { provider: "x402" },
    humanDependencies: [],
  };
  assert.equal(isSelfFunded(agent), false);
  assert.ok(selfFundedReasons(agent).includes("no-own-wallet"));
});

test("agent with wallet omitted entirely -> FAIL (fail-closed, never throws)", () => {
  assert.doesNotThrow(() => {
    assert.equal(isSelfFunded({ fuel: { provider: "x402" }, humanDependencies: [] }), false);
  });
});

// ---------------------------------------------------------------------------
// (c) violation: human OAuth/KYC/account dependency anywhere in earn/fuel path -> FAIL.
// ---------------------------------------------------------------------------
test("own wallet + own-funded fuel but a human OAuth dependency in the earn path -> FAIL", () => {
  const agent = {
    wallet: { evm: true, solana: false },
    fuel: { provider: "x402" },
    humanDependencies: ["coconala-oauth"],
  };
  assert.equal(isSelfFunded(agent), false);
  assert.ok(selfFundedReasons(agent).some((r) => r.startsWith("human-dependency")));
});

// ---------------------------------------------------------------------------
// Fail-closed edge cases: missing/malformed input never throws, always denies.
// ---------------------------------------------------------------------------
test("fail-closed: agent is null -> FAIL, never throws", () => {
  assert.doesNotThrow(() => {
    assert.equal(isSelfFunded(null), false);
  });
});

test("fail-closed: agent is undefined -> FAIL, never throws", () => {
  assert.doesNotThrow(() => {
    assert.equal(isSelfFunded(undefined), false);
  });
});

test("fail-closed: fuel provider is an unknown/typo'd string -> FAIL (deny, not allow)", () => {
  assert.equal(
    isSelfFunded({
      wallet: { evm: true, solana: false },
      fuel: { provider: "totally-unknown-provider" },
      humanDependencies: [],
    }),
    false,
  );
});

test("fail-closed: fuel object missing entirely -> FAIL", () => {
  assert.equal(
    isSelfFunded({ wallet: { evm: true, solana: false }, humanDependencies: [] }),
    false,
  );
});

test("selfFundedReasons on a fully-passing agent returns an empty array", () => {
  assert.deepEqual(
    selfFundedReasons({
      wallet: { evm: true, solana: true },
      fuel: { provider: "free-model" },
      humanDependencies: [],
    }),
    [],
  );
});
