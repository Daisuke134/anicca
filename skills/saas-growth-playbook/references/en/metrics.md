# Part 5: Data-Driven Growth Loop

## 1. North Star Metric

**Definition:** The single metric that best measures the core value your product creates for customers

**Requirements:**
- Entire company (product, engineering, marketing, sales) rallies around it
- Directly reflects customer value

**Examples:**
| Product Type | North Star Metric |
|:---|:---|
| AI Video Tool | Weekly videos exported |
| AI Meeting Assistant | Weekly meeting summaries generated |
| Collaboration Platform | Weekly active collaborating teams |

---

## 2. AARRR Funnel Metrics

| Stage | Core Question | Key Metrics |
|:---|:---|:---|
| **Acquisition** | Where do users come from? | Channel UV, Sign-ups, CAC |
| **Activation** | Did they experience core value? | "Aha Moment" conversion, Onboarding completion |
| **Retention** | Do they come back? | D1/D7/D30 retention, Feature retention |
| **Revenue** | Will they pay? | Conversion rate, ARPU, LTV |
| **Referral** | Will they recommend? | NPS, K-factor |

---

## 3. Key Metric Definitions

### Acquisition Metrics

| Metric | Definition | Formula |
|:---|:---|:---|
| **CAC** | Customer Acquisition Cost | Total Sales & Marketing / New Customers |
| **LTV** | Customer Lifetime Value | ARPU × Avg Customer Lifespan |
| **LTV/CAC** | Acquisition Efficiency | Healthy: > 3:1 |

### Activation Metrics

| Metric | Definition |
|:---|:---|
| **Aha Moment Rate** | % of users completing core value experience |
| **Time to Value** | Time from signup to first value received |

### Retention Metrics

| Metric | Formula |
|:---|:---|
| **D1 Retention** | Day 2 returners / Day 1 new users |
| **D7 Retention** | Day 8 returners / Day 1 new users |
| **D30 Retention** | Day 31 returners / Day 1 new users |

### Revenue Metrics

| Metric | Definition |
|:---|:---|
| **MRR** | Monthly Recurring Revenue |
| **ARR** | Annual Recurring Revenue = MRR × 12 |
| **ARPU** | Average Revenue Per User |
| **NRR** | Net Revenue Retention (incl. expansion, churn) |

---

## 4. Tool Stack

### Data Collection
| Tool | Purpose |
|:---|:---|
| **Mixpanel** | Frontend tracking, user behavior |
| **Amplitude** | Product analytics, user journeys |
| **Segment** | Data integration platform |

### User Behavior Analysis
| Tool | Purpose |
|:---|:---|
| **LogRocket** | Session replay, bug tracking |
| **Hotjar** | Heatmaps, behavior visualization |
| **FullStory** | Session replay, funnel analysis |

### BI & Visualization
| Tool | Purpose |
|:---|:---|
| **Metabase** | Open source BI, SQL visualization |
| **Looker** | Enterprise BI, data modeling |
| **Tableau** | Business intelligence, advanced viz |

### Experimentation
| Tool | Purpose |
|:---|:---|
| **LaunchDarkly** | Feature flags, progressive rollout |
| **Optimizely** | A/B testing platform |
| **PostHog** | Open source analytics + experimentation |

---

## 5. Growth Meeting Best Practices

### Frequency
Weekly or bi-weekly

### Participants
Product, Marketing, Sales, Data Analyst

### Agenda
1. Review last cycle's experiment results
2. Analyze data changes
3. Define next cycle's growth experiments

### Principles
- All changes based on clear hypotheses
- Validate through A/B testing
- Decisions must be data-backed

---

## 6. Growth Experiment Framework

### ICE Scoring

| Dimension | Description | Score (1-10) |
|:---|:---|:---|
| **Impact** | Potential impact on North Star | |
| **Confidence** | Confidence in hypothesis | |
| **Ease** | Implementation difficulty | |

**Priority = Impact × Confidence × Ease**

### Experiment Doc Template

```
Experiment Name:
Hypothesis: If we [do X], then [metric Y] will [change Z], because [reason]
Success Metric:
Design:
   - Control:
   - Treatment:
   - Sample Size:
   - Duration:
Result:
Conclusion:
Next Steps:
```
