---
name: ph-analytics-setup
description: Set up analytics tracking for your Product Hunt launch. Use this skill to configure tracking tools, create dashboards, and ensure you capture all important launch metrics.
---

# Product Hunt Analytics Setup

This skill helps you set up comprehensive analytics tracking to measure your Product Hunt launch performance and optimize your funnel.

## When to Use This Skill

- Before launch: Setting up tracking infrastructure
- Launch day: Monitoring real-time metrics
- Post-launch: Analyzing results and ROI

## Essential Metrics to Track

### Product Hunt Metrics
| Metric | Source | Importance |
|--------|--------|------------|
| Ranking position | PH homepage | Critical |
| Total upvotes | PH product page | Critical |
| Comments | PH product page | High |
| Saves/bookmarks | PH product page | Medium |

### Website Metrics
| Metric | Source | Importance |
|--------|--------|------------|
| Total visitors | Analytics | Critical |
| PH referral traffic | Analytics | Critical |
| Bounce rate | Analytics | High |
| Time on site | Analytics | Medium |
| Pages per session | Analytics | Medium |

### Conversion Metrics
| Metric | Source | Importance |
|--------|--------|------------|
| Signups | Your database | Critical |
| Trial starts | Your database | High |
| Purchases | Payment system | Critical |
| Conversion rate | Calculated | Critical |

## Analytics Tools Setup

### 1. Google Analytics 4

**Basic Setup:**
1. Create GA4 property
2. Install tracking code
3. Set up events
4. Create conversion goals

**Key Events to Track:**
```javascript
// Page view (automatic)
// Signup started
gtag('event', 'signup_started', {
  'source': 'producthunt'
});

// Signup completed
gtag('event', 'signup_completed', {
  'source': 'producthunt',
  'plan': 'free'
});

// Trial started
gtag('event', 'trial_started', {
  'source': 'producthunt',
  'plan': 'pro'
});

// Purchase completed
gtag('event', 'purchase', {
  'source': 'producthunt',
  'value': 99.00,
  'currency': 'USD'
});
```

**UTM Parameters:**
Add to all your links:
```
?utm_source=producthunt
&utm_medium=social
&utm_campaign=launch_jan2024
```

**Real-Time Dashboard:**
- Navigate to Reports > Realtime
- Filter by Traffic Source = producthunt.com

---

### 2. Plausible Analytics (Privacy-Focused Alternative)

**Setup:**
1. Add script to website
2. Configure goals
3. Set up custom events

**Benefits for PH Launch:**
- Real-time by default
- Clean, simple dashboard
- No cookie consent needed
- Easy referrer tracking

---

### 3. Mixpanel / Amplitude (Product Analytics)

**For Deeper Funnel Analysis:**

**Events to Track:**
```
- Page Viewed (with source)
- Signup Started
- Signup Completed
- Onboarding Step 1
- Onboarding Step 2
- Onboarding Completed
- Feature Used (first time)
- Upgrade Clicked
- Payment Completed
```

**Cohort Analysis:**
- Compare PH users vs other sources
- Retention by acquisition source
- Feature adoption by source

---

### 4. Product Hunt Specific Tracking

**Manual Tracking Spreadsheet:**

| Time | Rank | Upvotes | Δ Upvotes | Comments | Visits | Signups |
|------|------|---------|-----------|----------|--------|---------|
| 00:00 | - | 0 | - | 0 | 0 | 0 |
| 01:00 | | | | | | |
| 02:00 | | | | | | |

**Tools for PH Tracking:**
- Upvote Bell (upvote notifications)
- Manual refresh and logging
- Custom scripts (PH API)

## Dashboard Setup

### Launch Day Dashboard

**Create a single view showing:**

```
┌─────────────────────────────────────────────────┐
│           PRODUCT HUNT LAUNCH DASHBOARD         │
├─────────────────────────────────────────────────┤
│                                                 │
│  PH METRICS          │  WEBSITE METRICS        │
│  ───────────         │  ─────────────────      │
│  Rank: #4            │  Visitors: 1,234        │
│  Upvotes: 234        │  From PH: 987 (80%)     │
│  Comments: 45        │  Bounce: 34%            │
│                      │                         │
├─────────────────────────────────────────────────┤
│                                                 │
│  CONVERSIONS         │  HOURLY TREND           │
│  ────────────        │  ────────────           │
│  Signups: 156        │  [Chart showing         │
│  Conv Rate: 12.6%    │   upvotes over time]    │
│  Revenue: $1,240     │                         │
│                      │                         │
└─────────────────────────────────────────────────┘
```

**Tools for Dashboards:**
- Google Data Studio (free)
- Grafana (self-hosted)
- Geckoboard
- Notion (manual)

## Tracking Implementation Checklist

### Before Launch (Required)

**Website Analytics:**
- [ ] Google Analytics 4 installed
- [ ] Real-time dashboard accessible
- [ ] UTM parameters prepared
- [ ] Referrer tracking verified

**Conversion Tracking:**
- [ ] Signup event tracking
- [ ] Purchase event tracking
- [ ] Goals/conversions configured
- [ ] Test conversions working

**Referrer Attribution:**
- [ ] producthunt.com identified correctly
- [ ] Can filter traffic by source
- [ ] Landing page tracking works

### Before Launch (Recommended)

**Advanced Setup:**
- [ ] Custom dashboard created
- [ ] Alerts configured
- [ ] A/B testing tools ready
- [ ] Heatmap tool installed (Hotjar, etc.)

**Spreadsheet Tracking:**
- [ ] Manual tracking sheet created
- [ ] Hourly logging template ready
- [ ] Team access configured

### Launch Day

**Monitoring:**
- [ ] Real-time dashboard open
- [ ] Logging started at launch
- [ ] Team has access
- [ ] Alerts working

## Funnel Visualization

### Typical PH Launch Funnel

```
Product Hunt Page Views
        │
        ▼ (Click-through rate: ~20-40%)
Website Visitors from PH
        │
        ▼ (Engagement rate: ~40-60%)
Engaged Visitors (>30s or 2+ pages)
        │
        ▼ (Signup rate: ~5-15%)
Signups / Trial Starts
        │
        ▼ (Conversion rate: ~10-30%)
Paid Customers
```

### Track Drop-Off Points

**Set up funnel in analytics:**
1. PH page → Website
2. Website → Signup page
3. Signup page → Signup complete
4. Signup complete → Onboarding
5. Onboarding → First value
6. First value → Payment

## Benchmarks & Goals

### Typical PH Launch Benchmarks

| Metric | Poor | Average | Good | Great |
|--------|------|---------|------|-------|
| PH → Site CTR | <10% | 10-20% | 20-30% | >30% |
| Bounce rate | >70% | 50-70% | 30-50% | <30% |
| Visit → Signup | <3% | 3-8% | 8-15% | >15% |
| PH visitors | <500 | 500-1500 | 1500-3000 | >3000 |

### Set Your Goals

```
LAUNCH GOALS:

Product Hunt:
- Target upvotes: [___]
- Target comments: [___]
- Target ranking: Top [___]

Website:
- Target visitors from PH: [___]
- Target bounce rate: <[___]%

Conversions:
- Target signups: [___]
- Target conversion rate: [___]%
- Target revenue: $[___]
```

## Post-Launch Analysis

### Key Questions to Answer

1. **Acquisition:**
   - How many people visited from PH?
   - What was click-through rate?
   - How did PH compare to other sources?

2. **Engagement:**
   - Did PH visitors engage with content?
   - What pages did they visit?
   - How long did they stay?

3. **Conversion:**
   - How many signed up?
   - What was conversion rate?
   - How does this compare to other channels?

4. **Quality:**
   - Are PH users retained?
   - Do they convert to paid?
   - What's LTV of PH-acquired users?

### Analysis Template

```
POST-LAUNCH ANALYSIS: [Product Name]
Date: [Launch Date]

ACQUISITION
- PH referral visitors: [___]
- % of total launch traffic: [___]%
- Peak hour: [___] with [___] visitors

ENGAGEMENT
- Average time on site: [___]
- Pages per session: [___]
- Bounce rate: [___]%

CONVERSION
- Total signups: [___]
- Signup conversion rate: [___]%
- Paying customers: [___]
- Revenue: $[___]

COMPARISON
- PH conversion vs. average: [___]%
- PH user quality score: [___]/10

LEARNINGS
- What worked: [___]
- What didn't: [___]
- For next time: [___]
```

## Analytics Checklist

### Setup Phase (1 Week Before)
- [ ] All tracking code installed
- [ ] Events configured
- [ ] Funnels set up
- [ ] Dashboard created
- [ ] Test tracking working
- [ ] Team access granted

### Launch Day
- [ ] Real-time monitoring active
- [ ] Hourly logging in progress
- [ ] Alerts working
- [ ] No tracking issues

### Post-Launch
- [ ] All data captured
- [ ] Analysis completed
- [ ] Learnings documented
- [ ] Comparison to goals

## Output Format

```
ANALYTICS SETUP FOR: [Product Name]

TOOLS CONFIGURED:
- Website analytics: [Tool]
- Product analytics: [Tool]
- PH tracking: [Method]
- Dashboard: [Location]

EVENTS TRACKING:
- [ ] Page views with source
- [ ] Signup started
- [ ] Signup completed
- [ ] Trial started
- [ ] Purchase completed

FUNNEL CONFIGURED:
[Diagram of your funnel]

GOALS SET:
- Visitors: [Target]
- Signups: [Target]
- Conversion: [Target]%
- Revenue: $[Target]

DASHBOARD LOCATION: [Link]

TRACKING VERIFIED: [Yes/No]
```
