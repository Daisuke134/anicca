---
name: football-press-rehearsal-brief
description: >
  Turns a coach's pasted opposition-press notes and squad constraints into a football build-out rehearsal brief.
  Use when planning a training session against a known pressing problem without claiming match-feed or scouting access.
license: MIT
version: "1.0.0"
tags: [football, coaching, pressing, training, analysis]
compatibility: "Claude Code, ChatGPT, Gemini CLI, Cursor, Windsurf, OpenClaw, any AI agent"
metadata:
  author: anicca
  version: "1.0"
  stage: S1-Research
---

# Football Press-Rehearsal Brief

This skill converts the buyer's own notes about an opponent's press and their available players into a practical, text-only rehearsal brief. It separates supplied observations from coaching hypotheses so a staff member can use the output as a session starting point without mistaking it for a scouting feed or a promise of match performance.

## Stage

S1-Research — evidence-bounded tactical preparation.

## When to Use

- A coach has written notes about an opponent's high press and needs a build-out practice before the next match.
- An academy analyst must turn a few observed pressing triggers into roles, constraints, and coaching cues.
- A staff member wants to compare two supplied build-out responses without inventing unavailable players or opposition facts.
- A football writer needs a disciplined training-plan explainer from their own tactical notes.

## Input Schema

```text
opponent_press_notes: string (required) — pasted observations, not assumed facts
own_squad_constraints: string (required) — available roles, absences, strengths, or limits
training_objective: string (required) — one behaviour to rehearse
session_time_minutes: integer (optional, default 25) — available rehearsal time
preferred_build_shape: string (optional) — a supplied starting shape; do not infer one as fact
```

## Workflow

### Step 1: Extract the supplied record

List every opponent observation, own-team constraint, and requested objective separately. Preserve uncertainty and label missing information `[UNVERIFIED]`. Good work does not turn a single note into a complete opposition profile.

### Step 2: Define the rehearsal problem

State one build-out problem in a sentence using only the supplied record, then name the trigger, intended response, and failure condition. The response must remain conditional when a lineup, shape, or pressure cue was not provided.

### Step 3: Build two constrained practice options

Create a primary rehearsal and one fallback. For each, specify player numbers or roles only where supplied; otherwise use role placeholders. Include setup, progression, reset rule, and one measurable observation the staff can record.

### Step 4: Add coaching cues and trade-offs

Give three concise cues tied to the stated problem. Explain one advantage and one risk for each option; do not claim the plan will defeat the press or predict a result.

### Step 5: Close the evidence gap

Finish with a verification queue of information the buyer should confirm before assigning final roles. A high-quality answer makes unknowns usable rather than hiding them.

## Output Schema

```json
{
  "output_schema_version": "1.0.0",
  "supplied_record": {"opponent_notes": ["string"], "own_constraints": ["string"]},
  "rehearsal_problem": "string",
  "primary_rehearsal": {"setup": "string", "progression": "string", "reset_rule": "string"},
  "fallback_rehearsal": {"setup": "string", "trade_off": "string"},
  "coaching_cues": ["string"],
  "verification_queue": ["string"]
}
```

## Output Format

```markdown
# [Opponent] Press-Rehearsal Brief

## Supplied record
- Opponent note: [pasted observation]
- Own constraint: [pasted constraint]
- [UNVERIFIED]: [missing fact]

## Rehearsal problem
[conditional problem statement]

## Primary rehearsal — [name]
- Setup: [roles, area, and time]
- Progression: [trigger and response]
- Reset rule: [observable failure condition]

## Fallback rehearsal — [name]
- Setup: [alternative constrained option]
- Trade-off: [benefit and risk]

## Coaching cues
1. [cue]
2. [cue]
3. [cue]

## Verify before final assignment
- [unknown to confirm]
```

## Error Handling

- **No opponent observation:** ask for at least one pasted trigger, pressing location, or recovery behaviour; do not create a fictional opposition report.
- **No squad constraints:** use neutral role placeholders and mark player assignments `[UNVERIFIED]`.
- **Conflicting notes:** preserve both claims, describe the conflict, and make both rehearsal options conditional.
- **Request for a guaranteed result:** decline the guarantee and offer an evidence-bounded practice plan instead.
- **Request for match-feed facts:** explain that the skill works from pasted notes and model knowledge, then request the relevant notes.

## Examples

**Example 1: High press on the goalkeeper**

Input: opponent notes say the front three close the goalkeeper and force play toward the right touchline; the left centre-back is unavailable; objective is to exit the first line.

Decision: retain the right-side forcing note, do not assume the opponent's current lineup, and make the left-side replacement a role placeholder.

Output excerpt: “Primary rehearsal: goalkeeper, two centre-back roles, and one pivot role against three press roles. Start with the stated goalkeeper close-down. Score a reset when the ball is forced to the right touchline without a stated outlet.”

**Example 2: Mid-block trigger**

Input: notes say the opponent jump when a full-back receives facing their own goal; a receiving midfielder is available; objective is to rehearse a third-player exit.

Decision: build a trigger-response pattern and add a fallback that changes the receiver's starting position.

Output excerpt: “If the supplied jump appears on the back-facing full-back, rehearse a third-player support angle. The notes do not establish whether the opponent repeats this trigger on both sides; confirm that before finalising the session.”

## Flywheel Connections

### Feeds Into

- `football-match-analyst` — the buyer can add the rehearsal constraints to a future fixture discussion.
- `football-postmatch-decision-review` — staff can compare the planned cue with their own completed-match notes.

### Fed By

- Buyer-maintained opposition notes and squad availability notes.
- `football-set-piece-plan-brief` when a staff member separately prepares dead-ball work.

### Feedback Loop

After a session, the buyer can paste their own observed success and failure notes to tighten the next rehearsal's reset rules and verification queue.

```yaml
chain_metadata:
  skill_slug: football-press-rehearsal-brief
  stage: S1-Research
  timestamp: "2026-11-04"
  suggested_next:
    - football-postmatch-decision-review
    - football-match-analyst
```

## Quality Gate

1. Input contains at least one opponent observation and one own-team constraint, or the response requests them.
2. Every claimed fact is traceable to pasted input; unknown facts use `[UNVERIFIED]`.
3. The output contains one primary and one fallback rehearsal with a stated trade-off.
4. Each rehearsal has a setup, trigger/progression, and reset rule.
5. No player, lineup, match-feed, or result is asserted unless the buyer supplied it.
6. Coaching cues are observable behaviours, not outcome promises.
7. The verification queue contains at least one actionable unknown when the input is incomplete.

## References

- `LISTING.md` — buyer-facing subscription copy and plan limits.
- `evidence/verified-demonstration.md` — concrete offline input, output, and verification record.
