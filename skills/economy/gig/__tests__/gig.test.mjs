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
