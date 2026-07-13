# VCSDD Adversary — Phase 1c Spec Review (iteration 2)

Feature: `reality-gate` (mode: lean) — Phase 4.5 REALITY GATE
Reviewer: fresh-context adversary (zero context from Builder, zero context from iteration-1's
reviewer — this review re-derives everything from disk).

Artifacts actually read (paths + line ranges), used as the basis for every finding/PASS below:

- `.vcsdd/features/reality-gate/specs/behavioral-spec.md` (1-507, full file)
- `.vcsdd/features/reality-gate/specs/verification-architecture.md` (1-165, full file)
- `.vcsdd/features/reality-gate/reviews/spec-review-01.md` (1-139, full file — iteration 1's findings, verified against spec text below, not trusted from its own claims)
- `.claude/agents/reality-verifier.md` (1-140, full file)
- `skills/self/reality-verify-spawn.sh` (1-69, full file)
- `skills/self/lib/reality-verdict-schema.mjs` (1-129, full file)
- `skills/earn/gig/scripts/gig_reality_gate.py` (1-119, full file)
- `/Users/operator/.claude/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/schemas/vcsdd-state.schema.json` (1-107, full file)
- `/Users/operator/.claude/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/scripts/lib/vcsdd-state.js` (78-107, 1066-1125, 1280-1310, 1734-1770 — `GATE_PREREQUISITES`, `validateConvergenceForCompletion`, `transitionPhase`'s prereq check, `recordGate`)
- `/Users/operator/anicca-project/.claude/settings.json` (1-158, full file)
- `.githooks/pre-push` (1-142, full file, this repo — the "Cadence Contract Guard" already-working precedent)
- `~/.claude/rules/building-effective-ai-agents.md` (full file, via system context)
- `Glob` check: no `.claude/settings.json` exists yet in this worktree (confirms behavioral-spec.md's claim it will be created fresh); no `.githooks/pre-push` wiring for reality-gate exists yet (expected — Phase 1c, pre-implementation).

No `manifest.json`/`reviews/spec/iteration-N/input` scaffold exists for this scope; reviewed
directly against the task brief and iteration-1's review file, per the same convention iteration-1
used.

---

## Disposition of iteration-1's blocking findings (verified against spec text + ground truth myself, not taken on the Builder's word)

### FIND-001 (recordGate enum crash) — **CONFIRMED FIXED**
Independently re-read the real schema at `.../schemas/vcsdd-state.schema.json:37` (`"verdict": {"enum": ["PASS","FAIL","SKIP"]}`) and `:39` (`"reviewedBy": {"enum": ["adversary","verifier","human"]}`). `behavioral-spec.md:290-304` (REQ-008) now specifies exactly `recordGate(featureName, 'reality', 'PASS'|'FAIL'|'SKIP', 'verifier', details)` and explicitly forbids `'SKIPPED'`/`'reality-verifier'`. The values match the real enum. Genuinely fixed.

### FIND-002 (backstop inspects the LLM's own prose) — **MECHANISM REPLACED, BUT NOT ACTUALLY CLOSED — see new FIND-A below**
The specific criticized mechanism (`enforceLoggedOutEvidence`'s `"9222"`/`"daily-driver"` substring match over free text) is gone; `verification-architecture.md:19-35` now describes a structural `validateArtifactProvenance` that matches `tool`/`passId`/`ts` against an independently-read artifact-trail array — a real, structural improvement, and the substring-marker anti-pattern iteration-1 named is genuinely eliminated. **However**, this redesign introduces a new, adjacent bypass of the exact same underlying class (self-reported prose accepted without independent verification) — see **FIND-A (BLOCKING)** below. FIND-002 is not fully closed; it is closed for the specific mechanism it named and reopened by omission in the replacement.

### FIND-003 (marker false-positive) — **CONFIRMED MOOT**
`validateArtifactProvenance` as described (`verification-architecture.md:19-35`) does no substring/keyword scanning at all — it resolves structured citations against structured rows. The false-positive-marker risk cannot recur because there is no marker-substring check left in the design. Confirmed moot.

### FIND-004 (`evidence.fetchMethod` phantom field) — **CONFIRMED FIXED**
`behavioral-spec.md:156-157` and `verification-architecture.md:17-18` both now specify provenance citation reuses the existing `evidence.filePath`+`evidence.lineRange` shape from the unmodified `hasCiteableEvidence` (`reality-verdict-schema.mjs:62-65`, confirmed unchanged by direct read). No `fetchMethod` field appears anywhere in either spec file for this iteration. Genuinely fixed, and internally consistent between behavioral-spec.md and verification-architecture.md this time.

### FIND-005 (hook file path / live-fire proof) — **CONFIRMED FIXED AT THE DESIGN LEVEL**
Independently read `/Users/operator/anicca-project/.claude/settings.json:48-69` myself: top-level `"hooks"` key, `PreToolUse` array with `matcher`+`hooks[].type:"command"` entries pointing at `.claude/hooks/scripts/*.sh` — exactly the shape `behavioral-spec.md:343-348,375-378` now claims and quotes. There is no separate `hooks.json` file in the real observed convention, matching the spec's correction. `verification-architecture.md:107` (PROP-019) now requires the hook script's decision logic be directly, mechanically invoked with fixture payloads — a real upgrade from iteration-1's static-content-only check. This specific finding is fixed. **However**, a materially related but distinct verification-readiness gap remains open — see **FIND-B (BLOCKING)** below.

---

## Dimension 1: spec_fidelity — **PASS**

Reviewed: all 12 requirements (REQ-001..012) have explicit acceptance criteria and at least one
mapped proof obligation in `verification-architecture.md`'s table (PROP-009..021). REQ-001's
7-category catalog change is traced through the schema module, the agent prompt, and the existing
test file's required update (`behavioral-spec.md:76-79`, correctly identifying the one place that
must change deliberately rather than claiming false backward-compatibility). REQ-011's
"no-Instagram-hardcoding" acceptance criterion (`behavioral-spec.md:423-428`) is grep-checkable and
consistent with `~/.claude/rules/building-effective-ai-agents.md`'s anti-hardcoding rule. FIND-001
and FIND-004 (both spec-fidelity-class contradictions in iteration 1) are confirmed fixed above with
independent citations against the real schema/module files, not merely the Builder's own claim.

---

## Dimension 2: edge_case_coverage — **FAIL**

### FIND-A (BLOCKING) — the central false-PASS threat (shadowbanned/failed post still visible to the account owner) survives the FIND-002 redesign via a second, un-guarded door: evidence with NO artifact-trail citation at all

`behavioral-spec.md:158-166` (REQ-003 acceptance) and `verification-architecture.md:19-35`
(`validateArtifactProvenance`'s actual described behavior) both frame the backstop as something that
**walks existing citations and validates them**: "walks `verdict.findings[]` (and, for a PASS,
`verdict.evidenceReviewed[]`) looking for entries whose `evidence.filePath` matches the
artifact-trail path shape... resolves that citation against `capturedArtifacts`... if every citation
resolves cleanly, returns the input verdict unchanged."

This is vacuously satisfied when **zero** entries have an `evidence.filePath` at all. The schema this
feature explicitly keeps unmodified — `reality-verdict-schema.mjs:62-65` (`hasCiteableEvidence`,
confirmed unchanged by direct read, and `verification-architecture.md:14-18` confirms it is
"not touched by the FIND-004 fix... no new evidence key is added anywhere") — accepts
`evidence.domExcerpt` alone, with **no** `filePath`, as fully sufficient citeable evidence for any
finding or PASS:
```js
return Boolean(evidence.filePath || evidence.txHash || evidence.domExcerpt);
```
So a `PASS` verdict for a public-artifact claim whose only evidence is
`{ domExcerpt: "instagram.com/p/xyz shows the post, 1.2k likes, caption matches" }` — free prose the
LLM wrote itself, describing what it (possibly logged-in, possibly via CDP:9222, possibly not
checked at all) claims to have seen — passes `validateVerdictShape` (citeable evidence present) AND
passes `validateArtifactProvenance` untouched, because that function only inspects entries that
**already look like** artifact-trail citations; an entry with no `filePath` is simply never visited,
so there is nothing for the "does not resolve to a real row" rejection branch to catch.

This is **not** a hypothetical: it is a straight re-run of iteration-1's exact named threat
("a report that observed an authenticated-session view but described it in words that never mention
how it was observed... sails through as an undetected false PASS" — `spec-review-01.md:76`) through
a different door. Iteration-1's marker-substring mechanism at least LOOKED at every evidence string;
this iteration's structural mechanism only looks at strings that already declare themselves as
artifact-trail citations, and silently ignores every other string — which is a strictly weaker
default-open posture for the exact adversarial case this feature exists to close.

**Every proof obligation in the table presupposes a citation is present.** Cross-checked all of them:
- PROP-010/018 (wrong tool) — presupposes a `filePath+lineRange` citation exists.
- PROP-011/018b (no matching row) — presupposes a `filePath+lineRange` citation exists ("empty
  array, or a non-matching index" — still a citation, just unresolvable).
- PROP-012 (stale/foreign pass) — presupposes a citation exists.
- PROP-013 (identity-preserving positive case) — presupposes a citation exists and resolves.

None of REQ-003/004's acceptance criteria (`behavioral-spec.md:151-166`, `193-203`) and none of
PROP-009..021 (`verification-architecture.md:96-109`) requires feeding `validateArtifactProvenance`
a `PASS`/finding for a public-artifact `claimType` that has **zero** `evidence.filePath` entries
at all (domExcerpt-only), and asserting the result must be forced to `FAIL`. The only place this
requirement even appears is as a **prompt instruction** to the LLM ("cite the resulting row... never
a freeform... invocation", `behavioral-spec.md:152-157`; PROP-017's "domExcerpt-or-status + URL
evidence-citation requirement", `verification-architecture.md:104`) — i.e. compliance is asked of
the LLM's own behavior, with no independent, deterministic enforcement that a citation was actually
made. This is precisely the class of trust this feature's own "Judgment vs determinism" section
(`behavioral-spec.md:487-506`) says must never be the enforcement mechanism, and precisely what
iteration-1's FIND-002 was filed to prevent.

**Concrete failure scenario**: reality-verifier is asked to verify "posted video X to Instagram
publicly." It either forgets to call `public_artifact_snapshot.py` (prompt drift), or calls it and
then also separately eyeballs the post via the shared CDP:9222 daily-driver tab for an unrelated
reason permitted by REQ-003's own edge case (`behavioral-spec.md:129-135`, "that separate check MAY
use the existing daily-driver CDP:9222 tab"), and — instead of citing the REQ-012 row — writes its
`PASS` verdict's `evidenceReviewed` as `[{ domExcerpt: "confirmed visible, 1.2k likes" }]`, describing
what it saw on the authenticated tab in words that never reference how it was observed.
`validateArtifactProvenance` finds zero `filePath`-shaped entries to check, treats the verdict as
having no provenance violations, and returns it unchanged: `gates.reality = PASS`. The post can be
genuinely shadowbanned/invisible to the public and the gate still converges. This is the exact
scenario the task's item 1 names as BLOCKING by definition.

`routeToPhase`: 1b — `validateArtifactProvenance`'s acceptance criteria must add an explicit rule:
for a public-artifact `claimType`, a `PASS` (or any finding) whose evidence set contains **zero**
entries with a `filePath` matching the artifact-trail path shape must ALSO be forced to `FAIL` with
`post_not_publicly_visible` — "no citation attempted" must be treated identically to "citation
present but unresolvable," not left as an unvalidated default-open path — and this must be a new,
named PROP (fixture: a PASS verdict whose only evidence is `domExcerpt`, no `filePath` anywhere) with
the same `required: true` status as PROP-010/011/012.

### FIND-B-2 (MINOR, carried over context) — the REQ-002 "prompt must instruct preferring the most specific category" rule is not independently enforced
`behavioral-spec.md:103-105` requires the prompt to instruct the model to prefer specificity, but
this is (correctly, and by design) a prompt-only, judgment-layer rule with no proof obligation
attached — consistent with the spec's own judgment/determinism split, not a defect. Noting only
because PROP-017 (`verification-architecture.md:104`) checks the prompt CONTAINS the instruction, not
that the model FOLLOWS it — this is the intended, accepted limit of Tier-0 prompt-content checking
per this feature's own stated philosophy, not a new gap.

---

## Dimension 3: implementation_correctness — **FAIL**

### FIND-C (MAJOR) — `claimType`'s provenance (caller-supplied vs. LLM-self-declared) is never pinned down, leaving room for an implementation that lets the verifier's own output decide whether the strict check even applies

`validateArtifactProvenance(verdict, capturedArtifacts, claimType)` (`verification-architecture.md:19`)
takes `claimType` as a third, separate parameter. Neither `behavioral-spec.md` nor
`verification-architecture.md` states explicitly **where** the gate script's call sources this
argument from. Two materially different implementations are both consistent with the text as
written:
1. (Safe) `claimType` is threaded from the caller-supplied, deterministic `claim-type` argument
   given to `reality-verify-spawn.sh` at spawn time (REQ-005's 4th positional arg) — never touched
   by the LLM.
2. (Unsafe, and consistent with the spec's own EARS wording at `behavioral-spec.md:114-115`, "WHEN
   reality-verifier is asked to verify a claim... the claim's declared type is publish/post/deploy")
   — `claimType` is read off the verdict object itself (e.g. `verdict.claimType`, something the LLM's
   own output populates). Under this reading, an adversarial or drifted verifier could simply omit
   or misdeclare its own `claimType` (e.g. leave it as the generic fallback REQ-005's edge case
   explicitly exempts from the REQ-012 tool requirement — `behavioral-spec.md:218-221`, "unrecognized
   claim-type... fall through to the general narrate-only/evidence rules, no REQ-012 tool
   requirement") and the entire provenance backstop for that check never fires at all — the model
   grades its own admissibility into the strict check.

This ambiguity is exactly the class of "requirement not concrete enough to be implemented
unambiguously" this dimension exists to catch at Phase 1c, and it borders directly on reopening the
self-report-trust hole a second time (in addition to FIND-A) if a Builder picks interpretation 2.

`routeToPhase`: 1b — REQ-003/004 must add an explicit sentence: "`claimType` passed into
`validateArtifactProvenance` is always the deterministic value supplied at spawn time (the
`claim-type` argument to `reality-verify-spawn.sh` / threaded unmodified through the gate script);
it is never read from, or influenced by, the verdict object the LLM itself produces" — and this
should be a grep-checkable acceptance criterion on the gate script (`vcsdd-reality-gate.mjs`), not
left implicit.

---

## Dimension 4: structural_integrity — **PASS**

Reviewed: the purity boundary map (`verification-architecture.md:9-89`) cleanly separates the pure
schema/provenance module (`reality-verdict-schema.mjs`, extended in place: `FINDING_CATEGORIES`,
`isKnownCategory`, `validateVerdictShape`, new `validateArtifactProvenance`,
`buildVerdictTrailPath`/`buildVerdictTrailLine`/`buildArtifactTrailPath`, `decideConvergenceGate`)
from the effectful shell (agent prompt, spawn wrapper, `public_artifact_snapshot.py`, gate script,
command file, hook script + standalone backstop). No duplicate reimplementation of the existing
6-category catalog (REQ-001 extends the frozen array in place). `decideConvergenceGate` being shared,
byte-identical, between the hook handler and the standalone backstop
(`verification-architecture.md:47-53`) is a genuine anti-drift design choice, not incidental — two
enforcement paths that could disagree with each other by independent implementation are explicitly
prevented from doing so. Naming mirrors the base feature's established conventions
(`buildResultPath` → `buildVerdictTrailPath`/`buildArtifactTrailPath`). No new coupling introduced
between the pure core and I/O; `public_artifact_snapshot.py`'s structural incapacity for
authenticated access (no CDP client code path at all, per REQ-012's acceptance criteria) is a
genuine module-boundary property, distinct from FIND-A's citation-presence gap. FIND-A/FIND-B are
content-correctness/coverage defects in this design, not module-boundary defects, and are scored
under their respective dimensions above.

---

## Dimension 5: verification_readiness — **FAIL**

### FIND-B (BLOCKING) — SURVIVABILITY is asserted in prose but not mechanically required: nothing forces the "authoritative" backstop to actually run, and the plugin's own completion gate has zero awareness of `gates.reality`

Independently read `.../scripts/lib/vcsdd-state.js:1066-1125` (`validateConvergenceForCompletion`,
the plugin's own, real, unmodified check that runs via `GATE_PREREQUISITES['complete']` at
`vcsdd-state.js:279`, invoked from `transitionPhase` at `vcsdd-state.js:1287-1295`): it checks
sprint count, formal-hardening artifacts, required proof obligations, mode-strict criteria coverage,
and the latest adversary verdict/convergence signals — **it contains no reference to `gates.reality`
anywhere in its 60 lines**. This feature adds zero code to the plugin (correctly — REQ-008's own edge
case forbids touching the plugin cache), which means the plugin's own phase-transition machinery will
happily transition a feature to `'complete'` on its own 4-dimension criteria regardless of
`gates.reality`'s value, UNLESS something OUTSIDE the plugin independently intercepts that specific
transition.

The two things outside the plugin that could intercept it are:
1. The `.claude/settings.json` `PreToolUse` hook — `verification-architecture.md:154-161` itself
   concedes this is "an ASSUMPTION (not independently verified this session)... best-effort
   (heuristic text matching)."
2. `skills/self/verify-reality-gate.mjs`, described as "the AUTHORITATIVE check" — but
   `behavioral-spec.md:357-359` only says it "**can be** invoked manually or wired into this repo's
   existing `.githooks/pre-push`" (optional language, not a MUST), and none of REQ-009's acceptance
   criteria (`behavioral-spec.md:374-386`) or PROP-016/019/021 require it to actually be invoked from
   any automatic enforcement point — the acceptance criteria only test the script's exit code
   against **fixture inputs supplied by hand** ("exits non-zero when a fixture `state.json` has...",
   "covered by a unit test using fixture `state.json` files").

This repo already has a real, proven, working pattern for exactly this situation — I independently
read `.githooks/pre-push:18-30,75-96` (the "Cadence Contract Guard"), which is described in its own
header comment as existing specifically because "a code comment alone cannot stop a FUTURE... commit
from rewriting BOTH the guarded code AND its own regression-lock test" and because this repo has "no
PR/CI infra" so "pre-push (this file, the only already-wired local enforcement point,
`core.hooksPath=.githooks`) is where the gate has to live." That is precisely this feature's own
stated problem (a hook whose Claude-Code-level composition is unverified needs a git-level,
Claude-Code-independent fallback) — and this repo has already solved it once, in this exact file, for
a structurally identical "must not silently regress" requirement. REQ-009 gestures at this file as an
option but does not require wiring into it, so the fix this repo already knows how to do is left
undone by the spec.

**Concrete failure scenario**: a Builder (or a self-fix pass) invokes the plugin's phase-transition
path in a way the `PreToolUse` heuristic doesn't match (e.g. calling the plugin's exported
`transitionPhase`/CLI entrypoint through a wrapper script, an MCP call, or any Bash invocation whose
text doesn't match the hook's string heuristic) while `gates.reality` is missing or `FAIL`. The
plugin's own `validateConvergenceForCompletion` has no opinion on `gates.reality` and allows it. The
hook never fires (composition assumption, or heuristic miss). `verify-reality-gate.mjs` exists on
disk but nobody ran it, because nothing requires anyone to. The feature converges to `'complete'`
with a failed or absent reality check — the exact regression FIND-002/FIND-A exist to prevent, now
happening one layer up at the pipeline-convergence level instead of the individual-verdict level.

`routeToPhase`: 1b — REQ-009 must upgrade `.githooks/pre-push` wiring from optional prose to a
required acceptance criterion (mirroring the Cadence Contract Guard's own pattern verbatim: detect
that the push range would move a feature's `state.json` `currentPhase` to `complete`, or that
`.vcsdd/features/<name>/state.json` itself is part of the pushed diff with `currentPhase: complete`,
and fail-closed via `verify-reality-gate.mjs` if `gates.reality` doesn't pass), with a corresponding
`required: true` PROP that exercises `.githooks/pre-push` directly with a fixture push range —
exactly the rigor level PROP-019 already established for the `PreToolUse` hook script.

---

## Overall Gate Verdict: **FAIL**

Blocking findings (must be fixed before Phase 1c can pass and Phase 2 can begin):

1. **FIND-A** — `validateArtifactProvenance` only validates citations that already look like
   artifact-trail references; a `PASS`/finding for a public-artifact claim with **zero**
   `evidence.filePath` citations (e.g. `domExcerpt`-only, satisfying `hasCiteableEvidence` on its
   own) is never inspected and sails through unchanged — reopening iteration-1's exact "self-reported
   prose treated as evidence" threat model through an unguarded second door. No proof obligation in
   the table (PROP-009..021) tests this specific, most-important bypass.
2. **FIND-B** — nothing mechanically requires the "authoritative" `verify-reality-gate.mjs` backstop
   to actually run anywhere (wiring into `.githooks/pre-push` — this repo's own already-proven pattern
   for exactly this kind of fail-closed, Claude-Code-hook-independent gate, per `.githooks/pre-push`'s
   own Cadence Contract Guard precedent — is optional prose, not a required acceptance criterion), and
   the plugin's own `validateConvergenceForCompletion` (confirmed by direct read,
   `vcsdd-state.js:1066-1125`) has zero awareness of `gates.reality` — so convergence enforcement does
   NOT survive a hook-composition failure, contrary to the SURVIVABILITY property this feature must
   guarantee.

Non-blocking but must be tracked (MAJOR): **FIND-C** — `claimType`'s provenance (deterministic
caller-argument vs. LLM-self-declared) is never pinned down in either spec file, leaving an
ambiguity that could independently reopen the self-report-trust hole a third way if a Builder
threads it from the verdict object instead of the spawn-time argument.

Iteration-1's FIND-001, FIND-003, FIND-004, and FIND-005 are confirmed genuinely fixed, each verified
against the real ground-truth files myself (not taken on the spec's or Builder's own word) — see
"Disposition of iteration-1's blocking findings" above for exact citations. FIND-002 is
mechanism-replaced but not actually closed: the specific substring-marker anti-pattern it named is
gone, but the same underlying vulnerability class (self-reported prose accepted as sufficient
evidence for a public-artifact PASS) survives via FIND-A.
