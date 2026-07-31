# App Store Connect

Apple's official portal for managing your app on the App Store.

**URL:** [appstoreconnect.apple.com](https://appstoreconnect.apple.com)
**API Docs:** [developer.apple.com/app-store-connect/api](https://developer.apple.com/documentation/appstoreconnectapi)

## What It Provides

App Store Connect is the source of truth for your app's performance. It provides data that no third-party tool can access.

### Analytics (Free)

| Metric | Description | Skill Usage |
|--------|-------------|-------------|
| **Impressions** | Times your app appeared in search/browse | `aso-audit`, `ab-test-store-listing` |
| **Product Page Views** | Users who visited your product page | `screenshot-optimization`, `ab-test-store-listing` |
| **Conversion Rate** | Views → Downloads | `aso-audit`, `ab-test-store-listing` |
| **App Units** | First-time downloads | `app-analytics`, `ua-campaign` |
| **Proceeds** | Revenue after Apple's cut | `monetization-strategy`, `app-analytics` |
| **Sessions** | App opens | `retention-optimization`, `app-analytics` |
| **Active Devices** | Unique devices | `app-analytics` |
| **Retention** | Day 1, 7, 28 | `retention-optimization` |
| **Crash Rate** | Crashes per session | `app-analytics` |

### Source Types

Understand where your downloads come from:

| Source | Description |
|--------|-------------|
| App Store Search | User searched and found you |
| App Store Browse | User found you browsing charts/categories |
| App Referral | User came from another app |
| Web Referral | User came from a website link |

### Product Page Optimization (A/B Testing)

Built-in A/B testing for:
- App icon (up to 3 variants)
- Screenshots (up to 3 variants)
- App preview video (up to 3 variants)

See `ab-test-store-listing` skill for detailed guidance.

### Custom Product Pages

Create up to 35 custom product pages with unique:
- Screenshots
- App preview videos
- Promotional text

Each gets a unique URL for targeted campaigns.

## Key Actions for ASO

### Metadata Updates
- Update title, subtitle, keyword field with each version
- Update description and screenshots anytime
- Update promotional text without app review

### In-App Events
- Create events that appear on Today tab and search
- Schedule up to 10 events at a time
- Types: challenge, competition, live event, major update, premiere, special event

### App Review Responses
- Respond to user reviews directly
- Responses are public and visible to all users

## API Access

For automated workflows, use the App Store Connect API:

```bash
# Generate API key in App Store Connect → Users and Access → Keys
# Create JWT token from the key

curl -H "Authorization: Bearer $JWT_TOKEN" \
  "https://api.appstoreconnect.apple.com/v1/apps"
```

**Useful API endpoints:**
- `/v1/apps/{id}/appStoreVersions` — Version management
- `/v1/apps/{id}/customerReviews` — Read reviews
- `/v1/apps/{id}/customerReviewResponses` — Respond to reviews
- `/v1/apps/{id}/appAvailabilities` — Country availability

## When to Use App Store Connect vs Appeeky

| Need | App Store Connect | Appeeky Connect | Appeeky |
|------|------------------|----------------|---------|
| Your app's exact download numbers | ✓ (official) | ✓ (synced daily) | Estimates |
| Your app's exact revenue | ✓ (official) | ✓ (synced daily) | Estimates |
| IAP counts, trials, subscriptions | ✓ (official) | ✓ (synced daily) | ✗ |
| Country breakdown (exact) | ✓ | ✓ (synced daily) | ✗ |
| Competitor data | ✗ | ✗ | ✓ |
| Keyword rankings | ✗ | ✗ | ✓ |
| Keyword volume/difficulty | ✗ | ✗ | ✓ |
| A/B test setup | ✓ (native) | ✗ | ✗ |
| Review management | ✓ (respond) | ✗ | ✓ (analyze) |
| ASO audit | ✗ | ✗ | ✓ |
| Market intelligence | Limited | ✗ | ✓ |

**Appeeky Connect** = connect your ASC API key once in [appeeky.com → Settings → Integrations](https://appeeky.com). Data syncs nightly and is then accessible via the Appeeky API without repeated ASC auth. See [appeeky-connect.md](appeeky-connect.md) and the `asc-metrics` skill.
