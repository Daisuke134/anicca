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
  consumers are the Skip route request (REQ-002) and the signed Base transaction (REQ-006's choke
  point) — never a re-derived or independently recomputed amount.
- `validateRoute(routeResponse)` — pure predicate over the parsed Skip API response: rejects if
  `dest_asset_denom !== 'uakt'`, `dest_asset_chain_id !== 'akashnet-2'`, `amount_out` missing/zero/NaN,
  or `txs_required` missing (REQ-002).
- `planNextLeg(routeResponse, submittedTxLedger)` — pure state machine: given the ordered list of legs
  from the route and a ledger of which leg-indices already have a confirmed tx id, returns the next leg
  to submit, or `DONE`, or `ALREADY_COMPLETE` (REQ-004, REQ-005 idempotency/resumability core).
- `checkSourceFunded(baseUsdcBalance, baseGasBalance, neededUsd, minGasWei)` — pure precondition check
  (REQ-003).

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
  choke point specified in REQ-002/REQ-006/REQ-011: the same `capUsd(usdEquivalentOf(need, aktUsdPrice))`
  value is used as both the Skip request amount and the signed transaction amount, verified at the
  driver/call-argument level, not merely inside `capUsd()` in isolation (see PROP-019).
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
`akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523` and compute `need = max(0, threshold - current)`, and
SHALL exit 0 with no swap attempted WHEN `need == 0`.
**Edge Cases**:
- `current >= threshold` exactly at the boundary: no swap (never over-buy at the boundary either).
- Balance query returns an error/timeout: fail closed (non-zero exit), never assume `current = 0` and
  proceed to swap on a guess.
- `threshold` is unset or non-numeric: fail closed with a clear error, never default to swapping.
**Acceptance Criteria**:
- `computeSwapNeed(current, threshold)` returns `0` for all `current >= threshold` (property-tested).
- A run with `current >= threshold` never calls the Skip API or any signer (verified via a spy/mock
  transport asserting zero invocations).

### REQ-002: Skip API route acquisition — capped amount_in request, fail-closed on no route
**EARS**: WHEN `need > 0` (and after REQ-010's lock is held and REQ-011's price/cap value is computed)
THE SYSTEM SHALL request a route from the Skip API in **amount_in mode**, using
`amountInUsd = capUsd(usdEquivalentOf(need, aktUsdPrice))` (per REQ-011 — the already fail-closed-priced,
already-capped value) as the `amount_in` parameter, with `source_asset_chain_id=8453`,
`source_asset_denom=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, `dest_asset_chain_id=akashnet-2`,
`dest_asset_denom=uakt`, and SHALL validate the response satisfies `validateRoute` before proceeding, and
SHALL fail closed (non-zero exit, no tx submitted) WHEN no valid route is returned. THE SYSTEM SHALL NOT,
under any circumstance, request the route in `amount_out` mode using the raw AKT `need` as `amount_out`,
nor request `amount_in` using any value other than the exact `capUsd(usdEquivalentOf(need, aktUsdPrice))`
output.
**Edge Cases**:
- Skip API returns HTTP error or malformed JSON: fail closed.
- Skip API returns a route with `dest_asset_denom !== 'uakt'` or wrong `dest_asset_chain_id`: fail
  closed (defends against a Skip API bug or an intermediary hop swap-out to the wrong asset).
- Skip API returns `amount_out` far below a sane minimum (e.g. 0, negative, or NaN after parse): fail
  closed.
- Route requires more legs/chains than the system can execute (unsupported `txs_required` shape): fail
  closed rather than attempting a partial/unknown execution path.
- A code path attempts to request the route using the raw uncapped `need` (in AKT or USD) instead of
  `capUsd(usdEquivalentOf(need, aktUsdPrice))`: this is exactly the class of defect PROP-019 (driver-level
  choke-point assertion) exists to catch — fail closed / test failure, never a silent pass.
**Acceptance Criteria**:
- `validateRoute` rejects every malformed-response fixture in the test suite (empty body, wrong denom,
  wrong chain id, zero amount_out, missing txs_required) and accepts only the shape confirmed live this
  session.
- No tx-signing code path is reachable unless `validateRoute` returned true for the specific route object
  in hand (not a cached/prior route).
- A test asserts the mocked `SkipApiClient.getRoute()` call's `amount_in` argument is bit-identical to
  `capUsd(usdEquivalentOf(need, aktUsdPrice))` for the fixture's `need`/`aktUsdPrice`, and never equal to
  the raw uncapped USD-equivalent when the two differ (PROP-019).

### REQ-003: Source-funding precondition (fail closed — the live current blocker)
**EARS**: BEFORE any transaction is signed THE SYSTEM SHALL verify the Base-chain USDC balance of the
configured source wallet is `>= amountInRequiredByRoute` AND the Base-chain native-gas balance is
`>= minGasWei` for leg 1, and SHALL fail closed with an explicit "insufficient funded source" error WHEN
either check fails — THE SYSTEM SHALL NOT infer, borrow from, or auto-bridge from any other chain/wallet
(e.g. Franklin's Solana USDC) as an implicit fallback.
**Edge Cases**:
- Base USDC balance is 0 (the current real-world state, confirmed this session): fail closed, exit
  non-zero, log the specific shortfall (`have X, need Y`).
- Base USDC balance is nonzero but below `amountInRequiredByRoute`: fail closed with the exact deficit.
- Base USDC is sufficient but native ETH/gas for the Base-side approve+swap tx is insufficient: fail
  closed (a partially-fundable swap that dies mid-signature is worse than not starting).
- Source wallet address/key is misconfigured (points at the wrong instance's wallet): this is an
  identity-safety failure, not a funding failure — REQ-009 governs; REQ-003's balance check still applies
  on top of whatever wallet is configured.
**Acceptance Criteria**:
- `checkSourceFunded` returns `false` for every fixture where `baseUsdcBalance < neededUsd` or
  `baseGasBalance < minGasWei`, and the swap driver never proceeds past this check when it returns
  `false` (asserted via mock-transport call-count of zero for the sign/broadcast functions).
- The current real balances (Base USDC ≈ 0, Base gas ≈ 0) MUST be one of the fixtures exercised in
  Phase 2a tests, asserting the command fails closed exactly as it would today in production.

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
  acceptable slippage tolerance is an explicit, tested constant.
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
parameter (REQ-002) and the amount actually signed and broadcast by `BaseSigner.signAndBroadcast()` using
`capUsd(usdEquivalentOf(need, aktUsdPrice))` (REQ-011) as the sole source of the swap amount — no other
code path, value, re-query, or re-computation SHALL determine `amountIn` for the Skip request or for
signing. A swap SHALL NEVER be signed for an amount that was recomputed independently of the exact capped
value already used for the Skip request.
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
  `capUsd(...)` value already used for the Skip request: THE SYSTEM SHALL NOT permit this — this is
  precisely the class of defect the driver-level choke-point test (PROP-019) exists to catch; `capUsd()`
  passing its own isolated unit test is explicitly NOT sufficient evidence that this requirement holds.
**Acceptance Criteria**:
- `capUsd(x)` returns `Math.min(x, SWAP_MAX_USD)` for all `x`, verified by property test across a wide
  range of `x` including adversarial values (`Infinity`, negative, `NaN` → treated as 0/fail-closed, not
  as "unbounded").
- A test asserts `capUsd` output is bit-for-bit identical whether or not `process.env.SWAP_MAX_USD`,
  `process.env.SOL_TRADE_MAX_SPEND`-style vars, or any genome-provided override value is set.
- PROP-019: for any `need` whose USD-equivalent exceeds `SWAP_MAX_USD`, the mocked
  `SkipApiClient.getRoute()` call's `amount_in` argument AND the mocked `BaseSigner.signAndBroadcast()`
  call's transaction-amount argument are BOTH `<= SWAP_MAX_USD`-equivalent, asserted by inspecting the
  spy's actual call arguments — never by inspecting `capUsd()`'s return value in isolation.

### REQ-007: Final on-chain settlement verification before declaring success
**EARS**: AFTER the last route leg is confirmed THE SYSTEM SHALL re-query
`akash query bank balances akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523` (or equivalent REST query) and
SHALL only report success WHEN the observed `uakt` balance increased by an amount consistent with the
route's quoted `amount_out` (within slippage tolerance); THE SYSTEM SHALL NOT declare success merely
because all leg transactions returned a zero exit code.
**Edge Cases**:
- All legs report "confirmed" per their own chain's tx status, but the final Akash balance query shows
  no increase (funds stuck somewhere in the IBC path, or landed in a different denom): fail closed,
  report "legs confirmed but AKT not observed at destination" distinctly from a leg-level failure.
- Balance query itself times out/errors after legs are done: fail closed with a distinct "cannot verify
  final settlement" status (not silently reported as success).
**Acceptance Criteria**:
- The success path is unreachable in tests unless the mocked final-balance query shows the expected
  delta; a mock returning an unchanged balance after all legs "succeed" results in non-zero exit.

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
never `need` itself — as the sole amount input to REQ-002's Skip route request and to REQ-006's signing
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

## Edge Case Catalog (cross-cutting, applies across REQ-002 through REQ-011)

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
| Cap exceeded by computed need (REQ-002, REQ-006, REQ-011) | Skip request `amount_in` and the signed tx amount are both the identical `capUsd(usdEquivalentOf(need, aktUsdPrice))` value — never independently recomputed (single choke point, PROP-019) |
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
