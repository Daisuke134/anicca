# VCSDD Adversary — Phase 1c FINAL CONSISTENCY GATE (iteration 11)

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary, zero context carried over from any prior reviewer.
**Scope discipline**: narrow, internal-consistency-only check of exactly RULE 1 (tamper
evidence is a FACT) and RULE 2 (self-fix routing is a two-strike rule) across every location
named in the task, per standing rulings (A) (rows 12/13/16 open-disclosed is not a finding) and
(B) (no re-litigation of settled rows / FIND-H..V).

## Artifacts read

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (full file, this worktree, 690 lines)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (full file, this worktree, 182 lines)
- `.vcsdd/features/reality-gate/reviews/spec-review-10-delta.md` (prior findings FIND-Z/FIND-AA, under fix)

## RULE 1 — tamper evidence is a FACT — CLEAN, confirms FIND-Z closed

Checked every named location:
- `behavioral-spec.md:225` — REQ-004 taxonomy row: existing-but-unverified `rowHmac` →
  CONTRADICTION `artifact_trail_tampered` → `FAIL`. Correct.
- `behavioral-spec.md:429` — REQ-012 EARS text, the pre-existing-directory case: now reads
  "...yields `FAIL` / `artifact_trail_tampered` per REQ-017, NOT `CANNOT_VERIFY`** (corrected
  iteration 9: an earlier draft of this line said `CANNOT_VERIFY`...)". **This closes FIND-Z**
  (review-10's blocking finding that this exact line still said `CANNOT_VERIFY`) — the sentence
  is now edited and matches `verification-architecture.md:94-100`/`:140` (PROP-048).
- `behavioral-spec.md:604-611` (REQ-016) and `:648-659` (REQ-017 table) both state existing/
  mis-signed rows are CONTRADICTION → `FAIL`, never `CANNOT_VERIFY`. No stale phrasing found.
- `behavioral-spec.md:83` (closure row 12) and `:81` (row 22) — both route pre-staging/forgery
  to `FAIL`/`artifact_trail_tampered`, no stale `CANNOT_VERIFY` routing.
- `verification-architecture.md:44-52` (mirrored taxonomy) and `:94-100`/`:140` (PROP-048 prose
  + table row) — consistent with the above.
- PROP-048 (`verification-architecture.md:140`), PROP-053 (`:146`), PROP-054 (`:147`) all exist,
  Tier 0, `required: true`, each with a bound Tool.

No surviving sentence anywhere routes an existing-but-unverifiable row, or a pre-existing
CSPRNG-named directory, to `CANNOT_VERIFY`. **RULE 1: consistent. FIND-Z genuinely closed.**

(Minor, non-blocking, out of this gate's scope per ruling (B): `behavioral-spec.md:430` labels
this correction "iteration 9" while `verification-architecture.md:99` labels the identical
correction "iteration 8" — a historical-footnote numbering mismatch between the two files, not a
routing-outcome contradiction. Not raised as a finding.)

## RULE 2 — self-fix routing is a two-strike rule — **NOT clean, BLOCKING (FIND-AA only partially fixed)**

- `behavioral-spec.md:359-367` (REQ-010's "AMENDED by REQ-018" paragraph) correctly states the
  two-strike rule and instructs PROP-046 be restated.
- `behavioral-spec.md:373-383` (REQ-010's Acceptance Criteria) **is now fixed**: it explicitly
  says "**FIRST-`CANNOT_VERIFY`**" paths only, followed by "**CORRECTED iteration 9 (FIND-AA):
  this is NOT an unconditional rule... second consecutive `CANNOT_VERIFY`... MUST invoke
  `self-fix.sh`**". This closes the specific contradiction review-10 cited at this location.
- `verification-architecture.md:139` (PROP-046) and `:148` (PROP-055) are mutually consistent
  and both Tier 0 / `required: true`.
- **But `behavioral-spec.md:368-369` — REQ-010's own Edge Cases, four lines above the fixed
  Acceptance Criteria, in the SAME requirement — was never edited** and still reads:
  `"self-fix.sh's own dedupe/staleness logic is unaffected (still applies to the FAIL branch
  only)."` This is exactly the pattern review-10 named for this same finding (FIND-AA) and
  explicitly instructed be fixed ("edit `:368-369` to note the dedupe/staleness carve-out
  applies to the FAIL branch AND to a 2nd-consecutive-CANNOT_VERIFY self-fix call") — that edit
  was not made. The sentence, read as written, asserts self-fix.sh is only ever reached via the
  `FAIL` branch, directly contradicting the "AMENDED by REQ-018" paragraph three lines above it
  and the "FIRST-`CANNOT_VERIFY`"-qualified Acceptance Criteria four lines below it, within the
  identical requirement.

This is the same defect class review-10 itself named ("a new requirement's amendment paragraph
was added without editing every sibling passage that restates the old rule") recurring on the
SAME finding (FIND-AA): the fix was applied to one sibling passage (Acceptance Criteria) and not
the other (Edge Cases) three lines apart.

**BLOCKING.**

## Overall Verdict: **FAIL**

Blocking finding:
- `behavioral-spec.md:368-369` — REQ-010's Edge Cases still states "`self-fix.sh`'s own dedupe/
  staleness logic is unaffected (still applies to the `FAIL` branch only)," an unedited,
  unconditional-framing leftover that contradicts REQ-018's two-strike rule stated immediately
  above it (`:359-367`) and the already-corrected "FIRST-`CANNOT_VERIFY`" Acceptance Criteria
  stated immediately below it (`:373-383`), within the same requirement. Fix: edit `:368-369` to
  read that the dedupe/staleness carve-out applies to the `FAIL` branch AND to the
  2nd-consecutive-`CANNOT_VERIFY` self-fix call (per REQ-018/PROP-055), exactly as review-10's
  FIND-AA instructed. `routeToPhase`: 1b.

RULE 1 is fully consistent everywhere checked (FIND-Z closed). RULE 2 is consistent in three of
four checked locations (REQ-018, PROP-046, PROP-055 all correct) but is contradicted by one
unedited sentence remaining inside REQ-010 itself. This feature is NOT yet ready for Phase 2a.
