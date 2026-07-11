# Adversary notes -- franklin-sol-base-refill `--gas-eth` mode, final money-gate re-review
# (feature iteration-4, gas-eth mode's own impl-review iteration-2)

Fresh-context review, zero Builder history, no manifest present at
`reviews/impl/iteration-4/input/` (this scope was driven directly by the launching agent's task
description, which itself cites the exact worktree/commit/history to review -- cross-checked
directly against the actual files, not taken on faith). No Bash tool available to this role; the
177/177 funding-suite pass count and the live-relay dry-run's existence are taken as given per
task instructions (thinker independently ran both). Every finding below comes from static
code/spec/test/evidence cross-referencing performed directly in this session.

## Scope actually reviewed
- `skills/earn/funding/franklin_sol_base_refill.py` -- full read, all 1012 lines. `run_refill`
  spot-checked for drift (none beyond the intentional `_safe_append_ledger_factory` dedup).
  `run_gas_refill` re-traced line-by-line against each of iteration-3's FIND-001..005.
- `skills/earn/funding/lib/refill_plan.py` -- full read, all 334 lines. `is_valid_evm_address`
  and `evaluate_native_delivery` hand-traced against their own updated docstrings and the FIND-002/
  FIND-003/FIND-005 fix claims.
- `skills/earn/funding/lib/erc20.py` -- full read; `eth_get_balance` unchanged since iteration-3.
- `skills/earn/funding/tests/test_franklin_gas_eth_refill.py` -- full read, all tests, with
  particular attention to the new FIND-001/002/003 regression tests (lines 245-378, 384-423).
- `skills/earn/funding/tests/test_refill_plan.py` -- full read, gas-eth section (lines 300-521),
  particular attention to the new zero/negative-`expected_wei` tests (lines 486-511) and the
  whitespace/case normalization tests (lines 383-421).
- `specs/behavioral-spec.md` -- full read, REQ-GAS-001..005 + both Changelog entries.
- `specs/verification-architecture.md` -- full read, PROP-018..025 + both Changelog entries.
- `state.json` -- full read, all phaseHistory entries including the gas-eth-2 entry's own
  self-assessment.
- `evidence/live-dryrun-gas-eth-2026-07-11.md` -- full read, cross-checked byte-for-byte against
  what the CURRENT code (post-FIND-003-fix) would actually print for the identical command.
- `reviews/impl/iteration-3/output/verdict.json` + `findings/FIND-001..005.json` + `notes.md` --
  full read, every prior finding independently re-verified against the current code state (not
  assumed fixed just because the spec Changelog claims it).

## What is genuinely solid (re-confirmed directly, not assumed)

- **FIND-002 (critical, iteration-3) -- fully fixed.** `evaluate_native_delivery` now has an
  explicit `if expected_wei <= 0: return NativeDeliveryDecision(False, ...)` BEFORE
  `min_required` is ever computed (`lib/refill_plan.py:304-311`) -- traced the full function body,
  no path bypasses this. `run_gas_refill` ALSO has its own pre-sign guard
  (`franklin_sol_base_refill.py:760-766`) placed before `build_sign_submit` is ever reached --
  genuine defense-in-depth, not reliance on the pure function alone. Both `==0` and `<0` cases are
  covered by dedicated tests at both the pure-function level
  (`test_evaluate_native_delivery_zero_expected_wei_refused`,
  `test_evaluate_native_delivery_negative_expected_wei_refused`,
  `test_evaluate_native_delivery_zero_expected_wei_refused_even_with_large_delta`) and the
  orchestration level (`test_gas_quote_currency_out_amount_wei_zero_refuses_before_signing`).
- **FIND-001 (critical, iteration-3, field-shape half) -- fixed.** `_extract_quote_raw_units`
  fails closed on missing/null/non-numeric `amount` with direct test coverage for all three shapes
  (`test_gas_quote_missing_currency_out_amount_wei_refuses_before_signing`,
  `test_gas_quote_currency_out_amount_wei_null_refuses_before_signing`,
  `test_gas_quote_currency_out_amount_wei_non_numeric_refuses_before_signing`).
- **FIND-003 (medium, iteration-3) -- fully fixed in the current code.** `is_valid_evm_address`
  now returns the normalized address; `run_gas_refill` rebinds `recipient` to that value ONCE
  (line 619) and every downstream use (relay payload line 673, plan line 730, every ledger row's
  `to_addr` at lines 748/806/857/875/891) reads that same reassigned variable. Grepped every
  occurrence of `recipient` in `run_gas_refill`'s body by hand -- no stray reference to the
  original, pre-validation parameter remains.
- **FIND-004 (medium, iteration-3) -- fixed.** `_safe_append_ledger_factory` is now the one and
  only fail-closed ledger-append implementation, used by both `run_refill` and `run_gas_refill`.
- **FIND-005 (low, iteration-3) -- fixed.** The no-EIP-55-checksum residual is now explicitly
  documented as an accepted design decision in both `is_valid_evm_address`'s docstring and the
  spec.
- **USDC-mode non-regression**: the only change touching already-reviewed `run_refill` code is the
  `_safe_append_ledger_factory` extraction -- behavior-preserving (same try/except body, same
  stderr message shape, same `sys.exit(1)`), confirmed by direct read; the caps/fee literals
  (`PER_INVOCATION_USD_CAP`, `RESERVE_USD`, `MAX_FEE_PCT`) are untouched.
- **Full money-safety trace for the requested $3 live move**: kill-switch -> recipient validation
  (BEFORE any network call) -> identity resolve -> pubkey derive -> single in-flight guard
  (GAS_STEP, independent of USDC-mode STEP) -> live balance read -> `select_refill_amount` (GAS
  reserve/cap) -> relay quote -> non-Mapping/empty-details guards -> `evaluate_relay_fee` (GAS_MAX_
  FEE_PCT=12%) -> expected_wei None/<=0 pre-sign refusal -> native balance read (before) ->
  **signing happens here, and only here, after every above gate has passed** -> pending row
  written before poll -> poll relay status -> native balance read (after) ->
  `evaluate_native_delivery` (85% floor, fails closed on non-positive expected_wei) -> sent/failed
  row. No path reaches `build_sign_submit` without every cap/validation gate having already passed.
  Secret-safety: both raw-secret decode sites route through `sanitized_secret_error`, confirmed
  absent from output via genuine fake-secret-injection tests.

## What is not (this review's own finding)

- **FIND-001 (this iteration, critical, verification_readiness)**: the evidence attached to close
  REQ-GAS-004's MUST live-evidence gate does not reflect the CURRENT code's behavior. The evidence
  file's printed `plan.recipient_base` is mixed-case, byte-identical to the raw `--recipient`
  argument in its own command line -- but the current code (post FIND-003 fix) unconditionally
  lower-cases `recipient` before it is ever used in the plan OR the relay request payload. This is
  not an inference: `build_refill_plan`'s `recipient_base=recipient` argument (line 730) reads a
  local variable that was reassigned to `is_valid_evm_address`'s normalized return value at line
  619, with no code path back to the original candidate. The only consistent explanation is the
  evidence was captured against an earlier, since-superseded version of the code in this same
  development pass and never re-run after the normalization fix landed. The field-shape claim the
  evidence DOES support (`details.currencyOut.amount` present/parseable for this exact currency
  pair) remains genuinely true and useful; what is NOT verified is that relay.link's live endpoint
  accepts/handles the exact, now-fully-lowercased recipient string the current code will actually
  submit at `--live` time. Practical risk assessed as LOW (EVM address casing is essentially
  universally treated case-insensitively by API/RPC layers; EIP-55 checksums are a client-display
  convention, not typically enforced server-side) but not empirically confirmed for this pair/mode.
  Given this is the literal final gate before a real, irreversible on-chain money move and the
  remediation is a zero-cost, zero-risk, non-signing 30-second re-run, this review does not accept
  "low risk" as a substitute for "verified" on this specific gate.

## Go/no-go for the requested `--live` $3 gas top-up

**NO-GO** until this review's FIND-001 is closed: re-run the exact same non-signing
`--gas-eth --recipient 0x1F5b17f41524B02a4ee4d99D4158c86C942e43f3 --dry-run` command against the
CURRENT commit (6fe4908e), confirm the printed `plan.recipient_base` is lowercased (proving the
normalized-recipient code path actually ran) and that relay.link's live `/quote` still returns a
valid `details.currencyOut.amount` for that exact request, and attach that fresh output as
evidence (overwriting or supplementing the existing evidence file). Every other money-safety
invariant (caps, reserve, fee ceiling, single in-flight guard, pre-sign expected_wei refusal,
independent on-chain balance-delta verification before "sent", secret handling) is independently
re-traced and correct in the current code, with genuine (non-tautological) test coverage. This is
the ONLY remaining blocker; it is trivial and low-risk to close.
