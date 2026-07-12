# VCSDD Adversary — Phase 1c Spec Review (iteration 7, BOUNDED DELTA REVIEW)

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary, zero context carried over from iteration 6's reviewer.
**Scope discipline**: strictly the FIND-Q fix, the FIND-R fix, and their regression surface, per
the task brief. I did not re-litigate FIND-M/N/O/P's own closure (already independently
reconfirmed in `reviews/spec-review-06.md`) or any of rows 1-21/23.

## Artifacts read

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (full file, this worktree)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (full file, this worktree)
- `.vcsdd/features/reality-gate/reviews/spec-review-06.md` (full file — the findings under fix)
- `/Users/anicca/anicca/skills/self/reality-verify-spawn.sh` (ground truth — confirms CURRENT
  implementation is still the pre-fix, detached-tmux, no-passId-namespacing version; the
  behavioral-spec.md fix described below has not been implemented yet, as expected for Phase 1c)
- `/Users/anicca/anicca/skills/earn/gig/gig_reality_verify.sh` (ground truth — re-confirmed
  `PASS_ID="realityverify-$(date +%s)-$$"` at line 103, the precedent scheme this iteration's
  spec explicitly now forbids for reality-gate)
- `/Users/anicca/anicca/skills/self/self-fix.sh` (ground truth — confirms REQ-010's
  `self-fix.sh <loop> <blocker>` call shape is unaffected by this iteration's diff)

No manifest scaffold exists for this scope (matches the convention iterations 1-6 already used —
flat markdown files under `reviews/`, no `input`/`output` split). Reviewed directly against the
task brief.

---

## Item 1 — FIND-Q fix (`passId` unpredictability + tamper evidence)

**(a) CSPRNG requirement stated as a MUST, time+PID explicitly forbidden** — CONFIRMED.
`behavioral-spec.md:405-407` (REQ-012): "the value MUST be CSPRNG-derived (>= 128 bits entropy),
NOT time+PID-derived: a `$(date +%s)-$$` scheme is predictable by the calling loop... and would
leave closure row 22's pre-staging attack OPEN." `verification-architecture.md:78-84`
(`reality-verify-spawn.sh` effectful-shell entry): "A time+PID scheme
(`realityverify-$(date +%s)-$$`) is **REJECTED and forbidden**... Instead, `passId` MUST be drawn
from a CSPRNG (e.g. `openssl rand -hex 16` / `uuidgen`, >= 128 bits of entropy)." PROP-048(a)
(`verification-architecture.md:127`): "a time+PID-derived value is a test FAILURE (a fixture
that predicts `realityverify-$(date +%s)-$$` and finds it honored must fail the suite)." This is
a hard MUST/forbidden, not a preference — genuinely stated.

**(b) Exclusive-create requirement real; pre-existing directory genuinely fails closed** —
CONFIRMED. `behavioral-spec.md:408-411`: "The artifact-trail directory MUST additionally be
created with an EXCLUSIVE create that fails if it already exists... a pre-existing directory is
tamper evidence → `CANNOT_VERIFY`, never reuse, never PASS." `verification-architecture.md:85-88`
names the mechanism explicitly (`mkdir` without `-p`) and the same fail-closed rule. PROP-048(b)
(`verification-architecture.md:127`): a fixture that pre-creates the directory "MUST cause the
run to fail-closed with `CANNOT_VERIFY`, never to reuse the directory and never to PASS."
Genuinely specified and required.

**(c) PROP-048 forces both properties, required** — CONFIRMED. `verification-architecture.md:127`,
Tier 0, `Required: true`, two named assertions (a) entropy, (b) exclusive-create + fail-closed
reuse test. Both are the direct, mechanical proof of (a) and (b) above.

**(d) Can I still construct a pre-staging/forgery attack? YES — BLOCKING, new evidence.**

The fix closes the *prediction* vector (guessing the passId in advance via `$!`+`date +%s`) and
the *pre-creation* vector (writing into the directory before it exists). It does **not** close a
third, distinct vector: **observe-then-race**, using only capabilities the spec's own FIND-N/Q
disposition already grants the loop under test ("a Bash-capable growth-engine loop... already a
granted capability for any autonomous cron loop in this codebase," quoted verbatim in
`reviews/spec-review-06.md:114-117`).

Concrete sequence:
1. Before calling `reality-verify-spawn.sh`, the loop under test backgrounds a filesystem watcher
   on the artifact-trail parent directory (e.g. `fswatch`/`inotifywait -m
   "$HOME/.openclaw/state/reality-artifacts"`, or even a tight `while true; do ls ...; done`
   poll) — a trivial, cheap capability for any Bash-capable cron loop, and orthogonal to whether
   `reality-verify-spawn.sh` itself is invoked blocking or backgrounded (REQ-005's "run to
   COMPLETION, blocking" constrains the SCRIPT's own internal behavior; nothing in REQ-005/012
   constrains what OTHER background jobs the *caller* may run concurrently while waiting).
2. The loop calls `reality-verify-spawn.sh` (foreground or backgrounded, either way).
3. `reality-verify-spawn.sh` generates the CSPRNG `passId` and performs the exclusive `mkdir`.
   The **moment that `mkdir` succeeds**, the directory name (= the passId) becomes visible on the
   filesystem — this is an unavoidable side effect of using a plain, world-readable-by-the-same-
   user directory as the tamper-evidence mechanism. The watcher fires within milliseconds.
4. The watcher immediately (same OS user, full read/write access — nothing in
   `behavioral-spec.md`'s NFR section or `verification-architecture.md`'s purity-boundary map
   restricts filesystem permissions, chmod, or ownership on `.../reality-artifacts/<passId>/` to
   exclude the loop under test) writes a fabricated row into
   `.../reality-artifacts/<passId>/artifacts.jsonl` — `{ts: now, passId: <the-real-one>, seq: 1,
   label: ..., tool: "public_artifact_snapshot", requestedUrl: <the-loop's-own-claimed-URL>,
   finalUrl: <same>, httpStatus: 200, domExcerpt: "<fabricated>", contentHash: <matches
   loop-controlled precommit fingerprint>}` — a row indistinguishable, on every structural field
   REQ-004's taxonomy checks (`tool`, `passId`/`ts` freshness, `requestedUrl` membership,
   `httpStatus`, `contentHash`), from a row the REAL `public_artifact_snapshot.py` would have
   written, because **nothing in the schema cryptographically ties a row to having actually been
   produced by real network I/O** — `tool` is a free-text field the forger sets to the exact
   expected string, `contentHash` is a hash the forger can compute over content it invented, and
   the taxonomy (`behavioral-spec.md:207-225`) validates SHAPE and MEMBERSHIP, never PROVENANCE-
   of-authorship.
5. The genuine `reality-verifier` spawn (an LLM agent that must start up, read its prompt, and
   perform real navigation before writing anything) is structurally slower than a filesystem-
   event-triggered shell one-liner — the forged row has a comfortable head start, and even if it
   didn't, `enforceVerdict`'s citation-resolution logic (REQ-004's table) has no rule that prefers
   "verifier-authored" rows over "any row matching by passId/seq" — there is no seq-uniqueness-
   per-authorship or per-process authentication anywhere in the spec.

This is not a re-run of the closed row-22 threat (guess-in-advance) and not row 12 (the
*verifier* forging its own evidence, explicitly the only actor row 12's disclosure names — see
`behavioral-spec.md:83`, "this row covers only an adversarial VERIFIER forging evidence live
during its own run"). It is a **third variant of the exact actor row 22 was written to stop (the
loop under test)**, using a mechanically different vector (filesystem-event observation +
same-user write access, not prediction). The spec's own stated policy —
"`behavioral-spec.md:56`: 'A future review that finds a 24th path has found a spec defect'" —
applies directly: I found a path this closure table does not enumerate at all, under either row
12 or row 22.

`routeToPhase`: 1b. Concrete fixes, any one of: (a) do not use a same-permission,
same-user-writable plain directory as the sole tamper-evidence surface — restrict write access to
the artifact-trail directory (e.g. a directory created with a mode that excludes the invoking
loop's own write capability, or a directory the capture tool alone can write via a distinct
credential/socket); (b) have `public_artifact_snapshot.py` write with an append-only, per-row
authentication tag (e.g. an HMAC keyed by a secret only the capture tool process holds, verified
by `validateArtifactProvenance`) so a filesystem-level forgery is structurally detectable even
with full read/write access to the directory; (c) at minimum, narrow the closure claim for row 22
to what is actually proven ("not caller-*predictable* in advance," not "cannot be forged by a
same-user process observing directory creation") and open a new, explicitly disclosed row for
this vector, matching the honesty standard row 12/13/16 already set.

---

## Item 2 — FIND-R fix (PROP-047 scope widened to both callers)

`verification-architecture.md:128-129` (PROP-047's own table row) **is** genuinely, explicitly
updated: "Path: (i)+(ii) — BOTH callers' source files (FIND-R fix, iteration 7): the VCSDD gate
script AND `skills/self/reality-verify-spawn.sh`, the runtime path... 'ONE module, TWO callers'
must be proven on both callers or it is proven on neither," and "Description: a mechanical,
grep-level static check scans **each caller's** source... asserts ZERO matches." `Required: true`
is retained.

However, `behavioral-spec.md:512-520` — **REQ-014's own acceptance-criteria bullet, the actual
EARS requirement text a Builder implements against, quoted in full**:

> "a grep-level, mechanical (not judgment-based — bookkeeping, per the coordinator's own framing)
> static check, run as part of this feature's own test suite, scans **the gate script's source
> file** for definitions (not calls) of any of: `canonicalizeUrl`, `validateArtifactProvenance`,
> `enforceVerdict`, `computeContentFingerprint`, `hashRealityClaim`, `decideConvergenceGate`, or
> any function containing `httpStatus`/`referencedArtifactIds`/`contentHash` comparison logic
> OUTSIDE of `reality-verdict-schema.mjs`, and asserts ZERO such definitions exist in **the gate
> script (or anywhere outside `reality-verdict-schema.mjs`)** — `required: true` (PROP-047)."

**This is byte-for-byte the same text `reviews/spec-review-06.md:174-176` already flagged as
"internally ambiguous about scope... two different scopes stated in the same sentence"** (there:
cited as `behavioral-spec.md:506-514`; the line numbers shifted because of other edits, the
content did not change at all). `reality-verify-spawn.sh` is not named anywhere in this bullet.
The bullet still literally says "scans the gate script's source file," with the ambiguous
parenthetical "(or anywhere outside `reality-verdict-schema.mjs`)" that a Builder could
(as iteration 6 already found, and this iteration re-confirms unchanged) reasonably read either
way — and the narrower reading is exactly the one iteration 6 demonstrated PROP-047 actually
implemented at the time.

**This is BLOCKING.** The fix was applied to `verification-architecture.md`'s proof-obligation
table only. `behavioral-spec.md` — the document my own review instructions and this project's
own convention name "the authoritative specification" — was not touched by this iteration's diff
for REQ-014's acceptance criteria at all, and it still contains the exact ambiguity FIND-P/FIND-R
were scoped to close. A Builder implementing strictly from REQ-014's own acceptance-criteria text
(the normal, expected reading order — EARS requirements first, verification architecture as
elaboration) would reasonably reproduce the path-(i)-only static check FIND-R was raised
specifically to widen, because the requirement text they are implementing against never says
"both callers" or names `reality-verify-spawn.sh`.

`routeToPhase`: 1b. Update `behavioral-spec.md:512-520`'s bullet to explicitly name both caller
source files (the gate script AND `skills/self/reality-verify-spawn.sh`) by path, replacing the
ambiguous "(or anywhere outside `reality-verdict-schema.mjs`)" parenthetical with the same
explicit "(i)+(ii), both callers" language `verification-architecture.md:128` now correctly uses,
so the two documents agree and a Builder reading either one gets the same, unambiguous scope.

---

## Item 3 — Regression: does the new "pre-existing directory ⇒ `CANNOT_VERIFY`" trigger become a
new escape hatch for a lying loop to dodge `FAIL`?

**Answer: not as a standalone weaponization of THIS specific new trigger — the unpredictability
property (Item 1(a)/(b), taken at face value in isolation from Item 1(d)'s race) makes the
pre-existing-directory condition itself something the loop under test cannot deliberately,
repeatably engineer.** Reasoning:

1. To weaponize the new rule, the loop would need to pre-create a directory at the EXACT passId
   `reality-verify-spawn.sh` is about to generate, before the script's own `mkdir` runs. With a
   genuine ≥128-bit CSPRNG (per Item 1(a)/(b)'s citations), this requires guessing a 128-bit
   value in advance — infeasible, unlike the closed `date+PID` scheme. So the loop cannot cause
   *this specific* trigger to fire on demand, in the way it previously could (pre-iteration-7)
   engineer a `FAIL` or forge a `PASS` via the predictable scheme.
2. Even granting the trigger fired, `CANNOT_VERIFY` is subject to every existing anti-laundering
   guarantee `reviews/spec-review-06.md`'s "Row-1 `CANNOT_VERIFY` judgment" already independently
   verified and this iteration's diff does not touch: it blocks convergence exactly as `FAIL`
   does (`behavioral-spec.md:319-323`, REQ-008's `verdict: "FAIL"` + `details.enforcementOutcome`
   mapping), is never reportable as verified success (`behavioral-spec.md:351-356`, REQ-010's
   hard SHALL NEVER), and is never deduplicated or suppressed — repeated `CANNOT_VERIFY` rows for
   the same loop "accumulate," explicitly not hidden (`behavioral-spec.md:357-361`). A loop gains
   nothing toward "shipping" by triggering this path, and the recurrence itself is durable, visible
   signal (REQ-006's trail records every outcome, `behavioral-spec.md:292-294`; REQ-010's
   human-review queue is append-only).
3. **The one place this DOES connect to a live escape hatch is Item 1(d)'s race vector, not the
   pre-existing-directory rule itself.** A loop that can win the observe-then-race described above
   does not need to "weaponize `CANNOT_VERIFY`" at all — it can go straight for a forged `PASS`
   (inject a row with clean, matching structural fields) or, if it prefers to look merely
   "unlucky" rather than caught, inject a `capture_network_error`/`capture_empty_body` sentinel
   row to manufacture `CANNOT_VERIFY` on demand and hide behind "the platform just isn't provable
   yet" indefinitely. This second option **is** a real, live escape hatch — but it is a
   consequence of Item 1(d)'s unresolved gap (same-user write access to the artifact-trail
   directory), not of the new pre-existing-directory rule in isolation. I am not double-counting
   it as a separate blocking finding; it is additional evidence for Item 1(d)'s severity and is
   noted here because the task explicitly asked me to trace this connection.

**Conclusion**: the new trigger, evaluated on its own terms as specified (assuming the entropy
property holds unconditionally), is not a live escape hatch. It becomes one only through Item
1(d)'s already-blocking race gap, which is the real defect to fix — fixing Item 1(d) (e.g. via
write-access restriction or per-row authentication) closes both problems at once.

---

## Dimension verdicts (this delta's scope only)

| Dimension | Verdict | Basis |
|---|---|---|
| spec_fidelity | **FAIL** | Item 2: `behavioral-spec.md:512-520`'s own REQ-014 acceptance-criteria text was not updated to match `verification-architecture.md`'s claimed "both callers" scope for PROP-047 — the two spec documents disagree, and the authoritative one still carries the previously-flagged ambiguity verbatim. |
| edge_case_coverage | **FAIL** | Item 1(d): the observe-then-race vector (filesystem-event detection of the exclusive-`mkdir` + same-user write access to the artifact-trail directory) is an edge case within the loop-under-test's already-granted Bash capability that the spec's threat-model table (closure rows 12/22) does not enumerate at all — the spec's own stated policy ("a future review that finds a 24th path has found a spec defect," `behavioral-spec.md:56`) is directly triggered. |
| implementation_correctness | **FAIL** | Same as above — a Builder implementing REQ-012/PROP-048 exactly as specified produces a `passId` scheme that resists prediction and pre-creation but not observation+race, so the "structurally... never predicted" / "makes guessing infeasible" claims (`behavioral-spec.md:405-407`, `verification-architecture.md:78-88`) remain partly unsupported by the mechanism actually specified. |
| structural_integrity | **FAIL** | Item 2 — internal inconsistency between `behavioral-spec.md` and `verification-architecture.md` for the same acceptance criterion (PROP-047) is a structural defect: two documents that must agree do not. |
| verification_readiness | **FAIL** | Item 1(d): no proof obligation (PROP-048 or otherwise) exercises the observe-then-race path — the required fixture only pre-creates the directory BEFORE spawn (`verification-architecture.md:127`, PROP-048(b)), never AFTER, so the actual live vector is untested even once the entropy/exclusive-create fix ships. |

## Findings (this delta)

- **FIND-S (BLOCKING, new this iteration)** — FIND-Q's fix (CSPRNG entropy + exclusive-create)
  defeats *prediction* and *pre-creation* of `passId` but not *observe-then-race*: a Bash-capable
  loop under test can watch `.../reality-artifacts/` for the exclusive `mkdir`'s completion (a
  necessarily-visible filesystem event, since no permission restriction is specified anywhere for
  this directory) and, within the same-user write access nothing in the spec's NFR section
  restricts, immediately write a forged, structurally-indistinguishable `artifacts.jsonl` row —
  reopening row 22's closure claim and row 12's disclosed-scope boundary via a third, unenumerated
  actor/vector combination. See Item 1(d) for the full concrete sequence and citations.
  `routeToPhase`: 1b.
- **FIND-T (BLOCKING, new this iteration)** — `behavioral-spec.md:512-520` (REQ-014's own
  acceptance-criteria text for PROP-047) was not updated this iteration and still contains the
  exact ambiguous "gate script... or anywhere outside `reality-verdict-schema.mjs`" phrasing
  `reviews/spec-review-06.md` already flagged, contradicting `verification-architecture.md:128`'s
  now-explicit "(i)+(ii), both callers" scope. The two authoritative documents disagree; a Builder
  reading the EARS requirement text alone would not know to scan
  `skills/self/reality-verify-spawn.sh`. See Item 2. `routeToPhase`: 1b.

No other new blocking or major findings within the granted scope. The CSPRNG-and-exclusive-create
DESIGN direction (Item 1(a)-(c)) and the PROP-047 table-row widening (Item 2, first half) are both
real, substantive progress, not restated language — this delta's two blocking findings are each
narrow, mechanical gaps in an otherwise-sound fix direction, not a rejection of the approach.

---

## Overall Delta Verdict: **FAIL**

Blocking findings:
1. **FIND-S** — the passId fix closes prediction and pre-creation but leaves an observe-then-race
   forgery vector open, via filesystem-event detection of the exclusive-`mkdir` plus unrestricted
   same-user write access to the artifact-trail directory. Neither the closure table (rows
   12/22) nor PROP-048's fixture (which only tests pre-creation, `verification-architecture.md:127`)
   covers this vector.
2. **FIND-T** — `behavioral-spec.md:512-520`'s REQ-014 acceptance-criteria text for PROP-047 was
   not updated to match `verification-architecture.md:128`'s claimed "both callers" scope, leaving
   the previously-flagged scope ambiguity verbatim in the authoritative requirement text.

0 findings that were out of this delta's granted scope. FIND-M and FIND-O (iteration 6's other two
closures) were not re-examined and are not reopened by anything in this review.
