# RevenueCat

Subscription management and analytics platform for mobile apps.

**Website:** [revenuecat.com](https://www.revenuecat.com)
**Docs:** [docs.revenuecat.com](https://www.revenuecat.com/docs)

## What It Provides

RevenueCat handles in-app subscriptions and provides analytics that Apple doesn't surface easily.

### Key Features for ASO Skills

| Feature | Description | Skill Usage |
|---------|-------------|-------------|
| **Subscription analytics** | MRR, churn, LTV, trial conversion | `monetization-strategy`, `app-analytics` |
| **Paywall A/B testing** | Test pricing, trial length, paywall design | `monetization-strategy`, `ab-test-store-listing` |
| **Cohort analysis** | Revenue by acquisition date/source | `ua-campaign`, `retention-optimization` |
| **Customer lists** | Active, churned, trial users | `retention-optimization` |
| **Webhooks** | Real-time subscription events | `app-analytics` |

### Metrics Available

| Metric | Description |
|--------|-------------|
| **MRR** | Monthly Recurring Revenue |
| **Active Subscribers** | Currently paying users |
| **Active Trials** | Users in free trial |
| **Trial Conversion Rate** | Trials → Paid |
| **Churn Rate** | Monthly subscriber loss |
| **ARPU** | Average Revenue Per User |
| **LTV** | Lifetime Value |
| **Refund Rate** | Refunds / Purchases |
| **Renewal Rate** | Subscribers who renewed |

## Setup

```bash
# Install SDK (iOS)
pod 'RevenueCat'

# Or Swift Package Manager
# https://github.com/RevenueCat/purchases-ios
```

```swift
// Initialize
Purchases.configure(withAPIKey: "your_api_key")
```

## API Access

```bash
# REST API for server-side analytics
curl -H "Authorization: Bearer $REVENUECAT_API_KEY" \
  "https://api.revenuecat.com/v1/subscribers/$APP_USER_ID"
```

## When to Use RevenueCat vs App Store Connect

| Need | RevenueCat | App Store Connect |
|------|-----------|------------------|
| Real-time subscription events | ✓ | Delayed |
| Paywall A/B testing | ✓ (Paywalls SDK) | ✗ |
| Cross-platform (iOS + Android) | ✓ | iOS only |
| Cohort revenue analysis | ✓ | Basic |
| Churn analysis | ✓ (detailed) | Basic |
| LTV prediction | ✓ | ✗ |
| Free tier | ✓ ($2.5K MRR) | ✓ |

## Integration with ASO Skills

**`monetization-strategy` skill uses RevenueCat for:**
- Current MRR and growth trend
- Trial-to-paid conversion rate
- Churn rate by plan
- LTV for CAC calculations

**`retention-optimization` skill uses RevenueCat for:**
- Subscription churn patterns
- Cancellation reasons
- Win-back campaign targeting

**`ua-campaign` skill uses RevenueCat for:**
- LTV by acquisition source
- ROAS calculation
- Payback period by channel
