# VCSDD Adversary — Phase 1c FINAL CONSISTENCY GATE (iteration 12)

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary, zero context carried over from any prior reviewer.
**Scope discipline**: narrow, internal-consistency-only check of exactly RULE 1 (tamper
evidence is a FACT) and RULE 2 (self-fix routing is a two-strike rule) across every location
either rule appears in, in both spec files. Standing rulings honored: rows 12/13/16
open-disclosed are not findings; FIND-H..V/Z/AA are settled and not re-litigated (FIND-AA's
specific `:368-369` sentence IS now fixed — see below).

## Artifacts read

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (full file, this worktree, 695 lines)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (full file, this worktree, 182 lines)
- `.vcsdd/features/reality-gate/reviews/spec-review-11-final.md` (prior gate, FIND-AA at `:368-369`)

## RULE 1 — tamper evidence is a FACT — CLEAN

Checked every named location plus a full-file grep for `CANNOT_VERIFY`:

- `behavioral-spec.md:225` — REQ-004 taxonomy row: existing-but-unverified `rowHmac` →
  CONTRADICTION `artifact_trail_tampered` → `FAIL`. Correct.
- `behavioral-spec.md:432-436` — REQ-012 EARS text, pre-existing-directory case → `FAIL` /
  `artifact_trail_tampered`, explicitly "NOT `CANNOT_VERIFY`". Correct.
- `behavioral-spec.md:609-616` (REQ-016) and `:653-664` (REQ-017 table) both state
  existing/mis-signed rows are CONTRADICTION → `FAIL`, never `CANNOT_VERIFY`, and explicitly
  supersede any earlier reading that would classify them `CANNOT_VERIFY`.
- `behavioral-spec.md:83` (closure row 12) and `:81` (row 22) — both route pre-staging/forgery
  to `FAIL`/`artifact_trail_tampered`.
- `verification-architecture.md:44-52` (mirrored taxonomy) and `:94-100`/`:140` (PROP-048 prose
  + table row) — consistent with the above, including the identical "NOT `CANNOT_VERIFY`"
  correction.
- PROP-048 (`verification-architecture.md:140`), PROP-053 (`:146`), PROP-054 (`:147`) all exist,
  Tier 0, `required: true`, each with a bound Tool.

No surviving sentence anywhere routes an existing-but-unverifiable row, or a pre-existing
CSPRNG-named directory, to `CANNOT_VERIFY`. **RULE 1: consistent, no findings.**

## RULE 2 — self-fix routing is a two-strike rule — **NOT clean, BLOCKING**

FIND-AA (review-11's blocking finding at `behavioral-spec.md:368-369`) **is now fixed**: that
line correctly reads "it applies to EVERY path that reaches `self-fix.sh`, which per REQ-018 is
the `FAIL` branch AND the second-consecutive-`CANNOT_VERIFY` branch." Confirmed closed.

However, the same defect class (a sibling passage restating the pre-REQ-018 unconditional rule,
never updated when REQ-018/PROP-055 were added) survives in **three other locations** that were
never touched by the FIND-AA fix:

1. **`behavioral-spec.md:283-284`** (REQ-005's own Acceptance Criteria — a DIFFERENT
   requirement than REQ-010, so FIND-AA's fix to REQ-010 did not reach it):
   > "on `overallVerdict: "CANNOT_VERIFY"`, the script's post-spawn logic appends to the
   > human-review queue (REQ-010) and does NOT invoke `self-fix.sh` — grep-checkable, distinct
   > code path from the `FAIL` branch."

   This is unqualified — no "first" / "single-pass" caveat. A Builder implementing
   `reality-verify-spawn.sh`'s post-spawn routing literally per THIS sentence (which is what
   REQ-005's own Acceptance Criteria instructs them to grep-check) would never call
   `self-fix.sh` on any `CANNOT_VERIFY`, including the second consecutive one — directly
   failing PROP-055.

2. **`behavioral-spec.md:596-598`** ("Judgment vs determinism" section, presented as "the rule,
   stated once, finally" — a bolded capstone summary of the entire CANNOT_VERIFY semantics,
   predating REQ-016/017/018 which are appended after it and never reconciled back into it):
   > "...and everything in between — no capture, a network failure, an empty body, or an
   > unproven signal — is honestly `CANNOT_VERIFY`, routed to a human, never silently folded
   > into either PASS or FAIL, and never flogged with an escalation mechanism (self-fix) that
   > has nothing to fix."

   This is the exact pattern the task calls out verbatim: an unconditional "CANNOT_VERIFY never
   calls self-fix" that a Builder could implement literally and thereby fail PROP-055. It
   directly contradicts REQ-018 (`:359-367`, "TWO CONSECUTIVE `CANNOT_VERIFY` verdicts... SHALL
   invoke `self-fix.sh`") and PROP-055, both of which exist elsewhere in the same file.

3. **`verification-architecture.md:104-105`** (Purity Boundary Map, Effectful Shell description
   of `reality-verify-spawn.sh` itself — the architecture's own authoritative description of
   what the shipped code does):
   > "...on `CANNOT_VERIFY`, appends to the human-review queue (REQ-010) instead of invoking
   > `self-fix.sh` — a distinct branch from the existing `FAIL`→`self-fix.sh` branch."

   Unqualified. REQ-018/PROP-055 (the two-strike escalation) appear ONLY in the Proof
   Obligations table (`:148-149`) of this file — the Purity/Effectful-Shell narrative
   description of the actual code path was never updated to mention the second-consecutive
   branch at all. `verification-architecture.md:112` ("the VCSDD gate script... mirrors the
   spawn wrapper's") inherits the same staleness by explicit reference rather than restating it
   independently.

This is not three independent minor typos: it is the same root cause recurring at three sites —
REQ-018/PROP-055 were spliced into REQ-010 and the PROP table only, and never propagated to
every other requirement/summary/architecture passage that restates the "CANNOT_VERIFY → no
self-fix" rule as its own local claim. Per the task's own bright line, a single surviving
instance is blocking; there are three.

## Overall Verdict: **FAIL**

Blocking findings:
- `behavioral-spec.md:283-284` (REQ-005 Acceptance Criteria) — unqualified "does NOT invoke
  `self-fix.sh`" on any `CANNOT_VERIFY`, contradicting REQ-018/PROP-055's second-consecutive
  escalation. Fix: qualify as "on the FIRST `CANNOT_VERIFY` for a given loop... per REQ-018,
  the SECOND CONSECUTIVE one DOES invoke `self-fix.sh`" — mirroring the fix already applied at
  `:368-369`. `routeToPhase`: 1b.
- `behavioral-spec.md:596-598` ("Judgment vs determinism," bolded capstone rule) — states
  `CANNOT_VERIFY` is "never flogged with an escalation mechanism (self-fix)," an absolute claim
  contradicting REQ-018 (`:359-367`) and PROP-055. Fix: add the second-consecutive-escalation
  caveat to this sentence or delete the "never...self-fix" clause and point to REQ-018/REQ-010
  as the authoritative routing rule instead of restating it here. `routeToPhase`: 1b.
- `verification-architecture.md:104-105` (Effectful Shell description of
  `reality-verify-spawn.sh`) — unqualified "instead of invoking `self-fix.sh`," with no mention
  of REQ-018's second-consecutive branch anywhere in the Purity Boundary Map's narrative (only
  in the separate Proof Obligations table, PROP-055 at `:148`). Fix: add the second-consecutive
  branch to this bullet's own description so the architecture's own account of the effectful
  shell is self-consistent with its own Proof Obligations table. `routeToPhase`: 1b.

RULE 1 is fully consistent everywhere checked. RULE 2 is consistent at its primary, most-recently
edited site (REQ-010's body/Edge Cases/Acceptance Criteria, and PROP-046/055 themselves) but is
contradicted by three unedited sibling passages elsewhere in the same two files that still assert
the pre-REQ-018 unconditional rule. This feature is NOT yet ready for Phase 2a; gate does not
close on this iteration.
