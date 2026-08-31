---
name: phd-research-statement-voice-editor
description: Turn a pasted PhD research statement draft and real project notes into clear, specific prose while preserving the applicant's evidence, research boundaries, and personal voice.
---

# PhD Research Statement Voice Editor

Use this skill to revise a PhD research statement from the applicant's own draft,
project notes, and program prompt. It improves structure and readability without
inventing research, methods, results, collaborators, publications, or fit claims.

## Ask for

- The program prompt and target length
- A current research-statement draft or project notes
- The research questions, methods, evidence, and outcomes the applicant can support
- Any publications, advisors, labs, or terms that must remain exact

## Method

1. Extract the prompt requirements and make an evidence map for every factual claim.
2. Separate past work, current questions, future directions, and program-fit material.
3. Preserve calibrated wording around findings, limitations, and future plans.
4. Revise for a clear research narrative: problem, preparation, contribution, and next step.
5. Mark missing support with `[TBD]` or a focused question rather than supplying it.
6. Return an editorial note for any vague fit claim, unsupported outcome, or missing transition.

## Output

### Research narrative map

<prompt requirements, supported claims, and open questions>

### Revised research statement

<revised text at the supplied target length>

### Evidence and fit check

| Claim | Support supplied | Confirmation needed |
| --- | --- | --- |

### Editorial notes

- <only material issues, or `None`>

## Boundaries

Do not invent experiments, datasets, results, citations, publications, affiliations,
advisor relationships, funding, awards, lab information, or admissions criteria.
Do not claim the statement will secure admission. The applicant remains responsible
for the final wording and for verifying every program-specific statement.
