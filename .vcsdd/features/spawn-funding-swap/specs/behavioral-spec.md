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
- `capUsd(requestedUsd)` — hard-clamp of the USD amount to spend to `min(requestedUsd, SWAP_MAX_USD)`
  where `SWAP_MAX_USD` is a literal constant in the pure module, never read from `process.env` or any
  genome/config file (REQ-006).
- `validateRoute(routeResponse)` — pure predicate over the parsed Skip API response: rejects if
  `dest_asset_denom !== 'uakt'`, `dest_asset_chain_id !== 'akashnet-2'`, `amount_out` missing/zero/NaN,
  or `txs_required` missing (REQ-002).
- `planNextLeg(routeResponse, submittedTxLedger)` — pure state machine: given the ordered list of legs
  from the route and a ledger of which leg-indices already have a confirmed tx id, returns the next leg
  to submit, or `DONE`, or `ALREADY_COMPLETE` (REQ-004, REQ-005 idempotency/resumability core).
- `checkSourceFunded(baseUsdcBalance, baseGasBalance, neededUsd, minGasWei)` — pure precondition check
  (REQ-003).

**Effectful shell** (I/O, must be mocked/injected in tests, never exercised for real in Phase 2a/2b tests):
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
  regardless of the computed shortfall, env vars, CLI flags, or any config file.
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

### REQ-002: Skip API route acquisition, fail-closed on no route
**EARS**: WHEN `need > 0` THE SYSTEM SHALL request a route from the Skip API with
`source_asset_chain_id=8453`, `source_asset_denom=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`,
`dest_asset_chain_id=akashnet-2`, `dest_asset_denom=uakt`, and SHALL validate the response satisfies
`validateRoute` before proceeding, and SHALL fail closed (non-zero exit, no tx submitted) WHEN no valid
route is returned.
**Edge Cases**:
- Skip API returns HTTP error or malformed JSON: fail closed.
- Skip API returns a route with `dest_asset_denom !== 'uakt'` or wrong `dest_asset_chain_id`: fail
  closed (defends against a Skip API bug or an intermediary hop swap-out to the wrong asset).
- Skip API returns `amount_out` far below a sane minimum (e.g. 0, negative, or NaN after parse): fail
  closed.
- Route requires more legs/chains than the system can execute (unsupported `txs_required` shape): fail
  closed rather than attempting a partial/unknown execution path.
**Acceptance Criteria**:
- `validateRoute` rejects every malformed-response fixture in the test suite (empty body, wrong denom,
  wrong chain id, zero amount_out, missing txs_required) and accepts only the shape confirmed live this
  session.
- No tx-signing code path is reachable unless `validateRoute` returned true for the specific route object
  in hand (not a cached/prior route).

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
**EARS**: WHEN the command is invoked and a prior run's ledger file for this route exists with one or
more legs already `confirmed`, THE SYSTEM SHALL resume from the first unconfirmed leg and SHALL NOT
re-submit any leg already recorded `confirmed`, regardless of how many times the command is re-invoked.
**Edge Cases**:
- Process crashes immediately after broadcasting Leg 1 but before writing `confirmed` to the ledger: on
  the next run, the system MUST query the chain for the actual tx status by the previously-recorded
  (pre-confirmation) tx hash/nonce BEFORE deciding to resubmit — it MUST NOT resubmit blindly on the
  assumption the crash means "nothing happened" (this is the classic double-spend hazard).
- Ledger file is corrupted/unparseable: fail closed (do not treat "unreadable" as "empty/start fresh",
  since that risks re-submitting an already-confirmed leg) — surface a loud error for operator
  intervention.
- Two invocations run concurrently (cron overlap): a file lock or equivalent MUST prevent both from
  submitting the same leg; the second invocation MUST fail closed / no-op rather than race.
**Acceptance Criteria**:
- Property test: for any sequence of (crash-before-write, crash-after-write, normal-completion) injected
  at each leg boundary, replaying the command to completion never results in more than one
  `confirmed` broadcast call per leg index (fast-check property, REQ-005 is Tier 2, money-safety
  critical).
- A concurrent-invocation simulation (two drivers sharing one ledger file/lock) results in exactly one
  successful submission per leg across both invocations.

### REQ-006: Hard money-safety spend cap (never overridable)
**EARS**: THE SYSTEM SHALL NOT initiate a swap whose source-asset USD value exceeds a fixed constant
`SWAP_MAX_USD` defined as a literal in the pure cap-enforcement module, and THE SYSTEM SHALL apply this
cap unconditionally AFTER any shortfall/need computation, ignoring `process.env`, CLI flags, genome
output, or any config file value that would raise it (mirrors `sol-trade`'s
`lib/resolve-max-spend.sh` single-choke-point hard-override pattern — a script that prints a literal
value and explicitly ignores `SOL_TRADE_MAX_SPEND` and every other env var).
**Edge Cases**:
- Computed `need` (in USD-equivalent) exceeds `SWAP_MAX_USD`: the system swaps at most `SWAP_MAX_USD`
  worth and MUST clearly report that the swap was capped and the treasury may remain below threshold
  (never silently "top up as much as needed").
- An attacker-controlled or buggy env var / genome value attempts to set a higher cap: MUST have zero
  effect on the actual enforced value (asserted by a test that sets a hostile env var and confirms the
  enforced cap is unchanged).
- `SWAP_MAX_USD` itself is defined once, in one file, with no second definition anywhere else in the
  codebase that could drift out of sync.
**Acceptance Criteria**:
- `capUsd(x)` returns `Math.min(x, SWAP_MAX_USD)` for all `x`, verified by property test across a wide
  range of `x` including adversarial values (`Infinity`, negative, `NaN` → treated as 0/fail-closed, not
  as "unbounded").
- A test asserts `capUsd` output is bit-for-bit identical whether or not `process.env.SWAP_MAX_USD`,
  `process.env.SOL_TRADE_MAX_SPEND`-style vars, or any genome-provided override value is set.

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

## Edge Case Catalog (cross-cutting, applies across REQ-002 through REQ-007)

| Edge case | Required behavior |
|---|---|
| No route found (REQ-002) | Fail closed, exit non-zero, no tx |
| Insufficient source funds/gas (REQ-003) | Fail closed, exit non-zero, no tx, explicit deficit reported |
| Partial fill / slippage beyond tolerance (REQ-004) | Fail closed, ledger reflects true on-chain state |
| Relay timeout mid-route (REQ-004, REQ-005) | Ledger marks leg `pending`, not `failed`/`done`; resumable |
| Gas shortfall on any intermediate chain (REQ-004) | Fail closed at that leg; prior confirmed legs stay recorded |
| Crash before ledger write (REQ-005) | Next run queries chain state before resubmitting, never blind-resubmits |
| Concurrent invocation (REQ-005) | Lock/guard prevents double-submit; loser fails closed / no-ops |
| Cap exceeded by computed need (REQ-006) | Swap capped at `SWAP_MAX_USD`, reported as partial/under-target |
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
