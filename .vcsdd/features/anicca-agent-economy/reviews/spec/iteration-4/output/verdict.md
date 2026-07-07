# Phase 1c Spec Review — anicca-agent-economy — Iteration 4 (escalation-approved)

**Verdict: FAIL** (1 new finding, FIND-301 — the FIND-201 patch fixes the specific named
instance but not the underlying scope-definition gap, and a second live instance was found)

## Scope

Per manifest, this review is scoped to confirming FIND-201's resolution and checking the
REQ-204/verification-architecture.md patch for new contradictions, with only a light
no-regression spot-check of FIND-001..006/101/102 (not a full re-litigation). Artifacts read:
`specs/behavioral-spec.md` (REQ-204 in full), `specs/verification-architecture.md`
(PROP-203b/PROP-204a + Gate item 4), and `/Users/anicca/anicca/runtime/loop/prompt.mjs`
(`buildSystemPrompt`, read end-to-end lines 45-132, not just the previously-cited ranges).

## FIND-201: the named instance is fixed; the underlying pattern is not

The literal defect FIND-201 raised — `runtime/loop/prompt.mjs:71`'s `"the highest-leverage move
is to POST"` (inside the `economy/gig` bullet of `## Your earn tools`) — is now correctly named
in REQ-204's Acceptance Criteria, in verification-architecture.md's Purity Boundary Map, in
PROP-204a, and in the Gate section. That specific gap is closed.

But the patch's mechanism for generalizing beyond named phrases is itself inconsistent. REQ-204's
Acceptance Criteria now contain **two differently-scoped generality clauses**:
- Bullet 2 ("GENERALIZED, BINDING criterion"): scope = "anywhere within the `## ★COLONY BOOTSTRAP
  PRIORITY★` block itself, or anywhere within any paragraph that block references or duplicates."
- Bullet 3 (mirrored by PROP-203b): scope = "anywhere in the file's binding (non-tips,
  non-advice) sections" — the WHOLE file.

Bullet 2's scope is strictly narrower than bullet 3's. A fresh, full re-read of the current
`prompt.mjs` (not just the ranges already implicated by prior findings) found a second, currently
real ranking phrase that this narrower scope misses: the `## MINDSET` section (lines 98-103,
a section SIBLING to `## ★COLONY BOOTSTRAP PRIORITY★`, not something that block references or
duplicates) contains, one bullet away from the one MINDSET phrase REQ-204 does name (`"it is
almost never 'yield again'"`, lines 102-103), an un-named second phrase: **`"Re-yielding every
wake = failure."`** (line 99) — textbook steering under REQ-203's own definition, since
disparaging one remaining option is the same steering mechanism as ranking the others above it.

This phrase falls **outside** bullet 2 / PROP-204a's literal scope (MINDSET is not the bootstrap
block and is not referenced/duplicated by it) but **inside** bullet 3 / PROP-203b's scope (MINDSET
carries no "advice, NOT rules" disclaimer — only the later "Tips from a senior" section is
self-labeled non-binding). A Phase 3 implementation that satisfies REQ-204's named list and its
narrower bullet-2 criterion to the letter would leave this phrase in the shipped file, while
PROP-203b would have to treat it as a remaining violation for the identical code state — the
exact PROP-203b-vs-PROP-204a disagreement this very requirement says must never happen,
reproduced inside the patch meant to prevent it.

## Prior findings: spot-check only (per manifest), no regressions found

FIND-001, FIND-002, FIND-003, FIND-004, FIND-005, FIND-006, FIND-101, FIND-102 were each
spot-checked against the current spec text and are unchanged / not touched by this iteration's
patch (see `priorIterationResolution` in verdict.json for the specific line ranges checked).

## Recommendation

This gate has now returned FAIL on 4 consecutive iterations, each time on a variant of the same
failure class: REQ-204/PROP-204a's scope definition is anchored to specific named phrases or to
"the block + what it references," rather than to the whole file's binding sections, so it keeps
missing a real, currently-present phrase somewhere else in the same function. Recommend the next
revision **drop the narrower "block itself or what it references/duplicates" framing entirely**
and unify REQ-204, PROP-204a, and PROP-203b onto the single whole-file-scoped definition bullet 3
already states, rather than continuing to patch in one more named exception per iteration.
