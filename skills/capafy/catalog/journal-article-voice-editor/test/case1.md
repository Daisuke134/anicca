# Case 1 — claim-preserving discussion edit

## Input

Revise this discussion paragraph for a public-health journal. Keep all numbers,
citation placeholders, and cautious wording. Do not add findings.

"In our sample of 84 participants, 62% reported improved sleep after the
four-week program. This may reflect the weekly coaching calls [CITATION]. The
small sample and self-reported outcome mean that the result should be interpreted
carefully."

## Expected checks

- Retains `84`, `62%`, `four-week`, and `[CITATION]`.
- Does not turn "may reflect" into a causal claim.
- Does not add evidence, sources, or publication claims.
- Supplies a claim-preservation table and an edit ledger.
