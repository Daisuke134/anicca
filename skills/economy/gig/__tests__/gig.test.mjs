// node:test — orchestration-layer tests for gig.mjs (the layer where the adversary found 2 real live
// drains + 1 decorative-identity gap). These use REAL fs persistence + REAL per-gig locking (lib/lock.mjs)
// but INJECT fake `pay`/`verifyIdentityFn` implementations -- fast, deterministic, no real network call,
// no real testnet funds at risk. The fakes replace EXTERNAL I/O only; every assertion here is about OUR
// OWN orchestration logic (auth, locking, identity gating), which is exercised for real.
import { test } from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";
import { gigPost, gigTake, gigDeliver, gigVerifyAndPay, gigList } from "../gig.mjs";

// gigPost/gigVerifyAndPay read these from process.env (real production config); since `pay` is faked
// below, the VALUES don't need real testnet funds -- they just need to be present + syntactically valid.
process.env.GIG_ESCROW_ADDRESS = "0xEscrow00000000000000000000000000000000";
process.env.GIG_ESCROW_PRIVATE_KEY = generatePrivateKey();

const POSTER_PK = generatePrivateKey();
const ATTACKER_PK = generatePrivateKey(); // a real key, but NOT the poster's -- simulates finding 1
const POSTER_ADDR = privateKeyToAccount(POSTER_PK).address;
const TAKER_ADDR = "0xTaker00000000000000000000000000000taker";

async function tmpState() {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), "gig-test-"));
  return path.join(d, "gigs.json");
}

function fakePay(counter) {
  return async ({ privateKey, to, amountBase }) => {
    counter.n += 1;
    return { ok: true, tx: `0xfaketx${counter.n}`, payerAddress: privateKeyToAccount(privateKey).address, to, amountBase };
  };
}
function slowFakePay(counter, delayMs) {
  return async ({ privateKey, to, amountBase }) => {
    await new Promise((r) => setTimeout(r, delayMs));
    counter.n += 1;
    return { ok: true, tx: `0xfaketx${counter.n}`, payerAddress: privateKeyToAccount(privateKey).address, to, amountBase };
  };
}
const validIdentity = async ({ expectedAddress }) => ({ ok: true, valid: true, owner: expectedAddress });
const invalidIdentity = async () => ({ ok: true, valid: false, owner: "0xSomeoneElse00000000000000000000000000" });

async function postTakenDelivered(statePath, payCounter) {
  const posted = await gigPost({
    posterPrivateKey: POSTER_PK,
    posterAgentId: "8",
    taskSpec: "test task",
    bountyUsdcBase: 1000,
    statePath,
    pay: fakePay(payCounter),
    verifyIdentityFn: validIdentity,
  });
  assert.equal(posted.ok, true, "setup: gig_post must succeed");
  await gigTake({ gigId: posted.gig.id, takerAddress: TAKER_ADDR, takerAgentId: "9", statePath, verifyIdentityFn: validIdentity });
  await gigDeliver({ gigId: posted.gig.id, deliverable: "result", statePath });
  return posted.gig.id;
}

// ============ FINDING 1: no poster auth on verify_and_pay ============

test("★FINDING 1★ gig_verify_and_pay REJECTS a non-poster caller -- no payout is attempted", async () => {
  const statePath = await tmpState();
  const payoutCounter = { n: 0 };
  const gigId = await postTakenDelivered(statePath, { n: 0 });

  const attacker = await gigVerifyAndPay({
    gigId,
    verified: true,
    posterPrivateKey: ATTACKER_PK, // NOT the poster's key
    statePath,
    pay: fakePay(payoutCounter),
    verifyIdentityFn: validIdentity,
  });

  assert.equal(attacker.ok, false, "a non-poster's verify_and_pay must be rejected");
  assert.match(attacker.reason, /not the poster/);
  assert.equal(payoutCounter.n, 0, "the escrow-release payout function must NEVER be called for a non-poster caller");

  const list = await gigList({ statePath });
  assert.equal(list.gigs[0].status, "delivered", "gig must remain 'delivered', never 'paid' via an attacker call");
});

test("gig_verify_and_pay ACCEPTS the real poster and pays out exactly once", async () => {
  const statePath = await tmpState();
  const payoutCounter = { n: 0 };
  const gigId = await postTakenDelivered(statePath, { n: 0 });

  const result = await gigVerifyAndPay({
    gigId,
    verified: true,
    posterPrivateKey: POSTER_PK,
    statePath,
    pay: fakePay(payoutCounter),
    verifyIdentityFn: validIdentity,
  });

  assert.equal(result.ok, true);
  assert.equal(result.paid, true);
  assert.equal(payoutCounter.n, 1);
  const list = await gigList({ statePath });
  assert.equal(list.gigs[0].status, "paid");
});

// ============ FINDING 2: double-pay race ============

test("★FINDING 2★ two CONCURRENT gig_verify_and_pay(true) calls on the SAME gig pay out EXACTLY ONCE", async () => {
  const statePath = await tmpState();
  const payoutCounter = { n: 0 };
  const gigId = await postTakenDelivered(statePath, { n: 0 });

  const call = () =>
    gigVerifyAndPay({
      gigId,
      verified: true,
      posterPrivateKey: POSTER_PK,
      statePath,
      pay: slowFakePay(payoutCounter, 50), // artificial delay reproduces the race window the adversary hit
      verifyIdentityFn: validIdentity,
    });

  const [a, b] = await Promise.all([call(), call()]);
  const results = [a, b];
  const paidResults = results.filter((r) => r.ok && r.paid === true);
  const rejectedResults = results.filter((r) => !r.ok);

  assert.equal(paidResults.length, 1, "exactly ONE of the two concurrent calls must succeed in paying");
  assert.equal(rejectedResults.length, 1, "the OTHER concurrent call must be rejected (fail-closed lock contention)");
  assert.equal(payoutCounter.n, 1, "the escrow-release payout function must be invoked EXACTLY ONCE, not twice");

  const list = await gigList({ statePath });
  assert.equal(list.gigs[0].status, "paid");
  assert.equal(list.gigs[0].payoutTx, paidResults[0].tx, "the recorded payoutTx must be the one real payout, not clobbered");
});

test("gig_take + gig_deliver on the same gig are also serialized by the per-gig lock (no lost updates)", async () => {
  const statePath = await tmpState();
  const posted = await gigPost({
    posterPrivateKey: POSTER_PK,
    posterAgentId: "8",
    taskSpec: "test task",
    bountyUsdcBase: 1000,
    statePath,
    pay: fakePay({ n: 0 }),
    verifyIdentityFn: validIdentity,
  });
  const [t1, t2] = await Promise.all([
    gigTake({ gigId: posted.gig.id, takerAddress: "0xTakerA000000000000000000000000000000A", takerAgentId: "9", statePath, verifyIdentityFn: validIdentity }),
    gigTake({ gigId: posted.gig.id, takerAddress: "0xTakerB000000000000000000000000000000B", takerAgentId: "10", statePath, verifyIdentityFn: validIdentity }),
  ]);
  const succeeded = [t1, t2].filter((r) => r.ok);
  assert.equal(succeeded.length, 1, "only one of two concurrent takes on the same OPEN gig may succeed");
});

// ============ FINDING 3: ERC-8004 identity not enforced ============

test("★FINDING 3★ gig_post REJECTS a poster with an invalid ERC-8004 identity -- no escrow funding attempted, no gig created", async () => {
  const statePath = await tmpState();
  const payoutCounter = { n: 0 };
  const result = await gigPost({
    posterPrivateKey: POSTER_PK,
    posterAgentId: "999",
    taskSpec: "test task",
    bountyUsdcBase: 1000,
    statePath,
    pay: fakePay(payoutCounter),
    verifyIdentityFn: invalidIdentity,
  });
  assert.equal(result.ok, false);
  assert.match(result.reason, /poster ERC-8004 identity invalid/);
  assert.equal(payoutCounter.n, 0, "escrow-funding settle must never be attempted for an unverified poster");
  const list = await gigList({ statePath });
  assert.equal(list.gigs.length, 0, "no gig may be created for an unverified poster");
});

test("★FINDING 3★ gig_take REJECTS a taker with an invalid ERC-8004 identity -- gig stays OPEN", async () => {
  const statePath = await tmpState();
  const posted = await gigPost({
    posterPrivateKey: POSTER_PK,
    posterAgentId: "8",
    taskSpec: "test task",
    bountyUsdcBase: 1000,
    statePath,
    pay: fakePay({ n: 0 }),
    verifyIdentityFn: validIdentity,
  });
  const result = await gigTake({ gigId: posted.gig.id, takerAddress: TAKER_ADDR, takerAgentId: "666", statePath, verifyIdentityFn: invalidIdentity });
  assert.equal(result.ok, false);
  assert.match(result.reason, /taker ERC-8004 identity invalid/);
  const list = await gigList({ statePath });
  assert.equal(list.gigs[0].status, "open", "gig must remain OPEN, never assigned to an unverified taker");
});

test("★FINDING 3★ gig_verify_and_pay RE-verifies taker identity at payout time -- no payout if it's since gone invalid", async () => {
  const statePath = await tmpState();
  const payoutCounter = { n: 0 };
  const gigId = await postTakenDelivered(statePath, { n: 0 }); // taker identity was valid AT TAKE time

  const result = await gigVerifyAndPay({
    gigId,
    verified: true,
    posterPrivateKey: POSTER_PK,
    statePath,
    pay: fakePay(payoutCounter),
    verifyIdentityFn: invalidIdentity, // but identity check at PAYOUT time now fails
  });

  assert.equal(result.ok, false);
  assert.match(result.reason, /taker ERC-8004 identity invalid at payout time/);
  assert.equal(payoutCounter.n, 0, "escrow-release must never be attempted if the taker's identity fails re-verification");
  const list = await gigList({ statePath });
  assert.equal(list.gigs[0].status, "delivered", "gig must remain 'delivered', never falsely 'paid'");
});

// ============ GAP 2 (round 3): cross-gig shared-state clobber ============

test("★GAP 2★ a SLOW verify_and_pay on gig X does not clobber a concurrent take on unrelated gig Y", async () => {
  const statePath = await tmpState();
  const payoutCounter = { n: 0 };

  // gig X: already open->taken->delivered, about to be verify_and_paid SLOWLY
  const gigXId = await postTakenDelivered(statePath, payoutCounter);
  // gig Y: freshly posted, still OPEN -- someone else is about to take it while X is mid-settle
  const postedY = await gigPost({
    posterPrivateKey: POSTER_PK,
    posterAgentId: "8",
    taskSpec: "gig Y, unrelated to gig X",
    bountyUsdcBase: 1000,
    statePath,
    pay: fakePay(payoutCounter),
    verifyIdentityFn: validIdentity,
  });
  assert.equal(postedY.ok, true, "setup: gig Y post must succeed");
  const gigYId = postedY.gig.id;

  const SLOW_MS = 150;
  const xPromise = gigVerifyAndPay({
    gigId: gigXId,
    verified: true,
    posterPrivateKey: POSTER_PK,
    statePath,
    pay: slowFakePay(payoutCounter, SLOW_MS), // X's write won't happen until well after Y's take completes
    verifyIdentityFn: validIdentity,
  });
  // let X's operation start (load its snapshot, begin its slow "network" step) before Y's take fires
  await new Promise((r) => setTimeout(r, 20));
  const yTakeResult = await gigTake({ gigId: gigYId, takerAddress: TAKER_ADDR, takerAgentId: "9", statePath, verifyIdentityFn: validIdentity });

  const xResult = await xPromise;

  assert.equal(yTakeResult.ok, true, "gig Y's take call itself must report success");
  assert.equal(xResult.ok, true, "gig X's verify_and_pay must also succeed (they're unrelated gigs, both should proceed)");
  assert.equal(xResult.paid, true);

  const finalList = await gigList({ statePath });
  const finalY = finalList.gigs.find((g) => g.id === gigYId);
  const finalX = finalList.gigs.find((g) => g.id === gigXId);
  assert.equal(finalY.status, "taken", "gig Y's take must SURVIVE in the final persisted board, not be silently reverted to 'open' by X's later save");
  assert.equal(finalY.taker, TAKER_ADDR);
  assert.equal(finalX.status, "paid", "gig X's own payout must also be correctly persisted");
});

// ============================================================================
// anicca-agent-economy REQ-102 (Phase 2a, RED evidence note): the ★GAP 2★ test directly above this
// section already exercises the 2-gigId outcome scenario, and (per the increment's own scope note in
// behavioral-spec.md/verification-architecture.md) `gig.mjs`'s GAP-2 fix -- `applyAndSave()` re-reading
// the board fresh under a single "_board" lock, with the network settle held OUTSIDE that lock -- was
// already landed and adversary-verified in a PRIOR round (round 2/3, see gig.mjs's own header comment).
// This increment's REQ-102 formalizes that existing behavior with a dedicated spec + fresh, more precise
// tests (3-way concurrency, explicit call-order, explicit non-serialization timing) rather than
// introducing new application logic. These new tests are therefore expected, in good faith, to PASS
// immediately against the current code (this is recorded honestly in
// evidence/sprint-1-red-phase.log as a "coverage-retrofit" case, per this increment's own precedent for
// PROP-302a) -- they are not vacuous: each asserts a DIFFERENT, more precise proof obligation
// (PROP-102a's 3-way extension, PROP-102b's call-order, PROP-102c's non-serialization timing) than the
// pre-existing ★GAP 2★ test's single 2-gigId outcome assertion, and each would fail if a future edit
// reintroduced the GAP-2 regression.
// ============================================================================

// PROP-102a (3-way extension): "three or more concurrent operations across three or more distinct
// gigIds land in overlapping windows: every operation that returned {ok:true} to its caller must be
// reflected in the final persisted state" (behavioral-spec.md REQ-102 edge case).
test("★PROP-102a (3-way)★ three concurrent operations across THREE distinct gigIds all persist -- every {ok:true} result survives in the final board", async () => {
  const statePath = await tmpState();
  const payoutCounter = { n: 0 };

  const gigAId = await postTakenDelivered(statePath, payoutCounter); // ready for a slow verify_and_pay
  const postedB = await gigPost({
    posterPrivateKey: POSTER_PK,
    posterAgentId: "8",
    taskSpec: "gig B, unrelated to gig A/C",
    bountyUsdcBase: 1000,
    statePath,
    pay: fakePay(payoutCounter),
    verifyIdentityFn: validIdentity,
  });
  const postedC = await gigPost({
    posterPrivateKey: POSTER_PK,
    posterAgentId: "8",
    taskSpec: "gig C, unrelated to gig A/B",
    bountyUsdcBase: 1000,
    statePath,
    pay: fakePay(payoutCounter),
    verifyIdentityFn: validIdentity,
  });
  assert.equal(postedB.ok, true, "setup: gig B post must succeed");
  assert.equal(postedC.ok, true, "setup: gig C post must succeed");

  const [aResult, bResult, cResult] = await Promise.all([
    gigVerifyAndPay({
      gigId: gigAId,
      verified: true,
      posterPrivateKey: POSTER_PK,
      statePath,
      pay: slowFakePay(payoutCounter, 120), // gig A's settle is the slow one
      verifyIdentityFn: validIdentity,
    }),
    gigTake({ gigId: postedB.gig.id, takerAddress: "0xTakerB000000000000000000000000000000B", takerAgentId: "20", statePath, verifyIdentityFn: validIdentity }),
    gigTake({ gigId: postedC.gig.id, takerAddress: "0xTakerC000000000000000000000000000000C", takerAgentId: "21", statePath, verifyIdentityFn: validIdentity }),
  ]);

  assert.equal(aResult.ok, true, "gig A's verify_and_pay must succeed");
  assert.equal(aResult.paid, true);
  assert.equal(bResult.ok, true, "gig B's take must succeed");
  assert.equal(cResult.ok, true, "gig C's take must succeed");

  const finalList = await gigList({ statePath });
  const finalA = finalList.gigs.find((g) => g.id === gigAId);
  const finalB = finalList.gigs.find((g) => g.id === postedB.gig.id);
  const finalC = finalList.gigs.find((g) => g.id === postedC.gig.id);
  assert.equal(finalA.status, "paid", "gig A's payout must persist despite being the slow operation");
  assert.equal(finalB.status, "taken", "gig B's take must survive, not be clobbered by gig A's later, slower write");
  assert.equal(finalC.status, "taken", "gig C's take must survive, not be clobbered by gig A's later, slower write");
});

// PROP-102b: "Every write to the shared board file re-reads the board fresh from disk immediately
// before applying its mutation (never reuses an in-memory snapshot captured before a slow, concurrent
// step)" -- a CALL-ORDER assertion, not merely an outcome assertion (behavioral-spec.md REQ-102
// acceptance criteria; verification-architecture.md PROP-102b explicitly calls for testing that the
// write path's loadState call happens AFTER the slow step, not just that the final state is correct).
//
// Instrumented via a real monkey-patch of node:fs's `promises.readFile` (a genuine mutable object
// property, not an ES-module live binding -- persist.mjs's `fs.readFile(...)` call looks this property
// up fresh on every invocation, so patching it here observes every real disk read persist.mjs performs,
// without requiring node's --experimental-test-module-mocks flag that the rest of this codebase's test
// suites do not use).
test("★PROP-102b★ applyAndSave's authoritative loadState read happens AFTER the slow settle resolves, not before it (call-order, not just outcome)", async () => {
  const statePath = await tmpState();
  const payoutCounter = { n: 0 };
  const gigXId = await postTakenDelivered(statePath, payoutCounter);

  const reads = []; // { t: <ms> } for every real fs.readFile call against THIS test's statePath
  const originalReadFile = fs.readFile;
  fs.readFile = async (...args) => {
    if (String(args[0]) === statePath) reads.push({ t: Date.now() });
    return originalReadFile.apply(fs, args);
  };

  let settleResolvedAt = null;
  const SLOW_MS = 100;
  const slowPay = async ({ privateKey, to, amountBase }) => {
    await new Promise((r) => setTimeout(r, SLOW_MS));
    settleResolvedAt = Date.now();
    payoutCounter.n += 1;
    return { ok: true, tx: `0xfaketx${payoutCounter.n}`, payerAddress: privateKeyToAccount(privateKey).address, to, amountBase };
  };

  try {
    const result = await gigVerifyAndPay({
      gigId: gigXId,
      verified: true,
      posterPrivateKey: POSTER_PK,
      statePath,
      pay: slowPay,
      verifyIdentityFn: validIdentity,
    });
    assert.equal(result.ok, true);
    assert.equal(result.paid, true);
    assert.ok(settleResolvedAt !== null, "setup: the slow settle must actually have resolved");

    const readsAfterSettle = reads.filter((r) => r.t >= settleResolvedAt);
    assert.ok(
      readsAfterSettle.length >= 1,
      `at least one loadState read (the authoritative one feeding the actual write) must occur AT/AFTER the slow settle resolves (settleResolvedAt=${settleResolvedAt}, all reads=${JSON.stringify(reads)}) -- proves the write is not computed from a snapshot captured before the slow step`
    );
  } finally {
    fs.readFile = originalReadFile; // never leave the monkey-patch in place for other tests in this file
  }
});

// PROP-102c: "The (possibly slow) network/settle step for one gigId does not hold the shared-file lock
// for its own duration — only the brief local read-mutate-write portion does — so unrelated gigIds'
// writes are not needlessly serialized behind a slow network call" (behavioral-spec.md REQ-102
// acceptance criteria). This is a TIMING assertion: gig Y's take must complete quickly, not be blocked
// until gig X's slow settle finishes.
test("★PROP-102c★ gig Y's take is NOT serialized behind gig X's slow settle -- it completes quickly, proving the shared-file lock is held only for the brief write, not the whole network step", async () => {
  const statePath = await tmpState();
  const payoutCounter = { n: 0 };
  const gigXId = await postTakenDelivered(statePath, payoutCounter);
  const postedY = await gigPost({
    posterPrivateKey: POSTER_PK,
    posterAgentId: "8",
    taskSpec: "gig Y, unrelated to gig X",
    bountyUsdcBase: 1000,
    statePath,
    pay: fakePay(payoutCounter),
    verifyIdentityFn: validIdentity,
  });
  assert.equal(postedY.ok, true, "setup: gig Y post must succeed");
  const gigYId = postedY.gig.id;

  const SLOW_MS = 250;
  const xPromise = gigVerifyAndPay({
    gigId: gigXId,
    verified: true,
    posterPrivateKey: POSTER_PK,
    statePath,
    pay: slowFakePay(payoutCounter, SLOW_MS),
    verifyIdentityFn: validIdentity,
  });
  // let X's operation begin its slow "network" step before Y's take fires
  await new Promise((r) => setTimeout(r, 20));

  const yStart = Date.now();
  const yResult = await gigTake({ gigId: gigYId, takerAddress: TAKER_ADDR, takerAgentId: "9", statePath, verifyIdentityFn: validIdentity });
  const yElapsedMs = Date.now() - yStart;

  assert.equal(yResult.ok, true, "gig Y's take must succeed");
  assert.ok(
    yElapsedMs < SLOW_MS / 2,
    `gig Y's take took ${yElapsedMs}ms -- it must complete quickly (well under half of gig X's ${SLOW_MS}ms slow settle), not be blocked for the duration of X's network step`
  );

  const xResult = await xPromise;
  assert.equal(xResult.ok, true);
  assert.equal(xResult.paid, true);
});
