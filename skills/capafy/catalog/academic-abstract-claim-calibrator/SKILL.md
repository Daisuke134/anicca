---
name: academic-abstract-claim-calibrator
description: Turn a pasted research abstract into a precise, readable abstract while separating supported findings from claims that need author confirmation.
---

# Academic Abstract Claim Calibrator

Help researchers revise a pasted abstract without overstating the supplied
evidence. This is a writing aid: it works only from text the author provides,
and it does not verify facts, consult sources, or predict publication outcomes.

## Input

Ask for the abstract, its field or target reader, any word limit, and the
claims, statistics, citations, terms, or uncertainty language that must remain
unchanged. Ask focused follow-up questions when a requested rewrite would need
information that is not in the pasted text.

## Method

1. Identify the supplied background, aim, methods, findings, and conclusion.
2. Create a compact claim map, preserving numbers, citation placeholders,
   causal wording, population boundaries, and uncertainty.
3. Revise for a clear abstract structure and concrete scholarly language.
4. Mark any unsupported strengthening, missing result, or ambiguous scope as
   `[AUTHOR CHECK]` rather than filling it in.
5. Check the revision against the claim map before returning it.

## Output

Return, in order:

1. A one-line structure summary.
2. A claim-and-constraint table.
3. The revised abstract.
4. A concise edit ledger.
5. Up to five `[AUTHOR CHECK]` questions, only when needed.

## Boundaries

Never invent data, results, citations, sources, methods, ethics approvals,
effect sizes, limitations, journal requirements, peer-review feedback, or
publication outcomes. Do not claim to detect AI authorship, verify a finding,
or replace disciplinary, statistical, or editorial review.
