---
name: peer-review-response-editor
description: Turn pasted reviewer comments and manuscript evidence into a point-by-point response draft and revision plan without inventing changes, citations, or results.
---

# Peer Review Response Editor

Turn a pasted decision letter, reviewer comments, and manuscript evidence into
an evidence-bound point-by-point response draft. This is an editorial aid, not
legal, institutional, or publication advice.

## Input

Ask for the journal decision, the reviewer comments, the relevant manuscript
excerpts, changes already made, evidence available for each response, and any
non-negotiable constraints. Do not infer missing experiments, citations,
approvals, analyses, or revisions.

## Method

1. Split the decision letter into numbered, separately answerable comments.
2. Label each proposed answer as `supported`, `needs evidence`, `decline with rationale`, or `unclear`.
3. Draft a respectful point-by-point response using only the supplied material.
4. Pair every supported response with a specific revision location or mark it `[TBD]`.
5. Build a revision checklist with owner, manuscript location, and evidence gap.
6. Run a final claim check for invented studies, results, citations, page numbers, and completion claims.

## Output

Return, in order:

1. A decision summary and submission constraints.
2. A numbered response-letter draft that quotes or paraphrases each supplied comment.
3. A revision plan table: comment, response status, manuscript location, action, and evidence gap.
4. A short editor cover note only when the buyer supplied the needed facts.
5. An honesty check listing every `[TBD]`, unsupported claim, and fact that needs author confirmation.

## Boundaries

Never invent experiments, analyses, data, citations, ethics approvals, reviewer
intent, acceptance odds, page numbers, or manuscript changes. Do not claim to
submit a revision, contact an editor, access a journal system, or replace an
author's disciplinary judgment.
