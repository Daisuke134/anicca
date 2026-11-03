---
name: college-basketball-bubble-brief
description: >
  Turn buyer-pasted college basketball team-resume notes, conference-tournament
  context, and comparison criteria into a source-bounded bubble brief. Use when
  a college basketball writer, podcast producer, or fan-site editor needs a
  disciplined explanation of the supplied at-large case without claiming access
  to current bracketology, rankings, schedules, or results.
license: MIT
version: "1.0.0"
tags: [college-basketball, ncaa, bubble, tournament, sports-writing, analysis]
compatibility: "Claude Code, ChatGPT, Gemini CLI, Cursor, Windsurf, OpenClaw, any AI agent"
metadata:
  author: anicca
  version: "1.0"
  stage: S2-Analysis
---

# College Basketball Bubble Brief

College Basketball Bubble Brief transforms a buyer's own team-resume notes into
a traceable at-large-case brief for one college basketball team. It separates
the buyer's supplied results, opponent context, injuries, and committee-style
criteria from interpretation; missing facts remain `[UNVERIFIED]`. The result
is a reusable editorial brief, not a claim about a current selection decision.

## Stage

This skill belongs to Stage S2: Analysis.

## When to Use

- A college basketball writer has a team's supplied résumé notes and needs a
  qualified bubble-case article angle.
- A podcast producer wants a concise, evidence-bound tournament discussion for
  one team rather than a full-game preview.
- A fan-site editor needs to compare the buyer-supplied positive and negative
  résumé evidence without inventing rankings or results.

## Input Schema

```text
team: string (required) — team, conference, and season stage if known
resume_notes: string (required) — buyer-pasted wins, losses, opponent context, ranking metrics, or schedule-strength notes
availability_context: string (optional) — buyer-pasted injury, suspension, or return context and dates if known
comparison_context: string (optional) — buyer-pasted peer teams, committee criteria, or desired comparison frame
coverage_goal: string (optional) — article, podcast, fan-site update, and desired length
```

## Workflow

### Step 1: Set the evidence boundary

List the supplied résumé facts, availability context, and comparison criteria.
Label any missing selection criteria, current ranking, schedule update, or
result `[UNVERIFIED]`. Do not replace a missing current fact with model
knowledge.

### Step 2: Build the at-large case

Organize the supplied material into positive evidence, counterevidence,
availability context, and evidence strength. For each point, state the buyer
fact, a cautious editorial reading, confidence, and limitation. The quality
bar is a source-bounded case, not a bracket prediction.

### Step 3: Write conditional scenarios

Where the buyer supplies a forthcoming tournament game, an uncertain player,
or a missing peer comparison, produce `if` scenarios. Keep them as editorial
questions rather than declaring a bid or a seed.

### Step 4: Deliver the coverage package

Return an at-large case table, two or three evidence-bound coverage angles, a
verification queue, and a 45-second bubble rundown. The package must be useful
to a writer or host even when current bracketology is unavailable.

## Output Schema

```text
output_schema_version: "1.0.0"
team_label: string
evidence_boundary: string[]
at_large_case: { area: string, supplied_fact: string, editorial_read: string, confidence: "low" | "medium" | "high", limitation: string }[]
scenario_cards: { condition: string, coverage_implication: string }[]
coverage_angles: { angle: string, supporting_input: string, caveat: string }[]
verification_queue: string[]
bubble_rundown: string
```

## Output Format

```markdown
# College Basketball Bubble Brief: [team]

## Evidence boundary
- Supplied: [fact]
- [UNVERIFIED]: [missing current fact]

## At-large case
| Area | Supplied fact | Editorial read | Confidence | Limitation |
| --- | --- | --- | --- | --- |
| [positive case/countercase/availability/comparison] | [fact] | [evidence-bound interpretation] | [low/medium/high] | [gap] |

## Scenario cards
- If [condition]: [coverage implication].

## Coverage angles
1. [angle] — Evidence: [supplied material]. Caveat: [limitation].

## Verify before using
- [current fact to confirm]

## 45-second bubble rundown
[brief, source-bounded spoken summary]
```

## Error Handling

- **No team or résumé notes supplied:** Ask for one team and the buyer's notes;
  do not produce a generic bracket forecast.
- **Conflicting results or metrics:** Quote both supplied claims in the evidence
  boundary and ask which source should control the revision.
- **Request for current rankings, selection projections, schedules, or results:**
  Explain that the skill reasons only over pasted material and request the
  specific facts to analyze.
- **Request for a certain bid, seed, or betting pick:** Decline certainty
  framing and provide conditional editorial questions instead.

## Quality Gate

1. The output identifies exactly one buyer-supplied college basketball team.
2. Every named result, metric, availability detail, and peer comparison traces
   to the pasted input or is labeled `[UNVERIFIED]`.
3. Each at-large-case row includes a supplied fact, interpretation, confidence,
   and limitation.
4. Any future game, uncertain player, or absent peer comparison produces a
   conditional scenario rather than a bid or seed claim.
5. The brief contains no wagering advice, current-information claim, certain
   tournament outcome, or guaranteed selection result.
6. The verification queue includes only facts that would materially improve a
   later revision.

## References

- `LISTING.md` — buyer-facing offer, plans, and capability boundary.
- `evidence/verified-demonstration.md` — concrete offline input, output, and
  verification record.
