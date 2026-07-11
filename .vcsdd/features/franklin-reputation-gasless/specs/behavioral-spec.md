# Behavioral Spec — franklin-reputation-gasless

Source contract: `docs/superpowers/specs/2026-07-12-franklin-reputation-gasless-design.md` (all of it,
§0–§7) + `docs/loop-engineering/23-anicca-loop-architecture-redesign.md` §11 (real ERC-8004 Reputation
interfaces, verified addresses). This file translates that design spec into EARS requirements for VCSDD;
it does not restate rationale already in the design spec (§0/§7), only testable behavior.

## Purity boundary analysis

- **Pure core** (deterministic, zero I/O, unit-testable directly):
  - `ensure-gas.mjs::decideGasAction` — threshold comparison + testnet/mainnet branch.
  - `ensure-gas.mjs::countRecentDrips` — arithmetic over already-known log rows.
  - `reputation.mjs::buildFeedbackArgs` — builds `giveFeedback`'s 8 positional args (incl. deterministic
    `keccak256` hash of `gigId`).
  - `reputation-gate.mjs::passesOnchainReputationGate`'s own threshold-comparison branch (score/count vs
    configured minimums) is pure decision logic, though the function itself is async because it may call
    an injected `getSummaryFn`.
  - `lending-gate.mjs::isBorrowerEligible` (pre-existing, UNCHANGED) + the new
    `isBorrowerEligibleWithReputationGate`'s own short-circuit composition logic.
- **Effectful shell** (I/O: RPC reads/writes, disk log, real money movement):
  - `ensure-gas.mjs::ensureGas` — `getBalance`, `sendTransaction`, `waitForTransactionReceipt`, drip log
    file read/append.
  - `reputation.mjs::giveFeedback` / `getReputationSummary` — `writeContract` / `readContract` against
    the Base Reputation Registry.
  - `gig.mjs::gigVerifyAndPay`'s new `recordFeedbackBestEffort` call (composes the two effectful shells
    above; itself never touches the network directly).
  - `wallet-provider.mjs::createSignerFn` — constructs a viem `WalletClient` (I/O only at the point a
    caller actually sends a transaction through it; construction itself is synchronous and side-effect
    free but treated as shell code since its whole purpose is enabling I/O).

## Requirements

### REQ-001: Gas preflight threshold decision (pure)
**EARS**: WHEN `decideGasAction` is called with a balance, threshold, and `isMainnet` flag THE SYSTEM
SHALL return `{action:"ok"}` if balance >= threshold, `{action:"drip", ...}` if balance < threshold and
`isMainnet` is false, and `{action:"needs_gas", requiredWei, ...}` if balance < threshold and `isMainnet`
is true.
**Edge Cases**:
- balance exactly equal to threshold: `{action:"ok"}` (boundary is inclusive on the "ok" side).
- `isMainnet:true` with a below-threshold balance: MUST NEVER return `"drip"` under any input (money-safety MUST, spec §4).
**Acceptance Criteria**:
- `decideGasAction` is a pure function — same inputs always produce the same output, no I/O.
- A mainnet low-balance decision always includes `requiredWei` (threshold - balance, as a string).

### REQ-002: Gas auto-drip (testnet only, hard-capped, rate-limited)
**EARS**: WHEN `ensureGas` is called for a testnet address with a balance below threshold THE SYSTEM
SHALL send a drip transaction capped at `MAX_DRIP_WEI_PER_OP` (≤0.0005 ETH) regardless of the requested
`dripAmountWei`, refusing (fail-closed, `{ok:false, action:"needs_gas"}`) once `maxDripsPerDay` drips have
already been sent to that address within the trailing 24h window.
**Edge Cases**:
- No funder configured (`GIG_GAS_FUNDER_PRIVATE_KEY` unset, no `sendDripFn` override): refuse with
  `{ok:false, action:"needs_gas"}`, never throw, never silently skip to "ok".
- Drip tx reverts: report failure (`{ok:false}`), never `{ok:true}`.
- Drip tx receipt wait throws: report failure, never leave the caller uncertain about whether money moved.
- Malformed/unparseable rows in the on-disk drip log: ignored by `countRecentDrips`, never thrown.
**Acceptance Criteria**:
- The daily cap is enforced BEFORE any `sendDripFn` call is attempted once the cap is reached.
- `MAX_DRIP_WEI_PER_OP` caps the sent amount even if a caller passes a larger `dripAmountWei`.
- `ensureGas` never throws — every failure path returns `{ok:false, ...}`.

### REQ-003: Gas preflight (mainnet — no auto-spend)
**EARS**: WHEN `ensureGas` is called for a mainnet address with a balance below threshold THE SYSTEM
SHALL return a structured `{ok:false, action:"needs_gas", requiredWei}` error and SHALL NOT construct or
send any drip transaction.
**Edge Cases**: mainnet + `sendDripFn` override provided anyway — MUST still never be invoked (the
mainnet branch of `decideGasAction` never returns `"drip"`, so `ensureGas`'s drip code path is
structurally unreachable for `isMainnet:true`).
**Acceptance Criteria**: a unit test asserts `sendDripFn` is never called for any mainnet low-balance
input, regardless of `sendDripFn`'s presence.

### REQ-004: giveFeedback argument construction (pure)
**EARS**: WHEN `buildFeedbackArgs` is called with `{agentId, positive, gigId}` THE SYSTEM SHALL return
the 8 positional arguments for ERC-8004 `giveFeedback`, with `value = +100` when `positive` is true and
`value = -100` when `positive` is false, and a `feedbackHash` deterministically derived from `gigId` (the
same `gigId` always produces the same hash; different `gigId`s produce different hashes).
**Edge Cases**:
- missing `agentId`: throws synchronously at build time (never silently gives feedback for an undefined
  subject).
**Acceptance Criteria**: positive/negative outcomes map to exactly `+100`/`-100`; hash determinism and
distinctness are both independently asserted.

### REQ-005: giveFeedback write (fail-open shell)
**EARS**: WHEN `giveFeedback` is called with a signer key and gig outcome THE SYSTEM SHALL submit a
`giveFeedback` transaction to the active-network Reputation Registry, wait for its receipt, and return
`{ok:true, tx}` on a successful (status `"success"`) receipt.
**Edge Cases**:
- reverted receipt: return `{ok:false, reason, tx}`, never throw.
- `writeContract` throws (e.g. "Self-feedback not allowed" revert): return `{ok:false, reason}`, never
  throw out of the function.
**Acceptance Criteria**: `giveFeedback` never throws under any tested failure condition (money-safety §4
"reputation は fail-open" applies at this layer too).

### REQ-006: getReputationSummary read (fail-open shell)
**EARS**: WHEN `getReputationSummary` is called with `agentId` and a non-empty `clientAddresses` array
THE SYSTEM SHALL read `getSummary` from the active-network Reputation Registry and return
`{ok:true, count, summaryValue, decimals}` as plain numbers.
**Edge Cases**:
- empty/missing `clientAddresses`: refuse with `{ok:false, reason}` WITHOUT making any network call (the
  contract itself reverts on an empty array — fail fast instead of wasting a call).
- `readContract` throws: return `{ok:false, reason}`, never throw.
**Acceptance Criteria**: the empty-`clientAddresses` refusal path is proven to make zero network calls
(the injected `publicClientFactory` is never invoked).

### REQ-007: gigVerifyAndPay reputation wiring — success path
**EARS**: WHEN `gigVerifyAndPay` completes a real payout (`verified:true`, payout succeeds, state save
succeeds) THE SYSTEM SHALL, AFTER the payout and state save are both already final, call `ensureGasFn`
for the poster's own address and, if it returns `ok:true`, call `giveFeedbackFn` with
`{agentId: gig.takerAgentId, positive:true, gigId}`, attaching the outcome under `result.reputation`
without altering `result.ok`/`result.paid`/`result.tx`.
**Edge Cases**:
- `ensureGasFn` returns `{ok:false}` (e.g. mainnet needs_gas): `giveFeedbackFn` is never called;
  `result.reputation.ok === false`; `result.ok`/`result.paid` are unaffected.
- `giveFeedbackFn` throws: caught, `result.reputation.ok === false`; `result.ok`/`result.paid`/`result.tx`
  are unaffected.
- gig has no `takerAgentId`: reputation write is skipped (`{ok:false, reason:"no takerAgentId..."}`), no
  crash.
**Acceptance Criteria**: an explicit ordering test proves the payout call happens strictly before the
feedback call (fund-safety ordering — money is never gated on a reputation write).

### REQ-008: gigVerifyAndPay reputation wiring — reject path
**EARS**: WHEN `gigVerifyAndPay` is called with `verified:false` (poster rejects, no payout) THE SYSTEM
SHALL, after the state save to `REJECTED` is final, call `ensureGasFn`/`giveFeedbackFn` with
`positive:false`, attaching the outcome under `result.reputation` without altering `result.ok`/
`result.paid`.
**Acceptance Criteria**: `result.paid` remains `false`; `giveFeedbackFn` is called with
`positive:false`.

### REQ-009: gigVerifyAndPay auth/lock/identity guarantees are unaffected
**EARS**: THE SYSTEM SHALL preserve every pre-existing `gigVerifyAndPay` guarantee (fail-closed
poster-auth — a non-poster caller is rejected before any reputation code runs; the gig lock; taker
identity re-verification at payout time) unchanged by the reputation wiring.
**Acceptance Criteria**: the full pre-existing `gig.test.mjs`/`store.test.mjs`/`lock.test.mjs` suite (80
tests total, incl. the wiring feature's own 6 new tests) passes with zero regressions.

### REQ-010: On-chain reputation gate — fail-open by default (段階導入)
**EARS**: WHEN `passesOnchainReputationGate` is called with `minScore<=0` AND `minJobCount<=0` (the
default, unset) THE SYSTEM SHALL return `{eligible:true}` WITHOUT calling `getSummaryFn` at all.
**Acceptance Criteria**: a unit test asserts `getSummaryFn` is never invoked when both thresholds are
unset — the gate can be adopted per-lender with zero effect on existing borrowers until explicitly
configured.

### REQ-011: On-chain reputation gate — configured threshold enforcement
**EARS**: WHEN a gate is configured (`minScore>0` or `minJobCount>0`) with a valid `borrowerAgentId` and
non-empty `clientAddresses`, and the read succeeds, THE SYSTEM SHALL return `{eligible:false,
reason:"insufficient_job_count"}` if `count < minJobCount`, `{eligible:false,
reason:"insufficient_score"}` if `summaryValue < minScore`, and `{eligible:true, reason:"ok"}` otherwise.
**Edge Cases**:
- configured gate + no `borrowerAgentId`: `{eligible:false}` (fail-CLOSED on this specific gap — a
  caller bug, not a network outage, spec's own explicit distinction).
- configured gate + empty/missing `clientAddresses`: `{eligible:true}` (fail-open — cannot evaluate).
- configured gate + `getSummaryFn` returns `{ok:false}` (RPC outage): `{eligible:true}`, reason matching
  `/fail_open/` (money-safety §4 "reputation は fail-open" applies to reads too — an outage must never
  block lending).
**Acceptance Criteria**: job-count and score checks are independently testable (a gate with only one of
the two configured checks only that one).

### REQ-012: Reputation gate composed into lending eligibility, base check untouched
**EARS**: WHEN `isBorrowerEligibleWithReputationGate` is called THE SYSTEM SHALL first evaluate the
existing, unmodified `isBorrowerEligible` and return its result immediately (without ever consulting the
reputation gate) if it is not eligible; only if the base check passes SHALL it then evaluate
`passesOnchainReputationGate` and return its rejection reason if that also fails, or `{eligible:true,
reason:"ok"}` if both pass.
**Edge Cases**: no `reputationGateFn` override given — defaults to the real
`passesOnchainReputationGate`, which itself fail-opens on unset thresholds.
**Acceptance Criteria**: `isBorrowerEligible`'s own pre-existing test suite (150+ tests) is untouched and
stays green; the composition is additive-only, covered by its own separate test file.

### REQ-013: Gas/reputation money-safety invariants (cross-cutting, spec §4 MUST)
**EARS**: THE SYSTEM SHALL NEVER read, log, or otherwise touch wallet private keys outside their
documented DI parameter, `.env`, `.solana-session`, `ledger.mjs`, any spend-cap constant (incl.
`SOL_TRADE_MAX_SPEND`, which stays `0`), or `.vcsdd/features/anicca-agent-economy/**`, as part of this
feature's changes.
**Acceptance Criteria**: `git diff main` for this feature touches only the files declared in the design
spec's §3 file boundary (`skills/economy/gig/**`, `skills/economy/lending/**`) plus this feature's own
`.vcsdd/` directory.

## Non-functional requirements

- **Performance**: no new synchronous blocking calls added to any pure function; all new I/O
  (`ensureGas`, `giveFeedback`, `getReputationSummary`) is `async` and dependency-injectable for
  zero-network unit testing.
- **Security**: mainnet writes are never auto-triggered by a below-threshold gas balance (REQ-003);
  reputation reads/writes never gate fund movement (REQ-007/REQ-008 fail-open ordering).
- **Non-goals** (unchanged from design spec §2): no mainnet reputation writes as part of this feature's
  done-criteria; no ERC-4337 smart-account migration (G4 is a seam only, REQ not numbered — see
  `wallet-provider.mjs`'s own header); no ERC-8004 Validation registry adoption.
