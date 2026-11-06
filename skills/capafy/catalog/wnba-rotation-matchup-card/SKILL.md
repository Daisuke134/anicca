---
name: wnba-rotation-matchup-card
description: >
  Turn buyer-pasted WNBA rotation notes, defender assignments, and availability context into a source-bounded rotation matchup card. Use when a basketball writer, coach, or podcast producer needs to explain lineup-stint trade-offs without claiming current data.
license: MIT
version: "1.0.0"
tags: [wnba, basketball, rotations, matchup-analysis, sports-writing]
compatibility: "Claude Code, ChatGPT, Gemini CLI, Cursor, Windsurf, OpenClaw, any AI agent"
metadata:
  author: anicca
  version: "1.0"
  stage: S2-Analysis
---

# WNBA Rotation Matchup Card

WNBA Rotation Matchup Card turns the specific rotation facts a buyer already has into a practical, text-only matchup card. Rather than writing a whole-slate preview, it traces the supplied five-player stints, defensive assignments, and availability contingencies so a writer or coach can see which lineup questions deserve explanation.

## Stage

This skill belongs to Stage S2: Analysis.

## When to Use

- A WNBA writer has coach quotes, prior-stint notes, and assignment context for one upcoming game.
- A podcast producer needs a structured rundown of how supplied rotation changes could alter a matchup.
- A coach or analyst wants to organize a pasted rotation plan into questions and contingencies without inventing roster facts.

## Input Schema

```text
game: string (required) — the two teams and home/away context as supplied
rotation_notes: string (required) — named five-player stints, minutes or sequence notes, and role descriptions
matchup_notes: string (required) — supplied defensive assignments, tactical tendencies, or prior observations
availability_notes: string (optional) — supplied confirmed, doubtful, or unavailable-player notes
coverage_goal: string (optional) — coaching, article, podcast, or fan-analysis angle
```

## Workflow

### Step 1: Make an evidence ledger

Extract each team, player, stint, assignment, statistic, and status statement exactly as supplied. Separate direct facts from proposed interpretations. Mark a missing roster, minute, result, or health fact `[UNVERIFIED]`; never fill it with model knowledge.

### Step 2: Map supplied rotation pressure points

For every supplied lineup stint, identify its stated ball-handling, rim protection, shooting, rebounding, or defensive-assignment role only where the input supports it. State the matchup pressure point and the evidence behind it. Do not rank a lineup as better unless the buyer supplied a comparison.

### Step 3: Write conditional assignment scenarios

For each supplied availability or rotation uncertainty, write a clearly conditional `if available` / `if unavailable` or `if this stint is used` scenario. Explain the question the scenario raises, not a predicted score, outcome, or wagering edge.

### Step 4: Deliver the matchup card

Return a rotation table, the two or three most supported coverage angles, conditional scenarios, and a verification queue. Keep every conclusion traceable to the ledger and keep unknowns visible.

## Output Schema

```text
output_schema_version: "1.0.0"
game: string
evidence_ledger: list<{claim: string, status: "supplied" | "unverified"}>
rotation_table: list<{team: string, stint: string, pressure_point: string, evidence: string}>
coverage_angles: list<{angle: string, support: string}>
conditional_scenarios: list<string>
verification_queue: list<string>
```

## Output Format

```markdown
# WNBA Rotation Matchup Card: [away] at [home]
## Evidence boundary
- Supplied: [fact]
- Unverified: [missing fact]

## Rotation table
| Team | Supplied stint or assignment | Pressure point | Evidence |
| --- | --- | --- | --- |

## Coverage angles
1. [angle grounded in supplied material]
2. [angle grounded in supplied material]

## Conditional scenarios
- If [supplied condition]: [evidence-bound question or effect]

## Verify before use
- [missing fact to confirm]
```

## Error Handling

- **No rotation facts:** ask for at least one named lineup, role, or stint note before producing a card.
- **Conflicting assignments:** present both supplied versions, label the conflict, and ask which version controls.
- **Availability absent:** mark status `[UNVERIFIED]`; do not infer injuries or transactions.
- **Wagering or certainty request:** explain that the card is a source-bounded discussion aid, not betting advice or an outcome forecast.
- **Unsupported player claim:** retain it only as an attributed buyer note and add it to the verification queue.

## Examples

### Example 1: One closing-unit question

**Input:** Harbor starts a small closing group with Rivera at point and Chen as the only listed interior defender. Summit puts its tallest scorer on Chen's side; Harbor's coach said Rivera initiates late-clock actions. Chen's availability is confirmed.

**Key decisions:** Treat the coach quote and assignment as supplied; do not claim a current roster or predict the result.

**Output excerpt:** `Harbor's supplied small closing group concentrates late-clock initiation with Rivera while leaving Chen as the only listed interior defender. The supported coverage question is whether Summit's stated size assignment tests that interior workload; no result is implied.`

### Example 2: Uncertain bench role

**Input:** Bay's second unit uses Patel beside two listed shooters. The buyer notes Patel was limited in the previous game but gives no status for this game. Ridge's reserve guard is described as a point-of-attack defender.

**Key decisions:** Mark current availability unknown and frame both alternatives conditionally.

**Output excerpt:** `If Patel is available for the supplied second-unit stint, the stated question is how Ridge's reserve pressure meets that ball-handling role. If not, the replacement ball-handler is [UNVERIFIED].`

## Flywheel Connections

- **Feeds Into:** `sports-podcast-run-sheet`, `basketball-game-preview-editorial-brief`.
- **Fed By:** buyer-pasted coach quotes, rotation charts, assignment notes, and game observations.
- **Feedback Loop:** buyers can paste the verification queue after the game to make the next rotation card more specific without changing the evidence boundary.

```yaml
chain_metadata:
  skill_slug: wnba-rotation-matchup-card
  stage: S2-Analysis
  timestamp: "2026-11-05"
  suggested_next:
    - sports-podcast-run-sheet
    - basketball-game-preview-editorial-brief
```

## Quality Gate

1. The output names only teams and players supplied by the buyer.
2. Every rotation pressure point cites a supplied stint, role, assignment, or note.
3. Current availability is conditional or `[UNVERIFIED]` unless explicitly supplied.
4. The card separates facts, inference, and verification needs.
5. It provides no live-data, wagering, certainty, or performance claim.
6. The final verification queue contains only facts the buyer can check or add.

## References

- `LISTING.md` — buyer-facing offer, market rationale, and plan limits.
- `evidence/verified-demonstration.md` — concrete offline input, output, and verification notes.
