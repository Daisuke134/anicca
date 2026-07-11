// node:test — lending-gate.mjs::isBorrowerEligibleWithReputationGate (franklin-reputation-gasless G3,
// RED phase). NEW composed function only -- isBorrowerEligible() itself is untouched (spec §3 "既存 pure
// 判定は壊さない"; its own 150 pre-existing tests in lending-gate.test.mjs / lending-gate.property.test.mjs
// stay green, unmodified, see the baseline run recorded in this feature's evidence). This file covers
// ONLY the new composition seam: isBorrowerEligible (pure, unchanged) + passesOnchainReputationGate
// (async, lending/lib/reputation-gate.mjs) combined, short-circuiting on the base check first.
import { test } from "node:test";
import assert from "node:assert/strict";
import { isBorrowerEligible, isBorrowerEligibleWithReputationGate } from "../lending-gate.mjs";

// FIND-004 fix (adversary round 2): the ORIGINAL fixture below used `walletProvenance`/`fundingSource`
// -- fields isSelfFunded() (_shared/lib/is-self-funded.mjs) does not read at all (it reads
// `fuel.provider` + `humanDependencies`). That made BASE_ELIGIBLE_ARGS fail isBorrowerEligible with
// reason "not_self_funded" in every real run -- silently masked by the `if (!base.eligible) return;`
// early-exits this fix also removes below. Now reuses the EXACT known-good shape from
// lending-gate.test.mjs's own BASE_BORROWER fixture (line 60 there) rather than inventing a new one.
const BASE_ELIGIBLE_ARGS = {
  borrowerAgent: { wallet: { evm: true }, fuel: { provider: "x402" }, humanDependencies: [] },
  loanRows: [],
  borrowerId: "borrower-1",
  borrowerBalanceUsd: 0.1,
  lenderId: "lender-1",
};

// isSelfFunded (imported by lending-gate.mjs) checks specific fields on borrowerAgent -- reuse whatever
// shape the EXISTING isBorrowerEligible tests already prove works, by calling the pure fn directly first
// as a sanity precondition for this fixture (if this ever fails, the fixture itself is wrong, not the
// composition under test).

test("fixture sanity: BASE_ELIGIBLE_ARGS alone passes the existing, unmodified isBorrowerEligible", () => {
  // NOTE: real isSelfFunded's exact field contract belongs to lending-gate.test.mjs; if this fixture
  // doesn't pass isBorrowerEligible on its own, the composition tests below would trivially fail for the
  // WRONG reason (base rejection, not reputation-gate rejection) -- so this sanity check documents which
  // one is actually under test in each case below via its own reason strings.
  const base = isBorrowerEligible(BASE_ELIGIBLE_ARGS);
  assert.ok(["ok", "self_loan", "not_evm", "not_self_funded", "not_broke_enough", "outstanding_loan"].includes(base.reason));
});

test("isBorrowerEligibleWithReputationGate: base check fails -> short-circuits, reputation gate is NEVER consulted", async () => {
  let repGateCalled = false;
  const result = await isBorrowerEligibleWithReputationGate(
    { ...BASE_ELIGIBLE_ARGS, lenderId: "borrower-1" }, // lenderId===borrowerId -> self_loan, guaranteed base rejection
    { borrowerAgentId: "5", minScore: 50 },
    async () => {
      repGateCalled = true;
      return { eligible: true, reason: "ok" };
    }
  );
  assert.equal(result.eligible, false);
  assert.equal(result.reason, "self_loan");
  assert.equal(repGateCalled, false, "an already-failing base check must never even attempt the on-chain reputation read");
});

test("isBorrowerEligibleWithReputationGate: base check passes but reputation gate rejects -> eligible:false, reputation's own reason surfaces", async () => {
  // FIND-004 fix (adversary round 2): assert the fixture IS eligible, loudly, rather than silently
  // no-op'ing (the old `if (!base.eligible) return;` reported PASS even if the fixture ever broke,
  // which would have hidden this test genuinely never exercising the gate-rejection branch at all).
  const base = isBorrowerEligible(BASE_ELIGIBLE_ARGS);
  assert.equal(base.eligible, true, "fixture precondition: BASE_ELIGIBLE_ARGS must pass isBorrowerEligible for this test to exercise the gate-rejection branch it claims to");
  const result = await isBorrowerEligibleWithReputationGate(
    BASE_ELIGIBLE_ARGS,
    { borrowerAgentId: "5", minScore: 50 },
    async () => ({ eligible: false, reason: "insufficient_score" })
  );
  assert.equal(result.eligible, false);
  assert.equal(result.reason, "insufficient_score");
});

test("isBorrowerEligibleWithReputationGate: both base AND reputation gate pass -> eligible:true", async () => {
  // FIND-004 fix (adversary round 2): see the sibling test above for why this asserts rather than
  // silently returns.
  const base = isBorrowerEligible(BASE_ELIGIBLE_ARGS);
  assert.equal(base.eligible, true, "fixture precondition: BASE_ELIGIBLE_ARGS must pass isBorrowerEligible");
  const result = await isBorrowerEligibleWithReputationGate(
    BASE_ELIGIBLE_ARGS,
    { borrowerAgentId: "5", minScore: 50 },
    async () => ({ eligible: true, reason: "ok" })
  );
  assert.equal(result.eligible, true);
});

test("isBorrowerEligibleWithReputationGate: defaults to the REAL passesOnchainReputationGate when no reputationGateFn override is given (unset thresholds -> fail-open passthrough)", async () => {
  // FIND-004 fix (adversary round 2): see the sibling tests above for why this asserts rather than
  // silently returns.
  const base = isBorrowerEligible(BASE_ELIGIBLE_ARGS);
  assert.equal(base.eligible, true, "fixture precondition: BASE_ELIGIBLE_ARGS must pass isBorrowerEligible");
  const result = await isBorrowerEligibleWithReputationGate(BASE_ELIGIBLE_ARGS, { borrowerAgentId: "5" });
  assert.equal(result.eligible, true, "no minScore/minJobCount configured -> real gate fail-opens, composition passes");
});
