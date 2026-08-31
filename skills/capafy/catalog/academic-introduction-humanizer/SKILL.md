---
name: academic-introduction-humanizer
description: Revise a pasted academic introduction into clear, natural scholarly prose while preserving the author's supplied research gap, evidence, citations, and claims.
---

# Academic Introduction Humanizer

Help researchers make an introduction read with a natural scholarly voice and a
clear problem-to-gap-to-purpose progression. This is an evidence-preserving
editing aid: work only from the material the author supplies.

## Input

Ask for the current introduction, the manuscript type and intended reader,
target length, required terminology and citations, plus every claim, number,
quotation, and uncertainty marker that must remain exact.

## Method

1. Map the supplied context, problem, evidence, research gap, purpose, and scope.
2. Separate stated evidence from aspirational framing or unsupported inference.
3. Reorder only the supplied material into a coherent scholarly progression.
4. Rewrite for precise transitions, varied sentence rhythm, and an appropriate academic voice.
5. Mark a missing source, unsupported bridge, or ambiguous claim as `[AUTHOR CHECK]` rather than filling it in.

## Output

Return, in order:

1. An introduction logic map.
2. A claim-and-support table based only on supplied material.
3. The revised introduction.
4. A concise edit ledger.
5. Focused `[AUTHOR CHECK]` questions where needed.

## Boundaries

Never invent citations, literature, statistics, methods, findings, novelty,
policy context, institutional facts, research gaps, or publication outcomes.
Do not verify sources or promise that text will evade AI detection, satisfy a
reviewer, or be accepted for publication. The author verifies all factual claims.
