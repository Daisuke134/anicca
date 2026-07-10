# Behavioral Spec — spawn-funding-swap

## Context (money-path feature — treat every REQ below as MUST, none is optional)

`TREASURY_SWAP_CMD` is a hook already called by `~/anicca/skills/self/spawn/scripts/akt-treasury.sh:52`
when the Akash wallet's `uakt` balance is below `MINT_UAKT` (25 AKT). This feature IS that command: it
swaps USDC on Base into AKT on Akash mainnet via the Skip API multi-hop route (Base → noble-1 →
osmosis-1 → akashnet-2), lands the AKT at `akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523`
(`AKASH_KEY_NAME=anicca-akash`, keyring backend `test`), and never does anything else. It has no UI,
no genome, no learning loop — it is a deterministic money-mover with hard-fail defaults.

Confirmed this session (cite, do not re-trust blindly — verify balances/route live before each swap):
- Skip API route Base USDC → AKT is live: `POST https://api.skip.build/v2/fungible/route`,
  `source_asset_denom=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` (Base USDC),
  `source_asset_chain_id=8453`, `dest_asset_denom=uakt`, `dest_asset_chain_id=akashnet-2` →
  `amount_out≈24.65 AKT` for 15 USDC in, `txs_required=2`.
- Polygon USDC → AKT: Skip returned "no routes found". Solana USDC → AKT: Skip returned "Source token
  not found". **Base is the only currently-viable source chain** — this MUST NOT be hardcoded as an
  assumption; the route response is the source of truth every time (REQ-002).
- Current treasury: ~1.85 AKT at the Akash wallet; gate needs 26 AKT (23 Franklin funding target — treat
  the exact gate threshold as read from the caller's env, not hardcoded here, see REQ-001).
- **No funded routable source exists yet**: claude-p Base wallet `0x810f6d61f7606deee2657d3083e150a222bc29c5`
  has ~$0 USDC and ~$0 gas; claude-p Polygon wallet `0x904B50d2...` has $0; Franklin's $13.18 USDC sits
  on **Solana**, a chain the Skip route rejects as a source for this pair. This is the live blocker —
  see REQ-003 and the OPEN QUESTION at the bottom of this file.

## Purity Boundary Analysis

**Pure core** (deterministic, no I/O, unit- and property-testable in isolation):
- `computeSwapNeed(currentAkt, thresholdAkt)` — how much AKT (if any) must be acquired; MUST be 0 or
  negative-shortfall-clamped-to-0 when `currentAkt >= thresholdAkt` (REQ-001, no-over-buy).
- `usdEquivalentOf(needAkt, aktUsdPrice)` — pure conversion of the AKT shortfall computed by
  `computeSwapNeed` into its USD equivalent, given a price supplied by the effectful `PriceOracle`;
  returns `needAkt * aktUsdPrice` for finite non-negative `needAkt` and finite positive `aktUsdPrice`,
  and MUST resolve to an explicit fail-closed signal (throw, never an unbounded/NaN/negative
  pass-through) for `aktUsdPrice <= 0`, `NaN`, or `Infinity` (REQ-011). This is the ONLY place the
  AKT-need-to-USD conversion happens; its output feeds directly into `capUsd`, never a hand-rolled
  conversion elsewhere.
- `capUsd(requestedUsd)` — hard-clamp of the USD amount to spend to `min(requestedUsd, SWAP_MAX_USD)`
  where `SWAP_MAX_USD` is a literal constant in the pure module, never read from `process.env` or any
  genome/config file (REQ-006). `capUsd`'s only sanctioned input across this feature is
  `usdEquivalentOf(need, aktUsdPrice)`'s output (REQ-011), and `capUsd`'s only sanctioned output
  consumer is `toBaseUnits` (REQ-012) — `capUsd`'s dollar-float return value is NEVER passed directly to
  the Skip route request or to the signed Base transaction; it MUST first pass through REQ-012's
  conversion, whose bigint output alone reaches those two call sites — never a re-derived or
  independently recomputed amount, and never the raw dollar float.
- `toBaseUnits(amountFloat: number, decimals: number): bigint` — pure conversion from a decimal-float
  amount (USD or AKT) into the integer on-chain base-unit representation for the given asset's decimal
  precision (REQ-012); THE SINGLE named choke point between `capUsd(usdEquivalentOf(need, aktUsdPrice))`
  and both the Skip `amount_in` parameter (REQ-002) and the `BaseSigner.signAndBroadcast()` transaction
  amount (REQ-006). `decimals` MUST always be passed explicitly by the caller (`USDC_DECIMALS_BASE = 6`
  for Base USDC, `AKT_DECIMALS = 6` for `uakt`) — there is no default. Rounds DOWN (floor) to the nearest
  base unit for spend amounts — NEVER rounds up, since rounding up a capped spend amount could push the
  integer value fractionally past `toBaseUnits(SWAP_MAX_USD, decimals)`'s exact boundary. MUST throw
  (fail-closed) for `amountFloat` that is `NaN`, negative, non-finite (`Infinity`), or whose
  `amountFloat * 10^decimals` would exceed `Number.MAX_SAFE_INTEGER` before conversion to `BigInt`
  (overflow guard against float-precision loss silently mis-scaling the amount); MUST throw for
  `decimals` that is missing, non-integer, or negative.
- `fromBaseUnits(amount: bigint, decimals: number): number` — pure inverse of `toBaseUnits`; converts an
  integer on-chain base-unit balance (e.g. `ChainReader.getAkashBalance()`'s raw `uakt` `bigint`, REQ-001)
  into the decimal-float `currentAkt` value consumed by `computeSwapNeed` (REQ-001, REQ-012). MUST throw
  (fail-closed) for a negative `bigint` input (an impossible on-chain balance) rather than silently
  returning a negative float that `computeSwapNeed` would then have to guess is meaningful.
- `validateRoute(routeResponse)` — pure predicate over the parsed Skip API response: rejects if
  `dest_asset_denom !== 'uakt'`, `dest_asset_chain_id !== 'akashnet-2'`, `amount_out` missing/zero/NaN,
  or `txs_required` missing (REQ-002).
- `planNextLeg(routeResponse, submittedTxLedger)` — pure state machine: given the ordered list of legs
  from the route and a ledger of which leg-indices already have a confirmed tx id, returns the next leg
  to submit, or `DONE`, or `ALREADY_COMPLETE` (REQ-004, REQ-005 idempotency/resumability core).
- `checkSourceFunded(baseUsdcBalance: bigint, baseGasBalance: bigint, requiredBaseUnits: bigint, minGasWei: bigint)`
  — pure precondition check (REQ-003); `requiredBaseUnits` is the SAME
  `toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` `bigint` value REQ-012's single
  choke point produces (identical to the `amount_in` REQ-002 sends and the tx amount REQ-006 sends) — never an
  independently-derived or independently-named dollar float. `checkSourceFunded` performs an exact
  bigint-vs-bigint comparison of `baseUsdcBalance >= requiredBaseUnits`; the gas check
  (`baseGasBalance >= minGasWei`) remains a separate, independently-typed comparison, where `minGasWei` is
  ALWAYS the literal constant `MIN_GAS_WEI = 1_000_000_000_000_000n` (0.001 ETH, i.e. 10^15 wei) — given the
  exact same treatment REQ-006 gives `SWAP_MAX_USD`: a `const` literal defined once, in the same pure module,
  NEVER read from `process.env`, a CLI flag, or any genome/config file, with no second definition anywhere
  else in the codebase (FIND-001 fix). Reasoning for the value: a single Base L2 call's total fee (execution
  gas + L1 data fee) typically runs a few cents to low tens of cents at prevailing Base gas prices/ETH
  prices; `MIN_GAS_WEI` at 0.001 ETH (≈$2.50–$3.50 at ETH≈$2,500–$3,500) is a 25–100x margin over that
  typical per-tx cost, sized to cover BOTH an ERC-20 approve tx and the swap-broadcast tx that leg 1 may
  require, plus a spike in the Base L1 base-fee component, while staying small enough that it does not itself
  become an unfunded-gas blocker. `minGasWei` MUST NEVER be `0n` or any other value than `MIN_GAS_WEI`; an
  implementation defaulting it to `0n` makes REQ-003's gas check vacuous and MUST fail PROP-005's
  `MIN_GAS_WEI`-literal fixture (below).

**Effectful shell** (I/O, must be mocked/injected in tests, never exercised for real in Phase 2a/2b tests):
- AKT/USD price lookup (`PriceOracle.getAktUsdPrice()`) — an external price source queried once per
  invocation, AFTER the canonical lock (REQ-010) is held and BEFORE the Skip route request (REQ-002);
  MUST be injectable/mockable in tests, never queried live during Phase 2a/2b test runs (REQ-011).
- Canonical lock/ledger acquisition (`LedgerStore` lock primitive, destination-address-keyed, REQ-010)
  — effectful disk I/O, acquired BEFORE any Skip API call or price lookup.
- Skip API HTTP call (`fetch`/HTTP client to `api.skip.build`).
- Chain RPC balance queries (Base USDC/ETH balance, Akash `bank balances` via `akash` CLI or REST).
- Transaction signing and broadcast on Base (EVM signer) and Akash (`anicca-akash` key).
- Cross-chain relay polling / IBC packet confirmation polling (noble-1, osmosis-1 hops).
- Ledger file read/write for the idempotency tx-id log (local disk, effectful but not network).
- Wall-clock timeouts/sleeps for poll loops.

The pure core MUST be independently unit-testable with zero network/process access; the effectful shell
MUST be injectable (function-parameter transport/fetch/signer, not module-level singletons) so Phase 2a
tests can mock it without touching real money.

## Non-Functional Requirements

- **NFR-1 (fail-closed default)**: every ambiguous or unverifiable condition (no route, unfunded
  source, unconfirmed leg, stale balance read) MUST resolve to a non-zero exit / thrown error, never to
  "proceed optimistically."
- **NFR-2 (no silent partial state)**: the process MUST always leave the on-disk idempotency ledger in a
  state from which a subsequent run can determine exactly what has and has not been confirmed on-chain.
- **NFR-3 (bounded spend)**: no single invocation may move more than `SWAP_MAX_USD` of source value,
  regardless of the computed shortfall, env vars, CLI flags, or any config file — enforced at the single
  choke point specified in REQ-002/REQ-006/REQ-011/REQ-012: the same
  `toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` INTEGER value is used as
  both the Skip request amount and the signed transaction amount, verified at the driver/call-argument
  level against an exact `bigint` expectation — not merely inside `capUsd()`/`toBaseUnits()` in isolation,
  and never as an abstract dollar-float "-equivalent" comparison that a 10^6x-class base-unit conversion
  defect could still pass (see PROP-019, PROP-022).
- **NFR-4 (latency bound)**: each on-chain confirmation poll MUST have a finite, configurable timeout
  (default ≤ 10 minutes per leg) — the process MUST NOT hang indefinitely on the critical treasury path
  (this command is called synchronously from `akt-treasury.sh`, which itself is off the per-spawn deploy
  path but is still a bounded cron/wake job).
- **NFR-5 (identity isolation)**: the Base-chain signer key and the `anicca-akash` Cosmos key are
  distinct secrets; neither may be substituted for the other, and no key belonging to any other Anicca
  instance (Franklin, anicca-a3cdd4, etc.) may be loaded by this command (mirrors memory
  `feedback_earn_identity_resolve_per_instance_gate_on_anicca_home` — explicit gate, no shared-env
  fallback).

## Requirements

### REQ-001: Balance-gated idempotent trigger
**EARS**: WHEN the command is invoked THE SYSTEM SHALL query the current AKT balance at
`akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523` via `ChainReader.getAkashBalance()` (returning a raw
`uakt` `bigint`), SHALL convert it to a decimal-AKT float via `fromBaseUnits(balanceUakt, AKT_DECIMALS)`
(REQ-012, `AKT_DECIMALS = 6`) before using it as `computeSwapNeed`'s `current` input, and SHALL compute
`need = max(0, threshold - current)`, and SHALL exit 0 with no swap attempted WHEN `need == 0`.
**Edge Cases**:
- `current >= threshold` exactly at the boundary: no swap (never over-buy at the boundary either).
- Balance query returns an error/timeout: fail closed (non-zero exit), never assume `current = 0` and
  proceed to swap on a guess.
- `threshold` is unset or non-numeric: fail closed with a clear error, never default to swapping.
- `ChainReader.getAkashBalance()`'s raw `bigint` is passed to `computeSwapNeed` WITHOUT first being run
  through `fromBaseUnits`: this treats a micro-AKT integer as a whole-AKT float, an under-conversion
  error of the same class REQ-012 exists to prevent — fail closed / test failure, never a silent pass.
**Acceptance Criteria**:
- `computeSwapNeed(current, threshold)` returns `0` for all `current >= threshold` (property-tested).
- A run with `current >= threshold` never calls the Skip API or any signer (verified via a spy/mock
  transport asserting zero invocations).
- A test asserts the driver calls `computeSwapNeed` with `current === fromBaseUnits(mockedBalanceUakt,
  AKT_DECIMALS)`, never with the raw `bigint` or an un-scaled `Number(balanceUakt)` (PROP-023).

### REQ-002: Skip API route acquisition — capped amount_in request, fail-closed on no route
**EARS**: WHEN `need > 0` (and after REQ-010's lock is held and REQ-011's price/cap value is computed)
THE SYSTEM SHALL request a route from the Skip API in **amount_in mode**, using
`amountInBaseUnits = toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` (per
REQ-011 for the capped dollar figure and REQ-012 for its base-unit conversion — the already
fail-closed-priced, already-capped, already-integer-converted value) as the `amount_in` parameter, with
`source_asset_chain_id=8453`, `source_asset_denom=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`,
`dest_asset_chain_id=akashnet-2`, `dest_asset_denom=uakt`, and SHALL validate the response satisfies
`validateRoute` before proceeding, and SHALL fail closed (non-zero exit, no tx submitted) WHEN no valid
route is returned. THE SYSTEM SHALL NOT, under any circumstance, request the route in `amount_out` mode
using the raw AKT `need` as `amount_out`, nor request `amount_in` using any value other than the exact
`toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` output — in particular, THE
SYSTEM SHALL NOT pass the pre-conversion dollar float returned by `capUsd(...)` directly as `amount_in`.
**Edge Cases**:
- Skip API returns HTTP error or malformed JSON: fail closed.
- Skip API returns a route with `dest_asset_denom !== 'uakt'` or wrong `dest_asset_chain_id`: fail
  closed (defends against a Skip API bug or an intermediary hop swap-out to the wrong asset).
- Skip API returns `amount_out` far below a sane minimum (e.g. 0, negative, or NaN after parse): fail
  closed.
- Route requires more legs/chains than the system can execute (unsupported `txs_required` shape): fail
  closed rather than attempting a partial/unknown execution path.
- A code path attempts to request the route using the raw uncapped `need` (in AKT or USD) instead of
  `toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)`: this is exactly the class
  of defect PROP-019 (driver-level choke-point assertion) exists to catch — fail closed / test failure,
  never a silent pass.
- A code path passes `capUsd(usdEquivalentOf(need, aktUsdPrice))`'s raw dollar float (e.g. `15.32`)
  directly as `amount_in` instead of routing it through `toBaseUnits` first (an unconverted-unit defect,
  the exact class FIND-001/FIND-002 identified): fail closed / test failure — PROP-022's exact-integer
  fixture assertion exists specifically to catch this.
**Acceptance Criteria**:
- `validateRoute` rejects every malformed-response fixture in the test suite (empty body, wrong denom,
  wrong chain id, zero amount_out, missing txs_required) and accepts only the shape confirmed live this
  session.
- No tx-signing code path is reachable unless `validateRoute` returned true for the specific route object
  in hand (not a cached/prior route).
- A test asserts the mocked `SkipApiClient.getRoute()` call's `amount_in` argument is bit-identical to the
  INTEGER `toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` — not the dollar
  float — for the fixture's `need`/`aktUsdPrice`, and never equal to the raw uncapped USD-equivalent
  (converted or not) when the two differ (PROP-019, rewritten per FIND-001/FIND-002).

### REQ-003: Source-funding precondition (fail closed — the live current blocker)
**EARS**: BEFORE any transaction is signed THE SYSTEM SHALL verify the Base-chain USDC balance of the
configured source wallet (`baseUsdcBalance: bigint`, base units) is `>= requiredBaseUnits: bigint` — where
`requiredBaseUnits` is defined, exactly and only, as REQ-012's single choke-point value
`toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` (the identical `bigint` REQ-002
sends as Skip's `amount_in` and REQ-006 signs as the Base tx amount — never a re-derived or
independently-named raw dollar float) — AND the Base-chain native-gas balance (`baseGasBalance: bigint`) is
`>= minGasWei: bigint` for leg 1, where `minGasWei` is ALWAYS the literal constant
`MIN_GAS_WEI = 1_000_000_000_000_000n` defined in the Purity Boundary Analysis above (never `0n`, never
sourced from env/config), and SHALL fail closed with an explicit "insufficient funded source" error
WHEN either check fails — THE SYSTEM SHALL NOT infer, borrow from, or auto-bridge from any other chain/wallet
(e.g. Franklin's Solana USDC) as an implicit fallback.
**Edge Cases**:
- Base USDC balance is 0 (the current real-world state, confirmed this session): fail closed, exit
  non-zero, log the specific shortfall (`have X, need Y`, both expressed in the same `bigint` base units).
- Base USDC balance is nonzero but below `requiredBaseUnits`: fail closed with the exact deficit — this MUST
  be caught by an exact `bigint`-vs-`bigint` comparison, never a comparison against an independently-named or
  independently-scaled dollar float (see the PROP-005 nonzero discriminating fixture below).
- Base USDC is sufficient but native ETH/gas for the Base-side approve+swap tx is insufficient: fail
  closed (a partially-fundable swap that dies mid-signature is worse than not starting).
- Source wallet address/key is misconfigured (points at the wrong instance's wallet): this is an
  identity-safety failure, not a funding failure — REQ-009 governs; REQ-003's balance check still applies
  on top of whatever wallet is configured.
**Acceptance Criteria**:
- `checkSourceFunded` returns `false` for every fixture where `baseUsdcBalance < requiredBaseUnits` (exact
  `bigint`-vs-`bigint` comparison) or `baseGasBalance < minGasWei`, and the swap driver never proceeds past
  this check when it returns `false` (asserted via mock-transport call-count of zero for the sign/broadcast
  functions).
- The current real balances (Base USDC ≈ 0, Base gas ≈ 0) MUST be one of the fixtures exercised in
  Phase 2a tests, asserting the command fails closed exactly as it would today in production (PROP-006).
- A nonzero-balance discriminating fixture MUST also be exercised (PROP-005): `baseUsdcBalance = 5000000n`
  ($5.00 in base units) against `requiredBaseUnits = toBaseUnits(15.32, 6) = 15320000n` ($15.32 in base
  units) MUST return `false` (insufficient — `5000000n < 15320000n`). A wrong-unit implementation that
  instead compares `baseUsdcBalance` against the raw dollar float `15.32` (e.g. `baseUsdcBalance >=
  neededUsdFloat` → `5000000n >= 15.32` → `true`) would wrongly report `true` (funded) on this exact
  fixture and MUST fail this assertion — proving the test suite is falsifiable against the FIND-001/
  FIND-002 class of wrong-unit false-funded defect, which PROP-006's zero-balance-only fixture cannot catch
  (`0n` is `< ` any positive comparand regardless of its unit).
- A `MIN_GAS_WEI`-literal fixture (PROP-005, closing FIND-001) asserts `checkSourceFunded` is exercised with
  `minGasWei = MIN_GAS_WEI = 1_000_000_000_000_000n` and, for `baseGasBalance = 500_000_000_000_000n` (half
  of `MIN_GAS_WEI`, nonzero), returns `false`. A `minGasWei = 0n` stand-in for a defaulted-to-zero
  implementation MUST fail this fixture (it would wrongly return `true` for the same
  `baseGasBalance = 500_000_000_000_000n`), proving the test suite is falsifiable against a vacuous
  0n-default `minGasWei` implementation.
- A test asserts the driver's ACTUAL runtime argument to `checkSourceFunded`'s `minGasWei` parameter is
  bit-identical (`===`, `bigint`) to `MIN_GAS_WEI`, inspected via the spy's actual call argument (not
  `checkSourceFunded`'s pure return value in isolation, and not merely a test-supplied literal passed
  directly to the pure function) — a driver implementation that hardcodes, defaults, or independently
  derives a different `minGasWei` (e.g. `0n`) at its own call site MUST fail this assertion, even though
  the isolated `MIN_GAS_WEI`-literal fixture above already exercises the pure comparison logic correctly
  (PROP-005, mirroring the `requiredBaseUnits` driver-level assertion below).
- A test asserts the driver's ACTUAL runtime argument to `checkSourceFunded`'s `requiredBaseUnits` parameter
  is bit-identical (`===`, `bigint`) to the SAME value simultaneously passed as `SkipApiClient.getRoute()`'s
  `amount_in` argument AND `BaseSigner.signAndBroadcast()`'s tx-amount argument, inspecting all three spies'
  actual call arguments together in one test run (not `checkSourceFunded`'s pure return value or
  `requiredBaseUnits` in isolation) — a driver implementation using a stale or independently re-derived
  `requiredBaseUnits` (e.g. a cached prior price/need) while correctly computing the same value fresh for the
  other two call sites MUST fail this assertion (PROP-005, extended per FIND-003).

### REQ-004: Multi-tx route execution with per-leg on-chain verification
**EARS**: WHEN a valid route with `txs_required` legs is being executed THE SYSTEM SHALL submit each leg
in order, SHALL wait for and confirm that leg's transaction/IBC-packet finality on its destination chain
before submitting the next leg, and SHALL abort (fail closed, preserving all prior confirmed-leg state)
WHEN any leg fails to confirm within its timeout.
**Edge Cases**:
- Leg 1 (Base swap/bridge-out tx) confirms but Leg 2 (IBC relay through noble-1/osmosis-1 to akashnet-2)
  stalls: the system MUST NOT re-submit Leg 1, MUST poll/wait (bounded by NFR-4) or fail closed leaving
  the ledger showing Leg 1 confirmed / Leg 2 pending — a human/operator or a later resumed run can then
  act, but the process itself never silently loses the fact that Leg 1's funds already left the source
  wallet.
- Relay timeout with no error but no progress (funds in transit, IBC packet not yet relayed): treated as
  "pending", not "failed" — the ledger records `pending`, and the exit code signals "not yet done" rather
  than corrupting the ledger into a false `failed` or false `done` state.
- A leg's confirmed amount differs from the route's quoted `amount_out` for that leg (slippage/partial
  fill beyond tolerance): fail closed rather than silently accepting a worse-than-quoted fill; the
  acceptable slippage tolerance is the explicit, tested literal constant `TOLERANCE_BPS = 50` (0.5%) — see
  REQ-007 for its exact definition, reasoning, and boundary-value proof obligations (PROP-013).
**Acceptance Criteria**:
- `planNextLeg` never returns a leg index that already has a `confirmed` entry in the ledger.
- A simulated Leg-2 stall (mock transport returns `pending` repeatedly past the timeout) results in
  non-zero exit and a ledger file whose Leg-1 entry remains `confirmed` and whose Leg-2 entry is
  `pending`, not `failed` or absent.

### REQ-005: Idempotency and resumability — no double-spend on crash/retry
**EARS**: WHEN the command is invoked and the canonical ledger file (acquired per REQ-010, keyed by the
destination Akash address `akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523`, NOT by any Skip route/quote id)
shows one or more legs already `confirmed`, THE SYSTEM SHALL resume from the first unconfirmed leg and
SHALL NOT re-submit any leg already recorded `confirmed`, regardless of how many times the command is
re-invoked and regardless of whether the Skip API would return a different route/quote id on this
invocation than on the prior one.
**Edge Cases**:
- **Window 1 — crash before any broadcast RPC call is made for a leg**: nothing was sent to any chain; on
  the next run the system MUST treat that leg as not-yet-attempted and MAY submit it fresh.
- **Window 2 — crash after the broadcast RPC call is made but before (or during) the ledger's
  post-broadcast `confirmed`/tx-hash write**: THE SYSTEM SHALL, SYNCHRONOUSLY and BEFORE making the
  broadcast RPC call, durably persist a `submitting` record to the canonical ledger containing a
  deterministic, re-derivable on-chain query key for that leg (the source account's deterministic next
  nonce + leg index) — so that even if the process crashes before the broadcast RPC call returns
  (therefore before any tx hash exists) or after it returns but before the tx hash is written, the next
  run can ALWAYS re-derive an on-chain query key (source address + deterministic nonce) and query the
  chain for that leg's actual on-chain status BEFORE deciding whether to resubmit. THE SYSTEM SHALL NOT
  resubmit a leg found in a `submitting` state without first performing this on-chain query.
- **Window 3 — crash after the ledger's `confirmed` write for a leg**: the ledger already reflects ground
  truth for that leg; no on-chain query is needed to know it is done, but the system MUST still
  re-evaluate overall route-completion state (via `planNextLeg`) before continuing to the next leg.
- Ledger file is corrupted/unparseable: fail closed (do not treat "unreadable" as "empty/start fresh",
  since that risks re-submitting an already-confirmed leg) — surface a loud, explicit status for operator
  intervention.
- Two invocations run concurrently (cron overlap): prevented from both reaching this point at all by
  REQ-010's canonical destination-address-keyed lock, acquired BEFORE either invocation requests a route
  — the loser resumes the winner's in-progress operation per this REQ rather than racing to submit a leg.
**Acceptance Criteria**:
- Property test: for any sequence of (crash-before-broadcast-RPC-call [Window 1], crash-after-broadcast-
  RPC-call-before-tx-hash-write [Window 2, sub-case: RPC not yet returned], crash-after-tx-hash-write-
  before-confirmed-write [Window 2, sub-case: RPC returned], crash-after-confirmed-write [Window 3],
  normal-completion) injected at each leg boundary, replaying the command to completion never results in
  more than one `confirmed`-producing broadcast call per leg index, AND the pre-broadcast `submitting`
  record's nonce/leg-index key is always present and re-derivable whenever a broadcast RPC call was
  actually made (fast-check property, REQ-005 is Tier 2, money-safety critical — see PROP-009, PROP-020).
- A concurrent-invocation simulation (two drivers, each given a distinct freshly-mocked Skip quote id but
  contending for the same destination-address-keyed lock per REQ-010) results in exactly one successful
  submission per leg across both invocations.

### REQ-006: Hard money-safety spend cap (never overridable)
**EARS**: THE SYSTEM SHALL NOT initiate a swap whose source-asset USD value exceeds a fixed constant
`SWAP_MAX_USD` defined as a literal in the pure cap-enforcement module, and THE SYSTEM SHALL apply this
cap unconditionally AFTER any shortfall/need computation, ignoring `process.env`, CLI flags, genome
output, or any config file value that would raise it (mirrors `sol-trade`'s
`lib/resolve-max-spend.sh` single-choke-point hard-override pattern — a script that prints a literal
value and explicitly ignores `SOL_TRADE_MAX_SPEND` and every other env var).
**EARS (choke point)**: THE SYSTEM SHALL construct both the Skip API route request's `amount_in`
parameter (REQ-002) and the amount actually signed and broadcast by `BaseSigner.signAndBroadcast()` from
`toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` (REQ-011's capped dollar
figure, converted to an integer base-unit amount by REQ-012's single named conversion function) as the
sole source of the swap amount — no other code path, value, re-query, re-computation, or independent
unit-scaling SHALL determine `amountIn` for the Skip request or for signing, and the two call sites
(Skip `amount_in` and `BaseSigner.signAndBroadcast()`'s tx amount) SHALL receive the exact same `bigint`
value, not merely two values that happen to be numerically equal after separate conversions. A swap SHALL
NEVER be signed for an amount that was recomputed independently of the exact capped-and-converted value
already used for the Skip request, and SHALL NEVER be signed for the pre-conversion dollar float.
**Edge Cases**:
- Computed `need` (in USD-equivalent) exceeds `SWAP_MAX_USD`: the system swaps at most `SWAP_MAX_USD`
  worth and MUST clearly report that the swap was capped and the treasury may remain below threshold
  (never silently "top up as much as needed").
- An attacker-controlled or buggy env var / genome value attempts to set a higher cap: MUST have zero
  effect on the actual enforced value (asserted by a test that sets a hostile env var and confirms the
  enforced cap is unchanged).
- `SWAP_MAX_USD` itself is defined once, in one file, with no second definition anywhere else in the
  codebase that could drift out of sync.
- A code path signs/broadcasts using a re-derived or independently recomputed amount instead of the exact
  `toBaseUnits(capUsd(...), USDC_DECIMALS_BASE)` value already used for the Skip request, OR uses the
  pre-conversion dollar float, OR applies a different/wrong `decimals` value than `USDC_DECIMALS_BASE`
  when converting: THE SYSTEM SHALL NOT permit any of these — this is precisely the class of defect the
  driver-level choke-point test (PROP-019) and the conversion-exactness test (PROP-022) exist to catch;
  `capUsd()` and `toBaseUnits()` each passing their own isolated unit tests is explicitly NOT sufficient
  evidence that this requirement holds — only the driver-level call-argument assertion is.
**Acceptance Criteria**:
- `capUsd(x)` returns `Math.min(x, SWAP_MAX_USD)` for all `x`, verified by property test across a wide
  range of `x` including adversarial values (`Infinity`, negative, `NaN` → treated as 0/fail-closed, not
  as "unbounded").
- A test asserts `capUsd` output is bit-for-bit identical whether or not `process.env.SWAP_MAX_USD`,
  `process.env.SOL_TRADE_MAX_SPEND`-style vars, or any genome-provided override value is set.
- PROP-019: for any `need` whose USD-equivalent exceeds `SWAP_MAX_USD`, the mocked
  `SkipApiClient.getRoute()` call's `amount_in` argument AND the mocked `BaseSigner.signAndBroadcast()`
  call's transaction-amount argument are BOTH bit-identical to the exact INTEGER
  `toBaseUnits(SWAP_MAX_USD, USDC_DECIMALS_BASE)` `bigint` value for the capped case (never merely `<=`
  an undefined "-equivalent" float), asserted by inspecting the spy's actual call arguments — never by
  inspecting `capUsd()`'s or `toBaseUnits()`'s return values in isolation. A fixture using a WRONG
  `decimals` value (e.g. an implementation defect passing `0` or `18` instead of `6`) MUST fail this
  assertion, proving the test is falsifiable against a 10^6x-class unit error (see PROP-022).

### REQ-007: Final on-chain settlement verification before declaring success
**EARS**: AFTER the last route leg is confirmed THE SYSTEM SHALL re-query
`akash query bank balances akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523` (or equivalent REST query) and
SHALL only report success WHEN the observed `uakt` balance increased by an amount consistent with the
route's quoted `amount_out` (within slippage tolerance); THE SYSTEM SHALL NOT declare success merely
because all leg transactions returned a zero exit code. The slippage tolerance is ALWAYS the literal
constant `TOLERANCE_BPS = 50` (0.5%, i.e. `verifySettlement` accepts any `postBalanceUakt - preBalanceUakt`
`>= quotedAmountOutUakt * (10000n - 50n) / 10000n`), given the exact same treatment REQ-006 gives
`SWAP_MAX_USD` and REQ-003 gives `MIN_GAS_WEI`: a `const` literal defined once, in the same module,
NEVER read from `process.env`, a CLI flag, or any genome/config file, with no second definition anywhere
else in the codebase (FIND-002 fix). Reasoning for the value: this route is a 3-hop IBC path
(Base→noble-1→osmosis-1→akashnet-2) whose only sources of fill variance are AMM/DEX-hop rounding and
in-flight IBC relay timing, not open-market price discovery on an illiquid asset — 50 bps is tight enough to
reject a materially worse-than-quoted fill (the exact failure mode this REQ exists to prevent) while still
tolerating ordinary multi-hop rounding/fee dust, and is consistent with common DEX-aggregator "tight"
slippage defaults (0.5%–1%); given `SWAP_MAX_USD`'s already-small per-swap dollar cap, the absolute
worst-case dollar loss at 50 bps stays proportionally small.
**Edge Cases**:
- All legs report "confirmed" per their own chain's tx status, but the final Akash balance query shows
  no increase (funds stuck somewhere in the IBC path, or landed in a different denom): fail closed,
  report "legs confirmed but AKT not observed at destination" distinctly from a leg-level failure.
- Balance query itself times out/errors after legs are done: fail closed with a distinct "cannot verify
  final settlement" status (not silently reported as success).
**Acceptance Criteria**:
- The success path is unreachable in tests unless the mocked final-balance query shows the expected
  delta; a mock returning an unchanged balance after all legs "succeed" results in non-zero exit.
- Boundary-value fixtures (PROP-013, closing FIND-002) for `quotedAmountOutUakt = 1_000_000n` (1 AKT) and
  `TOLERANCE_BPS = 50`: (a) an observed delta of exactly `995_000n` uakt (`quotedAmountOutUakt * 9950n /
  10000n`, i.e. precisely at the 0.5% boundary) MUST pass (`verifySettlement` returns `true`); (b) an
  observed delta of `994_999n` uakt (one base unit below the boundary) MUST fail closed
  (`verifySettlement` returns `false`) — together proving the test suite discriminates a correctly-tight
  50-bps tolerance from an arbitrarily looser one, which the zero-delta-only fixture above cannot do.
- A test asserts the driver's ACTUAL runtime argument to `verifySettlement`'s `toleranceBps` parameter is
  bit-identical (`===`, `number`) to `TOLERANCE_BPS`, inspected via the spy's actual call argument (not
  `verifySettlement`'s pure return value in isolation, and not merely a test-supplied literal passed
  directly to the pure function) — a driver implementation that hardcodes or independently derives a
  different (looser) `toleranceBps` at its own call site MUST fail this assertion, even though the
  boundary fixtures above already exercise the pure comparison logic correctly (PROP-013, mirroring the
  `requiredBaseUnits`/`minGasWei` driver-level assertions in REQ-003).

### REQ-008: Wiring as TREASURY_SWAP_CMD
**EARS**: THE SYSTEM SHALL be invocable as a single shell command assignable to the `TREASURY_SWAP_CMD`
environment variable consumed by `akt-treasury.sh:52-54`, SHALL take no required interactive input, SHALL
exit 0 only on confirmed REQ-007 success, and SHALL exit non-zero on every other outcome (matching
`akt-treasury.sh`'s existing `|| { ... exit 1; }` wrapping).
**Edge Cases**:
- `akt-treasury.sh` invokes the command with `bash -c "$TREASURY_SWAP_CMD"` — the command MUST NOT
  depend on shell state (cwd, exported vars) beyond what `akt-treasury.sh` itself exports
  (`AKASH_KEY_NAME`, `AKASH_KEYRING_BACKEND`, `AKASH_NODE`, `AKASH_CHAIN_ID`) plus its own
  self-contained config.
- Command must be silent-but-logged on stdout/stderr in a way that does not corrupt any JSON stdout
  contract used elsewhere in the codebase (memory
  `feedback_loop_scripts_must_emit_clean_json_stdout` — human-readable status lines only, no
  interleaved JSON unless this command is itself consumed as JSON by something else, which it is not).
**Acceptance Criteria**:
- A test invokes the packaged CLI entrypoint exactly as `akt-treasury.sh` would (`bash -c "<cmd>"`) with
  a mocked transport injected via env/config, and asserts the exit code contract holds for a success and
  a failure fixture.

### REQ-009: Identity/key safety — signs only with the intended keys
**EARS**: THE SYSTEM SHALL sign the Base-chain leg only with the explicitly configured Base signer key
for this feature, SHALL sign the Akash-chain leg only with `AKASH_KEY_NAME=anicca-akash` in keyring
backend `test`, and SHALL fail closed WHEN either key is missing, unset, or resolves to an address that
does not match a pinned expected address.
**Edge Cases**:
- `AKASH_KEY_NAME` unset or points at a different key than `anicca-akash`: fail closed (mirrors
  `akt-treasury.sh:19`'s existing `: "${AKASH_KEY_NAME:?...}"` guard — this command MUST NOT weaken it).
- Base signer key resolves to an address other than the pinned/expected source wallet address: fail
  closed — this defends against accidentally loading another instance's key (Franklin, anicca-a3cdd4) via
  a shared-env fallback (mirrors memory
  `feedback_earn_identity_resolve_per_instance_gate_on_anicca_home` — explicit `ANICCA_HOME`/instance
  gate, no implicit fallback).
- No key configuration is present at all: fail closed with an explicit "no signer configured" error, not
  a silent no-op that reports success.
**Acceptance Criteria**:
- A test with a Base signer key resolving to an unexpected address results in non-zero exit and zero
  broadcast calls.
- A test with `AKASH_KEY_NAME` unset (or set to a non-`anicca-akash` value) results in non-zero exit and
  zero broadcast calls, mirroring the existing bash guard's behavior.

### REQ-010: Canonical destination-scoped lock — precondition to route request
**EARS**: BEFORE requesting any route from the Skip API (REQ-002) or performing any AKT/USD price lookup
(REQ-011) THE SYSTEM SHALL attempt to atomically acquire a single canonical lock/ledger keyed by the
destination Akash address `akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523` (NOT by any Skip route/quote id,
which changes freshly per request), backed by the same on-disk ledger file used for REQ-005's
resumability; WHEN the lock is already held by an incomplete prior operation THE SYSTEM SHALL resume that
prior operation per REQ-005 and SHALL NOT request a new route, perform a new price lookup, or acquire a
second lock; WHEN the lock is acquired successfully THE SYSTEM SHALL proceed to REQ-011 then REQ-002.
**Edge Cases**:
- Two invocations are near-simultaneous (cron overlap) and would each independently be quoted a distinct,
  freshly-timestamped Skip route/quote id: THE SYSTEM SHALL dedupe them via the shared
  destination-address-keyed lock regardless of the fact that their (not-yet-requested) route ids would
  differ — the second invocation MUST observe the lock held and resume/no-op per REQ-005 BEFORE it ever
  calls `PriceOracle.getAktUsdPrice()` (REQ-011) or `SkipApiClient.getRoute()` (REQ-002), never after.
- Lock file exists but its recorded holder is confirmed dead/stale (matches REQ-005's crash taxonomy):
  treat as an incomplete prior operation to resume via REQ-005's crash-recovery logic, not as live
  contention to reject outright.
- Lock acquisition itself fails/errors (e.g. filesystem error): fail closed — no route request, no price
  lookup, no signing.
**Acceptance Criteria**:
- A test asserts `SkipApiClient.getRoute()` and `PriceOracle.getAktUsdPrice()` are called zero times when
  a mocked lock-acquire call reports the lock already held.
- The concurrent-invocation property test (PROP-010) gives each of two simulated invocations a *distinct*
  mocked Skip route/quote id and confirms only one invocation proceeds past lock acquisition to request a
  price/route/sign a tx; the other resumes/no-ops — proving dedup is keyed by destination address, not by
  route content.

### REQ-011: AKT→USD conversion for capped spend sizing
**EARS**: BEFORE requesting a route (REQ-002) and AFTER REQ-010's lock is held, THE SYSTEM SHALL obtain
the current AKT/USD price via `PriceOracle.getAktUsdPrice()` and SHALL fail closed (non-zero exit, no
Skip request, no signing) WHEN the returned price is missing, zero, negative, non-numeric, or the query
errors/times out; WHEN a valid price is obtained THE SYSTEM SHALL compute `usdEquivalentOf(need,
aktUsdPrice)` as the pure USD-equivalent of the AKT shortfall computed in REQ-001, and SHALL pass
`capUsd(usdEquivalentOf(need, aktUsdPrice))` — never the raw, uncapped `usdEquivalentOf(...)` value and
never `need` itself — as the sole dollar-float input to REQ-012's `toBaseUnits` conversion, whose integer
`bigint` output is in turn the sole amount input to REQ-002's Skip route request and to REQ-006's signing
choke point.
**Edge Cases**:
- `aktUsdPrice` is `0`, negative, `NaN`, or `Infinity`: fail closed, no Skip request made, no price used.
- `PriceOracle.getAktUsdPrice()` call errors or times out: fail closed, treated identically to REQ-001's
  balance-query failure (never assume a default/stale/last-known price).
- `need == 0` (from REQ-001): `usdEquivalentOf` is never called and no price lookup occurs at all (mirrors
  REQ-001's zero-swap short-circuit — no unnecessary effectful calls when no swap is needed).
**Acceptance Criteria**:
- `usdEquivalentOf(needAkt, aktUsdPrice)` returns `needAkt * aktUsdPrice` for all finite non-negative
  `needAkt` and finite positive `aktUsdPrice` (property-tested, PROP-018).
- `usdEquivalentOf` resolves to an explicit fail-closed signal (throw) for `aktUsdPrice <= 0`, `NaN`, or
  `Infinity`, verified across adversarial inputs (PROP-018).
- A test asserts the driver never calls `SkipApiClient.getRoute()` when the mocked
  `PriceOracle.getAktUsdPrice()` rejects or returns an invalid price (zero call count on Skip/sign/
  broadcast functions, extending PROP-002's zero-call pattern to this precondition).

### REQ-012: Base-unit conversion choke point (USD/AKT float ↔ integer on-chain base units)
**EARS**: THE SYSTEM SHALL convert every decimal-float amount that crosses the boundary into an on-chain
integer amount, or out of one, through exactly ONE named pure function pair —
`toBaseUnits(amountFloat, decimals): bigint` and `fromBaseUnits(amount, decimals): number` — and no other
code path SHALL perform this conversion. Specifically: (a) the value passed as the Skip API's `amount_in`
parameter (REQ-002) and the value signed and broadcast by `BaseSigner.signAndBroadcast()` (REQ-006) SHALL
each be exactly `toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` where
`USDC_DECIMALS_BASE = 6` (Base USDC's decimal precision), and this integer value SHALL additionally satisfy
the runtime invariant `<= toBaseUnits(SWAP_MAX_USD, USDC_DECIMALS_BASE)`, and THE SYSTEM SHALL fail closed
if it does not (defense in depth, independent of `capUsd()`'s own correctness); (b) the `current` AKT
balance fed into `computeSwapNeed` (REQ-001) SHALL be exactly `fromBaseUnits(balanceUakt, AKT_DECIMALS)`
where `balanceUakt` is `ChainReader.getAkashBalance()`'s raw `bigint` and `AKT_DECIMALS = 6`; and (c) the
`requiredBaseUnits` comparand `checkSourceFunded` (REQ-003) compares against `baseUsdcBalance` SHALL be
exactly the SAME `toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` `bigint`
value as (a) — never a second, independently-named, or independently-derived value (e.g. a raw dollar
float). THE SYSTEM SHALL NOT define, inline, or tolerate any second/alternate conversion between these unit
spaces anywhere else in the codebase.
**Edge Cases**:
- `toBaseUnits` receives a `cappedUsd` value with more precision than `decimals` allows (e.g. sub-base-unit
  fractional cents): rounds DOWN (floor) to the nearest base unit — NEVER rounds up, since rounding up a
  spend amount on the boundary could push the integer value fractionally past
  `toBaseUnits(SWAP_MAX_USD, USDC_DECIMALS_BASE)`'s exact cap.
- `toBaseUnits` receives `NaN`, a negative number, or non-finite (`Infinity`) `amountFloat`: throws
  (fail-closed) — this is a second independent guard even though `capUsd`/`usdEquivalentOf` are already
  supposed to have excluded these values upstream.
- `toBaseUnits`'s intermediate scaled value (`amountFloat * 10^decimals`) would exceed
  `Number.MAX_SAFE_INTEGER` before conversion to `BigInt`: throws (fail-closed) rather than silently
  producing a precision-corrupted integer; acceptable given `SWAP_MAX_USD` is a small literal constant, so
  this can only trigger on a build-time misconfiguration of the constant itself.
- `decimals` is omitted, non-integer, or negative (no implicit default is ever used): `toBaseUnits`/
  `fromBaseUnits` throw — every call site MUST pass `USDC_DECIMALS_BASE` or `AKT_DECIMALS` explicitly.
- `fromBaseUnits` receives a negative `bigint`: throws (fail-closed) rather than returning a negative float
  that `computeSwapNeed` would silently have to interpret.
- An implementation passes the WRONG `decimals` constant (e.g. `0` or `18` instead of `6`) at either call
  site: THE SYSTEM SHALL NOT permit this to pass verification — PROP-022's exact-integer fixture assertion
  (checked against a concrete `$15.00 → 15000000n` expectation, not a range) is the mechanism designed to
  make this class of defect fail loudly rather than silently pass a `<=`-style comparison.
**Acceptance Criteria**:
- `toBaseUnits(15.0, 6) === 15000000n` (fixture, PROP-022).
- `toBaseUnits(15.0000009, 6) === 15000000n` (floor-rounding fixture — a naive `Math.round`-based
  implementation would produce `15000001n` and MUST fail this fixture, PROP-022).
- `toBaseUnits(SWAP_MAX_USD, 6)` is the exact upper-bound `bigint` asserted by REQ-006/PROP-019's rewritten
  choke-point test.
- A fixture with an implementation using the wrong `decimals` (e.g. `toBaseUnits(15.0, 0)` or
  `toBaseUnits(15.0, 18)`) produces an integer that FAILS the exact-equality assertion against the
  correctly-scaled expectation — proving the test suite is falsifiable against a 10^6x-class unit error
  (PROP-022, directly closing FIND-001/FIND-002).
- `fromBaseUnits(1850000n, 6) === 1.85` (round-trip fixture feeding REQ-001's `computeSwapNeed`, PROP-023).
- `toBaseUnits`/`fromBaseUnits` round-trip: for a representative set of fixture floats with no more than
  `decimals` fractional digits, `fromBaseUnits(toBaseUnits(x, decimals), decimals) === x` (PROP-022/023).
- `checkSourceFunded`'s (REQ-003) `requiredBaseUnits` parameter is bit-identical to
  `toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` for the fixture's `need`/
  `aktUsdPrice` — the same integer routed to Skip's `amount_in` and the Base tx amount — never a second,
  independently-named, or independently-scaled value (PROP-005).

## Edge Case Catalog (cross-cutting, applies across REQ-002 through REQ-012)

| Edge case | Required behavior |
|---|---|
| No route found (REQ-002) | Fail closed, exit non-zero, no tx |
| Insufficient source funds/gas (REQ-003) | Fail closed, exit non-zero, no tx, explicit deficit reported |
| Partial fill / slippage beyond tolerance (REQ-004) | Fail closed, ledger reflects true on-chain state |
| Relay timeout mid-route (REQ-004, REQ-005) | Ledger marks leg `pending`, not `failed`/`done`; resumable |
| Gas shortfall on any intermediate chain (REQ-004) | Fail closed at that leg; prior confirmed legs stay recorded |
| Crash before broadcast RPC call, or after RPC call but before ledger write (REQ-005) | Synchronous pre-broadcast `submitting` record (nonce+leg index) makes on-chain state always re-derivable/queryable before any resubmit decision — never blind-resubmit |
| Concurrent invocation (REQ-005, REQ-010) | Canonical destination-address-keyed lock (acquired before any route request) prevents double-submit even when each invocation would get a distinct fresh Skip quote id; loser resumes/no-ops |
| No canonical lock acquired before route/price request (REQ-010) | Fail closed / zero Skip and price-oracle calls until lock held |
| Cap exceeded by computed need (REQ-002, REQ-006, REQ-011, REQ-012) | Skip request `amount_in` and the signed tx amount are both the identical `toBaseUnits(capUsd(usdEquivalentOf(need, aktUsdPrice)), USDC_DECIMALS_BASE)` integer value — never independently recomputed, never the pre-conversion float (single choke point, PROP-019/PROP-022) |
| USD/AKT float passed to Skip or signer without base-unit conversion, or converted with the wrong `decimals` (REQ-012) | Fail closed / test failure — exact-integer fixtures (PROP-022/023) catch a 10^6x-class unit error that a `<=`-equivalent float comparison would miss |
| Invalid/unavailable AKT/USD price (REQ-011) | Fail closed before any Skip request or price-derived amount is used |
| Legs confirmed but destination balance unchanged (REQ-007) | Fail closed, distinct "settlement unverified" status |
| Wrong/missing signer key (REQ-009) | Fail closed before any signing occurs |

## OPEN QUESTION for Phase 1c / spec-review (flag as blocking until resolved)

**There is currently no funded, routable USDC source for this swap.** REQ-003 makes this an explicit,
tested fail-closed precondition rather than a silent assumption — which is correct and MUST stay in the
spec regardless of how the question below resolves. But the swap cannot actually run in production until
one of the following is decided and separately diligenced (out of scope for this feature's code, but the
choice affects which config/wallet this command is pointed at):
1. Franklin bridges its Solana USDC surplus to Base first (a *separate* Solana→Base bridge feature, with
   its own spec, its own fail-closed preconditions, and its own money-safety cap), after which this
   command's `checkSourceFunded` would pass against Franklin's Base wallet, **or**
2. The operator (Dais) manually seeds a small bootstrap amount of USDC + gas directly to a Base wallet
   dedicated to this command, **or**
3. Some other in-scope Anicca earn rail accumulates Base-native USDC directly (no bridge needed).

This feature's code and tests MUST NOT assume any of these three; it must work correctly (fail closed)
under option "none of the above yet" (today's real state) and succeed once any one of them supplies a
funded source wallet address into this command's config. Flag this explicitly for `vcsdd-spec-review`.
