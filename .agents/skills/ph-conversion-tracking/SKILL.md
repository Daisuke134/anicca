---
name: ph-conversion-tracking
description: Track and optimize conversions from your Product Hunt launch. Use this skill to measure signup rates, identify drop-offs, and calculate the true ROI of your launch.
---

# Product Hunt Conversion Tracking

This skill helps you measure the real business impact of your Product Hunt launch through conversion tracking and ROI analysis.

## When to Use This Skill

- Setting up conversion measurement
- Tracking launch day conversions
- Analyzing funnel performance
- Calculating launch ROI
- Comparing to other acquisition channels

## The Conversion Funnel

### Standard PH Conversion Path

```
PRODUCT HUNT
    │
    ├─── Impressions (people who see your listing)
    │         │
    │         ▼ [View Rate]
    ├─── Page Views (people who click)
    │         │
    │         ▼ [Click-through Rate]
    ├─── Website Visitors
    │         │
    │         ▼ [Engagement Rate]
    ├─── Engaged Visitors (>30s, 2+ pages)
    │         │
    │         ▼ [Signup Rate]
    ├─── Signups / Trials
    │         │
    │         ▼ [Activation Rate]
    ├─── Activated Users (reached value)
    │         │
    │         ▼ [Conversion Rate]
    └─── Paying Customers
```

### Key Conversion Points

| Stage | Typical Rate | What It Measures |
|-------|-------------|------------------|
| View → Click | 15-30% | Listing appeal |
| Click → Visit | 70-90% | Page load, relevance |
| Visit → Signup | 5-15% | Landing page effectiveness |
| Signup → Activation | 30-60% | Onboarding quality |
| Activation → Paid | 10-30% | Product-market fit |

## Setting Up Conversion Tracking

### 1. Define Your Conversions

**Primary Conversion (Pick One):**
- Signup completed
- Trial started
- Purchase made
- App installed

**Secondary Conversions:**
- Email collected
- Demo booked
- Free tier activated
- Feature used

### 2. Technical Implementation

**Google Analytics 4 Events:**
```javascript
// Signup conversion
gtag('event', 'generate_lead', {
  'event_category': 'signup',
  'event_label': 'producthunt',
  'value': 0
});

// Purchase conversion
gtag('event', 'purchase', {
  'transaction_id': 'T_12345',
  'value': 99.00,
  'currency': 'USD',
  'items': [{
    'item_name': 'Pro Plan',
    'price': 99.00
  }]
});
```

**Server-Side Tracking:**
```python
# When signup occurs
def track_signup(user, source):
    analytics.track(user.id, 'Signed Up', {
        'source': source,  # 'producthunt'
        'plan': user.plan,
        'timestamp': datetime.now()
    })
```

### 3. Attribution Setup

**First-Touch Attribution:**
- Capture source on first visit
- Store in cookie/database
- Associate with eventual conversion

**UTM Tracking:**
```
https://yoursite.com?utm_source=producthunt&utm_medium=launch&utm_campaign=jan2024
```

**Referrer Tracking:**
```javascript
// Capture referrer on page load
if (document.referrer.includes('producthunt.com')) {
  localStorage.setItem('acquisition_source', 'producthunt');
}
```

## Measuring Conversions

### Real-Time Tracking (Launch Day)

**Hourly Log Template:**

| Hour | PH Visitors | Signups | Conv Rate | Revenue |
|------|-------------|---------|-----------|---------|
| 00:00 | 45 | 3 | 6.7% | $0 |
| 01:00 | 89 | 7 | 7.9% | $99 |
| 02:00 | 67 | 5 | 7.5% | $0 |
| ... | | | | |
| Total | | | | |

### Conversion Rate Calculations

**Visitor to Signup Rate:**
```
Signup Rate = (Signups / PH Visitors) × 100

Example: 156 signups / 1,234 visitors = 12.6%
```

**Trial to Paid Rate:**
```
Conversion Rate = (Paid / Trials) × 100

Example: 23 paid / 156 trials = 14.7%
```

**Revenue per Visitor:**
```
RPV = Total Revenue / Total Visitors

Example: $2,277 / 1,234 = $1.85 per visitor
```

## Funnel Analysis

### Identifying Drop-Offs

**Funnel Visualization:**
```
PH Page Views:     2,500 (100%)
                      │
                      ▼ 49% continue
Website Visits:    1,234 (49%)
                      │
                      ▼ 38% continue
Engaged (>30s):      469 (19%)
                      │
                      ▼ 33% continue
Signup Started:      156 (6.2%)
                      │
                      ▼ 90% complete
Signup Done:         140 (5.6%)
                      │
                      ▼ 16% convert
Paid:                 23 (0.9%)
```

**Drop-Off Analysis:**
- PH → Site: 51% drop → Is listing compelling?
- Site → Engaged: 62% drop → Is landing page relevant?
- Engaged → Signup: 67% drop → Is CTA clear?
- Signup → Complete: 10% drop → Is form too long?
- Complete → Paid: 84% drop → Is value delivered?

### Optimization Opportunities

For each drop-off point:

1. **High Drop-Off?** → Investigate why
2. **Identify Pattern** → What's different about converters?
3. **Hypothesis** → What change might help?
4. **Test** → A/B test the change
5. **Measure** → Did conversion improve?

## ROI Calculation

### Basic ROI Formula

```
Launch ROI = (Revenue Generated - Costs) / Costs × 100
```

### Comprehensive ROI Analysis

**Revenue Side:**
```
Immediate Revenue:
- Direct purchases: $2,277

Projected Revenue (LTV-based):
- 23 customers × $480 LTV = $11,040

Total Value: $13,317
```

**Cost Side:**
```
Time Investment:
- Preparation: 40 hours × $100/hr = $4,000
- Launch day: 16 hours × $100/hr = $1,600
- Follow-up: 8 hours × $100/hr = $800

Direct Costs:
- Design assets: $500
- Tools/subscriptions: $100
- Promotional offer cost: $300

Total Costs: $7,300
```

**ROI Calculation:**
```
ROI = ($13,317 - $7,300) / $7,300 × 100 = 82.4%
```

### Customer Acquisition Cost

```
CAC from PH = Total Launch Costs / Customers Acquired
            = $7,300 / 23
            = $317.39 per customer
```

**Compare to Other Channels:**
| Channel | CAC | Quality |
|---------|-----|---------|
| Product Hunt | $317 | High |
| Google Ads | $150 | Medium |
| Content Marketing | $200 | High |
| Cold Outreach | $500 | Low |

## Cohort Analysis

### PH Users vs Other Sources

Track these metrics by acquisition source:

| Metric | PH Users | Organic | Paid Ads |
|--------|----------|---------|----------|
| Activation Rate | 45% | 38% | 28% |
| Day 7 Retention | 35% | 32% | 22% |
| Day 30 Retention | 25% | 24% | 15% |
| Upgrade Rate | 18% | 12% | 8% |
| Avg LTV | $520 | $380 | $240 |

### What This Tells You
- PH users often higher quality
- Worth the launch investment?
- Should you launch again?

## Benchmarks & Goals

### Industry Benchmarks

**B2B SaaS from PH:**
| Metric | Low | Average | High |
|--------|-----|---------|------|
| Visit → Trial | 3% | 8% | 15% |
| Trial → Paid | 10% | 18% | 30% |
| Launch Revenue | $500 | $3,000 | $15,000+ |

**Consumer Apps from PH:**
| Metric | Low | Average | High |
|--------|-----|---------|------|
| Visit → Signup | 5% | 15% | 30% |
| Signup → Active | 20% | 40% | 60% |
| Launch Downloads | 200 | 1,000 | 5,000+ |

### Setting Your Goals

```
PRE-LAUNCH CONVERSION GOALS

Visitors (from PH): [Target]
↓ [Target]% conversion
Signups: [Target]
↓ [Target]% conversion
Trials: [Target]
↓ [Target]% conversion
Paid: [Target]
↓ $[Avg Price]
Revenue: $[Target]
```

## Post-Launch Conversion Analysis

### Analysis Template

```
CONVERSION ANALYSIS: [Product Name]
Launch Date: [Date]

FUNNEL SUMMARY:
PH Views → Site: [X] ([Y]%)
Site → Signup: [X] ([Y]%)
Signup → Paid: [X] ([Y]%)

KEY METRICS:
Total PH Visitors: [X]
Total Signups: [X]
Signup Rate: [X]%
Total Paid: [X]
Conversion Rate: [X]%

REVENUE:
Immediate: $[X]
Projected LTV: $[X]
Total Value: $[X]

COSTS:
Time: $[X]
Direct: $[X]
Total: $[X]

ROI: [X]%
CAC: $[X]

COMPARED TO GOALS:
Visitors: [Actual] vs [Goal] ([Over/Under])
Signups: [Actual] vs [Goal] ([Over/Under])
Revenue: [Actual] vs [Goal] ([Over/Under])

INSIGHTS:
- [Key learning 1]
- [Key learning 2]
- [Key learning 3]

OPTIMIZATION PRIORITIES:
1. [Biggest drop-off to fix]
2. [Second priority]
3. [Third priority]
```

## Conversion Tracking Checklist

### Setup Phase
- [ ] Primary conversion defined
- [ ] Tracking code implemented
- [ ] Attribution model set
- [ ] Goals configured in analytics
- [ ] Test conversions verified

### Launch Day
- [ ] Real-time tracking active
- [ ] Hourly logging in progress
- [ ] Conversion alerts working
- [ ] No tracking issues

### Post-Launch
- [ ] All conversions captured
- [ ] Funnel analyzed
- [ ] ROI calculated
- [ ] Cohort analysis done
- [ ] Learnings documented

## Output Format

```
CONVERSION REPORT: [Product Name]

EXECUTIVE SUMMARY:
Launch Date: [Date]
Total Visitors: [X]
Total Conversions: [X]
Conversion Rate: [X]%
Revenue: $[X]
ROI: [X]%

FUNNEL BREAKDOWN:
[Step 1] → [Step 2]: [X]%
[Step 2] → [Step 3]: [X]%
[Step 3] → [Step 4]: [X]%

BIGGEST DROP-OFF: [Step] ([X]% loss)
RECOMMENDATION: [Action to improve]

COMPARISON TO BENCHMARKS:
[Metric]: [Actual] vs [Benchmark] - [Status]

NEXT STEPS:
1. [Priority action]
2. [Secondary action]
3. [Tertiary action]
```
