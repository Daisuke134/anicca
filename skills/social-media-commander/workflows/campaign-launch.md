---
name: campaign-launch-workflow
---

# Campaign Launch Workflow

## Preconditions
- [ ] Campaign goal defined and measurable
- [ ] Budget defined (even if zero)
- [ ] Timeline defined (start + end dates)
- [ ] Target audience segment identified
- [ ] Platforms selected

## Steps

### Step 1 — Campaign Manifest
- Create campaigns/active/<id>/manifest.md
- Define: goal, KPIs, audience, platforms, budget, timeline
- Create campaign hashtag (if needed)

### Step 2 — Content Planning
- Map funnel {{profile.lateness.stakeholders.senderType}}s to content pieces needed
- Minimum: 1 awareness + 1 consideration + 1 conversion piece
- Create content entries in drafts/ with campaign tag

### Step 3 — Content Creation
- Follow content-creation-workflow for each piece
- All pieces must be approved before campaign starts

### Step 4 — Scheduling
- Schedule all content per platform best times
- Space out posts per platform frequency rules
- Create analytics reminders for each post

### Step 5 — Launch Check
- All content approved and scheduled?
- Campaign hashtag ready?
- Landing page / link in bio updated?
- Analytics baseline captured (before launch metrics)?

## Gates
- G-001: Before Step 3 — manifest must be complete
- G-002: Before Step 5 — all content must be approved
- G-003: Before launch — analytics baseline captured

## During Campaign
Daily: check engagement on campaign posts
Flag if CTR/engagement drops significantly (>30% below average)

## Post-Campaign
Write performance report in campaigns/active/<id>/performance.md
Move to campaigns/completed/ after final report
