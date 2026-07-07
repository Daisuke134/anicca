// scripts/e2e-testnet.mjs — REAL, no-mock end-to-end proof of the P2.2 internal gig loop on Base
// Sepolia, INCLUDING re-proof that the two adversary-found drains (SPEC.md §3 P2.2 security fixes)
// now fail against the real facilitator + real ERC-8004 registry, not just against unit-test fakes.
//
// Requires: services/facilitator running at 127.0.0.1:8405 (services/facilitator/start.sh) and the
// env vars below sourced from ~/.anicca-signing/{x402-facilitator,gig-board}/.env.
//
// ★gig-board/.env now points GIG_STATE_PATH at the SHARED production witness board (automaton+Franklin
// both read/write it, by design — see WITNESS-RUNBOOK.md) and defaults GIG_CHAIN=base/:8407 (mainnet).
// Running this test script against those defaults clobbers real witness-track state (found live during
// Phase 5 hardening, sprint-1 FIND-501) and fails on testnet wallets with "gas required exceeds
// allowance". ALWAYS override both before running this script:
//
// Usage:
//   set -a; source ~/.anicca-signing/x402-facilitator/.env; source ~/.anicca-signing/gig-board/.env; set +a
//   export GIG_ESCROW_ADDRESS GIG_ESCROW_PRIVATE_KEY
//   export GIG_STATE_PATH=/tmp/gig-e2e-test-$(date +%s).json GIG_CHAIN=base-sepolia GIG_FACILITATOR_URL=http://127.0.0.1:8405
//   node scripts/e2e-testnet.mjs
import { gigPost, gigList, gigTake, gigDeliver, gigVerifyAndPay, registerIdentity, verifyIdentity } from "../gig.mjs";

const POSTER_PK = process.env.TEST_PAYER_PRIVATE_KEY; // reuses the already-funded P2.1 test payer as poster
const POSTER_ADDR = process.env.TEST_PAYER_ADDRESS;
const TAKER_PK = process.env.GIG_TAKER_PRIVATE_KEY; // also plays "the attacker" in the finding-1 re-proof (exact adversary scenario: the taker itself calling verify_and_pay)
const TAKER_ADDR = process.env.GIG_TAKER_ADDRESS;

function must(v, name) {
  if (!v) { console.error(`missing env: ${name}`); process.exit(1); }
  return v;
}
must(POSTER_PK, "TEST_PAYER_PRIVATE_KEY"); must(POSTER_ADDR, "TEST_PAYER_ADDRESS");
must(TAKER_PK, "GIG_TAKER_PRIVATE_KEY"); must(TAKER_ADDR, "GIG_TAKER_ADDRESS");
must(process.env.GIG_ESCROW_ADDRESS, "GIG_ESCROW_ADDRESS"); must(process.env.GIG_ESCROW_PRIVATE_KEY, "GIG_ESCROW_PRIVATE_KEY");

const evidence = {};

console.error("--- step 0: ERC-8004 identity for poster + taker (real on-chain register()) ---");
evidence.posterIdentity = await registerIdentity({ privateKey: POSTER_PK });
console.error("poster identity:", JSON.stringify(evidence.posterIdentity));
evidence.takerIdentity = await registerIdentity({ privateKey: TAKER_PK });
console.error("taker identity:", JSON.stringify(evidence.takerIdentity));
if (!evidence.posterIdentity.ok || !evidence.takerIdentity.ok) { console.error("ABORT: identity registration failed"); process.exit(1); }
const POSTER_AGENT_ID = evidence.posterIdentity.agentId;
const TAKER_AGENT_ID = evidence.takerIdentity.agentId;

evidence.posterIdentityVerify = await verifyIdentity({ agentId: POSTER_AGENT_ID, expectedAddress: POSTER_ADDR });
console.error("verify poster identity on-chain:", JSON.stringify(evidence.posterIdentityVerify));
evidence.takerIdentityVerify = await verifyIdentity({ agentId: TAKER_AGENT_ID, expectedAddress: TAKER_ADDR });
console.error("verify taker identity on-chain:", JSON.stringify(evidence.takerIdentityVerify));

async function postTakeDeliver(taskSpec) {
  const posted = await gigPost({ posterPrivateKey: POSTER_PK, posterAgentId: POSTER_AGENT_ID, taskSpec, bountyUsdcBase: 1000 });
  console.error("gig_post:", JSON.stringify(posted));
  if (!posted.ok) { console.error("ABORT: gig_post failed"); process.exit(1); }
  const taken = await gigTake({ gigId: posted.gig.id, takerAddress: TAKER_ADDR, takerAgentId: TAKER_AGENT_ID });
  console.error("gig_take:", JSON.stringify(taken));
  if (!taken.ok) { console.error("ABORT: gig_take failed"); process.exit(1); }
  const delivered = await gigDeliver({ gigId: posted.gig.id, deliverable: "ok" });
  console.error("gig_deliver:", JSON.stringify(delivered));
  if (!delivered.ok) { console.error("ABORT: gig_deliver failed"); process.exit(1); }
  return posted.gig.id;
}

// ============ GIG A: re-prove FINDING 1 is fixed (non-poster verify_and_pay must fail) ============
console.error("\n=== GIG A: FINDING 1 re-proof -- attacker (the taker itself) tries verify_and_pay ===");
const gigA = await postTakeDeliver("P2.2 re-proof A: FINDING 1 (poster auth)");

console.error("--- ATTACK: taker calls gig_verify_and_pay(true) on themselves (exact adversary scenario) ---");
const attackAttempt = await gigVerifyAndPay({ gigId: gigA, verified: true, posterPrivateKey: TAKER_PK });
console.error("attack result:", JSON.stringify(attackAttempt));
evidence.finding1AttackAttempt = attackAttempt;
if (attackAttempt.ok !== false) {
  console.error("★★★ SECURITY REGRESSION: the attack SUCCEEDED. Finding 1 is NOT fixed. ★★★");
  process.exit(1);
}
console.error("✓ attack REJECTED as expected:", attackAttempt.reason);

console.error("--- legit: real poster calls gig_verify_and_pay(true) ---");
const gigAPaid = await gigVerifyAndPay({ gigId: gigA, verified: true, posterPrivateKey: POSTER_PK });
console.error("legit result:", JSON.stringify(gigAPaid));
evidence.finding1LegitPayout = gigAPaid;
if (!gigAPaid.ok || !gigAPaid.paid) { console.error("ABORT: legit poster payout failed"); process.exit(1); }
console.error("✓ legit poster paid, tx:", gigAPaid.tx);

// ============ GIG B: re-prove FINDING 2 is fixed (concurrent real settles, exactly one payout) ============
console.error("\n=== GIG B: FINDING 2 re-proof -- two CONCURRENT real verify_and_pay(true) calls ===");
const gigB = await postTakeDeliver("P2.2 re-proof B: FINDING 2 (double-pay race)");

console.error("--- firing 2 concurrent REAL gig_verify_and_pay(true) calls on the same gig ---");
const [raceA, raceB] = await Promise.all([
  gigVerifyAndPay({ gigId: gigB, verified: true, posterPrivateKey: POSTER_PK }),
  gigVerifyAndPay({ gigId: gigB, verified: true, posterPrivateKey: POSTER_PK }),
]);
console.error("race result A:", JSON.stringify(raceA));
console.error("race result B:", JSON.stringify(raceB));
evidence.finding2Race = { raceA, raceB };
const paidCount = [raceA, raceB].filter((r) => r.ok && r.paid).length;
if (paidCount !== 1) {
  console.error(`★★★ SECURITY REGRESSION: ${paidCount} concurrent calls paid (expected exactly 1). Finding 2 is NOT fixed. ★★★`);
  process.exit(1);
}
console.error(`✓ exactly ${paidCount} of 2 concurrent calls paid, the other was rejected (fail-closed lock contention)`);

console.error("\n--- final board state ---");
const list = await gigList({});
console.error(JSON.stringify(list));
evidence.finalList = list;

console.log(JSON.stringify(evidence, null, 2));
