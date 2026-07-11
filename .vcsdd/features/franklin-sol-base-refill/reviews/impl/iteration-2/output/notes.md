# Adversary notes -- franklin-sol-base-refill impl review, iteration 2

Fresh-context review. No builder history consulted, no prior conversation with the Builder.
Files read directly from `/Users/anicca/anicca/.worktrees/sol-base-refill` at the stated HEAD
`92c41548`. No Bash tool available to this role; the 115/115 funding-suite pass count is taken
as given (thinker-executed), per task instructions -- this review's findings are all from static
code/spec/test cross-referencing, not from re-running the suite myself.

## Scope actually reviewed
- `.vcsdd/features/franklin-sol-base-refill/specs/behavioral-spec.md` (REQ-001..007, full read,
  including the Changelog documenting the iteration-1 FIND-001..007 fixes)
- `.vcsdd/features/franklin-sol-base-refill/specs/verification-architecture.md` (PROP-001..017,
  full read)
- `.vcsdd/features/franklin-sol-base-refill/reviews/impl/iteration-1/output/verdict.json` +
  all 7 `findings/FIND-00N.json` + `notes.md` (full read, every finding's exact text and cited
  evidence read before touching any code)
- `skills/earn/funding/lib/refill_plan.py` (pure core, full read)
- `skills/earn/funding/franklin_sol_base_refill.py` (effectful shell, full read, all 546 lines)
- `skills/earn/funding/lib/relay_swap.py` (new, full read) diffed BY HAND against
  `skills/earn/sol-to-usdc.py` (the cited precedent, full read) line-by-line for adaptation
  errors in instruction-building, ALT parsing, blockhash/sign/submit
- `skills/earn/funding/lib/erc20.py` (full read) -- manually verified `ERC20_TRANSFER_TOPIC0`
  against the known keccak256("Transfer(address,address,uint256)") value, and traced
  `parse_erc20_transfer_amount`'s topic/address/data parsing against standard ERC-20 log
  encoding by hand
- `skills/earn/funding/lib/identity.py`, `lib/ledger.py`, `lib/kill_switch.py` (full read)
- `skills/earn/funding/send_to_franklin.py` (partial, the identity-check block) and `run.py`
  (full read) -- to independently confirm REQ-007's no-cron-wiring claim and to trace whether
  `verify_solana_secret_file`'s secret-safety gap (see FIND-002 below) is actually reachable
- `skills/earn/funding/tests/{test_refill_plan.py,test_franklin_sol_base_refill.py,test_erc20.py,
  test_identity.py}` (full read; every FIND-001..007-labeled test in
  `test_franklin_sol_base_refill.py` individually inspected to confirm it genuinely injects
  through the FAILING path rather than asserting a tautology)
- Grep (this role has Grep/Read, unlike iteration-1's adversary which had neither): confirmed
  independently, with my own tool calls (not just trusting `evidence/red-green.txt`), that
  `franklin_sol_base_refill` is referenced nowhere under `~/.openclaw/cron/` and nowhere in this
  worktree outside this feature's own files -- REQ-007's no-cron-wiring claim holds on my own
  verification, not just the builder's self-reported grep.

## Verdict: FAIL (all 5 dimensions FAIL)

### What iteration-1's 7 findings actually look like at HEAD (traced individually, not assumed)
- **FIND-001 (fabricated fee-cap fallback): genuinely fixed.** `_extract_quote_usd`
  (franklin_sol_base_refill.py:138-157) returns `None` on any missing/null/wrong-type
  `amountUsd`, with no `or amount`/`or 0` fallback anywhere in the new code; `evaluate_relay_fee`
  fails closed on `None`. Four dedicated tests (missing-key, null, wrong-type, plus the exact
  FIND-001 regression asserting `plan.get('in_usd') is None`) all genuinely exercise this.
- **FIND-002 (citizens.json crash): genuinely fixed.** try/except now wraps `read_citizens()`,
  fails closed via `fail()`. Two dedicated tests (FileNotFoundError, JSONDecodeError) confirm.
- **FIND-003 (secret-safe error handling): genuinely fixed AT THE TWO SITES IT NAMED**
  (`derive_pubkey`, `build_sign_submit` in `franklin_sol_base_refill.py`), verified via
  dedicated tests that inject a fake secret through a raising fake dep and assert its absence
  from every ledger row and the result JSON -- these are real failing-path injections. HOWEVER
  a module-wide grep for `str(exc)`/f-string exception interpolation (explicitly requested by
  this review's task) surfaced a THIRD site touching the identical decode call
  (`lib/identity.py:verify_solana_secret_file`, used by `bridge.py`/`send_to_franklin.py`, both
  appending to the SAME ledger file) that was never brought under the same protection. New
  **FIND-002** (this iteration) files this.
- **FIND-004 (coarse balance-delta verification): genuinely fixed**, and this is the strongest
  piece of new work in this iteration. The tx-specific Transfer-log parsing
  (`lib/erc20.py:parse_erc20_transfer_amount`) is correctly implemented against real ERC-20 log
  encoding (topic0/topic2/data all verified by hand), the orchestration wires it as the sole
  gate for "sent" (fill_tx_hash + receipt status 0x1 + matching Transfer log + >=85% delivered),
  and the balance delta is genuinely demoted to a non-gating sanity flag recorded only for
  audit -- confirmed via a dedicated test asserting a flat/zero delta does NOT flip a
  tx-verified fill to failed, and separately that an unrelated-inflow-only scenario (delta ok,
  no matching Transfer log) does NOT get marked verified.
- **FIND-005 (unverified field-shape assumption): code-level mitigation only, NOT resolved.**
  The fix makes the wrong assumption fail SAFE, but the assumption itself -- that a real
  relay.link `/quote` response for USDC-SPL(Solana)->USDC(Base) actually contains
  `currencyIn.amountUsd`/`currencyOut.amountUsd` as numeric-parseable strings -- has still never
  been checked against production data. The spec's own MUST acceptance criterion (attach a real
  dry-run response as evidence in `.vcsdd`) is unmet: no such file exists. New **FIND-001** (this
  iteration) files this as the primary blocking finding, since this is the exact assumption the
  paramount 8% fee cap depends on.
- **FIND-006 (uncaught crashes in production wiring): mostly fixed, one gap remains.**
  `relay_quote`/`read_solana_balance_usd` are now wrapped as the finding required. But
  `deps['append_ledger']` -- called from the shared `fail()` helper on EVERY refusal path, plus
  five more sites -- and `deps['is_killed']()` remain unwrapped. New **FIND-003** (this
  iteration) files this; severity is medium because `append_ledger`'s underlying `open(path,
  'a')`/`os.makedirs` can plausibly raise (disk-full/permissions), unlike `is_killed`'s
  `os.path.exists` which essentially never does.
- **FIND-007 (copy-pasted tx code): genuinely fixed.** `lib/relay_swap.py` is a real extraction,
  hand-diffed against `sol-to-usdc.py` line-by-line with no adaptation errors found (instruction
  building, ALT byte-layout parsing, blockhash fetch, `MessageV0.try_compile`, `sendTransaction`
  call are all faithfully preserved; only the origin currency and the secret-decode call differ,
  both intentionally).

### New findings this iteration (not present in iteration-1's 7)
- **FIND-001** (spec_fidelity, high): REQ-004's own MUST evidence-gate for the live relay.link
  quote-shape verification is unmet -- no evidence artifact exists in `.vcsdd`, and the gate is
  unenforced by code.
- **FIND-002** (verification_readiness, high): the secret-sanitization fix is not module-wide;
  `lib/identity.py:verify_solana_secret_file` (reached via `bridge.py`/`send_to_franklin.py`,
  both sharing this feature's exact ledger file) still risks the identical secret-in-ledger leak
  iteration-1's FIND-003 flagged as unresolved, just via a different call path.
- **FIND-003** (implementation_correctness, medium): `append_ledger`/`is_killed` calls in
  `run_refill()` remain unwrapped, unlike every other effectful call FIND-006 fixed.
- **FIND-004** (edge_case_coverage, low): a non-dict truthy `quote` return value crashes
  uncaught at `.get('details')`, one line above where the equivalent guard already exists one
  level down.
- **FIND-005** (structural_integrity, low): `secret_b58` parameter naming in `relay_swap.py`
  now contradicts the dual-decode fix's own rationale.
- **FIND-006** (structural_integrity, low): `state.json` was never advanced past phase `2c`
  despite a completed impl-review-and-fix cycle already being documented in the spec's own
  Changelog.

## What I did NOT find blocking (re-confirmed, not just carried over from iteration-1)
- The amount-cap/reserve math (`select_refill_amount`) is still correctly implemented and
  boundary-tested (>=6 cases as REQ-003 requires) -- re-verified directly against
  `lib/refill_plan.py:36-73` and `tests/test_refill_plan.py:24-97`.
- `assert_own_citizen_row` still correctly refuses on zero-match and multi-match, never
  picks-first -- re-verified directly.
- `has_unresolved_pending` is still correctly order-independent -- re-verified directly.
- The pending-row-before-poll ordering (Finding-A pattern) is still correctly applied, with a
  call-order-spy test (`test_pending_row_written_before_poll_relay_status_call_order`).
- REQ-007's dry-run-default / `--dry-run`-wins-over-`--live` / no-cron-wiring claims all
  re-verified directly against the code AND my own independent Grep of both this worktree and
  `~/.openclaw/cron/` (not just trusting the builder's self-reported grep in `red-green.txt`).
- CAPS ordering: re-traced the full `run_refill()` control flow end-to-end -- no path exists
  where `--live` reaches `build_sign_submit` without both `select_refill_amount` and
  `evaluate_relay_fee` having been evaluated and allowed first.
- `USDC_SOLANA_MINT` (`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`) and `USDC_BASE`
  (`0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`) are both correct, real, canonical mainnet
  contract/mint addresses for native USDC on Solana and Base respectively (verified against
  training-data knowledge of these well-known addresses).
- `ERC20_TRANSFER_TOPIC0` is the correct keccak256 hash of
  `Transfer(address,address,uint256)` (verified by hand-counting the 64 hex characters against
  the well-known constant).

## Process note (not a code finding)
Every `Write` in this session triggered a `PostToolUse` hook message: "fablize gate observed a
tool failure. Do not report completion until it is fixed, isolated as a known baseline, or
explicitly documented." Each `Write` tool call itself returned "File created successfully"
with no error, and this message repeated identically after every single write regardless of
content -- isolating it as a generic/spurious hook artifact unrelated to this review's actual
file writes, and documenting it here per that hook's own instruction, since this adversary role
has no Bash access to investigate the hook's source further.
