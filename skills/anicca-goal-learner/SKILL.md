---
name: anicca-goal-learner
description: |
  Weekly proactive scan of the user's gcal past 30 days + gmail recent 50,
  classified against profile.identity.goals.ideal_state[]. Reports drift
  (= "you said weekly LT, actual is monthly 0.5") and proposes specific
  actions (= "book a connpass LT for next Friday").

  Composed deterministically + mailed via Gmail — no LLM required.
  Anicca's heartbeat can promote any suggestion to a concrete action.

metadata:
  tags: goals, learning, weekly, proactive
  requires:
    bins: [python3, gog]
    env: [GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
---

# anicca-goal-learner

Connects the user's stated ideal_state[] to their observed behaviour and
calls out the gap.

## Algorithm

```
ideal_state = profile.identity.goals.ideal_state[]
events_30d = gog calendar past 30 days
mails_50   = gog gmail recent 50 subjects

for goal in ideal_state:
    matches = events + mails matching goal.domain keywords
    actual_per_week = len(matches) / 4.3
    target_per_week = parse_target(goal.weekly_action)
    if actual_per_week < target_per_week * 0.7:
        drifts.append(goal)
    if actual_per_week > target_per_week * 1.3:
        excess.append(goal)

mail body:
  - For each drift: "Goal X said weekly N, observed weekly M — suggestion"
  - For each excess: "Goal X said weekly N, observed weekly M — sustainable?"
  - Top milestones (= time-bound) with countdown
  - Action items the user could book this week
```

## Cron

`0 9 * * 1`  (= Monday 09:00 JST) — same as weekly report so the user gets
one consolidated reflection at the start of the week.
