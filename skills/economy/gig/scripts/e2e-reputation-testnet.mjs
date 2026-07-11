// scripts/e2e-reputation-testnet.mjs — franklin-reputation-gasless: REAL, no-mock Base Sepolia proof of
// G1 (gas preflight, zero manual top-up) + G2 (giveFeedback write + getSummary count increase). See
// docs/superpowers/specs/2026-07-12-franklin-reputation-gasless-design.md §5 "E2E（Base Sepolia、fresh
// evidence）" for the exact three items this script proves: (a) register->giveFeedback with zero manual
// ETH top-up, (b) getSummary count increases, confirmed via an independent eth_call, (c) is covered
// separately by reputation-gate.mjs's own unit tests (no live-chain component needed there — see
// verification-architecture.md PROP-045's own tier-3 scoping note).
//
// ★KNOWN LIMITATION (documented in reputation.mjs's own header, not new here)★: the Reputation
// Registry's giveFeedback on base-sepolia checks isAuthorizedOrOwner against a DIFFERENT
// IdentityRegistry (0x8004A818BFB912233c491871b3d84c89A494BD9e) than identity.mjs's own default testnet
// registry (0xdc5277..., legacy v1.1.0) -- so this script registers a FRESH throwaway agentId directly
// against the Reputation-linked registry (registryAddress override) instead of using identity.mjs's
// default, purely to exercise giveFeedback/getSummary against a valid subject. This has no bearing on
// production register() calls, which correctly keep using identity.mjs's own default testnet registry.
//
// Requires a Base Sepolia-funded EVM private key (POSTER = the client giving feedback; TAKER's identity
// only needs to exist, never needs its own gas). This script deliberately does NOT read any .env file or
// keychain itself -- the key must be exported into the environment by whoever runs it, per this
// feature's own MONEY-SAFETY boundary (no wallet key handling inside this feature's own code).
//
// Usage:
//   export GIG_CHAIN=base-sepolia
//   export E2E_REP_POSTER_PRIVATE_KEY=0x...   # funded with Base Sepolia ETH
//   export GIG_GAS_FUNDER_PRIVATE_KEY=0x...   # optional: a SEPARATE funded key for ensureGas's own testnet drip proof; if unset, G1's zero-manual-topup claim is only proven when POSTER already has enough balance
//   node scripts/e2e-reputation-testnet.mjs
import { registerIdentity } from "../lib/identity.mjs";
import { giveFeedback, getReputationSummary, REPUTATION_REGISTRY_BASE_SEPOLIA } from "../lib/reputation.mjs";
import { ensureGas } from "../lib/ensure-gas.mjs";
import { privateKeyToAccount } from "viem/accounts";

// The real testnet IdentityRegistry the Reputation Registry itself is linked to (see header above) --
// NOT identity.mjs's own DEFAULT_RPC_URL/registryAddress, overridden explicitly for this script only.
const REPUTATION_LINKED_IDENTITY_REGISTRY_BASE_SEPOLIA = "0x8004A818BFB912233c491871b3d84c89A494BD9e";

function must(v, name) {
  if (!v) { console.error(`missing env: ${name}`); process.exit(1); }
  return v;
}
const POSTER_PK = must(process.env.E2E_REP_POSTER_PRIVATE_KEY, "E2E_REP_POSTER_PRIVATE_KEY");
if (process.env.GIG_CHAIN !== "base-sepolia") {
  console.error("ABORT: this script is testnet-only (money-safety §4) -- set GIG_CHAIN=base-sepolia");
  process.exit(1);
}
const POSTER_ADDR = privateKeyToAccount(POSTER_PK).address;

const evidence = {};

console.error("--- step 1: G1 gas preflight (real ensureGas, zero manual top-up claim) ---");
evidence.ensureGasResult = await ensureGas({ address: POSTER_ADDR, isMainnet: false });
console.error("ensureGas:", JSON.stringify(evidence.ensureGasResult));
if (!evidence.ensureGasResult.ok) {
  console.error("ABORT: ensureGas refused -- no manual ETH top-up performed, exactly as designed; re-run once a funder is configured or the poster already holds enough testnet ETH");
  process.exit(1);
}

console.error("\n--- step 2: register a fresh throwaway agentId against the Reputation-linked IdentityRegistry ---");
evidence.registerResult = await registerIdentity({ privateKey: POSTER_PK, registryAddress: REPUTATION_LINKED_IDENTITY_REGISTRY_BASE_SEPOLIA });
console.error("register:", JSON.stringify(evidence.registerResult));
if (!evidence.registerResult.ok) { console.error("ABORT: register failed"); process.exit(1); }
const AGENT_ID = evidence.registerResult.agentId;

console.error("\n--- step 3: independent getSummary BEFORE giveFeedback (baseline count) ---");
evidence.summaryBefore = await getReputationSummary({ agentId: AGENT_ID, clientAddresses: [POSTER_ADDR] });
console.error("summary before:", JSON.stringify(evidence.summaryBefore));

console.error("\n--- step 4: real giveFeedback(+100, 'gig-complete') ---");
evidence.feedbackResult = await giveFeedback({ signerPrivateKey: POSTER_PK, agentId: AGENT_ID, positive: true, gigId: `e2e-${Date.now()}` });
console.error("giveFeedback:", JSON.stringify(evidence.feedbackResult));
if (!evidence.feedbackResult.ok) { console.error("ABORT: giveFeedback failed"); process.exit(1); }

console.error("\n--- step 5: independent getSummary AFTER giveFeedback (count must increase) ---");
evidence.summaryAfter = await getReputationSummary({ agentId: AGENT_ID, clientAddresses: [POSTER_ADDR] });
console.error("summary after:", JSON.stringify(evidence.summaryAfter));
if (!evidence.summaryAfter.ok || evidence.summaryAfter.count <= (evidence.summaryBefore.ok ? evidence.summaryBefore.count : -1)) {
  console.error("★★★ E2E FAILURE: getSummary count did not increase after a confirmed giveFeedback tx ★★★");
  process.exit(1);
}
console.error(`✓ count increased ${evidence.summaryBefore.ok ? evidence.summaryBefore.count : "?"} -> ${evidence.summaryAfter.count}`);
console.error(`✓ registry used: ${REPUTATION_REGISTRY_BASE_SEPOLIA} (base-sepolia)`);

console.log(JSON.stringify(evidence, null, 2));
