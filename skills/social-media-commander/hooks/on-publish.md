---
name: social-media-commander-on-publish
description: Fires when content is published. Creates analytics tracking reminders and updates all logs.
---

# On-Publish Hook

## Step 1 — Mark Published
Update content entry: state → published
Add: published_at, platform_post_url (if known)

## Step 2 — Create Analytics Checkpoints
Create 3 reminders (via crons or session flags):
- +1h: capture initial engagement (likes, comments, reach)
- +24h: capture full day metrics
- +7d: capture weekly performance

## Step 3 — Update Logs
Append to CONTENT_LOG.md:
```
YYYY-MM-DD HH:MM | PUBLISHED | <slug> | <platform> | <type> | <funnel-{{profile.lateness.stakeholders.senderType}}>
```

Update soul [CONTENT PIPELINE].
Update platform/<platform>/performance.md.

## Step 4 — Calendar Update
Mark as published in calendar/YYYY-MM.md.

## Step 5 — Repurpose Check
Is this long-form content (article, video, thread)?
→ Advisory: "Consider repurposing to: <platform list>"
