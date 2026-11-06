# Verified demonstration — Football Press-Rehearsal Brief

## Concrete input

```text
Opponent press notes: In our last two analyst clips, Vale's front three closed the goalkeeper
and tried to steer the first pass toward our right touchline. When the right full-back received
facing their own goal, their near midfielder stepped forward. These are notes from our staff,
not a complete opposition record.

Own squad constraints: Our left centre-back is unavailable. The goalkeeper and one holding
midfielder are available. We want the replacement left centre-back role to have a simple first action.

Training objective: Rehearse one safe first-phase exit from the stated goalkeeper close-down.
Session time: 25 minutes.
```

## Actual output

```markdown
# Vale Press-Rehearsal Brief

## Supplied record
- Opponent note: Vale's front three closed the goalkeeper and steered the first pass toward the right touchline in two staff-noted clips.
- Opponent note: a near midfielder stepped when the right full-back received facing their own goal.
- Own constraint: the left centre-back is unavailable; the goalkeeper and one holding midfielder are available.
- [UNVERIFIED]: Vale's lineup, whether the trigger appears on both sides, and the replacement defender's preferred foot.

## Rehearsal problem
If the stated goalkeeper close-down steers the first pass right, rehearse a simple left-side replacement role and holding-midfielder outlet before the right full-back receives back-facing pressure.

## Primary rehearsal — goalkeeper exit with pivot outlet
- Setup: 6 x 20m grid; goalkeeper, right and replacement-left centre-back roles, holding-midfielder role, and three press roles. Run four 3-minute blocks inside the 25-minute session.
- Progression: begin with the stated three-player goalkeeper close-down. The replacement-left centre-back's first action is an open support angle; the holding midfielder offers a second line only after the first pass.
- Reset rule: reset when the ball is played to the right full-back role facing their own goal without a stated support angle.

## Fallback rehearsal — delayed right-side release
- Setup: use the same roles, but require the right full-back role to receive only after the holding-midfielder role has moved into a visible outlet lane.
- Trade-off: this reduces the stated back-facing pressure moment, but it may slow the first exit; the supplied notes do not establish whether Vale allow that extra time.

## Coaching cues
1. Goalkeeper: name the first safe side before the press role reaches you.
2. Replacement left centre-back: show an open body shape, then take the simple first action.
3. Holding midfielder: arrive as an outlet after the first pass, not on the same line as it.

## Verify before final assignment
- Confirm whether the stated steering pattern appears against both centre-back sides.
- Confirm the replacement left centre-back's receiving comfort.
- Confirm the available training numbers before fixing player assignments.
```

## Verification notes

- The output was generated offline from the concrete input above; it relies on no external match feed, opponent database, or player lookup.
- Every football-specific fact in the output is either quoted from the input or marked `[UNVERIFIED]`.
- The output has a primary rehearsal, a fallback with a trade-off, three observable coaching cues, and a verification queue, matching the SKILL.md quality gate.
- The listing makes no claim that the skill has access to current lineups, match feeds, or result prediction.
