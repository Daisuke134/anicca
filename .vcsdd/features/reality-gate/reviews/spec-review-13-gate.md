# VCSDD Adversary — Phase 1c FINAL CONSISTENCY GATE (iteration 13, closing check)

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary, zero context carried over from any prior reviewer.
**Scope discipline**: narrow, internal-consistency-only check of the THREE-BRANCH self-fix
routing rule (FAIL→self-fix; first CANNOT_VERIFY→human-review-only; second-consecutive
CANNOT_VERIFY→human-review AND self-fix, REQ-018/PROP-055), checked at every location it
appears, in both spec files. Standing rulings honored (not findings): row 12 (same-uid trail
forgery), row 13 (TOCTOU), row 16 (local git-hook bypass) — OPEN, disclosed architectural
limits, HMAC mitigates row 12 without closing it.

## Artifacts read

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (full file, this worktree, 704 lines)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (full file, this worktree, 186 lines)
- `.vcsdd/features/reality-gate/reviews/spec-review-12-gate.md` (prior gate, FAIL, 3 blocking
  findings at `behavioral-spec.md:283-284`, `behavioral-spec.md:596-598`,
  `verification-architecture.md:104-105`)

## Exhaustive check: every `self-fix` / `CANNOT_VERIFY` hit, both files

Grepped both files in full for `self-fix` and `CANNOT_VERIFY` and read every hit in context,
plus explicitly re-checked REQ-004, REQ-005 (incl. Acceptance Criteria), REQ-010 (EARS body,
Edge Cases, Acceptance Criteria), REQ-011's three-scenario table, REQ-016/017/018, closure-table
rows 22/23, the "Judgment vs determinism" capstone, PROP-046/055/056, and
verification-architecture.md's Purity Map / Effectful Shell narrative / Proof-Obligations table.

**All three sites review-12 found BLOCKING are now fixed, verified by direct re-read:**

1. **`behavioral-spec.md:283-288`** (REQ-005 Acceptance Criteria, `reality-verify-spawn.sh`'s
   own post-spawn routing) — now reads: "the **FIRST** such verdict does NOT invoke
   `self-fix.sh`; the **SECOND CONSECUTIVE** one DOES (REQ-018/PROP-055 ...) — grep-checkable,
   distinct code path from the `FAIL` branch." Correctly qualified; no longer an unconditional
   claim. FIXED.

2. **`behavioral-spec.md:604-608`** ("Judgment vs determinism" capstone, the "rule stated once,
   finally") — now reads: "...is honestly `CANNOT_VERIFY`, routed to a human, never silently
   folded into either PASS or FAIL, and — on its FIRST occurrence — not flogged with an
   escalation mechanism (self-fix) that has nothing to fix. **But a SECOND CONSECUTIVE
   `CANNOT_VERIFY` DOES escalate to self-fix (REQ-018/PROP-055)...**" Correctly qualified,
   reconciled with REQ-018 in the same paragraph. FIXED.

3. **`verification-architecture.md:104-109`** (Effectful Shell narrative for
   `reality-verify-spawn.sh`) — now reads: "**The FIRST `CANNOT_VERIFY` does NOT invoke
   `self-fix.sh`; the SECOND CONSECUTIVE one DOES (REQ-018/PROP-055).** So the code has three
   branches, not two: `FAIL`→`self-fix.sh`; first-`CANNOT_VERIFY`→human-review queue only;
   second-consecutive-`CANNOT_VERIFY`→human-review queue AND `self-fix.sh`. The
   consecutive-`CANNOT_VERIFY` counter is read from the durable verdict trail (REQ-006/018), not
   from in-memory state, so it survives the process dying between passes." The narrative now
   matches its own Proof-Obligations table (PROP-046/055) and adds the counter-durability detail
   the rule prompt specifically asked about. FIXED, and strengthened beyond the minimum fix.

**No new unqualified restatement was introduced elsewhere.** Every other location carrying this
rule — REQ-010 EARS body (`:342-357`), REQ-010's REQ-018 amendment paragraph (`:365-373`),
REQ-010's Edge Cases (`:374-381`, includes the iteration-9 FIND-AA correction of the dedupe-scope
sentence) and Acceptance Criteria (`:382-392`), REQ-011 scenario 1 (`:401-409`), REQ-016's own
description of the (rejected, pre-HMAC) laundering hole (`:659-661`, correctly framed as
describing the BUG being fixed by REQ-017, not a current-behavior claim), REQ-018 itself
(`:683-698`), PROP-046/055 in the proof-obligations table (`behavioral-spec.md` implicit via
REQ-018, `verification-architecture.md:152-153`) — all state the two-strike/three-branch rule
consistently. Grepping for `consecutive`/`CONSECUTIVE` across the file confirms every one of the
9 hits (`:82,285,349,367,376,387,389,407,605` plus `:694` in REQ-018) is correctly scoped.

**No surviving NORMATIVE sentence states an unconditional "CANNOT_VERIFY never calls
self-fix."** None found in either file.

## Final sanity check (end-to-end read as a Builder would)

- (a) A loop that fabricates a post → REQ-004's CONTRADICTION taxonomy (e.g. `url_mismatch`,
  `fingerprint_mismatch`, `server_confirmed_absent`) → `FAIL` → REQ-010 routes to `self-fix.sh`.
  Reachable.
- (b) A healthy post on a not-yet-proven platform → REQ-011 scenario 1: every structural check
  clean, only `automated_verification_unproven` fires → `CANNOT_VERIFY` → REQ-010/REQ-018 routes
  to human-review (first occurrence, no self-fix); PROP-056 forces it is never reported to the
  owner with a verified/success framing. Reachable, and never misreported as verified.
- (c) A permanently-unverifiable loop cannot hide in silence → REQ-018 point 1 (every pass
  reports, `CANNOT_VERIFY` included, PROP-056) + point 2 (second-consecutive `CANNOT_VERIFY`
  escalates to `self-fix.sh`, PROP-055) + point 3 (durable trail makes the streak mechanically
  visible). Reachable — silence is structurally excluded.
- (d) PASS is reachable for a genuinely healthy, proven-platform post → REQ-011 scenario 2:
  identical clean structural checks, `automatedVerification: true` (post-Phase-2a) → the final
  gate passes → `PASS`. Reachable.

All four hold; none is unreachable.

## Overall Verdict: **PASS**

0 blocking findings. The three sites that blocked iteration 12 (`behavioral-spec.md:283-284`,
`behavioral-spec.md:596-598`, `verification-architecture.md:104-105`) are each independently
confirmed fixed by direct re-read at their current line numbers
(`behavioral-spec.md:283-288`, `:604-608`; `verification-architecture.md:104-109`), and no new
unqualified restatement of the pre-REQ-018 rule was found anywhere else in either file. The
three-branch self-fix-routing rule (REQ-005/REQ-010/REQ-018, PROP-046/055/056) is internally
consistent across every location it appears. The end-to-end reachability sanity check (a)-(d)
holds. Standing-disclosed rows 12/13/16 are not re-litigated per the task's own ruling.

**Phase 1c gate: CLOSED. Feature `reality-gate` is cleared to proceed to Phase 2a
(implementation).**
