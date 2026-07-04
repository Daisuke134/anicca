---
name: ph-real-time-monitor
description: Monitor and track your Product Hunt launch in real-time. Use this skill to set up tracking systems, interpret metrics, and make data-driven decisions during your 24-hour launch window.
---

# Product Hunt Real-Time Monitor

This skill helps you set up and use monitoring systems to track your Product Hunt launch performance and make real-time adjustments.

## When to Use This Skill

- Setting up launch day tracking
- Interpreting real-time metrics
- Making mid-launch adjustments
- Identifying issues early
- Benchmarking against goals

## Key Metrics to Track

### Primary Metrics (Check Every 30 Minutes)

| Metric | What It Tells You | How to Get It |
|--------|-------------------|---------------|
| Ranking Position | Your visibility | PH homepage |
| Total Upvotes | Overall support | PH product page |
| Upvote Velocity | Momentum | Calculate hourly |
| Comments | Engagement depth | PH product page |

### Secondary Metrics (Check Hourly)

| Metric | What It Tells You | How to Get It |
|--------|-------------------|---------------|
| Website Traffic | Conversion funnel | Analytics tool |
| Signups | Actual conversion | Your database |
| Bounce Rate | Content quality | Analytics tool |
| Time on Site | Interest level | Analytics tool |

## Monitoring Setup

### Product Hunt Tracking

**Manual Method:**
- Open PH in dedicated browser tab
- Refresh every 15-30 minutes
- Log metrics in spreadsheet

**Tools:**
- **Upvote Bell** - Real-time upvote notifications
- **PH Dashboard** - Track multiple metrics
- **Custom scripts** - API-based tracking

### Analytics Dashboard

**Google Analytics 4:**
1. Create Real-Time view
2. Filter traffic source = producthunt.com
3. Monitor: Users, Events, Conversions

**Plausible/Fathom:**
- Real-time visitor dashboard
- Referrer breakdown
- Goal tracking

### Communication Hub

Set up central place for team updates:
- Slack channel (#ph-launch)
- Discord server
- WhatsApp group

## Tracking Spreadsheet Template

### Hourly Log

| Time | Rank | Upvotes | Δ | Comments | Website | Signups | Notes |
|------|------|---------|---|----------|---------|---------|-------|
| 00:00 | - | 0 | - | 0 | 0 | 0 | Launch! |
| 01:00 | #8 | 42 | +42 | 7 | 156 | 12 | Good start |
| 02:00 | #5 | 78 | +36 | 14 | 289 | 28 | Moving up |
| 03:00 | #4 | 112 | +34 | 21 | 445 | 41 | Strong |
| ... | | | | | | | |

### Velocity Tracking

```
Upvote Velocity = (Current Upvotes - Previous Upvotes) / Hours Elapsed
```

| Time Period | Upvotes Gained | Velocity |
|-------------|----------------|----------|
| Hour 1 | 42 | 42/hr |
| Hour 2 | 36 | 36/hr |
| Hour 3 | 34 | 34/hr |
| Hour 4 | 45 | 45/hr |

## Benchmark Targets

### By Hour (Weekday Launch)

| Hour | Top 5 Target | Top 3 Target | #1 Target |
|------|--------------|--------------|-----------|
| 1 | 40+ | 50+ | 60+ |
| 2 | 80+ | 100+ | 120+ |
| 4 | 150+ | 180+ | 220+ |
| 6 | 220+ | 270+ | 330+ |
| 12 | 350+ | 420+ | 500+ |
| 24 | 500+ | 600+ | 800+ |

### By Hour (Weekend Launch)

| Hour | Top 5 Target | Top 3 Target | #1 Target |
|------|--------------|--------------|-----------|
| 1 | 25+ | 35+ | 45+ |
| 2 | 50+ | 70+ | 90+ |
| 4 | 100+ | 130+ | 160+ |
| 6 | 150+ | 190+ | 230+ |
| 12 | 220+ | 280+ | 350+ |
| 24 | 300+ | 400+ | 500+ |

## Interpreting Signals

### Positive Signals
- ✅ Upvote velocity stable or increasing
- ✅ Comments are substantive
- ✅ Ranking climbing or stable
- ✅ Healthy website traffic-to-signup ratio
- ✅ Organic shares appearing

### Warning Signals
- ⚠️ Velocity dropping significantly
- ⚠️ Ranking falling
- ⚠️ High traffic but low signups
- ⚠️ Negative comment sentiment
- ⚠️ Technical issues reported

### Red Flags
- 🚨 Sudden large upvote removal
- 🚨 Product unfeatured
- 🚨 Website down
- 🚨 Spam accusations

## Real-Time Adjustments

### If Velocity is Dropping

**Diagnose:**
- Natural lull (check time of day)?
- Competition heating up?
- Content not resonating?

**Actions:**
1. Activate next supporter wave early
2. Push social media reminder
3. Engage more in comments
4. Share progress milestone

### If Ranking is Falling

**Diagnose:**
- New strong competitor launched?
- Your velocity vs theirs?
- Comments/engagement quality?

**Actions:**
1. Focus on comment quality, not just upvotes
2. Don't panic-blast emails
3. Maintain steady engagement
4. Accept gracefully if outperformed

### If Conversion is Low

**Diagnose:**
- Is landing page clear?
- Is onboarding broken?
- Is offer compelling?

**Actions:**
1. Check for technical issues
2. Review landing page clarity
3. Test signup flow yourself
4. Adjust CTA if needed

### If Comments Turn Negative

**Actions:**
1. Respond professionally
2. Address legitimate concerns
3. Don't argue or get defensive
4. Learn from feedback

## Alert System Setup

### Set Up Notifications For:

**Product Hunt:**
- New comments (check frequently)
- Major upvote milestones
- Ranking changes

**Website:**
- Traffic spikes
- Error rates
- Server load

**Communication:**
- Team messages
- Supporter questions

### Tools for Alerts
- Email notifications from PH
- Upvote Bell alerts
- Analytics alerts (GA, etc.)
- UptimeRobot (website monitoring)
- Slack/Discord integrations

## Competitor Monitoring

### Track Top 5 Competitors

| Product | Upvotes | Comments | Velocity | Threat Level |
|---------|---------|----------|----------|--------------|
| [Comp 1] | | | | |
| [Comp 2] | | | | |
| [Comp 3] | | | | |
| [Comp 4] | | | | |
| [Comp 5] | | | | |

### Assess Threat Level
- **Low:** Different category, not competing
- **Medium:** Similar product, similar traction
- **High:** Strong product, outpacing you

## Status Update Templates

### Hourly Internal Update
```
📊 HOUR [X] UPDATE

Rank: #[X] ([↑/↓/→])
Upvotes: [X] (+[X] this hour)
Comments: [X] (+[X] this hour)
Website: [X] visits, [X] signups

Velocity: [X]/hour (target: [X]/hour)
Status: [On track / Behind / Ahead]

Next actions:
→ [Action 1]
→ [Action 2]
```

### Team Alert (Issue)
```
⚠️ ATTENTION NEEDED

Issue: [Description]
Impact: [What's affected]
Action needed: [What to do]
Owner: [Who's handling]

Please [specific request].
```

### Social Progress Update
```
[X] hours in! 🚀

• #[X] on @ProductHunt
• [X] upvotes and counting
• [X] amazing comments

Thanks for the support! 🙏
→ [Link]
```

## End-of-Day Summary

### Metrics Summary
```
📊 FINAL RESULTS: [Product Name]

RANKING
Final Position: #[X] of the Day
Peak Position: #[X] at [Time]

ENGAGEMENT
Total Upvotes: [X]
Total Comments: [X]
Featured in Newsletter: [Yes/No]

CONVERSION
Website Visits: [X]
Signups: [X]
Conversion Rate: [X]%

COMPARISON
Goal: [Original target]
Result: [Actual result]
Status: [Met / Exceeded / Missed]
```

### Learnings Log
```
📝 LEARNINGS

What Worked:
• [Successful tactic]
• [Successful tactic]

What Didn't:
• [Unsuccessful tactic]
• [Unsuccessful tactic]

Surprises:
• [Unexpected observation]

For Next Time:
• [Actionable improvement]
• [Actionable improvement]
```

## Monitoring Checklist

### Setup (Night Before)
- [ ] Tracking spreadsheet ready
- [ ] Analytics dashboard configured
- [ ] Team communication channel set
- [ ] Notification alerts enabled
- [ ] Competitor list prepared

### During Launch
- [ ] Logging metrics every hour
- [ ] Monitoring alerts
- [ ] Tracking velocity trends
- [ ] Watching competitors
- [ ] Sharing updates with team

### After Launch
- [ ] Final metrics captured
- [ ] Summary prepared
- [ ] Learnings documented
- [ ] Screenshots saved
