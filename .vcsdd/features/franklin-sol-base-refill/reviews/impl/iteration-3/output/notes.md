# Adversary notes -- franklin-sol-base-refill `--gas-eth` mode, impl review iteration 1 (feature iteration 3)

Fresh-context review, zero Builder history. Files read directly from
`/Users/operator/anicca/.worktrees/gas-refill` at HEAD `e98f83ad`. No Bash tool available to this
role; the 167/167 funding-suite pass count is taken as given per task instructions (thinker
independently ran it) -- every finding below comes from static code/spec/test cross-referencing.

## Scope actually reviewed
- `.vcsdd/features/franklin-sol-base-refill/specs/behavioral-spec.md` -- full read, both REQ-001..007
  (unchanged, for context) and the new REQ-GAS-001..005 section plus its own Changelog entry.
- `.vcsdd/features/franklin-sol-base-refill/specs/verification-architecture.md` -- full read,
  PROP-018..024 (new) plus the Reused-Not-Re-Verified section (confirms lib/erc20.py's
  pre-existing functions carry a prior PASS money-safety verdict and were NOT touched by this
  addition).
- `.vcsdd/features/franklin-sol-base-refill/state.json` -- full read, all phaseHistory entries,
  including the gas-eth-1 entry's own self-assessment ("NOT yet been through its own fresh-context
  adversary review pass; not merged, not run --live").
- `skills/earn/funding/franklin_sol_base_refill.py` -- full read, all 1006 lines, both `run_refill`
  (unchanged per Changelog claim, spot-checked for drift -- none found) and the new `run_gas_refill`
  traced line-by-line against every REQ-GAS-001..005 clause.
- `skills/earn/funding/lib/refill_plan.py` -- full read, all 310 lines, including the new
  `is_valid_evm_address`/`evaluate_native_delivery`/`GAS_*` constants, manually hand-traced against
  their own docstrings and the spec's EARS text.
- `skills/earn/funding/lib/erc20.py` -- full read; confirmed `eth_get_balance` (new) structurally
  mirrors `erc20_balance_units`'s already-reviewed contract (raises on failure, same header, same
  hex-to-int parse); `ERC20_TRANSFER_TOPIC0`/`parse_erc20_transfer_amount` re-confirmed unchanged
  (not in scope for this pass, gas mode never calls them -- native transfers have no Transfer log).
- `skills/earn/funding/tests/test_franklin_gas_eth_refill.py` -- full read, all 24 tests, each one
  individually checked against which REQ-GAS clause/edge-case it claims to cover.
- `skills/earn/funding/tests/test_refill_plan.py` -- full read; the 24 gas-related tests (lines
  300-477) individually checked the same way.
- `skills/earn/funding/tests/test_erc20.py` -- read to confirm `eth_get_balance` has no dedicated
  unit test (consistent with the existing, already-accepted convention that raw-RPC I/O wrappers
  are exercised only via the orchestration-test fake-deps boundary, not in isolation).

## Verdict: FAIL (all 5 dimensions FAIL)

### What is genuinely solid (re-confirmed directly, not assumed)
- **Caps-before-signing ordering**: traced `run_gas_refill`'s full control flow end-to-end --
  `select_refill_amount` (REQ-GAS-003 amount/reserve cap) and `evaluate_relay_fee` (REQ-GAS-003 fee
  cap, gas-mode literal `GAS_MAX_FEE_PCT=12.0` explicitly passed, never defaulted) are both
  evaluated and must pass before `build_sign_submit` is ever reached. No code path skips this.
- **Independent single-in-flight lock**: `GAS_STEP` ("franklin_gas_eth_refill") is a distinct
  literal from `STEP` ("franklin_sol_base_refill"); `has_unresolved_pending` is called with the
  correct step in each mode; two dedicated tests (`test_gas_unresolved_pending_blocks_new_live_run`,
  `test_gas_unresolved_usdc_mode_pending_does_not_block_gas_run`) prove cross-step independence in
  both directions.
- **Secret safety**: both of `run_gas_refill`'s raw-secret decode sites (`derive_pubkey`,
  `build_sign_submit`) route through the SAME `sanitized_secret_error` helper `run_refill` already
  uses -- no new raw `str(exc)` interpolation reintroduced. Confirmed against two genuine
  failing-path-injection tests that assert a fake secret's absence from all output.
- **Wei/decimals**: no unit confusion found. The source leg (Solana USDC, 6 decimals) uses
  `amount * 1e6` exactly like the USDC mode; the destination leg (native ETH, 18 decimals) is
  handled entirely in raw wei ints end-to-end (`_extract_quote_raw_units` -> `expected_wei` ->
  `eth_get_balance` -> `evaluate_native_delivery`) with no `*1e18`/`/1e18` scaling anywhere --
  correct, since relay.link's own `amount` field is already the raw base-unit string.
- **Test count**: independently grep-counted `^def test_` across both new/extended test files --
  24 + 24 = 48, exactly matching the task's claimed figure.
- **Relay currency-id citation**: the `0x0000...0000` native-currency sentinel is correctly cited
  against relay.link's own documented `/quote` and `/quote/v2` example (both endpoints checked per
  the spec's Changelog), and is genuinely distinct from the unrelated "Gas Top-Up" feature the spec
  explicitly rules out using.

### What is not (new findings, this iteration)
- **FIND-001** (spec_fidelity + verification_readiness, CRITICAL): gas-ETH mode depends on a field
  (`details.currencyOut.amount`, raw wei) never checked against a real live relay.link response for
  the actual USDC(Solana)->native-ETH(Base) pair -- only against relay's own static docs example
  for a different pair (ETH<->ETH). This is the identical class of gap iteration-1's FIND-005
  identified and escalated into a MUST spec gate for the USDC mode's `amountUsd` fields; that gate
  was never replicated for REQ-GAS-004. This is the primary reason this review recommends NO-GO on
  a real `--live` invocation until a real non-signing dry-run's raw response is captured as
  evidence.
- **FIND-002** (edge_case_coverage + implementation_correctness, HIGH): `evaluate_native_delivery`
  silently disables its own 85%-floor check whenever `expected_wei <= 0`, verifying ANY positive
  balance delta as "delivered" in that degenerate case -- reachable because `expected_wei` and
  `out_usd` are extracted from two independent relay-response fields with no cross-check, unlike
  the USDC mode where the same value gates both the fee check and the delivery floor (so a
  zero/negative value is already caught upstream there, but not here). Untested (all 10
  `evaluate_native_delivery` test cases use strictly-positive `expected_wei`).
- **FIND-003** (implementation_correctness, MEDIUM): `is_valid_evm_address` validates a
  `.strip()`-ped local copy of its argument but every downstream use (relay quote payload,
  `build_sign_submit`, every ledger row) uses the original, unstripped string -- a validate-vs-use
  mismatch that would let a whitespace-padded address pass validation and be used verbatim.
- **FIND-004** (structural_integrity, MEDIUM): the builder's own flagged 1006-line file size has a
  concrete, traceable cost -- a fail-closed ledger-append helper now exists in two independently
  maintained copies (`run_refill`'s inline closure, `_safe_append_ledger_factory` for
  `run_gas_refill`) rather than one shared implementation, a drift risk for money-safety-critical
  logic.
- **FIND-005** (spec_fidelity, LOW): `is_valid_evm_address` is syntactic-only (no EIP-55 checksum),
  which is acceptable per this task's own "operator-supplied is fine IF validated+logged" framing
  (it is both), but the spec does not explicitly acknowledge this as an accepted residual for a
  fully unbound, no-allowlist real-money destination.

## Go/no-go for the requested `--live` $3 gas top-up
**NO-GO** until FIND-001 is closed (a real, non-signing `--gas-eth` invocation's relay.link response
is captured and inspected, confirming `expected_wei` actually resolves for this exact pair) and
FIND-002 is fixed (the delivery-floor bypass is in the exact function this money move's independent
on-chain proof depends on). FIND-003 is a trivial, low-probability fix that should also land before
`--live` given the small remaining cost of doing so, but is not itself a hard blocker to the
recommended remediation sequence. FIND-004/FIND-005 are non-blocking for a `--live` decision.
