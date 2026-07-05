# VCSDD Adversary — impl review, iteration 3 (FINAL convergence) — lm-capafy-loop

**Overall verdict: FAIL**

Reviewed (disk only, Read/Grep/Glob, no Bash — static trace, no live execution):
- `/Users/anicca/anicca/skills/self/lm-capafy-loop/loop.sh`
- `/Users/anicca/anicca/skills/self/lm-capafy-loop/test-loop.sh`
- `/Users/anicca/anicca/skills/self/lm-capafy-loop/state/STATE.md`
- Spec: `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-04-anicca-money-loop-lm-capafy-design.md`
- Prior verdicts: iteration-1, iteration-2

## Disposition of prior findings

| ID | Status | Evidence |
|---|---|---|
| FIND-001 ($ not count) | **RESOLVED, holds** | loop.sh:54-68 — real $ MRR, unit_amount/100, year→/12, $0 items stay $0 |
| FIND-002 (error masked as $0) | **RESOLVED, holds** | loop.sh:37 (Capafy `code!=0`/no `data`→NA), loop.sh:58 (`error`/`object!=list`→NA) |
| FIND-003 (NA→happy string) | **RESOLVED, holds** | loop.sh:84 `READ-FAILED (...) — DO NOT trust, recompute` |
| FIND-005 (loose regex) | **RESOLVED, holds** | no regex-numeric guard anywhere; python round()/'NA' + exact string compare throughout |
| FIND-007 (STATUS hides EARNING under HEAL) | **RESOLVED** | loop.sh:82 `EARN_NOTE`, loop.sh:83 `STATUS="HEAL-NEEDED — ${HEAL}${EARN_NOTE}"` — the dollar figure now survives even when HEAL fires |
| FIND-009 (no sk_live guard) | **RESOLVED, holds** | loop.sh:25 `case ... sk_live_*) : ;; "") add_heal ...; *) add_heal ...` |
| FIND-011 (critical — freshness log had no seam, test polluted prod) | **RESOLVED** | loop.sh:15 `LP="${LMCAP_LOGFILE:-$HOME/...}"`; test-loop.sh:7-10 always sets `LMCAP_LOGFILE="$LOG"` to a per-test tempfile. Grepped test-loop.sh for the literal prod path string — it never appears; the real `daily_loop.log` is never opened by the test suite. Test E (line 19) exercises the STALE branch + asserts `REQEXISTS=yes`. This is the single most important fix of this round and it is genuinely closed. |
| FIND-012 (3-day summed into "/mo" monthly goal) | **RESOLVED at the top layer, but see FIND-015** | loop.sh:79-82: `TOTAL` is computed ONLY from `LM_MRR + CAP_MO`; `CAP_3D` (loop.sh:43-50) is fetched, printed as `capafy_3d_net_usd_leading` (loop.sh:99), and explicitly commented "NOT summed into the monthly goal" (loop.sh:42) — never enters `TOTAL`. The literal unit-mismatch bug from iteration 2 is gone. However, `CAP_MO` itself turns out to have its own, different monthly-accuracy bug — see FIND-015. |
| FIND-013 (Stripe shape unverified from disk) | **NARROWED, not closed — tracked as FIND-017** | expand path deepened to `expand[]=data.items.data.price` (loop.sh:53) and the parser matches that nesting (loop.sh:62-64), which is an improvement. But no on-disk artifact (saved real response, dated log, cited subscription ID) substantiates the "confirmed against a real live sub" claim, and the one real production run in `state/STATE.md` had `lm_mrr_usd: 0.0` with zero active subs — meaning the `items.data[].price` walk has still never actually executed against a real non-empty Stripe body. Failure mode is fail-safe (NA), so this is a verification-readiness gap, not an anti-fake violation. |
| FIND-014 (no auto-fix/escalation on HEAL) | **CORE RESOLVED** | loop.sh:89 writes `selfheal-request.json` on any HEAL and removes it when healthy — this is the "handoff so the claude-p loop self-fixes" mechanism the spec's step-0 required; a live Telegram ping is still not wired, but the spec's own minimum bar (a machine-readable self-heal signal, not just a STATE.md sentence nobody reads) is met. |

## New findings this iteration

- **FIND-015 (critical, implementation_correctness/requirement_mismatch)** — `loop.sh:31-41`. The Capafy "monthly" figure is `max(amount)` across **every** payout record ever returned, not the record matching the current `payoutMonth`. Once Capafy has had one good month, `capafy_monthly_payout_usd` will report that historical peak **forever**, on every future wake, even after revenue collapses to $0 — a real (not fabricated) number that nonetheless silently misrepresents "current month" and can permanently hide a real revenue collapse from the loop's own JUDGE step. No test catches this because every fixture in test-loop.sh (`PAY0`, line 13) contains exactly one payout record, so `max()` and "the current month's record" are indistinguishable in every test that exists today.
- **FIND-016 (minor, edge_case_coverage/test_coverage)** — `test-loop.sh:9`. `run()` unconditionally `touch`es the fixture log file, so the `CAPAFY-LOOP-NEVER-RAN` branch (`loop.sh:74`, distinct wording from STALE) has zero test coverage — only the STALE branch is exercised.
- **FIND-017 (minor, verification_readiness/verification_tool_mismatch)** — residual of FIND-013: the "live-verified" Stripe shape claim has no supporting artifact on disk, and the one real wake captured in STATE.md never exercised the code path in question (zero active subs). Fails safe if wrong, so not anti-fake-breaking, but not yet actually proven either.

## Anti-fake core assessment

The specific failure mode this whole harness exists to prevent — **an API error or a genuinely-zero result being reported as, or confused with, a trustworthy non-zero dollar figure** — remains fixed and is not re-broken by anything found this round: both Capafy parsers and the Stripe parser fail to the literal string `NA` on any error/shape mismatch (loop.sh:37,47,58), which forces `READ-FAILED — DO NOT trust` (loop.sh:84), never a happy or demand-bottleneck string. A true `$0` only reaches STATE.md via a genuinely empty subscription list / genuinely zero net revenue (test D). The critical iteration-2 test-pollution defeat (FIND-011) is fully closed via the `LMCAP_LOGFILE` seam. The 3-day/monthly unit-mismatch (FIND-012) that literally corrupted the summed total is gone.

What is **not** yet trustworthy: the Capafy monthly figure itself can be a real-but-wrong-month number that looks exactly like a fresh, current-month reading (FIND-015) — this is precisely the "wrong number passing as real" failure mode this convergence round was asked to hunt for, and it is present and untested. Two smaller verification-readiness gaps (FIND-016, FIND-017) remain open as well.

**Verdict: FAIL.** The measurement spine is close but not yet fully trustworthy — fix FIND-015 (select payoutMonth == current month, not max-ever), add the corresponding multi-record test, add the NEVER-RAN test coverage (FIND-016), and (lower priority, tracked for phase 5) back FIND-013/017's live-shape claim with a real artifact before declaring 4-D convergence.
