# VCSDD Adversary — Phase 1c Spec Review (iteration 6, BOUNDED ESCALATION)

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary. Zero context from Builder, zero context from iterations
1-5's reviewers beyond what is quoted verbatim on disk. Every disposition below is
independently re-derived from the files listed, not trusted from the spec's own
"CLOSED"/"CONFIRMED FIXED" claims.

**Scope discipline**: per `escalations/escalation-01-spec-review.md`, this iteration is
strictly bounded to FIND-M (blocking), FIND-N (blocking), FIND-O (major), FIND-P (major)
from `reviews/spec-review-05.md`, plus a regression check on rows 1, 2, 8, 14, 18, 19. I did
not go looking for new scope outside these four findings' own territory. Both blocking
findings below are about whether the FIND-N and FIND-P *fixes themselves*, as specified, are
real — i.e. still inside the granted scope.

## Artifacts actually read (paths + line ranges)

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (1-562, full file, this worktree)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (1-149, full file, this worktree)
- `.vcsdd/features/reality-gate/reviews/spec-review-05.md` (1-446, full file — independently re-checked)
- `.vcsdd/features/reality-gate/escalations/escalation-01-spec-review.md` (1-21, full file)
- `/Users/anicca/anicca/skills/self/lib/reality-verdict-schema.mjs` (1-129, full file — confirmed
  CURRENT implementation still has the 6-category, PASS/FAIL-only shape; `validateVerdictShape`
  currently rejects anything but `"PASS"`/`"FAIL"` at line 87 — expected/correct for Phase 1c,
  none of REQ-004/013/014/015's new functions exist yet)
- `/Users/anicca/anicca/skills/self/reality-verify-spawn.sh` (1-69, full file — confirmed CURRENT
  implementation is still the detached `tmux new-session -d`, 3-positional-arg
  `<loop-name> <artifact-or-report-path> [claim-text]`, no `enforceVerdict`/`passId`-namespacing
  yet — expected for Phase 1c)
- `/Users/anicca/anicca/.claude/agents/reality-verifier.md` (1-139, full file)
- `/Users/anicca/anicca/skills/earn/gig/gig_reality_verify.sh` (1-203, full file — re-confirmed
  `PASS_ID="realityverify-$(date +%s)-$$"` generated INSIDE this script, lines 100-105, and that
  the entity generating `pass_id` (`gig_reality_verify.sh`, run by `auditor.sh`) is a DIFFERENT
  entity from the one under test (the gig core loop) — this asymmetry is exactly what makes gig's
  low-entropy scheme safe for gig and NOT safe, unmodified, for this spec's design, see FIND-N below)
- `/Users/anicca/anicca/skills/self/self-fix.sh` (1-60 read — confirms `self-fix.sh <loop> <blocker>`
  signature REQ-010 assumes)
- `~/.claude/rules/building-effective-ai-agents.md` (full file, via system context)

No `manifest.json` scaffold exists for this scope; reviewed directly against the task brief,
matching the convention iterations 1-5 already used.

---

## Item 1 — FIND-M (the inverse bug): checked against the spec text

**(a) Fabrication yields FAIL even when `automatedVerification` is false** — CONFIRMED CLOSED.
`behavioral-spec.md:190-206` (REQ-004 EARS) and `:469-497` (REQ-014 EARS) both state
`validateArtifactProvenance` is reached "UNCONDITIONALLY... REGARDLESS of `automatedVerification`'s
value" and that the flag is consulted "ONLY inside `validateArtifactProvenance`, as its LAST
check, after every CONTRADICTION check has already had the chance to fire."
`verification-architecture.md:48-65` reproduces the identical composition with a named
**Rejected design** paragraph explicitly forbidding the iteration-5 gating-as-precondition
design. Forcing PROP: **PROP-043(b)** (`verification-architecture.md:113`) — "a COMPANION
fixture identical to (a) except ALSO containing one contradiction... ⇒ `FAIL`/`url_mismatch`,
NOT `CANNOT_VERIFY`" — this is the direct, required, tier-1 proof that contradiction detection
fires regardless of the flag. Genuinely fixed.

**(b) Healthy post pre-diagnosability yields `CANNOT_VERIFY`, never self-fix, never reported as
verified** — CONFIRMED CLOSED. `behavioral-spec.md:338-366` (REQ-010) states explicitly: "WHEN
`enforceVerdict` yields `overallVerdict: "CANNOT_VERIFY"`... THE SYSTEM SHALL NOT invoke
`self-fix.sh`" and "A `CANNOT_VERIFY` verdict SHALL NEVER... (b) be reported to a loop's
owner-facing success report... AS a verified post." Forcing PROP: **PROP-046**
(`verification-architecture.md:116`) — grep-checkable, two distinct branches
(`FAIL`→`self-fix.sh`, `CANNOT_VERIFY`→queue, explicitly NOT `self-fix.sh`). Genuinely fixed.

**(c) `CANNOT_VERIFY` cannot be laundered into `PASS`; `PASS` cannot be reached without a
diagnostic capture** — CONFIRMED CLOSED, with one calibration. `enforceVerdict` step (2) passes
any non-`PASS` raw verdict through UNCHANGED (`behavioral-spec.md:476-478`); `PASS` is only ever
reachable when EVERY structural check (citation/tool/row/URL/redirect/count/dup/status/
fixed-surface/fingerprint/precommit-order) resolves clean AND `automatedVerification === true`
(`verification-architecture.md:44-46`). `automatedVerification` itself can only be flipped `true`
by the Phase 2a diagnosability proof (REQ-012/013). Note this is a platform-level flag, not a
per-invocation "did we capture a diagnostic signal this exact time" flag — but every
per-invocation structural check (citation presence, row match, fixed-surface membership,
fingerprint) is independently, unconditionally still required on top of the flag, so `PASS` still
requires real, per-invocation captured evidence, not merely the flag alone. Genuinely fixed.

**(d) Phase 2a diagnosability experiment genuinely REQUIRED, real logged-out fetch, differs on a
named structured field, named fallback** — CONFIRMED CLOSED. `behavioral-spec.md:424-441` (REQ-012)
states explicitly "REQUIRED, scheduled Phase 2a task, not optional or deferred," names the exact
experiment (known-public vs known-removed IG post URL), requires the differentiating signal be "a
NAMED structured field... never DOM prose interpretation," and names the fallback
(`fixedPublicSurfaceUrl`/`referencedArtifactIds` membership) explicitly, not hand-waved. Forcing
PROP: **PROP-033** (`verification-architecture.md:110`), `required: true`, explicit acceptance
criterion quoted verbatim. Genuinely fixed.

**FIND-M verdict: genuinely, structurally fixed. No blocking issue found in this specific finding.**

---

## Item 2 — FIND-N: `passId` internal generation — **NOT genuinely closed (BLOCKING, new evidence)**

The spec's own closure claim (`behavioral-spec.md:405-407`, REQ-012): "a directory whose name is
ALWAYS the internally-generated `passId` from REQ-005 — no caller-facing API anywhere accepts OR
PREDICTS this value in advance, closing closure row 22's pre-staging attack **structurally, not
merely by convention**." (Emphasis mine — this is the spec's own strength claim.) The NFR
(`behavioral-spec.md:530-533`) similarly claims `passId` generation is "never writable/choosable
by any component that also produces the verdict checked against them."

The review task explicitly asks me to check "never predictable by the loop under test" — not just
"never accepted as a caller argument." I checked this, and it is false as specified:

`verification-architecture.md:78` specifies the generation mechanism verbatim: "`PASS_ID=
"realityverify-$(date +%s)-$$"`-equivalent, generated at spawn time." This is the EXACT SAME
low-entropy scheme (unix-second timestamp + process PID) as `gig_reality_verify.sh:103` — but
gig's scheme is safe BECAUSE the entity generating `pass_id` (`gig_reality_verify.sh`, invoked by
`auditor.sh`) is a DIFFERENT process from the entity under test (the gig core loop) — the core
loop never invokes `gig_reality_verify.sh` itself and has no privileged visibility into exactly
when/with-what-PID it runs. In THIS spec's design, by contrast, REQ-011/REQ-005
(`behavioral-spec.md:392-394`, "the growth-engine loop calls `reality-verify-spawn.sh` directly")
name the loop UNDER TEST as the DIRECT PARENT PROCESS of `reality-verify-spawn.sh` itself.

**Concrete derivation, not a theoretical exploit**: a bash-capable caller (already a granted
capability the spec's OWN FIND-N concrete-scenario paragraph names, `behavioral-spec.md`'s
iteration-history row 5, quoting "a Bash-capable growth-engine loop... already a granted
capability for any autonomous cron loop in this codebase") invokes the script as
`bash "$SPAWN" ... & pid=$!; wait "$pid"` instead of a plain blocking call — functionally
IDENTICAL blocking semantics from the caller's perspective (REQ-005's own "run to COMPLETION,
blocking" requirement is a constraint on `reality-verify-spawn.sh`'s OWN internal behavior, not on
how its caller may invoke it) — and this trivially yields `$!` = the exact PID that becomes `$$`
inside the script (this is basic, deterministic bash semantics: `bash script.sh &` does not
re-fork; the backgrounded PID and the script's own `$$` are identical). Combined with `date +%s`
read by the caller in the same wall-clock second (a search space of at most 2 candidate seconds,
not a race), the caller can derive the EXACT `passId` the script is about to use, before or during
the up-to-600-second verifier spawn window (`behavioral-spec.md:261`, "capped at 600s") — giving
it a comfortable, non-racy window (not a split-second race) to write into the predicted
`.../reality-artifacts/<derived-passId>/` directory. No `mkdir`-exclusive / pre-existing-directory
refusal is specified anywhere in REQ-005/REQ-012 that would detect or reject a pre-staged
directory.

I am NOT claiming every downstream contradiction check is defeated by this (the `ts`/`seq`
citation-matching checks, row 4/`stale_row`, may provide partial defense-in-depth depending on
`ts` precision, which the spec does not pin down — REQ-012's row shape,
`behavioral-spec.md:404-407`, lists `ts` with no stated precision). What I AM asserting, with
direct citation, is narrower and sufficient to be blocking on its own: **the spec's own closure
justification for row 22 ("structurally... not merely by convention," "no caller-facing API...
predicts this value in advance") is factually false given the exact mechanism the spec itself
specifies** — this is a `spec_fidelity`/`security_surface` defect in the fix's own stated
reasoning, independent of whether every possible resulting forgery is separately caught elsewhere.
No proof obligation tests this: **PROP-042** (`verification-architecture.md:112`) only proves
that explicit injection channels (a `pass-id`-shaped CLI arg, a `PASS_ID`/`passId` env var) are
*ignored* — it never attempts to *derive* the internally-generated value via the `$!`/`wait`
idiom and assert the derivation fails or is refused. This is precisely FIND-N's own named threat
("reachable by the accused") surviving under a fix that only closed the syntactic channel, not
the semantic one.

`routeToPhase`: 1b — either (a) add real entropy the calling process cannot derive (e.g. a random
component, `$RANDOM`/`/dev/urandom`, mixed into `passId`, not merely time+PID), or (b) make the
artifact-trail directory creation exclusive (`mkdir` fails if pre-existing) and treat a
pre-existing directory at spawn time as itself a `CANNOT_VERIFY`/tamper-suspected condition, or
(c) narrow the closure claim to what is actually true ("not caller-suppliable via any argument
channel" — a real, lesser guarantee) rather than the stronger, unsupported "never predicted...
structurally" claim currently in `behavioral-spec.md:407` and the NFR.

---

## Item 3 — FIND-O: capture-tool failure modes — **genuinely CLOSED**

`behavioral-spec.md:409-423` (REQ-012) explicitly separates: network-level failure → reserved
`httpStatus` sentinel (never a real in-range code) → `capture_network_error` →
`CANNOT_VERIFY` (PROP-044); empty/near-empty 2xx body → real status recorded, `domExcerpt`
empty/marked → `capture_empty_body` → `CANNOT_VERIFY` (PROP-045); soft-404 (real 200,
not-found-looking body) deliberately NOT special-cased, falls through to
`automated_verification_unproven` → `CANNOT_VERIFY` (never silent PASS, never false FAIL); a
genuine server-returned non-2xx (real 404/410/403) → `server_confirmed_absent` → `FAIL`. This
maps exactly onto the taxonomy table (`behavioral-spec.md:207-225`) and
`verification-architecture.md:32-46`'s reproduction of it. Genuinely fixed, no blocking issue.

---

## Item 4 — FIND-P: no-duplicated-provenance-logic PROP — **only HALF closed (BLOCKING, new evidence)**

`behavioral-spec.md:506-514` (REQ-014's new acceptance criterion) is internally ambiguous about
scope ("scans the gate script's source file for definitions... asserts ZERO such definitions
exist in the gate script **(or anywhere outside `reality-verdict-schema.mjs`)**" — two different
scopes stated in the same sentence). `verification-architecture.md:117` (**PROP-047**) resolves
that ambiguity DOWNWARD, not upward: its own "Path" column states explicitly **"(i) only — a
property of the gate script's source file."** This means `skills/self/reality-verify-spawn.sh` —
path (ii), the RUNTIME customer, the exact invocation path REQ-011 names as the first/only real
customer and the one FIND-M's entire fix was about — has **no forcing static check** against a
Builder re-implementing/duplicating `httpStatus`/`referencedArtifactIds`/`contentHash`
comparison logic, or a shadow copy of `canonicalizeUrl`/`validateArtifactProvenance`/
`enforceVerdict`, directly inside it.

This directly contradicts REQ-014's own EARS framing, "ONE module, TWO callers" (title,
`behavioral-spec.md:469`) and its explicit statement that `enforceVerdict` is "the SOLE function
EITHER invocation path may treat a raw LLM verdict as accepted through" (`:484-485`) — a claim
that is exactly as unenforced-by-proof for path (ii) as REQ-014's original, FIND-P-flagged gap
was for BOTH paths. `verification-architecture.md:117` even cross-references PROP-047 to
**closure row 18**, which is explicitly a path-(ii) closure row ("(ii), was fully unprotected...
CLOSED... unconditionally invoked by the now-blocking `reality-verify-spawn.sh`",
`behavioral-spec.md:77`) — an internal inconsistency inside the same table: a PROP scoped "(i)
only" is cited as (part of) the evidence closing a row whose own definition is about (ii).

**Concrete failure scenario**: a Builder, implementing `reality-verify-spawn.sh`'s "on
`CANNOT_VERIFY`, append to the human-review queue; on `FAIL`, call `self-fix.sh`" branching logic
(REQ-010/REQ-005 acceptance criteria), re-derives a local `if httpStatus not in 200..299` check
inline (a plausible, easy-to-reach-for shortcut given the script already needs to inspect the
verdict) instead of routing everything through `enforceVerdict`'s return value alone. Nothing in
this feature's own required test suite — PROP-047 is scoped away from this file — would catch it.

`routeToPhase`: 1b — widen PROP-047's scope (or add a PROP-047b) to also scan
`skills/self/reality-verify-spawn.sh`'s source for the same forbidden definitions/comparison
logic, matching REQ-014's own "TWO callers" framing.

---

## Regression audit (rows 1, 2, 8, 14, 18, 19)

| Row | Spec-claimed status | My finding | Verdict |
|---|---|---|---|
| 1 | CLOSED (reclassified `FAIL`→`CANNOT_VERIFY`) | Mechanism traced through the taxonomy (`behavioral-spec.md:211`) and `enforceVerdict`'s composition — genuinely reachable, `no_citation` fires only when literally nothing citeable is present, which the UNCHANGED `validateVerdictShape` (`reality-verdict-schema.mjs:117-125`, current file — a `PASS` with zero findings already requires `evidenceReviewed` or is rejected as malformed at step 1) makes hard for a compliant, well-behaved reality-verifier to trigger honestly. See "Row-1 judgment" below for full reasoning. | reclassification is correctly reasoned, **not** a laundering channel — see below |
| 2 | CLOSED (`wrong_tool`) | Still CONTRADICTION-class, checked before `automatedVerification`, unaffected by the reordering (`verification-architecture.md:33-37`). PROP-010/018 unchanged. | genuinely CLOSED, no regression |
| 8 | CLOSED (non-2xx status) | Correctly split this iteration into `server_confirmed_absent` (real non-2xx, `FAIL`) vs `capture_network_error` (no real status ever received, `CANNOT_VERIFY`) — exactly FIND-O's fix, traced above. | genuinely CLOSED, strengthened not regressed |
| 14 | CLOSED (URL mismatch / redirect) | `url_mismatch`/`redirect_off_artifact` still CONTRADICTION-class, checked first, unaffected by reordering. PROP-028/029/030/041 unchanged. | genuinely CLOSED, no regression |
| 18 | CLOSED (backstop reaches runtime path) | `enforceVerdict` unconditional invocation by `reality-verify-spawn.sh` is real (REQ-005 EARS, `behavioral-spec.md:261-262`) — the WIRING is sound. BUT see FIND-P above: the "no shadow re-implementation" guarantee for this exact path has no forcing PROP, so the wiring's *exclusivity* claim is asserted, not proven, for path (ii). | wiring genuinely CLOSED; **exclusivity claim unproven for this row's own path** (new evidence, see FIND-P) |
| 19 | CLOSED (fixed-surface + fingerprint, loop URL demoted to locator) | Unchanged from iteration 5 (REQ-015 explicit "Unchanged"). Interacts positively with FIND-N's fix: citation resolution now looks up rows in the internally-named directory rather than a caller-chosen one — BUT see FIND-N above: that directory name is still derivable by the loop under test, which weakens (does not eliminate) row 19's anti-forgery value the same way it weakens row 22's. | mechanism sound in isolation; **same derivability caveat as FIND-N** |

## Row-1 `CANNOT_VERIFY` judgment (task item 4)

**My answer: correctly fail-closed, not a free-pass channel for a lying loop — with one
disclosed, accepted residual limitation.** Reasoning:

1. `CANNOT_VERIFY` blocks convergence exactly as `FAIL` does — REQ-008
   (`behavioral-spec.md:311-330`) maps it to `recordGate`'s stored `verdict: "FAIL"` (the only
   schema-legal blocking value), distinguished only by `details.enforcementOutcome`. A lying
   loop gains nothing toward "shipping" by triggering this path over `FAIL`.
2. It is never reportable as success — REQ-010's explicit prohibition
   (`behavioral-spec.md:351-356`) is a hard SHALL NEVER, not a preference.
3. It is not silently dropped — REQ-010's edge case (`:357-361`) explicitly forbids
   deduplication/suppression of repeated `CANNOT_VERIFY` rows, "an unresolved diagnosability gap
   recurring daily is itself useful signal."
4. Critically, `no_citation` is not something the LOOP under test can reliably force. The party
   whose behavior determines whether citations exist is `reality-verifier` — a fresh, independent
   spawn the loop under test does not control (row 12's disclosed, unchanged residual risk is the
   ONLY channel by which the verifier's own output could be compromised, and that risk is already
   named, not newly introduced here). A loop lying about a post it never made would, if
   `reality-verify-spawn.sh`'s "no URL ⇒ refuse to spawn" edge case (`behavioral-spec.md:266`)
   doesn't apply (i.e., it supplies SOME URL, even a garbage one, as REQ-005 requires for a
   public-artifact claim), cause the REAL capture tool to record a REAL response for that garbage
   URL — most plausibly a genuine non-2xx (`server_confirmed_absent`/`FAIL`, a CONTRADICTION, not
   `CANNOT_VERIFY`) — not a `no_citation` outcome.

**The one genuine, disclosed limitation** (not a new finding — the spec discloses this itself at
`verification-architecture.md:143-149`, "Whether a `CANNOT_VERIFY` outcome will, in practice, ever
actually get resolved... this feature specifies the MECHANISM... but does not... guarantee
operational follow-through"): the human-review queue has no forcing function ensuring a human
reads it. A healthy loop stuck at `CANNOT_VERIFY` pre-Phase-2a is not falsely rewarded, but it is
also not reliably resolved either, absent someone reading the queue. This is honestly disclosed,
not hidden, and is consistent with the escalation's own framing (avoid over-correcting the
false-PASS direction into a new "always-inert" direction) — I do not treat it as blocking.

## Falsifiability (task item 5)

Real, required proof obligations force an actual end-to-end `FAIL`: **PROP-020/020b**
(`verification-architecture.md:109`, live spawns via the runtime path against a genuinely
nonexistent URL and a genuinely different real URL — both must yield `FAIL`), backed by REQ-007's
"live, fresh spawn... against a genuinely nonexistent public URL" requirement
(`behavioral-spec.md:299-309`). These are genuine, unaffected by this iteration's scope.

## No-hardcoded-judgment (task item 6) — **PASS**

Re-checked `~/.claude/rules/building-effective-ai-agents.md`'s rule against this iteration's
diff: the CONTRADICTION-vs-INCONCLUSIVE taxonomy (`behavioral-spec.md:207-225`) is a fixed,
declared lookup table, decided once in the spec text, never a runtime heuristic; `enforceVerdict`
and `validateArtifactProvenance`'s composition are pure boolean/structural checks
(`verification-architecture.md:15-73`); `automatedVerification`'s role remains "a final, boolean
gate... not a judgment about whether a platform is 'probably fine'" (`behavioral-spec.md:552-553`,
explicit "Judgment vs determinism" section, read in full). No regex/keyword-based honesty
classification was introduced by FIND-M/N/O/P's fixes. This dimension remains sound.

---

## Dimension verdicts

| Dimension | Verdict | Basis |
|---|---|---|
| spec_fidelity | **FAIL** | FIND-N: the spec's own row-22 closure claim ("structurally, not merely by convention," "no caller-facing API... predicts this value in advance") is textually contradicted by the exact mechanism (`date +%s`+PID) the spec itself specifies. |
| edge_case_coverage | **FAIL** | FIND-N: the `$!`/`wait` derivation path is an edge case (an adversarial caller of a blocking script) the spec does not consider, despite explicitly naming Bash-capable adversarial callers elsewhere in its own FIND-N disposition. |
| implementation_correctness | **FAIL** | A Builder implementing REQ-005/012 exactly as specified produces a `passId` scheme that does NOT deliver the unpredictability property the spec claims for it. |
| structural_integrity | **FAIL** | FIND-P: PROP-047 is scoped to path (i) only, contradicting REQ-014's own "ONE module, TWO callers" framing and leaving path (ii) — the named first customer's own invocation path — with no forcing no-duplication check. |
| verification_readiness | **FAIL** | Same PROP-047 gap: REQ-014's acceptance criterion for path (ii) has, in substance, no required proof obligation, which is precisely the shape of defect FIND-P was granted scope to close and did not fully close. |
| no-hardcoded-judgment | **PASS** | Evidence above — taxonomy remains a fixed, declared lookup table; `automatedVerification` remains a boolean gate, not an LLM judgment call. |

## Findings

- **FIND-Q (BLOCKING)** — `passId`'s internal-generation scheme (`date +%s`+PID,
  `verification-architecture.md:78`) is derivable in advance by the calling loop via the standard
  `bash "$SPAWN" ... & pid=$!; wait "$pid"` idiom, contradicting the spec's own "never predicted...
  structurally" closure claim for row 22 (`behavioral-spec.md:405-407`). See Item 2 above for full
  citation and concrete scenario. `routeToPhase`: 1b.
- **FIND-R (BLOCKING)** — PROP-047 (`verification-architecture.md:117`), FIND-P's forcing proof
  obligation, is scoped "(i) only — a property of the gate script's source file," leaving
  `skills/self/reality-verify-spawn.sh` (path ii, the runtime/first-customer path) with no
  forcing check against duplicated provenance logic, contradicting REQ-014's own "ONE module, TWO
  callers" framing (`behavioral-spec.md:469, 484-485`). See Item 4 above. `routeToPhase`: 1b.

No other new blocking or major findings within the granted scope. FIND-M and FIND-O are
independently reconfirmed as genuinely, structurally fixed (Items 1 and 3 above).

---

## Ship/no-ship judgment (first customer: the IG-posting marketing loop, REQ-011)

I would **NOT** ship this gate yet. FIND-M's fix is real and is the correct, substantive design —
the three-outcome verdict space genuinely solves the inverse-bug this feature was escalated over,
and I would not send this back over FIND-M alone. But the TWO findings that were specifically
granted for re-review this iteration (FIND-N, FIND-P) each have a real, citable gap between what
their fix *claims* and what their fix *specifies*: FIND-N's passId is syntactically
caller-unsuppliable but semantically caller-derivable by the exact actor (the loop under test)
the finding was about protecting against; FIND-P's no-duplication proof obligation was narrowed
to the wrong one of the "two callers" REQ-014 itself names, missing the runtime path that is this
feature's own stated reason for existing. Both are narrow, mechanical fixes (add entropy /
exclusive-directory-creation to `passId`; widen PROP-047's file scope to include
`reality-verify-spawn.sh`) — not a redesign — and I would expect a 7th, tightly-scoped iteration
to close them cleanly given the trajectory of iterations 4-6.

---

## Overall Gate Verdict: **FAIL**

Blocking findings:
1. **FIND-Q** — `passId` internal-generation scheme is derivable by the loop under test via
   standard bash idioms, contradicting the spec's own unpredictability closure claim for row 22
   (FIND-N not genuinely closed).
2. **FIND-R** — PROP-047's file scope excludes `reality-verify-spawn.sh` (path ii), leaving
   REQ-014's "no duplicated provenance logic" acceptance criterion unforced for the runtime path
   (FIND-P not genuinely closed for both named callers).

FIND-M and FIND-O are independently reconfirmed genuinely, structurally fixed — this iteration's
rework on those two findings is real progress, not restated language.
