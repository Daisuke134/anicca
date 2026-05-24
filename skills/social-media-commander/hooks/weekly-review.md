---
name: social-media-commander-weekly-review
description: Runs every Monday 9 AM IST. Compiles weekly performance, identifies patterns, updates strategy.
---

# Weekly Review Hook — Monday 9 AM IST

## Step 1 — Compile Weekly Metrics

For each active platform:
- Total posts published
- Total reach
- Total engagement
- Avg engagement rate
- Followers gained/lost
- Top post (by engagement rate)
- Worst post (by engagement rate)

## Step 2 — Funnel Balance Check

Count posts by funnel {{profile.lateness.stakeholders.senderType}} this week.
Calculate percentages.
Compare to target: 40/30/20/10.
Flag imbalance if any {{profile.lateness.stakeholders.senderType}} > 20% off target.

## Step 3 — Pillar Balance Check

Count posts by content pillar.
Flag any pillar > 50% or < 5% of weekly content.

## Step 4 — Content Calendar Check

How many days ahead is the calendar?
< 14 days approved/scheduled → generate advisory + suggest ideas.

## Step 5 — Hashtag Review (every 10 posts)

Check if any hashtag set has 10+ new data points.
Update brand/hashtags/performance.md.
Flag underperformers.

## Step 6 — Write Weekly Analytics Report

Write to analytics/weekly/YYYY-WNN.md:
```markdown
# Week WNN — YYYY-MM-DD to YYYY-MM-DD

## Summary
[2-3 sentence narrative of the week]

## Platform Performance
[table: platform | posts | reach | avg_engagement% | followers_delta]

## Top Content
[slug | platform | engagement_rate | why it worked]

## Underperformer
[slug | platform | engagement_rate | why it underperformed]

## Funnel Balance
[table with actual vs target]

## Key Insights
1. [insight 1]
2. [insight 2]
3. [insight 3]

## Actions for Next Week
- [ ] [action 1]
- [ ] [action 2]
```

## Step 7 — Update GROWTH_JOURNAL.md

2-4 sentence reflection on the week's growth trajectory.

## Step 8 — Update Soul

Upsert all soul sections with fresh data.
Append [SESSION LOG].
