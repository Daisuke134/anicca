# Verified demonstration — College Basketball Bubble Brief

## Concrete input

```text
team: Northbridge Falcons, Metro Conference, conference quarterfinal week
resume_notes: The buyer's notes list two wins over teams ranked inside their chosen top 40 measure, one neutral-court win over a top-75 team, and one home loss to a team outside their chosen top 150 measure. The buyer notes a 9-6 record in conference play. No overall record, schedule-strength figure, committee ranking, or peer-team resume is supplied.
availability_context: Northbridge's starting guard is questionable after missing the previous game. No final status is supplied.
comparison_context: The buyer wants an at-large case for a tournament podcast; no named bubble peers are supplied.
coverage_goal: 45-second pre-conference-quarterfinal discussion.
```

## Actual output

```markdown
# College Basketball Bubble Brief: Northbridge Falcons

## Evidence boundary
- Supplied: two buyer-noted wins over teams inside the buyer's chosen top-40 measure.
- Supplied: one buyer-noted neutral-court win over a top-75 team and one home loss outside the buyer's chosen top-150 measure.
- Supplied: a 9-6 conference record and a starting guard listed questionable after missing the previous game.
- [UNVERIFIED]: overall record, schedule-strength figure, committee ranking, peer-team resumes, and final guard status.

## At-large case
| Area | Supplied fact | Editorial read | Confidence | Limitation |
| --- | --- | --- | --- | --- |
| Positive case | Two supplied top-40 wins plus one neutral-court top-75 win | The supplied quality wins give the case its clearest positive evidence. | medium | The chosen measure and full schedule context are not supplied. |
| Countercase | One supplied home loss outside the chosen top 150 | This is the clearest negative item in the pasted case and should be addressed directly. | medium | No loss profile or peer comparison is supplied. |
| Conference context | 9-6 in conference play | The record gives context but does not establish comparative standing by itself. | low | No standings, strength, or tournament seeding is supplied. |
| Availability | Starting guard questionable after missing the prior game | The quarterfinal coverage should remain conditional on the final status. | low | No final availability or replacement-role information is supplied. |

## Scenario cards
- If the guard is available: frame the quarterfinal as a chance to add to the supplied quality-win case, not as a bid guarantee.
- If the guard is unavailable: foreground the availability uncertainty and avoid assuming how the offense changes.
- If peer resumes are added: compare only the supplied criteria in the next revision.

## Coverage angles
1. The quality-wins-versus-bad-loss tension — Evidence: the two supplied top-40 wins and one outside-top-150 home loss. Caveat: the full schedule and measure definition are missing.
2. The conference-quarterfinal leverage question — Evidence: the supplied 9-6 conference record and upcoming quarterfinal context. Caveat: no opponent or seeding information is supplied.
3. The guard-status wrinkle — Evidence: the buyer's questionable designation after a missed game. Caveat: the final status is unknown.

## Verify before using
- Confirm the buyer's ranking measure and the full résumé record.
- Add current peer-team résumés if a comparative bubble segment is required.
- Confirm the guard's final availability and the quarterfinal opponent.

## 45-second bubble rundown
Northbridge's supplied case starts with quality: two buyer-noted top-40 wins and a neutral-court top-75 win. The complication is the supplied home loss outside the top 150, which is the cleanest counterargument in this record. A 9-6 conference mark adds context but cannot settle the comparison without a fuller schedule and peer résumés. The conference quarterfinal matters as the next evidence point, but the starting guard is questionable after missing the last game, so any preview should stay conditional. Confirm the ranking measure, peer cases, opponent, and final availability before treating this as more than a source-bounded bubble discussion.
```

## Verification notes

- **Input traceability:** Every team reference, résumé item, conference record, and availability detail in the output comes from the concrete input; no rankings, results, opponents, or player facts were added.
- **Unknown handling:** Overall record, schedule strength, committee ranking, peer cases, opponent, and final availability remain `[UNVERIFIED]` and are listed for confirmation.
- **Capability boundary:** The demonstration is self-contained text analysis of buyer-pasted notes. It does not claim browsing, current bracket retrieval, wagering, or a guaranteed bid or seed.
- **Output contract:** The output contains every SKILL.md output-schema field: `team_label`, `evidence_boundary`, `at_large_case`, `scenario_cards`, `coverage_angles`, `verification_queue`, and `bubble_rundown`.
- **Quality gate:** Exactly one supplied team is analyzed; every table row has a fact, interpretation, confidence, and limitation; uncertainty is conditional; and the verification queue is limited to facts that would improve a later revision.
