# VCSDD Adversary — Phase 1c Spec Review (iteration 10, CONSISTENCY GATE CHECK)

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary, zero context carried over from any prior reviewer.
**Scope discipline**: bounded to review-09's 3 blocking findings (FIND-W/X/Y, REQ-016/017/018
internal consistency) plus a sweep for NEW contradictions introduced by their fixes. Rows 1-11,
14-23 (excl. 22/23's own text touched here), row 12's open/disclosed status, and all
previously-confirmed fixes are NOT re-litigated, per standing rulings (A) and (B).

## Artifacts read

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (full file, this worktree, 680 lines)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (full file, this worktree, 182 lines)
- `.vcsdd/features/reality-gate/reviews/spec-review-09-delta.md` (full file, findings under fix)

---

## (1) Tampered-row taxonomy — CLEAN, all four sub-checks pass

- (a) `behavioral-spec.md:225` — REQ-004's taxonomy table now carries the row: `**Row exists in
  the trail but its rowHmac is absent, mis-signed, or signed with another pass's secret
  (REQ-016/017)** | **CONTRADICTION (artifact_trail_tampered)** ... | **FAIL**`. Present and
  correctly classed.
- (b) `verification-architecture.md:44-52` mirrors it: an explicit `CONTRADICTION
  (artifact_trail_tampered) — new, REQ-016/017, iteration 8 (FIND-U)` bullet under
  `validateArtifactProvenance`'s documented taxonomy, forced by PROP-053/PROP-054.
- (c) `behavioral-spec.md:594-601` (REQ-016) no longer says "not a valid capture →
  CANNOT_VERIFY" for a mis-signed row. It now reads: "**A row that EXISTS but whose HMAC does
  not verify ... is NOT 'a missing capture' — it is positive evidence of trail tampering and
  SHALL yield FAIL / artifact_trail_tampered ... this supersedes any earlier 'not a valid
  capture → CANNOT_VERIFY' reading of this requirement.**" The prior contradiction (review-09's
  FIND-W part 1) is gone — REQ-016's own text was edited, not merely overridden by REQ-017
  elsewhere.
- (d) PROP-053 (`verification-architecture.md:146`) and PROP-054 (`:147`) both exist, Tier 0,
  `required: true`, each with a bound Tool column (`node fixture: sign a row, mutate a byte, run
  enforceVerdict` / `node fixture over enforceVerdict`).

No surviving path where an existing-but-unverifiable row yields `CANNOT_VERIFY`. Review-09's
FIND-W is genuinely closed.

---

## (2) self-fix routing — **NOT clean, BLOCKING**

- (a) REQ-010's unconditional rule is only **partially** amended. `behavioral-spec.md:359-367`
  adds an explicit "AMENDED by REQ-018" paragraph stating the correct two-strike rule and
  instructing "PROP-046 MUST be restated as 'a single, first CANNOT_VERIFY does not call
  self-fix'". `verification-architecture.md:139` correctly carries out that restatement for
  PROP-046 itself. **But `behavioral-spec.md:373-377` — REQ-010's own Acceptance Criteria,
  a few lines below the amendment paragraph, in the SAME requirement — was never edited** and
  still reads: "...their `CANNOT_VERIFY` paths each contain a literal append to the human-review
  queue and **explicitly NO `self-fix.sh` call** — grep-checkable, two distinct code paths
  (PROP-046)." This is unconditional, names PROP-046 by name, and directly contradicts both the
  paragraph immediately above it and `verification-architecture.md:139`'s restated PROP-046.
  `behavioral-spec.md:368-369`'s edge case — "`self-fix.sh`'s own dedupe/staleness logic is
  unaffected (still applies to the `FAIL` branch only)" — is also unedited and reinforces the
  same stale, unconditional reading.
- (b) PROP-055 exists (`verification-architecture.md:148`), Tier 0, `required: true`, bound tool
  "bash/node fixture asserting the escalation call."
- (c) **Not jointly satisfiable as specified.** `verification-architecture.md`'s own two rows
  (PROP-046 restated at `:139`, PROP-055 at `:148`) ARE mutually consistent with each other. The
  contradiction is that `behavioral-spec.md:373-377` — REQ-010's normative Acceptance Criteria,
  the text a Builder implements REQ-010 against — was never brought into line with the
  restatement its own sibling paragraph (`:365-366`) mandates. A Builder implementing
  `behavioral-spec.md:373-377` literally ("explicitly NO self-fix.sh call" in the CANNOT_VERIFY
  branch, unconditionally) necessarily fails PROP-055's required fixture (2nd-consecutive
  CANNOT_VERIFY → self-fix escalation). This is the identical defect class review-09 found
  (FIND-X) — narrowed (verification-architecture.md's own table is now internally consistent)
  but NOT eliminated, because the source-of-truth requirement text in behavioral-spec.md still
  contains the unedited, contradicting sentence.

**BLOCKING.**

---

## (3) Obligations-table binding — CLEAN

PROP-049 through PROP-056 all have rows in `verification-architecture.md`'s Proof Obligations
table, each with Tier, Required, and Tool columns populated:
- PROP-049 `:142`, PROP-050 `:143`, PROP-051 `:144`, PROP-052 `:145`, PROP-053 `:146`,
  PROP-054 `:147`, PROP-055 `:148`, PROP-056 `:149` — all Tier 0, all `required: true`, all with
  a named Tool (node fixture / grep+static check / node fixture over the report renderer).

Review-09's FIND-Y is genuinely closed.

---

## (4) New-contradiction sweep — **NOT clean, BLOCKING (new finding)**

The pre-existing-artifact-directory rule was supposed to move uniformly from `CANNOT_VERIFY` to
`FAIL`/`artifact_trail_tampered`. It was changed in ONE of its two locations only:

- `verification-architecture.md:94-100` (PROP-048's own prose) states the corrected rule
  explicitly, and even flags its own prior draft as wrong: "**A pre-existing directory at a
  freshly-drawn 128-bit CSPRNG name cannot be a collision or a stale leftover ... this yields
  `FAIL` / `artifact_trail_tampered`, NOT `CANNOT_VERIFY`** (corrected iteration 8 — an earlier
  draft of this line said `CANNOT_VERIFY`...)." `verification-architecture.md:140`'s PROP-048
  table row matches: "...MUST cause the run to yield `FAIL` / `artifact_trail_tampered` (NOT
  `CANNOT_VERIFY`...)."
- **`behavioral-spec.md:420-422` — REQ-012's own EARS text, the "earlier draft" the
  verification-architecture.md comment refers to — was never updated to match.** It still reads:
  "The artifact-trail directory MUST additionally be created with an EXCLUSIVE create that fails
  if it already exists; a pre-existing directory is tamper evidence → **`CANNOT_VERIFY`**, never
  reuse, never PASS."

Same event (exclusive-create fails because the directory already exists at a fresh 128-bit
CSPRNG name), two directly opposite mandated outcomes in the spec's own two files —
`behavioral-spec.md:421` says `CANNOT_VERIFY`, `verification-architecture.md:97-98`/`:140` says
`FAIL`/`artifact_trail_tampered`. `verification-architecture.md` is explicitly self-aware that
this is a correction from an earlier `CANNOT_VERIFY` draft, which means the fix was applied to
the verification-architecture side of the pair and never propagated back to
`behavioral-spec.md`'s REQ-012 — a Builder reading REQ-012's own EARS text (the requirement
text, not the verification-architecture commentary) would wire the exclusive-create failure to
`CANNOT_VERIFY`, silently handing a watching/racing loop exactly the soft, non-escalating
outcome PROP-048 was written to deny it.

**BLOCKING.**

**Legitimate non-adversarial pre-existing-directory scenario — none found.** `passId` is
generated fresh, internally, per invocation (`behavioral-spec.md` REQ-005/REQ-012); nothing in
the spec persists or reuses a previously-generated `passId` across retries or crash-resumption,
so a legitimate retry or a resumed crashed run would draw a NEW 128-bit value, not reuse the old
directory name. I found no described or inferable path by which two legitimate invocations
would collide on the same CSPRNG-derived directory name (collision probability negligible at
128 bits). This part of the FAIL classification is sound in principle — the defect is purely
that `behavioral-spec.md:421` was not edited to say so.

---

## Dimension verdicts (this delta's scope only)

| Dimension | Verdict | Basis |
|---|---|---|
| spec_fidelity | **FAIL** | `behavioral-spec.md:421` (REQ-012) still mandates `CANNOT_VERIFY` for a case `verification-architecture.md:97-98`/`:140` (PROP-048) explicitly, self-referentially corrects to `FAIL`/`artifact_trail_tampered`. |
| edge_case_coverage | **FAIL** | The exact pre-staged-directory edge case is assigned two different outcomes by the spec's two companion documents. |
| implementation_correctness | **FAIL** | A Builder implementing REQ-010's own Acceptance Criteria (`behavioral-spec.md:373-377`) as written necessarily violates PROP-055's required 2-strike-escalation fixture. |
| structural_integrity | **FAIL** | Both surviving contradictions are the same defect class as review-08/09 repeatedly found: a new requirement's amendment paragraph was added without editing every sibling passage (Acceptance Criteria, edge case, or companion document) that restates the old rule. |
| verification_readiness | **PASS** | PROP-049..056 are now fully bound (Tier/Required/Tool) in `verification-architecture.md`'s Proof Obligations table; no obligation from this delta's scope is left unbound. |

## Findings (this delta)

- **FIND-Z (BLOCKING)** — `behavioral-spec.md:420-422` (REQ-012's EARS text: pre-existing
  artifact-trail directory → `CANNOT_VERIFY`) contradicts `verification-architecture.md:94-100`
  and `:140` (PROP-048: the identical event → `FAIL`/`artifact_trail_tampered`, explicitly noted
  as a correction from an earlier `CANNOT_VERIFY` draft). Fix: edit `behavioral-spec.md:421` to
  read `→ FAIL / artifact_trail_tampered` (matching REQ-017's principle and PROP-048's already-
  corrected description), removing the word `CANNOT_VERIFY` from that sentence. `routeToPhase`: 1b.
- **FIND-AA (BLOCKING)** — `behavioral-spec.md:373-377` (REQ-010's own Acceptance Criteria: "...
  their `CANNOT_VERIFY` paths each contain ... explicitly NO `self-fix.sh` call ... (PROP-046)")
  is unconditional and contradicts (i) the "AMENDED by REQ-018" paragraph immediately above it at
  `behavioral-spec.md:359-367`, which instructs PROP-046 be restated with a two-strike exception,
  and (ii) `verification-architecture.md:139`'s own restated PROP-046, which already carries that
  exception. `behavioral-spec.md:368-369`'s edge case ("dedupe/staleness logic ... still applies
  to the FAIL branch only") independently reinforces the same stale, unconditional reading. Fix:
  edit `behavioral-spec.md:373-377` to state the CANNOT_VERIFY path calls `self-fix.sh` on the
  2nd consecutive occurrence for the same loop (never on the first), and edit `:368-369` to note
  the dedupe/staleness carve-out applies to the FAIL branch AND to a 2nd-consecutive-CANNOT_VERIFY
  self-fix call. `routeToPhase`: 1b.

No other new blocking or major findings within the granted scope. Check (1) (tampered-row
taxonomy) and check (3) (PROP-049..056 obligations-table binding) are both genuinely, fully
resolved — review-09's FIND-W and FIND-Y are closed. Check (2)'s core mechanism
(`verification-architecture.md`'s own PROP-046/PROP-055 pair) is now internally consistent; only
`behavioral-spec.md`'s own REQ-010 text was left stale. Check (4) surfaces one new contradiction
that review-09 could not have found (it did not exist at iteration 9 — PROP-048's text was
already corrected by iteration 8, but review-09's scope was bounded to REQ-017/REQ-018 and did
not re-sweep REQ-012).

0 findings outside this delta's granted scope (REQ-016/017/018 internal consistency + the fixes'
own new-contradiction sweep); rows 1-11, 14-21, row 12's open-disclosed status, and prior
confirmed fixes were not re-litigated.

---

## Overall Delta Verdict: **FAIL**

Blocking findings:
1. **FIND-Z** — REQ-012's own EARS text (`behavioral-spec.md:421`) still says `CANNOT_VERIFY` for
   the pre-existing-directory case that `verification-architecture.md` already corrected to
   `FAIL`/`artifact_trail_tampered`.
2. **FIND-AA** — REQ-010's own Acceptance Criteria (`behavioral-spec.md:373-377`) still states an
   unconditional "no self-fix.sh on CANNOT_VERIFY" rule that contradicts REQ-018's required
   two-strike escalation and `verification-architecture.md:139`'s already-restated PROP-046.

Both are real, line-citable, in-scope contradictions surviving (or newly exposed by) the
iteration-9 fix cycle — not merely missing PROPs, not out-of-scope, and not a re-litigation of
row 12's disclosed same-trust-domain limit. This feature is NOT yet ready for Phase 2a.
