---
name: academic-conclusion-scope-editor
description: Turn a pasted academic conclusion and its supplied findings or limitations into a clear, appropriately scoped conclusion without adding evidence.
---

# Academic Conclusion Scope Editor

Revise a pasted academic conclusion so that its claims match the findings, scope,
and limitations the author supplies. Work only with the material in the current
conversation. Do not add citations, evidence, methods, or implications that are
not supplied.

## Input

Ask for:

- the conclusion to revise;
- the study aim or research question;
- the findings that the conclusion may rely on; and
- any stated population, setting, sample, method, limitation, or required wording.

If an essential item is missing, ask one focused question or continue with a
clearly labelled `[AUTHOR CHECK]` rather than guessing.

## Method

1. Build a claim ledger: identify each conclusion claim and the supplied finding,
   scope, or limitation that supports it.
2. Flag claims that introduce a causal result, universal statement, practical
   recommendation, citation, or numerical result not present in the supplied
   material.
3. Preserve supported findings, exact numbers, citation placeholders, and required
   terminology.
4. Rewrite the conclusion in this order: answer to the stated aim, bounded
   interpretation, scope or limitation, and a proportionate next step when the
   author supplied one.
5. Replace unsupported certainty with precise conditional language. Mark anything
   that cannot be supported from the supplied material as `[AUTHOR CHECK]`.
6. Perform a final claim-by-claim check against the supplied facts.

## Output

Return these sections in order:

1. **Scoped conclusion** — the revised prose.
2. **Claim ledger** — each material claim labelled `supported`, `softened`, or
   `[AUTHOR CHECK]`, with its supplied basis.
3. **Preservation check** — exact numbers, required terms, and citation
   placeholders retained.
4. **Author checks** — only the unresolved facts or decisions the author needs to
   confirm.

## Boundaries

- Do not claim a finding is generalisable, causal, clinically useful, statistically
  significant, or publication-ready unless the author supplied a basis for that
  claim.
- Do not invent literature, citations, sample details, methods, effect sizes,
  policies, or outcomes.
- Do not browse, retrieve sources, or verify facts outside the text the author
  provides.
- This is an editing aid, not peer review, methodological validation, or advice on
  what a study proves.
