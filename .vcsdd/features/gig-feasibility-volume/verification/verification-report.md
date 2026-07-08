# Verification Report

## Feature: gig-feasibility-volume | Sprint: Phase 5 (lean, formal hardening) | Date: 2026-07-08

**Verifier session note (process fact, not a finding)**: this feature's two worktrees
(`~/profitable-claude/.worktrees/gig-fv` @ ff3a43f, `~/anicca/.worktrees/gig-fv` @ 3df9081) were
merged into each repo's `main` branch and the worktrees removed **mid-session, by a process outside
this verifier's control**, partway through this audit. Verified via `git log`/`md5`/line-count that
`main` in both repos contains byte-identical content to the worktree HEADs named in the task (main is
now exactly at those two commits). All verification below completed against `main` in both repos
after that point; every earlier probe result captured before the merge remains valid evidence since
the content did not change. `~/gig/strategy.json`/`~/gig/applied.jsonl` (the real production ledgers)
were read-only throughout — never mutated by this verifier.

## Proof Obligations

Read from `specs/verification-architecture.md` §2 directly, since `state.json.proofObligations` is
`[]` (denormalize step not yet run) per the task's explicit instruction. 32 `required:true` obligations
(PROP-001..007, 010..018, 020..033, 036, 037); 6 `required:false` (PROP-008, 009, 019, 034, 035, 038,
evidence-only/non-blocking, correctly left unchanged/not gated).

| ID | Tier | Required | Status | Tool | Artifact / Evidence |
|----|------|----------|--------|------|---------|
| PROP-001 | 0 | true | **proved** | grep (this session) | zero `re.compile`/regex-judgment hits across scope-locked files; `feasibility_rules.ai_doable`/`.ai_infeasible` non-empty in `strategy.default.json` |
| PROP-002 | 1 | true | **proved** | pytest (`__tests__/test_feasibility_fillforward.py`, 10/10) + own probe | fill-forward adds N+3 keys (feasibility_rules+listing_playbook+proposal_playbook), all originals byte-identical |
| PROP-003 | 1 | true | **proved** | node:test (`passprep.test.mjs`, 6 crash-safety cases) + own probe (§security-results, item 7: malformed `listings.jsonl` row → exit 0) | all 4 fallback branches exit 0, valid JSON |
| PROP-004 | 0 | true | **proved** | own python assert script | `skip_categories` 占い/霊感/スピリチュアル count=0; `listing_categories` uranai-style count=1 |
| PROP-005 | 1 | true | **proved** | pytest (`test_listing_categories_seed.py`) + own script | 9 entries (≥8), all price_jpy_initial in [50%,70%] of target |
| PROP-006 | 1 | true | **proved** | pytest (`test_listings_due_pure.py`, 7/7) + own boundary probe (target-1/target/target=0) | see GAP-2 below for a related but out-of-scope-of-this-PROP finding at target=0 |
| PROP-007 | 1 | true | **proved** | node:test (`passprep.test.mjs`) | `listings_due` boolean present on every branch incl. fallback |
| PROP-010 | 1 | true | **proved** | node:test (`passprep.test.mjs`: "skip_categories ⊇ priority_categories → reset to []") | regression pinned, unaffected by this feature |
| PROP-011 | 1 | true | **proved** | node:test (`passprep.test.mjs`: fresh-bootstrap=30 vs live-fixture stays 12) | confirmed also against REAL `~/gig/strategy.json` (read-only): `apply_skip_thresholds.max_applicants` still 12 in production |
| PROP-012 | 1 | true | **proved** | pytest (`test_funnel_by_category.py`, 27/27 incl. 17 randomized partition-invariance trials) | |
| PROP-013 | 0 | true | **proved** | grep (this session) | `_WON_STATUSES`/`_PAID_STATUSES` each defined exactly once in `funnel.py` |
| PROP-014 | 1 | true | **proved** | pytest (`test_funnel_report_schema.py`, 8/8) | additive schema confirmed, old + new keys coexist |
| PROP-015 | 0 | true | **proved** | `git show 3df9081 -- cadence-contracts.json` (this session) | diff confined to exactly the `gig.source` value; `kind` unchanged; every other loop entry untouched |
| PROP-016 | 1 | true | **proved** | pytest (`test_gig_evaluator_by_category.py`) | `evaluate_stage1` golden-value regression pinned unchanged |
| PROP-017 | 0 | true | **proved** | grep (this session) | `evaluator.py` new-function imports only `os`/`sys`/`ledger_metrics` — no post/apply/dispatch/browser import |
| PROP-018 | 1 | true | **proved** | pytest (`test_gig_evaluator_by_category.py`) | mixed-schema (no `by_category`) row contributes zero, no raise |
| PROP-020 | 0 | true | **proved** | `git log`/`git diff` (this session) | `weekly_compare.py` untouched by any commit in this feature (last touched by an unrelated prior commit) |
| PROP-021 | 0 | true | **proved** | grep (this session) | NEVER-REFUSE CLAUSE text present verbatim in STARTUP |
| PROP-022 | 1 | true | **proved** | pytest (`test_gig_ts_parser.py` 8/8, `test_gig_activity_event_dates.py` 10/10) + own adversarial probes | see GAP-1 below for a related but out-of-scope-of-this-PROP finding (non-dict row) |
| PROP-023 | 1 | true | **proved** | node:test (`passprep.test.mjs`) | `cold_start` boolean present on every branch |
| PROP-024 | 0 | true | **proved** | grep (this session) | `agent-reach` web-search required unconditionally inside B4; no `if cold_start: skip search` pattern found |
| PROP-025 | 0 | true | **proved** | grep (this session) | "METRICS HALF (b): runs unconditionally on EVERY do_improve pass too, cold_start or not" present verbatim |
| PROP-026 | 0 | true | **proved** | own python assert script | 松竹梅/モニター/30分/5段/80% spot-check phrases present across listing_playbook+proposal_playbook |
| PROP-027 | 1 | true | **proved** | pytest (`test_feasibility_fillforward.py`) | listing_playbook/proposal_playbook fill-forward confirmed, no other key touched |
| PROP-028 | 0 | true | **proved** | grep (this session) | individualization clause present for both B1 and B2 |
| PROP-029 | 1 | true | **proved** | pytest (`test_gig_ts_parser.py`, 8/8) + own extended probe (18 additional adversarial cases: bool, NaN, inf, negative/huge epoch, naive ISO, date-only, list/dict-typed ts, numeric-string epoch — zero crashes, see security-results probe file) | |
| PROP-030 | 1 | true | **proved** | pytest (`test_gig_activity_event_dates.py`, 10/10) + own extended probe (12 additional cases) | zero crashes on all fixtures the PROP literally specifies; see GAP-1 for a case OUTSIDE the PROP's specified fixtures |
| PROP-031 | 0 | true | **proved** | own python assert script + `git diff` | `kind=="row-exists"` confirmed unchanged; all 6 other loop entries byte-for-byte identical |
| PROP-032 | 1 | true | **proved** | pytest (`test_cadence_evidence_gig_branch.py`, 4/4) | real-today-row→met=true, housekeeping-only→met=false, mixed ISO+epoch same-day→correct union |
| PROP-033 | 0 | true | **proved** | grep (this session) | broken-path occurrences=0, both corrected paths present ≥1× each |
| PROP-036 | 0 (evidence, required:true) | true | **proved** | pytest (`test_gig_cadence_real_evidence.py`, 4/4) against REAL `~/gig/applied.jsonl` (270 rows, re-verified this session, read-only) | SUT `_gig_activity_event_dates` matches an independent reference tally exactly; all 10 real JST activity days recovered, zero false negatives |
| PROP-037 | 0 | true | **proved** | grep (this session) | `category:<...NEVER omit this field>` present in the B2-APPLY append instruction |

## Additional findings beyond the literal PROP acceptance criteria (adversarial probing, this session)

These do **not** cause any `required:true` PROP above to fail against its own literally-specified
acceptance criteria/fixtures (all 32 pass). They are gaps this verifier found by probing inputs the
spec's fixtures do not enumerate, surfaced because the task explicitly asked for adversarial boundary
probing beyond the existing test suite. Raw command + output for both:
`verification/security-results/gig-security-probe-2026-07-08-verifier-session2.txt` (items 6 and 8).

### GAP-1 (BLOCKING-severity invariant violation, recommended pre-Phase-6 fix — does not fail a named PROP)
`cadence-evidence.py`'s `_gig_activity_event_dates` (and the `_gig_ts_to_jst_date` it calls) assume
every JSONL row parses to a `dict` (`row.get(...)` pattern, matching the pre-existing convention
already used by `funnel.py`/`passprep.py` elsewhere in this codebase). A syntactically-valid-JSON but
non-object line (e.g. a bare string `"oops"` on its own line) anywhere in `~/gig/applied.jsonl` or
`~/gig/listings.jsonl` causes an **uncaught `AttributeError`** that propagates all the way through
`cadence-evidence.py status gig`'s `_main()` (no try/except at that layer, unlike `passprep.py`'s
`main()` which DOES catch this class of error and degrades to its documented exit-0 fallback —
verified directly, see probe item 7). Traced one level further: `cadence-deadline-check.sh` (the
daily 21:00 JST launchd escalation trigger) captures this crash via
`STATUS_JSON="$(python3 cadence-evidence.py status gig 2>>"$LOG")"` + `MET="$(... || echo False)"`,
which silently converts the crash into `MET=False` — **even on a day where a genuine real `"applied"`
row for TODAY exists in the same file** (reproduced directly: probe item 6). This is exactly the
false-negative failure class REQ-GFV-021/022/023's iteration-2 rewrite was explicitly designed to
eliminate (per behavioral-spec.md §0 and PROP-036's own stated purpose). It is not currently
triggered by the real production ledger (all 270 real rows are dict-shaped, confirmed via
`test_gig_cadence_real_evidence.py`), so no `required:true` PROP fails today — but the ledger is
agent-written and append-only-forever, and the agent already writes creative ad-hoc status strings
(e.g. `0_applied_genuinely_viable_none`), so a future malformed line is a real, non-hypothetical risk
class, not a contrived edge case. **Recommended fix**: guard `_gig_activity_event_dates`'s row
iteration with the same `(row or {}).get(...)`-plus-`isinstance` tolerance already implied elsewhere,
or wrap `status_for_loop()`/`_main()` in a top-level try/except that degrades to `met:false` +
`_error` field (matching `passprep.py`'s own documented crash-safety pattern) rather than an uncaught
traceback.

### GAP-2 (low severity, non-blocking, informational)
`passprep.py`'s `compute_listings_due(listing_rows, now_epoch, listing_weekly_target)` computes
`count < int(listing_weekly_target or 2)`; `main()`'s call site independently does the same
`int((strategy.get("listing_weekly_target")) or 2)` coalescing. Because Python's `or` treats `0` as
falsy, `listing_weekly_target: 0` (a plausible future "pause all new listings" operator setting) is
silently treated as the default `2`, never as `0`. Confirmed via probe item 8: `target=0` with 1 row
present still returns `listings_due:true` (i.e. behaves as target=2, not target=0). Not covered by
PROP-006's specified fixtures (which test target-1/target only, not target=0), so does not fail that
PROP. `listing_weekly_target` is not currently set anywhere in production. Recommended fix if `0` is
ever meant to be a legitimate value: use an explicit `is None` check instead of `or`.

### Minor robustness note (very low severity, non-blocking)
`funnel_report.py --out-path <bare-filename-with-no-directory-component>` raises an uncaught
`FileNotFoundError` from `os.makedirs(os.path.dirname(out_path), exist_ok=True)` when `dirname()`
returns `""`. Not attacker-reachable: the STARTUP prompt always invokes this script with a fixed
absolute `--listings-path ~/gig/listings.jsonl` and never varies `--out-path`; there is no untrusted
external caller of this CLI. Noted for completeness (probe item 5).

## Summary

- Required obligations: 32
- Proved: 32
- Failed: 0
- Skipped: 0 (all required obligations were evaluated this session, real fresh evidence, not merely
  re-quoted from a prior pass)
- Non-required (evidence-only) obligations left unchanged as instructed: PROP-008, 009, 019, 034, 035,
  038 (real-pass evidence pending post-ship activity — `~/gig/listings.jsonl` does not exist yet in
  production, confirmed this session, consistent with REQ-GFV-006 not having fired live yet)
- **2 additional gaps found via adversarial probing beyond the spec's own fixtures** (GAP-1
  BLOCKING-severity/non-PROP-failing, GAP-2 low-severity/non-PROP-failing) — see above. GAP-1 is
  flagged prominently because it reintroduces, under an untested input shape, exactly the
  false-negative risk class this feature's iteration-2 spec rewrite was built to close.
