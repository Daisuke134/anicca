# Spec Review Verdict — anicca-agent-lending — Iteration 6

**Overall verdict: FAIL**

## Part 1 — Re-verification of the 3 prior findings (FIND-401..403)

All three findings from iteration 5 are **genuinely resolved** on their technical merits, after a fresh,
skeptical re-read of `lock.mjs`'s real signature and a manual walk-through of the nested dual-lock design
with concrete lender/borrower IDs.

| Finding | Status | Basis |
|---|---|---|
| FIND-401 (borrower double-loan race across lenders) | **Resolved** | REQ-106 now acquires BOTH `loan_${lenderId}` AND `loan_borrower_${borrowerId}` for every issuance attempt, and takes a FRESH read of `loans.jsonl` while BOTH locks are held, before re-checking REQ-102. Because `ledger.js::appendChild` is a synchronous `fs.appendFileSync` and the fresh read is specified to occur only after acquiring the shared borrower lock, the re-check is structurally guaranteed to observe the latest committed state, never a stale pre-lock snapshot. Walked the PROP-106n scenario (two lenders, one borrower) concretely: exactly one lock key is ever shared between the two attempts; the loser's re-check correctly sees `reason:"outstanding_loan"`. |
| FIND-402 (self-loan exploit) | **Resolved** | Condition (d) (`lenderId !== borrowerId`) is checked first, before any other condition, any lock, or any surplus computation, backed by a binding fixture (PROP-102e) that would fail if the check were not genuinely first. |
| FIND-403 (`issued_ms` ambiguity) | **Resolved** | `issued_ms` is now unambiguously defined as the FOLLOW-UP `"active"` row's own append-time timestamp only, never the provisional row's, with a binding fixture (PROP-106o) proving `issued_ms`/`due_ms` are computed from the later, reconciled timestamp when the two rows are appended at different times. |

## Part 2 — Fresh, full pass over the rest of the spec

A full fresh pass over the remaining ~1,700 lines of `behavioral-spec.md` and 384 lines of
`verification-architecture.md` (not just the three previously-fixed areas) surfaced **three new findings** —
one embedded inside the very mechanism iteration 5 just finished hardening.

### FIND-501 (major, verification_readiness) — The "deadlock avoidance" justification for total lock ordering is analytically unsound

`resolveLoanLockAcquisitionOrder`'s own stated purpose (behavioral-spec.md:793-802) is to prevent a
classical lock-ordering deadlock. But `lock.mjs`'s `withGigLock`/`acquire()` is a **non-blocking, fail-fast**
primitive (confirmed fresh this session, lines 153-158/174-179/187-209): a caller that cannot acquire a
lock is rejected **immediately**, with **no queueing, no waiting, no retry loop**. Classical deadlock
requires hold-and-wait; nothing in this mechanism ever waits. Walked two concrete scenarios with real
citizen IDs (automaton/Franklin): (1) reversed-role concurrent lending shares **zero** lock keys between
the two attempts; (2) the actual same-borrower, different-lender race (PROP-106n) shares **exactly one**
key — and deadlock requires at least two shared resources acquired in reversed order. Neither precondition
for real deadlock is ever present in this design, independent of key-sort order. The mechanism itself is
harmless, but the spec's own justification for it is wrong, and no proof obligation (PROP-106m) tests or
could test the claimed property, since no deadlock is constructible against this lock.

### FIND-502 (major, spec_fidelity) — The cold-start kill-switch has zero coverage for the highest-dollar loan tranche

`computeColdStartRepaymentRate`'s own definition is total and explicit: it samples **only** loans where
`successfulOnTimeRepayments === 0` at issuance. `evaluateColdStartKillSwitch` is fed exclusively by that
sample. But REQ-105's own doubling ladder is precisely what grows an established borrower's loan size from
`$0.02` up to the `$5.00` ceiling (250x) as its reputation count rises — and `successfulOnTimeRepayments`
is a colony-wide, not lender-specific, signal, fully portable across unrelated lenders. A borrower can
cheaply build reputation via small, low-risk, successfully-repaid loans and then default on the single
largest loan an unrelated, trusting lender extends it — and this default is, by the kill-switch's own
definition, **invisible** to the only automated risk-monitoring mechanism this feature builds. Five
iterations have hardened this mechanism's wiring and internal consistency (FIND-203, FIND-303) without ever
asking whether its scope covers the tranche of highest dollar exposure. REQ-102(c)'s one-strike lockout
caps the blast radius to roughly one maximal loan per exploiting borrower, so this is not unbounded — but
it is a real, currently undocumented gap, unlike this spec's other honestly-disclosed limitations.

### FIND-503 (minor, spec_fidelity) — The document's own revision header/changelog is stale

The header still says "revision: iteration 3" and the Changelog tables stop at "iteration 2 → iteration 3,"
even though the body clearly incorporates iterations 3/4/5's resolutions throughout. `RESOLUTION-NOTES.md`
exist on disk for iterations 3, 4, and 5 but are never cross-referenced from the document's own header the
way iterations 1/2 are — a real regression in the self-documenting discipline the document itself
established early on.

## Conclusion — is convergence genuinely close?

**No — treat the decreasing finding-count trend (7→8→6→5→3→3) as a false signal, not evidence of
convergence.** A fresh, skeptical pass over material NOT flagged by any of the prior five iterations again
surfaced a substantive concurrency-reasoning defect (FIND-501, embedded inside the exact mechanism iteration
5 just finished hardening) and a substantive, previously-unexamined risk-coverage gap in the feature's own
flagship safety mechanism (FIND-502) — neither of which is a re-discovery of anything in the 29 cumulative
prior findings. The document is genuinely improving on the specific issues each iteration targets (FIND-401
through FIND-403 are all real, well-verified fixes), but the review process itself is still finding new
classes of defect on each fresh pass rather than running out of things to find — the honest read is that
convergence is not yet close, `overallVerdict: FAIL`.
