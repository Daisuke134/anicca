# Adversary notes -- franklin-sol-base-refill impl review, iteration 1

Fresh-context review. No builder history consulted. Files read directly from
`/Users/anicca/anicca/.worktrees/sol-base-refill` at commit 02089614.

## Scope actually reviewed
- specs/behavioral-spec.md (REQ-001..007), specs/verification-architecture.md (PROP-001..012)
- skills/earn/funding/lib/refill_plan.py (pure core, full read)
- skills/earn/funding/franklin_sol_base_refill.py (effectful shell, full read, all 490 lines)
- skills/earn/funding/lib/{identity,erc20,ledger,solana_rpc,kill_switch}.py (reused-unchanged deps, full read)
- skills/earn/sol-to-usdc.py (the cited "proven" precedent, full read, diffed against the new
  _build_sign_submit_solana_tx by hand)
- skills/earn/funding/tests/{test_refill_plan.py,test_franklin_sol_base_refill.py} (full read, all
  57 new test cases enumerated and cross-checked against the spec's edge-case list)
- grep confirmed: no cron/loop wiring anywhere under the worktree or `~/.openclaw/cron` outside
  this feature's own files (REQ-007 claim holds).

External test evidence (thinker-executed, not re-run by this adversary, no Bash tool available to
this role): 90/90 funding suite pass (33 pre-existing + 57 new), 210/210 runtime/loop suite pass.
Taken as given per task instructions; this review's findings are all from static code/spec
cross-referencing, not from re-running the suite.

## Verdict: FAIL (all 5 dimensions FAIL)

The two critical findings (FIND-001, FIND-002) are both concrete, line-cited orchestration bugs
that defeat an explicitly-named spec edge case for a money-safety-critical requirement (REQ-004's
fee cap, REQ-002's destination-binding fail-closed guarantee) -- not speculative or style
concerns. Both are also confirmed-untested: the orchestration test fixtures never exercise the
"malformed/missing quote field" or "citizens.json unreadable" paths, so the 57/57 green test run
cannot be read as covering these spec-mandated refusal behaviors.

FIND-003/FIND-005 are money-safety-relevant risks this review could not fully resolve without
live network access or running solders locally (no Bash available to this role): whether solders'
base58-decode exception message embeds the raw input, and whether relay.link's real /quote
response for USDC-SPL(Solana)->USDC(Base) actually contains `currencyIn.amountUsd`/
`currencyOut.amountUsd` in the shape assumed. Both are flagged because (a) the codebase's own
docstrings document the exact real-world condition (base64-encoded secret file) that would trigger
the decode-path inconsistency, and (b) the cited "proven" precedent (sol-to-usdc.py) demonstrably
never exercised the specific fields REQ-004 depends on, so "verified live" cannot be claimed to
cover them.

## What I did NOT find blocking
- The pure/effectful split (lib/refill_plan.py vs franklin_sol_base_refill.py) is clean: the pure
  module has zero I/O/network/clock imports, matching the purity-boundary claim.
- Amount cap / reserve math (select_refill_amount) is correctly implemented and thoroughly
  boundary-tested (>=6 cases as REQ-003 requires).
- assert_own_citizen_row correctly refuses on zero-match and multi-match (never picks-first),
  well tested.
- has_unresolved_pending is correctly order-independent and well tested.
- The pending-row-before-poll ordering (Finding-A pattern from the 2026-07-08 money-safety
  review) is correctly applied and has a call-order-spy test.
- REQ-007's dry-run-default / --dry-run-wins-over---live / no-cron-wiring claims all verified
  directly against the code and a repo-wide grep.
- CAPS ordering: traced the full run_refill() control flow end-to-end -- there is no path where
  --live reaches build_sign_submit without both select_refill_amount and evaluate_relay_fee
  having been evaluated and allowed first (independent of FIND-001's field-fallback bug, which is
  about the INPUT to evaluate_relay_fee being wrong, not about the cap being skippable).
