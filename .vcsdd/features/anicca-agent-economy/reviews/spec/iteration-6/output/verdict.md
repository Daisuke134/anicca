# Phase 1c Spec Review — iteration 6 — anicca-agent-economy

**Verdict: FAIL**

## Scope reviewed

`specs/behavioral-spec.md` and `specs/verification-architecture.md` in full, against the manifest's
three-part charge: (1) is the REQ-204 removal clean (no dangling normative references)? (2) is
REQ-203/PROP-203b's rescoped ("this increment's own new code only") boundary internally consistent
and free of a smuggled-back REQ-204-shaped obligation? (3) do the previously-resolved findings
(FIND-001..006, FIND-101, FIND-102, FIND-201) remain resolved with no regression from the scope cut?
Also performed a fresh, no-prior-context final pass over all 8 in-scope requirements (REQ-101..103,
REQ-201..203, REQ-301..302).

## spec_fidelity — PASS

The REQ-204 removal is clean. Every remaining mention of REQ-204/PROP-204a across
`behavioral-spec.md`, `verification-architecture.md`, and `specs/SPEC.md` is explicitly historical/meta
(revision notes, a dedicated "Scope of this increment" note, "OUT OF SCOPE for this increment" table
rows, and REQ-203's own scope-boundary edge case + acceptance criterion). None of these creates or
implies a live obligation on the retired requirement's content, and none instructs a Phase 3 adversary
to check `prompt.mjs`'s pre-existing text.

REQ-203/PROP-203b's narrowed scope ("filterCatalog + its index.mjs wiring" only) is internally
consistent and does not quietly reopen REQ-204. This was verified not just by re-reading the spec's
own claim but by reading the actual current `/Users/anicca/anicca/runtime/loop/index.mjs` and
`/Users/anicca/anicca/runtime/loop/prompt.mjs`: `activeSkillSlots`/`skillCatalog` are already computed
entirely inside `index.mjs` and passed as plain arguments into `buildSystemPrompt`, which already
accepts an externally-supplied slot list, and `getToolDefinitions` already appends `sleep`
unconditionally. This confirms, against real code rather than the spec's own assertion, that
implementing REQ-201/202/203 as scoped genuinely never requires touching `prompt.mjs`'s source text —
so the narrower scope is achievable, not just claimed.

All previously-resolved findings (FIND-001..006, FIND-101, FIND-102) were individually re-checked
against the current text of both spec files and remain intact and unweakened. FIND-201/301/401/402/403
(all specific to the now-retired REQ-204/PROP-204a whole-file-audit mechanism) are correctly rendered
moot rather than silently patched over — the mechanism they attacked no longer exists in this
increment's scope, which is the documented, Dais-approved resolution.

## verification_readiness — FAIL

**FIND-501 (high, requirement_mismatch)**: `verification-architecture.md`'s `## Gate` section (lines
132-183) — the section explicitly framed as what "Phase 3 (adversarial review) must confirm" — is a
closed, numbered checklist: (1) REQ-101, (2) REQ-102, (3) REQ-103, (4) REQ-201/203, (4a)/(4b) REQ-201
detail, (5) REQ-301. It contains **no item for REQ-202** (automatic, non-sticky catalog restoration)
or **REQ-302** (research spike must not gate the parallel witness track) — even though both have their
own dedicated, `required: true` proof obligations earlier in the same document (PROP-202a line 90,
PROP-202b line 91, PROP-302a line 96) and both are separately named in the Verification Strategy tier
breakdown (lines 103-105, 119-121). A Phase 3 adversary following the Gate section literally — exactly
as its own imperative "(1)...(5), must confirm" wording invites — could treat items (1)-(5) as
complete sign-off and never be explicitly directed to confirm REQ-202's balance-oscillation/
non-sticky-restoration behavior or REQ-302's non-blocking-dependency guarantee. This is the same
"closed enumerated list that turns out incomplete" failure class that already produced three
consecutive Phase-1c FAILs in this exact feature's history (FIND-201, FIND-301, FIND-401) — this time
the omitted items are two entire requirements missing from the increment's own final Gate checklist,
not a phrase inside `prompt.mjs`. This defect is independent of, and unrelated to, the REQ-204 scope
cut — it exists in the current text regardless.

See `findings/FIND-501.json` for full evidence and line citations.

## Required action before iteration 7

Add explicit Gate-section confirmation items for REQ-202 and REQ-302 (e.g., items (6) and (7),
or folded into the existing numbered sequence) so the Gate section's own enumeration matches the
Proof Obligations table and Verification Strategy section it is meant to operationalize.
