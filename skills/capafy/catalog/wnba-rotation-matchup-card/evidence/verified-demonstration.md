# Verified Demonstration — WNBA Rotation Matchup Card

## Concrete input

```text
Game: Harbor at Summit.
Rotation notes: Harbor closes small with Rivera at point, Lee and Moss on the wings,
and Chen as the only listed interior defender. Rivera initiates late-clock actions.
Summit's listed closing group uses its tallest scorer on Chen's side and a reserve
guard assigned to pressure Rivera. Harbor's replacement guard is not supplied.
Availability: Chen is confirmed. No current status is supplied for any other player.
Coverage goal: a 90-second podcast matchup segment, not a prediction.
```

## Actual output

```markdown
# WNBA Rotation Matchup Card: Harbor at Summit
## Evidence boundary
- Supplied: Harbor closes small with Rivera at point and Chen as its only listed interior defender.
- Supplied: Summit's tallest listed scorer works on Chen's side; a reserve guard pressures Rivera.
- Unverified: Harbor's replacement guard and every player status other than Chen.

## Rotation table
| Team | Supplied stint or assignment | Pressure point | Evidence |
| --- | --- | --- | --- |
| Harbor | Small closing group; Rivera initiates late-clock actions | Ball-handling load under the supplied reserve-guard pressure | Buyer rotation and assignment notes |
| Harbor | Chen is the only listed interior defender | Interior workload against Summit's stated size assignment | Buyer rotation and assignment notes |
| Summit | Tallest listed scorer on Chen's side | Whether the supplied closing group can preserve Chen's interior role | Buyer assignment note |

## Coverage angles
1. Harbor's stated small closing group puts two supplied matchup questions in the same segment: Rivera's late-clock initiation and Chen's listed interior workload.
2. Summit's supplied assignments make the closing-group trade-off a useful podcast angle without establishing a likely winner.

## Conditional scenarios
- If Harbor uses the supplied small closing group, the stated pressure points are Rivera's handling role and Chen's interior assignment.
- If a replacement guard enters, that player's identity and role are [UNVERIFIED], so no substitution effect is asserted.

## Verify before use
- Confirm Harbor's replacement guard and role.
- Confirm any player status other than Chen.
- Confirm whether the supplied closing groups are planned or historical.
```

## Verification notes

1. Every team, player, role, and assignment in the output appears in the concrete input.
2. The output labels the missing replacement guard and unsupplied current statuses `[UNVERIFIED]` instead of filling them in.
3. The conditional section does not predict a score, game outcome, or wager.
4. The example is self-contained text analysis: it performs no browsing, retrieval, posting, file export, or external action.
5. Differentiation check: the base catalog has NBA slate, college-basketball bubble, and volleyball rotation workflows, but no WNBA card that converts supplied five-player stints and defender assignments into a rotation stress-test and verification queue.
