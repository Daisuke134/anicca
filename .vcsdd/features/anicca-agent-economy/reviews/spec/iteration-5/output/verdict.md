# Phase 1c Spec Review — iteration 5 — anicca-agent-economy

**Overall verdict: FAIL**

Scope of this iteration (per manifest.json): confirm that REQ-204's redesign from
phrase-enumeration to whole-section-deletion (heading-through-next-heading, Tier-0,
mechanical) genuinely makes PROP-204a's PASS structurally imply PROP-203b's PASS, by
re-reading `runtime/loop/prompt.mjs` fresh and in full for any ranking/imperative language
that would survive outside the two named sections (`## ★COLONY BOOTSTRAP PRIORITY★`, `## MINDSET`).

## What was verified as sound

- The whole-section-deletion redesign itself is a real structural improvement: heading-substring
  absence, given the "heading through next `## ` heading" section definition, is mechanically
  checkable and does correctly resolve the SPECIFIC FIND-301 defect (the `## MINDSET` section is
  now one of PROP-204a's two named removal targets; its boundary — lines 98-104 inclusive of the
  trailing blank line before `## Tips` — was independently re-derived against the current file and
  matches).
- Deleting the two named whole sections does not remove any information the model actually needs:
  every tool-mechanics detail (post/take/deliver args, vault/APY behavior, etc.) already lives in
  the retained `## Your earn tools` section, confirmed by re-reading both removed sections' bodies
  line by line (lines 89-97, 98-104) and finding no unique mechanical content in either.
- The two named `economy/gig` bullet clauses ("the highest-leverage move is to POST", "Prefer this
  over re-yielding surplus.") are correctly cited against the real current line numbers (71, 76).

## Why it still FAILs

1. **FIND-401 (spec_fidelity, critical).** REQ-204's own "Closed-inventory cross-check" claims a
   fresh, full re-read of `prompt.mjs` found nothing outside its closed 4-part list. This is false
   for the CURRENT file: `buildUserMessage` (lines 181-234, a separate exported function in the
   SAME file) contains its own pre-existing steering mechanism — `overuse`/`avoid` diversification
   text (lines 202-206: "Do NOT repeat them now... Switch to a different earn path... it is
   FORBIDDEN this wake. Pick a DIFFERENT slot...") — that recommends/forbids specific remaining
   slots, the exact thing REQ-203 prohibits. "Do NOT repeat them now" is a literal, case-insensitive
   match for the "do not" marker PROP-203b's OWN Tool/Method column names as something a full-file
   grep must search for. This is the third consecutive iteration in which a claimed-complete removal
   scope is disproven by a real, currently-present hit found by a genuinely fresh full-file read.
2. **FIND-402 (verification_readiness, high).** PROP-203b's verification method is a fixed keyword
   list. That is under-inclusive by construction — paraphrases ("FORBIDDEN", "Pick a DIFFERENT
   slot") and typographic/rhetorical emphasis (the `economy/gig` bullet's unique
   `★THE LABOR MARKET — the colony economy★` star framing, the only bullet of six singled out this
   way even after the two named ranking clauses are removed) evade every listed marker word while
   functioning as exactly the steering signal REQ-203 forbids.
3. **FIND-403 (verification_readiness, medium).** REQ-204's Tier-0 check claims standalone
   sufficiency ("no separate check-the-body step") that it does not actually have: a naive
   heading-only deletion (leaving body paragraphs to become a headerless continuation of a
   neighboring section) would still pass PROP-204a's heading check while leaving the imperative
   text intact. The only thing that would catch this is PROP-203b's separate full-file re-scan — an
   undocumented dependency REQ-204 never states.

## Recommendation for the next revision

Extend REQ-204's named-target list to explicitly cover (or explicitly, narrowly adjudicate out of
scope) `buildUserMessage`'s `overuse`/`avoid` diversification steering; replace or supplement
PROP-203b's fixed-keyword grep with a holistic/semantic read (this project's own hard rule already
says judgment calls belong to a reviewer/model, not a brittle keyword list); and state REQ-204's
Tier-0 check's real dependency on PROP-203b explicitly rather than claiming self-sufficiency.

Findings: `findings/FIND-401.json`, `findings/FIND-402.json`, `findings/FIND-403.json`.
