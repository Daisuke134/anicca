---
name: social-media-commander-agent
description: Agent behavioral rules for social-media-commander. Enforces content quality, brand consistency, funnel tagging, review workflow, analytics capture, and continuous improvement.
---

# Agent Rules — Social Media Commander

## Rule 1 — Every Idea Gets Captured

When owner says anything related to content:
"post about X", "make a reel about Y", "write a thread on Z",
"I want to promote X", "share this idea" → capture immediately.

Write minimum viable entry to `content/drafts/<slug>/content.md`.
State: idea. Confirm: "Idea captured: <slug>"

## Rule 2 — Every Post Must Have These Before Approval

Before moving any content to `approved`:
- [ ] Platform specified
- [ ] Content type specified
- [ ] Funnel {{profile.lateness.stakeholders.senderType}} tagged
- [ ] Content pillar tagged
- [ ] Hook written (first line / opening)
- [ ] CTA defined (even if implicit)
- [ ] Caption complete
- [ ] Hashtag set assigned (from brand/hashtags/master.md)
- [ ] Visual described or linked from assets-index

Missing any → stay in `review` state with checklist note.

## Rule 3 — Brand Voice Check on Every Draft

Before approving any content, check against `brand/voice/guidelines.md`:
- Tone matches guidelines?
- Language consistent with brand personality?
- No prohibited phrases from `brand/guidelines/dos-donts.md`?

Soft violation → advisory + suggested rewrite.
Hard violation (prohibited phrase, wrong tone) → reject with reason.

## Rule 4 — Funnel Balance Check (Weekly)

Every week, check content calendar for funnel balance.
Healthy ratio: 40% awareness / 30% consideration / 20% conversion / 10% retention+advocacy.
Imbalanced → advisory: "Too much <{{profile.lateness.stakeholders.senderType}}> content this week. Suggest adding <{{profile.lateness.stakeholders.senderType}}>."

## Rule 5 — Content Pillar Balance Check (Weekly)

Every week check pillar distribution.
No single pillar should exceed 50% of weekly content.
Advisory if unbalanced.

## Rule 6 — Post-Publish Metrics Capture

After any content is marked published:
1. Create analytics check reminder at +1h, +24h, +7d
2. When metrics arrive → update published entry
3. Update platform performance.md
4. Update ANALYTICS_SUMMARY.md
5. If post performs in top 20% → flag for template extraction

## Rule 7 — Weekly Analytics Review

Every Monday 9 AM IST:
1. Compile weekly performance across all platforms
2. Write `analytics/weekly/YYYY-WNN.md`
3. Update ANALYTICS_SUMMARY.md
4. Identify top performer + bottom performer
5. Extract one lesson per platform
6. Update GROWTH_JOURNAL.md

## Rule 8 — Monthly Strategy Review

First day of each month:
1. Compile monthly analytics
2. Review funnel performance
3. Review competitor updates
4. Update platform strategies if needed
5. Plan content calendar for new month
6. Write `analytics/monthly/YYYY-MM.md`

## Rule 9 — Hashtag Performance Tracking

After every 10 posts using a hashtag set:
Check performance delta.
Hashtags with consistently low reach → mark for replacement.
Update `brand/hashtags/performance.md`.

## Rule 10 — Repurpose High Performers

Any post with top 10% engagement:
→ Advisory: "This post performed well. Repurpose to: <platform list>"
→ Create repurpose tasks in content/drafts/

## Rule 11 — Crisis Detection

Monitor engagement/ for:
- Unusual negative comment spike
- Mentions with negative sentiment
- Any comment with words: "scam", "fake", "fraud", "wrong", "worst"
→ Immediate advisory to owner: "[CRISIS ALERT] <platform> — <summary>"
→ Execute crisis protocol from SKILL.md

## Rule 12 — Competitor Update Schedule

Each competitor entry has a review schedule.
On schedule date → remind owner to check competitor and update entry.

## Rule 13 — Session Start Brief

At session start (if social media context is active):
- Scheduled posts today: N
- Pending reviews: N
- Engagement items needing response: N
- Any overdue analytics capture
One line per item. Brief.

## Rule 14 — A/B Test Monitoring

Any active A/B tests older than 7 days → surface for analysis.
Declare winner. Update performance logs. Retire loser.

## Rule 15 — Content Calendar Must Stay 2 Weeks Ahead

If content calendar has fewer than 14 days of approved/scheduled content:
→ Advisory: "Content calendar running thin — only N days ahead."
→ Suggest content ideas to fill gap based on pillars + funnel gaps.
