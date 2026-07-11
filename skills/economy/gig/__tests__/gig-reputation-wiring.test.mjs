// node:test — gig.mjs's G2 wiring (franklin-reputation-gasless): gigVerifyAndPay records ERC-8004
// Reputation feedback (+100 on real payout, -100 on reject) via injected ensureGasFn/giveFeedbackFn,
// STRICTLY fail-open (spec §4 MONEY-SAFETY: "reputation は fail-open: 書込/読取の失敗で payout・lending
// の本処理を壊さない") -- every test here proves a reputation-layer failure NEVER changes `ok`/`paid`/the
// board state that the existing 51 gig.test.mjs/store.test.mjs/lock.test.mjs tests already lock down.
// This file is ADDITIVE ONLY -- it does not modify gig.test.mjs's existing 12 tests or their fakes.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";
import { gigPost, gigTake, gigDeliver, gigVerifyAndPay } from "../gig.mjs";

process.env.GIG_ESCROW_ADDRESS = "0xEscrow00000000000000000000000000000000";
process.env.GIG_ESCROW_PRIVATE_KEY = generatePrivateKey();

const POSTER_PK = generatePrivateKey();
const POSTER_ADDR = privateKeyToAccount(POSTER_PK).address;
const TAKER_ADDR = "0xTaker00000000000000000000000000000taker";

async function tmpState() {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "gig-rep-test-"));
  return path.join(d, "gigs.json");
}
const fakePay = () => async ({ privateKey, to, amountBase }) => ({
  ok: true,
  tx: "0xfaketx",
  payerAddress: privateKeyToAccount(privateKey).address,
  to,
  amountBase,
});
const validIdentity = async ({ expectedAddress }) => ({ ok: true, valid: true, owner: expectedAddress });

async function postTakenDelivered(statePath) {
  const posted = await gigPost({
    posterPrivateKey: POSTER_PK,
    posterAgentId: "8",
    taskSpec: "test task",
    bountyUsdcBase: 1000,
    statePath,
    pay: fakePay(),
    verifyIdentityFn: validIdentity,
  });
  assert.equal(posted.ok, true, "setup: gig_post must succeed");
  await gigTake({ gigId: posted.gig.id, takerAddress: TAKER_ADDR, takerAgentId: "9", statePath, verifyIdentityFn: validIdentity });
  await gigDeliver({ gigId: posted.gig.id, deliverable: "result", statePath });
  return posted.gig.id;
}

const alwaysReadyGas = async () => ({ ok: true, action: "ok" });

test("gigVerifyAndPay(verified:true): on success, calls giveFeedbackFn with positive:true for the taker's agentId", async () => {
  const statePath = await tmpState();
  const gigId = await postTakenDelivered(statePath);
  let feedbackCall = null;
  const result = await gigVerifyAndPay({
    gigId,
    verified: true,
    posterPrivateKey: POSTER_PK,
    statePath,
    pay: fakePay(),
    verifyIdentityFn: validIdentity,
    ensureGasFn: alwaysReadyGas,
    giveFeedbackFn: async (args) => {
      feedbackCall = args;
      return { ok: true, tx: "0xfeedbacktx" };
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.paid, true);
  assert.ok(feedbackCall, "giveFeedbackFn must be called on a successful payout");
  assert.equal(feedbackCall.agentId, "9", "feedback targets the TAKER's agentId, not the poster's");
  assert.equal(feedbackCall.positive, true);
});

test("gigVerifyAndPay(verified:false): on reject, calls giveFeedbackFn with positive:false", async () => {
  const statePath = await tmpState();
  const gigId = await postTakenDelivered(statePath);
  let feedbackCall = null;
  const result = await gigVerifyAndPay({
    gigId,
    verified: false,
    posterPrivateKey: POSTER_PK,
    statePath,
    pay: fakePay(),
    verifyIdentityFn: validIdentity,
    ensureGasFn: alwaysReadyGas,
    giveFeedbackFn: async (args) => {
      feedbackCall = args;
      return { ok: true, tx: "0xfeedbacktx" };
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.paid, false);
  assert.ok(feedbackCall);
  assert.equal(feedbackCall.positive, false);
});

test("★MONEY-SAFETY fail-open★ giveFeedbackFn throwing does NOT change gigVerifyAndPay's ok/paid/tx result -- payout is already final", async () => {
  const statePath = await tmpState();
  const gigId = await postTakenDelivered(statePath);
  const result = await gigVerifyAndPay({
    gigId,
    verified: true,
    posterPrivateKey: POSTER_PK,
    statePath,
    pay: fakePay(),
    verifyIdentityFn: validIdentity,
    ensureGasFn: alwaysReadyGas,
    giveFeedbackFn: async () => {
      throw new Error("reputation registry exploded");
    },
  });
  assert.equal(result.ok, true, "a reputation-layer crash must never flip a successful payout to failure");
  assert.equal(result.paid, true);
  assert.equal(result.tx, "0xfaketx", "the real payout tx is still reported");
});

test("★MONEY-SAFETY fail-open★ ensureGasFn returning ok:false (e.g. mainnet needs_gas) does NOT change gigVerifyAndPay's ok/paid result, and giveFeedbackFn is never called", async () => {
  const statePath = await tmpState();
  const gigId = await postTakenDelivered(statePath);
  let feedbackCalled = false;
  const result = await gigVerifyAndPay({
    gigId,
    verified: true,
    posterPrivateKey: POSTER_PK,
    statePath,
    pay: fakePay(),
    verifyIdentityFn: validIdentity,
    ensureGasFn: async () => ({ ok: false, action: "needs_gas", reason: "mainnet gas insufficient" }),
    giveFeedbackFn: async () => {
      feedbackCalled = true;
      return { ok: true, tx: "0xshouldnothappen" };
    },
  });
  assert.equal(result.ok, true, "gas-preflight failure for the reputation write must never affect the already-final payout");
  assert.equal(result.paid, true);
  assert.equal(feedbackCalled, false, "no gas -> no feedback attempt (ensureGas is a real preflight, not decorative)");
  assert.equal(result.reputation.ok, false, "the reputation outcome is still reported for observability, just never allowed to affect ok/paid");
});

test("reputation write happens AFTER the real payout settles, never before (fund-safety ordering)", async () => {
  const statePath = await tmpState();
  const gigId = await postTakenDelivered(statePath);
  const order = [];
  await gigVerifyAndPay({
    gigId,
    verified: true,
    posterPrivateKey: POSTER_PK,
    statePath,
    pay: async (args) => {
      order.push("payout");
      return fakePay()(args);
    },
    verifyIdentityFn: validIdentity,
    ensureGasFn: alwaysReadyGas,
    giveFeedbackFn: async (args) => {
      order.push("feedback");
      return { ok: true, tx: "0xfeedbacktx" };
    },
  });
  assert.deepEqual(order, ["payout", "feedback"]);
});

test("gigVerifyAndPay still defaults to fail-closed poster-auth (FINDING 1) exactly as before -- reputation wiring adds no bypass", async () => {
  const statePath = await tmpState();
  const gigId = await postTakenDelivered(statePath);
  const ATTACKER_PK = generatePrivateKey();
  const result = await gigVerifyAndPay({
    gigId,
    verified: true,
    posterPrivateKey: ATTACKER_PK,
    statePath,
    pay: fakePay(),
    verifyIdentityFn: validIdentity,
  });
  assert.equal(result.ok, false);
  assert.match(result.reason, /not the poster/);
});
