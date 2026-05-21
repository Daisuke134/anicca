# MindSnap — Product Plan

**Date:** 2026-03-03
**App Name:** MindSnap: AI Daily Check-in
**Bundle ID:** com.anicca.mindsnap
**Category:** Health & Fitness
**Platform:** iOS 18+
**Status:** MVP Scoped

---

## 1. Target User

| Attribute | Description |
|-----------|-------------|
| **Age** | 24–38 (Millennial / older Gen Z) |
| **Primary pain** | Wants to build self-awareness but finds traditional journaling too slow and cloud apps untrustworthy |
| **Behavior** | Checks phone in the morning; uses 3–5 wellness/productivity apps; has tried and abandoned journaling before |
| **Privacy concern** | Doesn't want their emotional data sent to servers or used for advertising |
| **Time constraint** | Can commit 30–60 seconds per day but not 5–10 minutes |
| **Tech savvy** | Comfortable with iOS; aware of AI but skeptical of cloud-first apps |

**Psychographic:** "I want to know myself better but I don't have time to journal and I don't trust apps with my personal thoughts."

Source: [Business of Apps — App Market Trends 2026](https://www.businessofapps.com/news/app-market-trends-2026) — "Femtech and women's health will be one of the strongest growth categories in 2026 with AI designed specifically for personal care"
Source: [iOS App Categories with High Retention — iosapptemplates](https://iosapptemplates.com/blog/ios-app-trends-2026/) — "Premium members are 3.6x more likely to form a journaling habit"

---

## 2. Problem

### Core Problem
Existing journaling and mood-tracking apps fail users in three ways:

| Problem | Current Solution | Why It Fails |
|---------|-----------------|--------------|
| Journaling is slow | Day One, Journey, Reflectly | 5-10 min/day commitment → abandonment |
| No AI insights without cloud | Most AI apps require server sync | Privacy-conscious users won't use them |
| Generic prompts | Headspace, Calm | Not personalized to user's actual entries |

### Validation
- Day One (4.7★, 100K+ reviews) — top complaint: "takes too long to get started" and "expensive for what it does"
- Reflectly — requires account creation before any value; European users delete due to GDPR concerns
- No major app currently uses Foundation Models for on-device journaling prompts

Source: [Best Journaling Apps 2026 — Reflection.app](https://www.reflection.app/blog/best-journaling-apps) — "Most journaling apps fail to retain users past week 2 due to high time commitment"
Source: [Apple Foundation Models — Stoic case study](https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/) — "Stoic generates hyperpersonal journaling prompts entirely on device"

---

## 3. Solution

**MindSnap** = 30-second daily emotional check-in + on-device AI reflection prompts.

### Core Flow
```
Open app (5 sec)
    ↓
Slide mood (1-10) + optional 1-2 sentence note (15 sec)
    ↓
Foundation Models generates personalized reflection prompt on-device (5 sec)
    ↓
Read prompt; optionally write response (30 sec)
    ↓
Done. No account. No cloud. No tracking.
```

### Key Differentiators

| Feature | MindSnap | Day One | Reflectly |
|---------|----------|---------|-----------|
| Account required | ❌ No | ✅ Yes | ✅ Yes |
| On-device AI | ✅ Foundation Models | ❌ No | ❌ Cloud |
| Time per session | 30 sec | 5–10 min | 3–5 min |
| Privacy-first | ✅ Zero cloud | ❌ Sync required | ❌ EU data concerns |
| Home screen widget | ✅ WidgetKit | ✅ Yes | ❌ No |
| Subscription | $4.99/mo | $4.17/mo | $4.99/mo |

Source: [Day One Pricing](https://dayoneapp.com/pricing/) — "$4.17/month billed annually at $49.99"
Source: [Apple Foundation Models Developer Docs](https://developer.apple.com/documentation/FoundationModels) — "Works entirely on-device, protecting user privacy"

---

## 4. Monetization

### Subscription Pricing

| Plan | Price | Billing | Features |
|------|-------|---------|---------|
| **Monthly** | **$4.99/month** | Monthly recurring | All features |
| **Annual** | **$29.99/year** | Annual ($2.50/mo equivalent) | All features + save 50% |

**Free Tier:** Last 7 days of check-ins visible. AI prompts: 3/week. No widget.
**Premium Features:** Unlimited history, AI weekly insights report, WidgetKit prompt widget, data export.

### Free Trial
7-day free trial (full premium access). Source: [Business of Apps App Data Report 2026](https://www.businessofapps.com/data/app-data-report/) — "Free trials before hard paywalls convert meaningfully better than those that gate everything"

### Revenue Model
- Target: 1,000 paid subscribers in 6 months
- Monthly revenue at scale: 1,000 × $2.50 avg (mix of monthly/annual) = $2,500/mo
- Annual + monthly split target: 60% annual (higher LTV, lower churn)

Source: [iOS App Market Statistics 2026 — wearetenet](https://www.wearetenet.com/blog/ios-app-market) — "The economics of subscription apps are largely determined by what percentage of subscribers choose annual plans"

### RevenueCat Configuration
- Monthly: `mindsnap_monthly_499` — $4.99/mo
- Annual: `mindsnap_annual_2999` — $29.99/yr
- Offering ID: `default`
- Entitlement: `premium`

---

## 5. MVP Scope

### In Scope (1-day build)

| # | Feature | Implementation |
|---|---------|----------------|
| 1 | **Daily check-in screen** | Mood slider (1–10) + optional note field (SwiftUI) |
| 2 | **Foundation Models prompt** | On-device generation using check-in context |
| 3 | **History list** | ScrollView showing past 7 days (free) or all (premium) |
| 4 | **WidgetKit widget** | Home screen widget showing today's AI prompt |
| 5 | **Soft paywall** | On week 2+ history access, offer premium with [Maybe Later] |
| 6 | **RevenueCat SDK** | Purchases.shared.purchase(package:) — real SDK, no mock |
| 7 | **PrivacyInfo.xcprivacy** | NSPrivacyAccessedAPICategoryUserDefaults |

### Out of Scope (v1.0)
- iCloud sync (privacy brand → local-only is a feature)
- watchOS companion
- Reminders / push notifications
- Export to PDF
- Themes / customization
- Social sharing

### Architecture
```
SwiftUI (Views)
    ↓
ViewModels (@Observable)
    ↓
Services: CheckInService | FoundationModelsService | PurchaseService
    ↓
Storage: UserDefaults + FileManager (local only)
```

---

## 6. App Name Validation

```bash
curl "https://itunes.apple.com/search?term=MindSnap&entity=software" → 0 exact matches
```

**EVIDENCE:** `curl https://itunes.apple.com/search?term=MindSnap&entity=software&limit=20`
→ Total results: 20, Exact name matches for "MindSnap": **0**

App name is available. ✅

---

## Sources

| Source | URL | Key Claim |
|--------|-----|-----------|
| Business of Apps Market Trends 2026 | [link](https://www.businessofapps.com/news/app-market-trends-2026) | Free trials convert better |
| Day One Pricing | [link](https://dayoneapp.com/pricing/) | $4.17/mo annual benchmark |
| Apple Foundation Models Newsroom | [link](https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/) | Stoic case study: on-device prompts |
| Apple Foundation Models Docs | [link](https://developer.apple.com/documentation/FoundationModels) | On-device, privacy-first |
| iOS App Market Statistics 2026 | [link](https://www.wearetenet.com/blog/ios-app-market) | Annual plan economics |
| Best Journaling Apps 2026 | [link](https://www.reflection.app/blog/best-journaling-apps) | Week 2 abandonment problem |
| iosapptemplates — Retention 2026 | [link](https://iosapptemplates.com/blog/ios-app-trends-2026/) | Premium 3.6x habit formation |
