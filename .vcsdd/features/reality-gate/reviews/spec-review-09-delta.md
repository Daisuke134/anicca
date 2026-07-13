# VCSDD Adversary — Phase 1c Spec Review (iteration 9, FINAL BOUNDED DELTA REVIEW)

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary, zero context carried over from any prior reviewer.
**Scope discipline**: strictly REQ-017 (FIND-U fix) and REQ-018 (FIND-V fix), just added to close
review-08's two blocking findings. Rows 1-11, 14-23 and previously-confirmed fixes
(FIND-H/I/J/K/L/M/N/O/P/T) are NOT re-litigated, per the standing orchestrator ruling. Row 12's
same-trust-domain limit is accepted as OPEN/disclosed, not re-argued.

## Artifacts read

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (full file, this worktree)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (full file, this worktree)
- `.vcsdd/features/reality-gate/reviews/spec-review-08-delta.md` (full file — FIND-U/FIND-V under fix)

---

## REQ-017 (FIND-U fix)

### Check (a) — is the taxonomy now unambiguous?

**NO — a surviving contradiction remains.** REQ-016's own EARS text, `behavioral-spec.md:583-586`,
is UNCHANGED by this iteration and still reads: "`enforceVerdict` SHALL recompute the HMAC for
every cited row and treat any row that is unsigned, mis-signed, or signed with a different pass's
secret as **not a valid capture** → the verdict cannot reach PASS on it (fail-closed:
`CANNOT_VERIFY` if no valid capture remains; `FAIL` if a valid capture contradicts the claim)."
This sentence, read on its own — and nothing in REQ-016's section is edited to qualify or
supersede it — routes a mis-signed row to the "not a valid capture" bucket, which its OWN
parenthetical resolves to `CANNOT_VERIFY` when no valid capture remains. REQ-017's new ruling
table at `behavioral-spec.md:629` says the opposite for exactly this state ("A row exists and its
HMAC does NOT verify" → `FAIL`/`artifact_trail_tampered`). Two SHALL/MUST-level statements in the
same spec now assign different outcomes to the identical trail state, and REQ-017 never strikes or
amends REQ-016's lines 583-586 to remove the conflicting rule. This is the exact class of gap the
task brief asked me to hunt for, found.

### Check (b) — do PROP-053/054 force the distinction?

Yes, in isolation: `behavioral-spec.md:637-641` marks both `required: true`, both fixture-level
("a trail containing a row whose bytes were modified after signing → FAIL/artifact_trail_tampered
... MUST NOT be CANNOT_VERIFY" / "a trail with NO row at all → CANNOT_VERIFY"). That part of the
fix is sound. But a fixture-level PROP does not resolve a contradiction in the prose it is meant to
be derived from — see (a) and (c).

### Check (c) — contradiction with earlier requirement text?

**YES, BLOCKING, two independent instances:**

1. **REQ-016 vs REQ-017** (detailed in (a) above): `behavioral-spec.md:583-586` (unedited) vs.
   `behavioral-spec.md:629` (new). Same trail state, two different mandated outcomes.
2. **REQ-004's taxonomy table vs REQ-017's own mandate on it.** REQ-017 states, at
   `behavioral-spec.md:633`: "REQ-004's taxonomy MUST carry `artifact_trail_tampered` as a
   first-class CONTRADICTION category." I grepped `behavioral-spec.md` for `tamper` and the ONLY
   three hits outside REQ-017's own new section are line 410 (an unrelated `passId`
   pre-existing-directory case) and REQ-017's own lines 629/633/638 — `artifact_trail_tampered`
   never appears in REQ-004's actual violation table
   (`behavioral-spec.md:207-225`), which the spec elsewhere declares, unedited, to be "a fixed,
   deterministic lookup table... decided once, in this spec" (`behavioral-spec.md:560-562`,
   `verification-architecture.md:27-47` mirrors the same table verbatim and also lacks the row).
   REQ-017 issues a MUST directive against a table it never actually edits. A Builder implementing
   REQ-004 as written — the spec's own declared single source of truth for this exact decision —
   finds no `artifact_trail_tampered` row there at all.

Both are real, line-citable, unresolved contradictions in the spec TEXT (not merely a missing
PROP) — per the task brief's own stated bar, this is BLOCKING.

---

## REQ-018 (FIND-V fix)

### Check (a) — can a loop still be silently-broken-forever?

The POSITIVE-reporting half of the fix is sound: `behavioral-spec.md:651-653` (point 1) now
requires every pass to report its verdict, including `CANNOT_VERIFY`, "never as a post that
happened," and PROP-056 (`behavioral-spec.md:663-664`) forces that framing at the fixture level.
That closes FIND-V's item (ii)/silence gap on its own terms.

But the escalation half (point 2) creates a **new, direct, mechanical contradiction with existing,
unedited, `required: true` text — BLOCKING:**

- `behavioral-spec.md:342-344` (REQ-010, unedited): "WHEN `enforceVerdict` yields
  `overallVerdict: 'CANNOT_VERIFY'`... THE SYSTEM **SHALL NOT** invoke `self-fix.sh` — there is no
  code bug to fix."
- `behavioral-spec.md:362-366` (REQ-010's own Acceptance Criteria, unedited, backing
  `verification-architecture.md:126`'s PROP-046): "...their `CANNOT_VERIFY` paths each contain a
  literal append to the human-review queue and **explicitly NO `self-fix.sh` call** — grep-checkable,
  two distinct code paths (PROP-046)." PROP-046 is `required: true`, Tier 0, and its own
  description in `verification-architecture.md:126` says the `CANNOT_VERIFY` branch "**explicitly
  does NOT call `self-fix.sh`** in that branch."
- `behavioral-spec.md:654-655` (REQ-018, new): "Two consecutive `CANNOT_VERIFY` verdicts for the
  same loop escalate **exactly like `FAIL`** — to `self-fix.sh`."
- `behavioral-spec.md:357` (REQ-010 edge case, unedited): "`self-fix.sh`'s own dedupe/staleness
  logic is unaffected (**still applies to the `FAIL` branch only**)."

REQ-018 requires the `CANNOT_VERIFY` code path to call `self-fix.sh` under a specific condition
(2nd consecutive occurrence). REQ-010's text and its `required: true` PROP-046 both mandate,
unconditionally, that the `CANNOT_VERIFY` branch NEVER calls `self-fix.sh`. As written, it is
IMPOSSIBLE to satisfy both PROP-046 and PROP-055 simultaneously — PROP-046's own grep-level check
("explicitly NO self-fix.sh call" in the CANNOT_VERIFY path) would fail against any implementation
that satisfies REQ-018. REQ-018 never edits REQ-010's EARS text, Acceptance Criteria, or edge-case
sentence to carve out the 2-consecutive exception. This is not a missing PROP — it is two
`required: true` proof obligations in direct, mechanical opposition.

### Check (b) — is the 2-strike escalation forced by a fixture-level PROP?

Yes on its own terms: PROP-055 (`behavioral-spec.md:661-662`) is fixture-level and required.
(This does not cure the contradiction in (a) — it is itself one half of that contradiction.)

### Check (c) — is the streak counter gameable?

No concrete exploit found. `self-fix.sh` already fires unconditionally on any genuine `FAIL`
(REQ-010, unaffected by this iteration), so a loop cannot "reset" the counter by alternating
`CANNOT_VERIFY` with a fabricated `FAIL` without also triggering the escalation it would be trying
to avoid; and reaching a genuine `PASS` between `CANNOT_VERIFY`s requires defeating the entire
provenance backstop honestly, which is not gaming — it is a real verified post. Non-blocking note
only: REQ-018 never states what event resets the streak counter (any non-`CANNOT_VERIFY` verdict?
only two-or-more?), which is a completeness gap worth closing in the same edit that resolves (a),
but I found no exploitable path through it and do not raise it as blocking on its own.

---

## Additional finding — new PROPs have no home in verification-architecture.md

`verification-architecture.md`'s Proof Obligations table runs only to PROP-048
(`verification-architecture.md:110-129`). I grepped the file for `PROP-04[9]`, `PROP-05[0-6]`, and
`REQ-016|REQ-017|REQ-018`: **zero matches, all patterns.** REQ-016/017/018's `required: true`
PROPs (049-056, including this iteration's PROP-053/054/055/056) have no Tier/Tool/Path row in the
document this project's own convention uses to bind every other required PROP to a verification
mechanism (see, e.g., PROP-047's own row, added specifically because FIND-P demanded exactly this
binding for a different requirement). This is not merely stale bookkeeping: without a Tier/Tool
assignment, nothing tells a Builder whether PROP-053 (the row-tampering fixture) is unit-tested in
`node:test`/`fast-check` alongside the other pure-function PROPs, or requires the live/manual tier
REQ-016's HMAC-secret-channel work implies. In-scope because it directly concerns the two
requirements under review in this iteration.

---

## Dimension verdicts (this delta's scope only)

| Dimension | Verdict | Basis |
|---|---|---|
| spec_fidelity | **FAIL** | REQ-017 issues a MUST against REQ-004's taxonomy table (`behavioral-spec.md:633`) without ever editing that table (`behavioral-spec.md:207-225`, `verification-architecture.md:27-47`) to contain the mandated row. |
| edge_case_coverage | **FAIL** | The exact FIND-U attack state (row exists, HMAC invalid) is assigned two different outcomes by two different unedited/new SHALL clauses (REQ-016 line 585 vs REQ-017 line 629) — the taxonomy this spec claims is deterministic is not, for this state. |
| implementation_correctness | **FAIL** | A Builder implementing REQ-018 exactly as written (2nd-consecutive CANNOT_VERIFY → self-fix.sh) necessarily violates PROP-046's own required, grep-checkable assertion that the CANNOT_VERIFY branch never calls self-fix.sh — the two required specs cannot both be satisfied by one implementation. |
| structural_integrity | **FAIL** | REQ-017/018 were bolted onto REQ-004/REQ-010/PROP-046 without integrating with or amending their existing, still-authoritative text — the same defect class review-08 flagged against REQ-016's original addition (FIND-U itself), now recurring in the very requirements meant to fix it. |
| verification_readiness | **FAIL** | PROP-053/054/055/056 (all `required: true`) have zero entry in `verification-architecture.md`'s proof-obligation table — no Tier/Tool binding exists for any of them. |

## Findings (this delta)

- **FIND-W (BLOCKING)** — REQ-017 contradicts REQ-016's own unedited text (`behavioral-spec.md:
  583-586` says a mis-signed row is "not a valid capture" → `CANNOT_VERIFY` if none remain;
  `behavioral-spec.md:629` says the same state → `FAIL`), AND REQ-017 mandates a change to REQ-004's
  taxonomy table (`behavioral-spec.md:633`) that was never actually made to the table
  (`behavioral-spec.md:207-225`; also absent from `verification-architecture.md:27-47`'s mirrored
  copy). Fix: edit REQ-016's lines 583-586 to explicitly carve out "structurally-present,
  signature-invalid" as its own case pointing to REQ-017's ruling (removing the conflicting
  `CANNOT_VERIFY`-if-none-remain language for that specific case), and add the
  `artifact_trail_tampered` row directly into REQ-004's table in both `behavioral-spec.md` and
  `verification-architecture.md`. `routeToPhase`: 1b.
- **FIND-X (BLOCKING)** — REQ-018's 2-consecutive-`CANNOT_VERIFY`-escalates-to-`self-fix.sh` rule
  (`behavioral-spec.md:654-655`) directly contradicts REQ-010's unconditional "SHALL NOT invoke
  self-fix.sh" on `CANNOT_VERIFY` (`behavioral-spec.md:342-344`), its Acceptance Criteria's
  "explicitly NO self-fix.sh call" (`behavioral-spec.md:362-366`), the still-standing "dedupe/
  staleness logic... still applies to the FAIL branch only" edge case (`behavioral-spec.md:357`),
  and `verification-architecture.md:126`'s PROP-046 (`required: true`), which grep-checks that the
  `CANNOT_VERIFY` branch never calls `self-fix.sh`. As written, no single implementation can satisfy
  both PROP-046 and PROP-055. Fix: amend REQ-010's EARS text, Acceptance Criteria, and edge case,
  plus PROP-046's own description in `verification-architecture.md`, to carve out the
  2nd-consecutive-`CANNOT_VERIFY` exception explicitly, so PROP-046 and PROP-055 test compatible
  behavior. `routeToPhase`: 1b.
- **FIND-Y (BLOCKING)** — PROP-049 through PROP-056 (REQ-016/017/018, all `required: true`) have no
  row in `verification-architecture.md`'s Proof Obligations table (verified by grep: zero matches
  for `PROP-04[9]`, `PROP-05[0-6]`, `REQ-016|REQ-017|REQ-018` in that file). No Tier/Tool is bound
  to any of them, unlike every other required PROP in this spec (cf. PROP-047's row, added for
  exactly this reason after FIND-P). Fix: add rows for PROP-049..056 to
  `verification-architecture.md`'s table before this feature proceeds past Phase 1c.
  `routeToPhase`: 1b.

No other new blocking or major findings within the granted scope. REQ-018's positive-reporting
requirement (point 1, PROP-056) and its streak-gaming resistance (check c) are sound as written.

---

## Overall Delta Verdict: **FAIL**

Blocking findings:
1. **FIND-W** — REQ-017 contradicts REQ-016's still-standing text and never actually edits REQ-004's
   taxonomy table it claims to amend.
2. **FIND-X** — REQ-018's escalation rule is mechanically incompatible with REQ-010's unedited
   "SHALL NOT"/PROP-046's required grep-check.
3. **FIND-Y** — REQ-017/018's four new required PROPs (053-056) are absent from
   `verification-architecture.md` entirely.

0 findings outside this delta's granted scope (REQ-017/REQ-018 only); rows 1-11, 14-23 and prior
confirmed fixes were not re-litigated.
