# VCSDD Adversary — impl review, iteration 2 — lm-capafy-loop

**Overall verdict: FAIL**

Reviewed (disk only, Read/Grep/Glob, no Bash — static trace, no live execution):
- `/Users/anicca/anicca/skills/self/lm-capafy-loop/loop.sh`
- `/Users/anicca/anicca/skills/self/lm-capafy-loop/test-loop.sh` (new)
- Reference: `/Users/anicca/anicca/skills/self/founder-loop/founder-loop.sh`
- Spec: `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-04-anicca-money-loop-lm-capafy-design.md`
- Prior: `/Users/anicca/anicca-project/.vcsdd/features/lm-capafy-loop/reviews/impl/iteration-1/output/verdict.json`

## Disposition of the 9 iteration-1 findings

| ID | Status | Evidence |
|---|---|---|
| FIND-001 (count not $) | **RESOLVED** | loop.sh:55-69, real $ MRR, unit_amount/100, year->/12, $0 items contribute $0 |
| FIND-002 (error masked as $0) | **RESOLVED** | loop.sh:46 (Capafy code!=0/no data -> NA), loop.sh:59 (Stripe 'error'/object!=list -> NA) |
| FIND-003 (NA said happy string) | **RESOLVED** | loop.sh:84, `READ-FAILED (...) — DO NOT trust` |
| FIND-004 (no tests) | **PARTIAL** | test-loop.sh exists, 4 meaningful VALUE-line assertions — but see FIND-011 (critical) |
| FIND-005 (loose numeric regex) | **RESOLVED** | the `^[0-9.]+$` guard is gone; design now uses python round()/'NA' + exact string compare |
| FIND-006 (no prior-STATE / snapshot-vs-goal) | **PARTIAL** | prior-STATE read done (loop.sh:79,99); 3-day-vs-monthly unit mismatch NOT fixed — FIND-012 |
| FIND-007 (STATUS winner-take-all masks EARNING) | **STILL OPEN** | loop.sh:83-89 unchanged shape — FIND-010 |
| FIND-008 (no cron-freshness heal) | **PARTIAL** | freshness check correct (loop.sh:72-76); auto-fix/escalation half still missing — FIND-014; and see FIND-011 for a test-coverage/pollution problem on this exact check |
| FIND-009 (no sk_live guard) | **RESOLVED** | loop.sh:34 case-guards the key; empty/non-live -> HEAL |

## Dimension verdicts

| Dimension | Verdict | Key findings |
|---|---|---|
| Spec Fidelity | **FAIL** | FIND-012 (unit-mismatch total mislabeled '/mo'), FIND-014 (spec's auto-fix/escalation requirement still unimplemented) |
| Edge Case Coverage | **FAIL** | FIND-011 (the one edge case the whole fix exists for — stale/dead cron — has zero test coverage, and the workaround pollutes prod) |
| Implementation Correctness | **FAIL** | FIND-013 (fixture-vs-reality risk on the Stripe `items[].price` expand assumption — unverified against a real API call), FIND-012 |
| Structural Integrity | **FAIL** | FIND-010 (STATUS still winner-take-all, unchanged from iteration 1), FIND-011 (freshness-check path lacks the seam every other surface has) |
| Verification Readiness | **FAIL** | FIND-011 (critical: test suite self-defeats the exact invariant it's meant to prove) |

## New findings this iteration

- **FIND-011 (critical, verification_readiness/test_quality)** — `test-loop.sh:13` does `touch "$HOME/.openclaw/skills/capafy-autopublish/state/daily_loop.log"` — a REAL production path, not a fixture path, because `loop.sh:72` hardcodes `LP="$HOME/.openclaw/skills/capafy-autopublish/state/daily_loop.log"` with no `LMCAP_TEST`/`LMCAP_DIR` seam (every other surface in the file has one; this one doesn't). Two consequences: (1) none of the 4 tests ever exercises the `CAPAFY-LOOP-STALE`/`CAPAFY-LOOP-NEVER-RAN` heal branches — the exact FIND-008 invariant has **zero** test coverage; (2) running the test suite on this machine (same `$HOME` the real loop runs from) **resets the real production staleness clock**, meaning the test suite itself can silently mask a real recurrence of the 6-week-silent-death incident FIND-008 exists to catch. This is the most serious issue found this iteration: the fix for the original production incident is unverified and can be defeated by its own test.
- **FIND-012 (major, spec_fidelity/requirement_mismatch)** — `loop.sh:86-87` sums a genuine monthly `LM_MRR` with a genuine but 3-DAY-trailing `CAP_REV` (field literally named `capafy_net_revenue_usd_3d`, loop.sh:100) and reports the sum as `"EARNING $TOTAL/mo"`. This is a real unit-mismatch bug (not a fabrication) that can over- or under-state the true monthly run rate the spec's GOAL line (loop.sh:95, "> Dais monthly spend (~$200)") is meant to be compared against.
- **FIND-013 (major, implementation_correctness/verification_tool_mismatch)** — the LM_MRR parser assumes Stripe's `items[].price` is embedded as a full object with the requested `expand[]=data.items`; this shape is hand-constructed in test-loop.sh's fixtures so tests pass by construction regardless of the real API's actual nesting. If wrong, the broad `except Exception: print('NA')` (loop.sh:69) will fail SAFE (no fabricated number — the anti-fake invariant itself holds) but the harness would return NA/READ-FAILED on every real production wake, making it functionally dead despite 4 green tests. Flagged as an unverified-from-disk risk per the review brief, not as an anti-fake violation.
- **FIND-010 / FIND-014** — restatements of iteration-1 FIND-007 and the unaddressed half of FIND-008, confirmed still-open by direct code trace (see table above).

## Anti-fake assessment (the core question)

The specific failure mode iteration 1 was built to close — **an API error silently reported as a trustworthy-looking $0** — is genuinely fixed: both the Capafy trend parser (loop.sh:42-51) and the Stripe MRR parser (loop.sh:55-69) check their own body's error shape and emit the literal string `NA`, which then forces `STATUS="READ-FAILED (...) — DO NOT trust"` (loop.sh:84), never the happy or the demand-bottleneck string. A `$0` that reaches STATE.md now only gets there via a genuinely empty subscription list / genuinely zero `netRevenue` (verified by test-loop.sh TEST D), which is correct behavior for a true zero.

That said, this iteration is **not a PASS** because: (a) the one test-coverage gap that remains (cron freshness) is the exact incident this whole harness exists to prevent, and the test file's workaround for it actively pollutes the real production signal it's checking (FIND-011, critical); (b) a real STATUS-narrative field can still misrepresent the true picture via unit-mismatch (FIND-012) or full omission (FIND-010, still open from iteration 1); (c) the live-Stripe-shape assumption (FIND-013) is unverified from disk and could make the "fixed" LM_MRR path functionally inert in production even though every fixture test is green — a live single-run confirmation against the real Stripe key is still owed before this can be trusted as working end-to-end.
