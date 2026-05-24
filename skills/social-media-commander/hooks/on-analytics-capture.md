---
name: social-media-commander-on-analytics-capture
description: Fires at +1h, +24h, +7d after publish. Captures metrics and analyses performance.
---

# On-Analytics-Capture Hook

## Metrics to Capture by Platform

### Instagram
- Reach, Impressions, Likes, Comments, Saves, Shares, Profile visits, Follows from post

### Twitter/X
- Impressions, Engagements, Likes, Retweets, Quote tweets, Replies, Link clicks, Profile visits

### LinkedIn
- Impressions, Reactions, Comments, Shares, Clicks, CTR, Follows from post

### YouTube
- Views, Watch time, CTR (thumbnail), Likes, Comments, Subscribers gained, Retention rate

### Threads/Telegram/WhatsApp Channel
- Views, Likes, Replies, Reposts

## Engagement Rate Formula
`(Likes + Comments + Saves + Shares) / Reach × 100`

## Performance Classification

| Rate | Classification |
|---|---|
| > 5% | Viral / exceptional |
| 3-5% | High performing |
| 1-3% | Average |
| < 1% | Under-performing |

## After Capture

1. Update content entry with metrics
2. Update platform/performance.md
3. Update ANALYTICS_SUMMARY.md
4. If top 20% → flag for template extraction + soul [TOP PERFORMING CONTENT]
5. If bottom 20% → add to improvement review queue
6. At 7d: close analytics cycle, write final assessment in entry

## Final Assessment Format (7d)
```markdown
## Performance Summary (7d)
- Reach: N | Engagement rate: N%
- Classification: viral / high / average / under
- Best element: [what worked — hook / visual / timing / topic]
- Weak element: [what didn't — hook / cta / hashtags / timing]
- Lesson: [one sentence]
- Repurpose: yes [platforms] / no
- Template worthy: yes / no
```
