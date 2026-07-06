// node:test — pure state-machine tests for the gig board (no fs, no network). See lib/store.mjs.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as store from "../lib/store.mjs";

function posted() {
  const s0 = store.emptyState();
  const { state, gig } = store.applyPost(s0, {
    poster: "0xPoster",
    taskSpec: "translate 500 words",
    bountyUsdcBase: 1000,
    escrowAddress: "0xEscrow",
    postTx: "0xpostTx",
  });
  return { s0, state, gig };
}

test("applyPost creates an OPEN gig recording the real escrow-funding tx, without mutating the input state", () => {
  const { s0, state, gig } = posted();
  assert.equal(gig.status, "open");
  assert.equal(gig.postTx, "0xpostTx");
  assert.equal(gig.bountyUsdcBase, 1000);
  assert.deepEqual(s0, { nextId: 1, gigs: {} }, "original state must be untouched (immutability)");
  assert.equal(state.gigs[gig.id].status, "open");
});

test("applyTake assigns the taker and moves OPEN -> TAKEN", () => {
  const { state, gig } = posted();
  const result = store.applyTake(state, gig.id, "0xTaker");
  assert.equal(result.ok, true);
  assert.equal(result.gig.status, "taken");
  assert.equal(result.gig.taker, "0xTaker");
});

test("applyTake rejects taking a gig that is already taken (not 'open')", () => {
  const { state, gig } = posted();
  const first = store.applyTake(state, gig.id, "0xTaker1");
  const second = store.applyTake(first.state, gig.id, "0xTaker2");
  assert.equal(second.ok, false);
  assert.match(second.reason, /not 'open'/);
});

test("applyDeliver records the deliverable and moves TAKEN -> DELIVERED", () => {
  const { state, gig } = posted();
  const taken = store.applyTake(state, gig.id, "0xTaker");
  const result = store.applyDeliver(taken.state, gig.id, "https://example.com/result.txt");
  assert.equal(result.ok, true);
  assert.equal(result.gig.status, "delivered");
  assert.equal(result.gig.deliverable, "https://example.com/result.txt");
});

test("applyDeliver rejects delivering a gig that hasn't been taken yet", () => {
  const { state, gig } = posted();
  const result = store.applyDeliver(state, gig.id, "too early");
  assert.equal(result.ok, false);
  assert.match(result.reason, /not 'taken'/);
});

test("applyVerifyAndPay rejects verifying before delivery (fail-closed ordering)", () => {
  const { state, gig } = posted();
  const taken = store.applyTake(state, gig.id, "0xTaker");
  const result = store.applyVerifyAndPay(taken.state, gig.id, { verified: true, payoutTx: "0xpayout" });
  assert.equal(result.ok, false);
  assert.match(result.reason, /not 'delivered'/);
});

test("★CORE★ applyVerifyAndPay(verified:true) WITHOUT a payoutTx is REFUSED -- no-verify-evidence -> no-pay, fail-closed", () => {
  const { state, gig } = posted();
  const taken = store.applyTake(state, gig.id, "0xTaker");
  const delivered = store.applyDeliver(taken.state, gig.id, "result");
  const result = store.applyVerifyAndPay(delivered.state, gig.id, { verified: true, payoutTx: undefined });
  assert.equal(result.ok, false);
  assert.match(result.reason, /refusing to mark paid without on-chain evidence/);
  assert.equal(store.getGig(delivered.state, gig.id).status, "delivered", "gig must remain 'delivered', never silently 'paid'");
});

test("applyVerifyAndPay(verified:true, payoutTx) moves DELIVERED -> PAID and records the real tx", () => {
  const { state, gig } = posted();
  const taken = store.applyTake(state, gig.id, "0xTaker");
  const delivered = store.applyDeliver(taken.state, gig.id, "result");
  const result = store.applyVerifyAndPay(delivered.state, gig.id, { verified: true, payoutTx: "0xpayoutTx" });
  assert.equal(result.ok, true);
  assert.equal(result.gig.status, "paid");
  assert.equal(result.gig.payoutTx, "0xpayoutTx");
});

test("applyVerifyAndPay(verified:false) moves DELIVERED -> REJECTED, no payoutTx ever stored", () => {
  const { state, gig } = posted();
  const taken = store.applyTake(state, gig.id, "0xTaker");
  const delivered = store.applyDeliver(taken.state, gig.id, "result");
  const result = store.applyVerifyAndPay(delivered.state, gig.id, { verified: false });
  assert.equal(result.ok, true);
  assert.equal(result.gig.status, "rejected");
  assert.equal(result.gig.payoutTx, null);
});

test("listGigs filters by status; getGig returns null for an unknown id", () => {
  const { state, gig } = posted();
  assert.equal(store.listGigs(state, { status: "open" }).length, 1);
  assert.equal(store.listGigs(state, { status: "paid" }).length, 0);
  assert.equal(store.getGig(state, "does-not-exist"), null);
});
