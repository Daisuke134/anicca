# Firebase Analytics

Google's free app analytics and engagement platform.

**Website:** [firebase.google.com](https://firebase.google.com)
**Docs:** [firebase.google.com/docs/analytics](https://firebase.google.com/docs/analytics)

## What It Provides

Firebase Analytics (Google Analytics for Firebase) is the most widely used free analytics SDK for mobile apps.

### Key Features for ASO Skills

| Feature | Description | Skill Usage |
|---------|-------------|-------------|
| **Event tracking** | Custom events with parameters | `app-analytics` |
| **User properties** | Segment users by attributes | `retention-optimization` |
| **Funnels** | Multi-step conversion analysis | `app-analytics`, `monetization-strategy` |
| **Cohort analysis** | Retention by install date | `retention-optimization` |
| **Audiences** | Dynamic user segments | `ua-campaign` |
| **Attribution** | Install source tracking | `ua-campaign`, `app-analytics` |
| **A/B testing** | Remote Config experiments | `ab-test-store-listing` |
| **Crashlytics** | Crash reporting | `app-analytics` |

### Key Metrics

| Metric | Description |
|--------|-------------|
| **Active Users** | DAU, WAU, MAU |
| **Sessions** | App opens with duration |
| **Retention** | Day 1, 2, 3, 7, 14, 21, 28, 30 |
| **Engagement** | Session duration, screens per session |
| **Revenue** | In-app purchases and ad revenue |
| **Conversions** | Custom conversion events |
| **User Properties** | Custom segmentation |

## Setup

```bash
# iOS (Swift Package Manager)
# Add firebase-ios-sdk package

# Android (Gradle)
implementation 'com.google.firebase:firebase-analytics'
```

```swift
// Log custom event
Analytics.logEvent("level_completed", parameters: [
  "level_name": "tutorial",
  "time_seconds": 45
])
```

## Recommended Events for ASO

### Core Events to Track

```
// Onboarding
Analytics.logEvent("onboarding_started")
Analytics.logEvent("onboarding_completed", parameters: ["steps_completed": 5])

// Core feature usage
Analytics.logEvent("feature_used", parameters: ["feature_name": "meditation_timer"])

// Monetization
Analytics.logEvent("paywall_viewed", parameters: ["source": "settings"])
Analytics.logEvent("trial_started", parameters: ["plan": "annual"])
Analytics.logEvent("purchase_completed", parameters: ["plan": "annual", "price": 49.99])

// Engagement
Analytics.logEvent("content_viewed", parameters: ["type": "guided_meditation"])
Analytics.logEvent("share_tapped", parameters: ["content": "progress_card"])
```

### User Properties

```
// Set once
Analytics.setUserProperty("subscription_status", forName: "free") // free, trial, premium
Analytics.setUserProperty("onboarding_completed", forName: "true")

// Update as needed
Analytics.setUserProperty("sessions_count", forName: "15")
Analytics.setUserProperty("feature_tier", forName: "power_user")
```

## Integration with ASO Skills

**`app-analytics` skill uses Firebase for:**
- Setting up the event tracking plan
- Creating funnels (onboarding → activation → purchase)
- Monitoring DAU/MAU and stickiness ratio
- Identifying drop-off points

**`retention-optimization` skill uses Firebase for:**
- Cohort retention curves
- Comparing retained vs churned user behavior
- Identifying activation events that predict retention
- Measuring push notification impact

**`monetization-strategy` skill uses Firebase for:**
- Purchase funnel analysis
- Paywall view → trial → purchase conversion
- Revenue per user segment
- A/B testing paywall variants (via Remote Config)

**`ua-campaign` skill uses Firebase for:**
- Install attribution by source
- Post-install event tracking by campaign
- Audience creation for remarketing
- ROAS measurement

## When to Use Firebase vs Other Tools

| Need | Firebase | App Store Connect | RevenueCat | Appeeky |
|------|---------|-------------------|-----------|---------|
| In-app event tracking | ✓ | ✗ | ✗ | ✗ |
| Custom funnels | ✓ | ✗ | ✗ | ✗ |
| Retention cohorts | ✓ | Basic | By revenue | ✗ |
| Crash reporting | ✓ | Basic | ✗ | ✗ |
| A/B testing (in-app) | ✓ | ✗ | Paywalls only | ✗ |
| Download attribution | ✓ | By source type | By source | ✗ |
| Keyword rankings | ✗ | ✗ | ✗ | ✓ |
| ASO data | ✗ | ✗ | ✗ | ✓ |
| Cost | Free | Free | Free tier | Credit-based |
