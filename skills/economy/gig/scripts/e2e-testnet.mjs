// scripts/e2e-testnet.mjs — REAL, no-mock end-to-end proof of the P2.2 internal gig loop on Base
// Sepolia (SPEC.md §3 P2.2 verification): a test poster posts a small gig with escrow, a test taker
// takes+delivers, the poster verifies -> a real gasless payout tx to the taker.
//
// Requires: services/facilitator running at 127.0.0.1:8405 (services/facilitator/start.sh) and the
// env vars below sourced from ~/.anicca-signing/{x402-facilitator,gig-board}/.env.
//
// Usage:
//   set -a; source ~/.anicca-signing/x402-facilitator/.env; source ~/.anicca-signing/gig-board/.env; set +a
//   export GIG_ESCROW_ADDRESS GIG_ESCROW_PRIVATE_KEY
//   node scripts/e2e-testnet.mjs
import { gigPost, gigList, gigTake, gigDeliver, gigVerifyAndPay, registerIdentity, verifyIdentity } from "../gig.mjs";

const POSTER_PK = process.env.TEST_PAYER_PRIVATE_KEY; // reuses the already-funded P2.1 test payer as poster
const POSTER_ADDR = process.env.TEST_PAYER_ADDRESS;
const TAKER_PK = process.env.GIG_TAKER_PRIVATE_KEY;
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

if (evidence.posterIdentity.ok && evidence.posterIdentity.agentId) {
  evidence.posterIdentityVerify = await verifyIdentity({ agentId: evidence.posterIdentity.agentId, expectedAddress: POSTER_ADDR });
  console.error("verify poster identity on-chain:", JSON.stringify(evidence.posterIdentityVerify));
}
if (evidence.takerIdentity.ok && evidence.takerIdentity.agentId) {
  evidence.takerIdentityVerify = await verifyIdentity({ agentId: evidence.takerIdentity.agentId, expectedAddress: TAKER_ADDR });
  console.error("verify taker identity on-chain:", JSON.stringify(evidence.takerIdentityVerify));
}

console.error("\n--- step 1: gig_post (poster funds escrow, real on-chain settle) ---");
const posted = await gigPost({
  posterPrivateKey: POSTER_PK,
  posterAddress: POSTER_ADDR,
  taskSpec: "P2.2 E2E proof: reply 'ok'",
  bountyUsdcBase: 1000, // 0.001 USDC
});
console.error(JSON.stringify(posted));
if (!posted.ok) { console.error("ABORT: gig_post failed"); process.exit(1); }
evidence.post = posted;

console.error("\n--- step 2: gig_take ---");
const taken = await gigTake({ gigId: posted.gig.id, takerAddress: TAKER_ADDR });
console.error(JSON.stringify(taken));
if (!taken.ok) { console.error("ABORT: gig_take failed"); process.exit(1); }
evidence.take = taken;

console.error("\n--- step 3: gig_deliver ---");
const delivered = await gigDeliver({ gigId: posted.gig.id, deliverable: "ok" });
console.error(JSON.stringify(delivered));
if (!delivered.ok) { console.error("ABORT: gig_deliver failed"); process.exit(1); }
evidence.deliver = delivered;

console.error("\n--- step 4: gig_verify_and_pay (verified=true -> REAL escrow release payout) ---");
const paid = await gigVerifyAndPay({ gigId: posted.gig.id, verified: true });
console.error(JSON.stringify(paid));
evidence.verifyAndPay = paid;
if (!paid.ok || !paid.paid) { console.error("ABORT: gig_verify_and_pay did not pay"); process.exit(1); }

console.error("\n--- step 5: gig_list (final board state) ---");
const list = await gigList({});
console.error(JSON.stringify(list));
evidence.finalList = list;

console.log(JSON.stringify(evidence, null, 2));
