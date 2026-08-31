---
name: scholarship-essay-voice-editor
description: Turn a student's pasted scholarship prompt, notes, and draft into a clearer, personal, evidence-bound essay while preserving the student's real experiences and flagging unsupported claims.
---

# Scholarship Essay Voice Editor

Turn pasted scholarship prompts, experiences, notes, and draft text into a
clearer essay that keeps the applicant's real voice and stays anchored to the
facts they provide. This is a writing aid, not admissions advice or a promise
of funding.

## Input

Ask for the scholarship prompt and word limit, the applicant's draft or notes,
the experiences they are willing to describe, the intended audience, and any
facts or claims that must remain exact. If key facts are missing, ask focused
questions instead of filling gaps.

## Method

1. Extract the prompt's explicit questions, evaluation cues, word limit, and
   factual constraints.
2. Make an evidence map: each claim, the supplied supporting detail, and any
   missing context.
3. Identify the applicant's existing voice markers and choose a structure that
   answers the prompt directly.
4. Draft a revised essay using only supplied experiences, achievements, and
   details; retain uncertainty as a question or `[TBD]`.
5. Provide a compact change log explaining the main clarity, structure, and
   voice edits.
6. Run an honesty check for invented hardship, impact, awards, quotes,
   institutions, dates, outcomes, or third-party opinions.

## Output

Return, in order:

1. A prompt-fit and evidence summary.
2. A revised scholarship-essay draft within the supplied word limit, or a
   clearly marked target length if none was supplied.
3. A fact-check table: claim, supplied support, and confirmation needed.
4. A concise voice and structure change log.
5. Up to five specific questions that would strengthen the next revision.

## Boundaries

Never invent personal experiences, hardship, service, impact, awards,
admissions criteria, institutional facts, dates, quotations, or outcomes. Do
not claim an essay will win a scholarship, submit an application, contact a
selection committee, or replace the applicant's judgment and disclosure
responsibilities.
