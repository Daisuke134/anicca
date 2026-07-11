# Verification Architecture — franklin-reputation-gasless

## Purity Boundary Map

- **Pure Core**:
  - `skills/economy/gig/lib/ensure-gas.mjs::decideGasAction`, `::countRecentDrips`
  - `skills/economy/gig/lib/reputation.mjs::buildFeedbackArgs`
  - `skills/economy/lending/lib/reputation-gate.mjs::passesOnchainReputationGate`'s internal
    threshold-comparison branches
  - `skills/economy/lending/lib/lending-gate.mjs::isBorrowerEligible` (pre-existing, unmodified) +
    `::isBorrowerEligibleWithReputationGate`'s own short-circuit branch
- **Effectful Shell**:
  - `ensure-gas.mjs::ensureGas` (RPC `getBalance`/`sendTransaction`/`waitForTransactionReceipt`, on-disk
    drip log read/append)
  - `reputation.mjs::giveFeedback` (RPC `writeContract` + receipt wait), `::getReputationSummary` (RPC
    `readContract`)
  - `gig.mjs::recordFeedbackBestEffort` (composes the two effectful shells above; itself no direct I/O)
  - `wallet-provider.mjs::createSignerFn` (viem client construction; I/O happens only when a caller later
    sends through the returned client)

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001 | `decideGasAction`: balance>=threshold -> "ok" regardless of network | 1 | true | node:test |
| PROP-002 | `decideGasAction`: mainnet + low balance -> NEVER "drip" | 1 | true | node:test |
| PROP-003 | `decideGasAction`: testnet + low balance -> "drip" (never "needs_gas") | 1 | true | node:test |
| PROP-004 | `countRecentDrips`: counts only matching-address rows within window | 1 | true | node:test |
| PROP-005 | `countRecentDrips`: malformed rows ignored, never throw | 1 | true | node:test |
| PROP-006 | `ensureGas`: sufficient balance -> no drip attempted | 1 | true | node:test |
| PROP-007 | `ensureGas`: mainnet low balance -> structured needs_gas, drip fn never called | 1 | true | node:test |
| PROP-008 | `ensureGas`: testnet drip hard-capped at MAX_DRIP_WEI_PER_OP even if a larger amount requested | 1 | true | node:test |
| PROP-009 | `ensureGas`: daily drip cap reached -> refuses (fail-closed), no further drip sent | 1 | true | node:test |
| PROP-010 | `ensureGas`: no funder configured -> ok:false, no throw | 1 | true | node:test |
| PROP-011 | `ensureGas`: reverted drip tx -> reported as failure, never ok:true | 1 | true | node:test |
| PROP-012 | `ensureGas`: no address -> ok:false, never crashes | 1 | true | node:test |
| PROP-013 | `buildFeedbackArgs`: positive -> +100, negative -> -100 | 1 | true | node:test |
| PROP-014 | `buildFeedbackArgs`: same gigId -> same feedbackHash (deterministic) | 1 | true | node:test |
| PROP-015 | `buildFeedbackArgs`: different gigId -> different feedbackHash | 1 | true | node:test |
| PROP-016 | `buildFeedbackArgs`: missing agentId -> throws at build time | 1 | true | node:test |
| PROP-017 | `giveFeedback`: success -> ok:true + real tx hash | 1 | true | node:test |
| PROP-018 | `giveFeedback`: reverted tx -> ok:false, never throws | 1 | true | node:test |
| PROP-019 | `giveFeedback`: writeContract exception -> ok:false, never throws | 1 | true | node:test |
| PROP-020 | `getReputationSummary`: empty clientAddresses -> ok:false, zero network calls | 1 | true | node:test |
| PROP-021 | `getReputationSummary`: success -> plain-number count/summaryValue/decimals | 1 | true | node:test |
| PROP-022 | `getReputationSummary`: readContract exception -> ok:false, never throws | 1 | true | node:test |
| PROP-023 | `gigVerifyAndPay` success path calls giveFeedbackFn(positive:true, agentId=takerAgentId) | 1 | true | node:test |
| PROP-024 | `gigVerifyAndPay` reject path calls giveFeedbackFn(positive:false) | 1 | true | node:test |
| PROP-025 | giveFeedbackFn throwing never changes ok/paid/tx | 1 | true | node:test |
| PROP-026 | ensureGasFn ok:false never changes ok/paid, giveFeedbackFn never called | 1 | true | node:test |
| PROP-027 | reputation write strictly after payout settle (fund-safety ordering) | 1 | true | node:test |
| PROP-028 | fail-closed poster-auth unaffected by reputation wiring | 1 | true | node:test |
| PROP-029 | `passesOnchainReputationGate`: unset thresholds -> fail-open, getSummaryFn never called | 1 | true | node:test |
| PROP-030 | `passesOnchainReputationGate`: both thresholds met -> eligible:true | 1 | true | node:test |
| PROP-031 | `passesOnchainReputationGate`: insufficient job count -> eligible:false, reason named | 1 | true | node:test |
| PROP-032 | `passesOnchainReputationGate`: insufficient score -> eligible:false | 1 | true | node:test |
| PROP-033 | `passesOnchainReputationGate`: configured gate + no borrowerAgentId -> eligible:false (fail-closed) | 1 | true | node:test |
| PROP-034 | `passesOnchainReputationGate`: read failure -> eligible:true (fail-open) | 1 | true | node:test |
| PROP-035 | `passesOnchainReputationGate`: no clientAddresses -> eligible:true (fail-open) | 1 | true | node:test |
| PROP-036 | `isBorrowerEligibleWithReputationGate`: base check fails -> reputation gate never consulted | 1 | true | node:test |
| PROP-037 | `isBorrowerEligibleWithReputationGate`: base passes, gate rejects -> eligible:false | 1 | true | node:test |
| PROP-038 | `isBorrowerEligibleWithReputationGate`: both pass -> eligible:true | 1 | true | node:test |
| PROP-039 | `isBorrowerEligibleWithReputationGate`: defaults to real gate when no override given | 1 | true | node:test |
| PROP-040 | pre-existing `isBorrowerEligible`/`lending-gate` suite (150+ tests) unaffected | 0 | true | node:test (regression) |
| PROP-041 | pre-existing gig/store/lock suite (80 tests incl. this feature's 6) unaffected | 0 | true | node:test (regression) |
| PROP-042 | Reputation Registry addresses used match independently-confirmed `eth_call` results (mainnet
  `getVersion()`/`getIdentityRegistry()` cross-checked against identity.mjs's own mainnet registry) | 2 | true | manual eth_call (this session, see reputation.mjs header) |
| PROP-043 (E2E) | Base Sepolia: register->giveFeedback with zero manual ETH top-up | 3 | true | live testnet script |
| PROP-044 (E2E) | Base Sepolia: getSummary count increases after a real giveFeedback tx, confirmed via an
  independent `eth_call` | 3 | true | live testnet script |
| PROP-045 (E2E) | configured gate rejects a real low-reputation borrower on testnet | 3 | true | live testnet script |

## Verification Strategy

- **Tier 0**: pre-existing regression suites (gig 80 tests, lending 162 tests) — no new proof needed,
  just re-run and diff pass count.
- **Tier 1**: all pure-logic and DI-fake-based unit tests above (PROP-001..041) — `node --test`, no
  network in the loop, fast/deterministic.
- **Tier 2**: the two Reputation Registry addresses (mainnet + base-sepolia) are verified once, by hand,
  via a real `eth_call` against `getVersion()`/`getIdentityRegistry()` this session (see
  `reputation.mjs`'s own header comment for the exact confirmed values and the one known testnet
  identity-registry mismatch). This is a one-time address-provenance check, not a repeatable proof
  obligation — it is re-verifiable by anyone re-running the same two read calls.
- **Tier 3**: the three E2E items (PROP-043..045) require a funded Base Sepolia signer key. This build
  session's own MONEY-SAFETY boundary explicitly forbids reading/touching wallet private keys or `.env`
  at all — so obtaining and using such a key is structurally out of scope for this session, not merely
  unavailable. They remain open, tracked here (see this feature's `evidence/e2e-status.md`), to be closed
  by a separate, explicitly-authorized session/operator that runs the live script with a funded key,
  before this feature is considered fully done per the design spec's own §5 "E2E（Base Sepolia、fresh
  evidence）" requirement.
