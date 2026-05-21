# Product Requirements Document: EyeBreakIsland

Source: [Product School PRD Template](https://productschool.com/blog/product-strategy/product-template-requirements-document-prd) — "A product requirements document (PRD) defines the product you are about to build."
Source: [AOA: Computer Vision Syndrome](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) — "take a 20-second break to view something 20 feet away every 20 minutes"
Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — "H&F median: $7.73/mo, $29.65/yr"

---

## 1. App Overview

| Field | Value |
|-------|-------|
| app_name | Eye Break - EyeBreakIsland |
| bundle_id | com.aniccafactory.eyebreakisland |
| one_liner | 20-20-20 rule timer in Dynamic Island — "Next break in 12 minutes" always visible |
| platform | iOS 16+ (Dynamic Island requires iPhone 14 Pro+) |
| iOS minimum | 16.1 |
| Xcode minimum | 16.0+ |
| Swift version | 5.9+ |
| Category | Health & Fitness |
| Secondary Category | Productivity |
| Age Rating | 4+ |
| Subtitle | 20-20-20 Rule, Dynamic Island |

---

## 2. Target User

**ICP:** Screen-bound professionals aged 25–45 who experience digital eye strain but forget to take breaks because they are too focused.

| Attribute | Value |
|-----------|-------|
| Name | Alex — The Screen-Bound Professional |
| Age | 25–45 |
| Occupation | Software engineer, designer, remote worker, student |
| Device | iPhone 14 Pro or later (Dynamic Island) |
| Screen time | 6+ hours/day |
| Pain point | Eye fatigue, headaches, dry eyes. Knows the 20-20-20 rule but cannot follow it during deep work |
| Behavior | Ignores notifications when focused. Has used Pomodoro timers before |
| WTP | $4.99/month (price of one coffee) for eye health |

Source: [Vision Council: Digital Eye Strain Report 2021](https://visioncouncil.org) — "65% of US adults report symptoms of digital eye strain"
Source: [Counterpoint Research 2024](https://www.counterpointresearch.com) — "Dynamic Island devices (iPhone 14 Pro+, 15 all, 16 all) exceed 50M units (US) as of early 2026"

---

## 3. Problem Statement

Digital eye strain (DES) affects 65% of US adults. The 20-20-20 rule — every 20 minutes, look 20 feet away for 20 seconds — is the AOA-recommended treatment. Yet compliance is nearly zero. Why?

**Existing apps fail because notifications are ignorable.** When you are in flow state, a banner notification is swiped away in under a second. You never actually stop to rest.

| Competitor | Reviews | Primary Failure |
|------------|---------|----------------|
| EyeMed | 23,676 | Overpriced, no Dynamic Island |
| Eye Care 20 20 20 | 365 | Background timer stops, login required |
| Eye Strain Guard | 1 | Essentially non-functional |

Real user reviews (iTunes RSS, id=967901219, 2026-03-07):
- "As soon as you switch to another app it stops counting and never notifies you" — 1★
- "Are you kidding me? You need an account to send reminders now?" — 1★
- "it hardly ever gives me notifications that the 20min are up, making it pointless" — 1★

Source: iTunes RSS Review Feed (2026-03-07) — `https://itunes.apple.com/us/rss/customerreviews/id=967901219/json`

---

## 4. Goals & Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Downloads (M1) | 500 | App Store Connect analytics |
| Downloads (M6) | 5,000 | App Store Connect analytics |
| Free → Pro conversion | 5% | RevenueCat dashboard |
| MRR (M6) | $200 | RevenueCat dashboard |
| App Store rating | 4.5+ | App Store Connect |
| Day-7 retention | 30%+ | App Store Connect |
| Break completion rate | 80%+ | UserDefaults local tracking |

---

## 5. Solution Overview

EyeBreakIsland uses ActivityKit Live Activities to permanently display a countdown timer in the Dynamic Island. The timer is impossible to ignore — it lives on the bezel of the iPhone, always visible, always counting down. When 20 minutes elapse, a full-screen break overlay appears and a 20-second countdown runs before automatically starting the next cycle. No account required. No background timer failures. No ignoring the Dynamic Island.

---

## 6. MVP Features

| Feature ID | Feature | Priority | Description |
|-----------|---------|----------|-------------|
| F-001 | 20-20-20 Timer Core | MUST | 20-min countdown → 20-sec break overlay → repeat. Start/stop/reset controls. |
| F-002 | Dynamic Island Live Activity | MUST | ActivityKit Live Activity showing "👁 18:34" countdown. Persistent across all apps. |
| F-003 | Background Notifications | MUST | UNUserNotificationCenter break notification when app is backgrounded. Works with screen locked. |
| F-004 | Onboarding Flow | MUST | 3 screens: problem intro → feature demo → notification permission → soft paywall |
| F-005 | PaywallView (custom SwiftUI) | MUST | Purchases.shared.purchase(package:). [Maybe Later] button. Monthly + Annual display. Rule 20. |
| F-006 | Schedule Mode (Pro) | PRO | Active hours (e.g., 9am–6pm only). Pause on weekends. |
| F-007 | Custom Intervals (Pro) | PRO | 15 / 20 / 25 minute work intervals. 15 / 20 / 30 second break durations. |
| F-008 | Break Statistics (Pro) | PRO | Daily/weekly break count. Streak tracking. Simple bar chart. |
| F-009 | Localization | MUST | en-US + ja. Localizable.xcstrings. |

Note: Apple Watch, Screen Time API, HealthKit are Out of Scope for v1.0.

---

## 7. User Stories

| ID | As a | I want to | So that |
|----|------|-----------|---------|
| US-A | remote worker | start the 20-20-20 timer with one tap | I do not have to configure anything |
| US-B | deep-focus developer | see the countdown in Dynamic Island | I never need to check the app |
| US-C | iPhone user | receive a break notification even when the app is backgrounded | the timer works reliably |
| US-D | new user | complete onboarding in under 60 seconds | I can start using the app immediately |
| US-E | free user | try core timer features without paying | I can evaluate the app before subscribing |
| US-F | Pro user | set active hours (9am–6pm) | the timer does not interrupt evenings |
| US-G | Pro user | see my break stats | I am motivated by streaks |

---

## 8. Monetization

| Tier | Price | Trial | Features |
|------|-------|-------|---------|
| Free | $0 | — | F-001 (Timer), F-002 (Dynamic Island), F-003 (Notifications), F-004 (Onboarding) |
| Pro Monthly | $4.99/month | None | Free + F-006 (Schedule), F-007 (Custom Intervals), F-008 (Statistics) |
| Pro Annual | $29.99/year | 7 days | Same as Pro Monthly. $2.50/month effective. |

| Setting | Value |
|---------|-------|
| RevenueCat Entitlement | `pro` |
| RevenueCat Offering | `default` |
| Monthly Product ID | `com.aniccafactory.eyebreakisland.monthly` |
| Annual Product ID | `com.aniccafactory.eyebreakisland.annual` |
| free_tier_limit | Core timer only; F-006/007/008 require Pro |

Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — "H&F median: $7.73/mo, $29.65/yr" — $4.99/mo is below median = entry pricing strategy
Source: Jake Mor Rule #17 — "Two-product: trial-less monthly + trialed annual"

---

## 9. Market Context

**TAM:** $280M (global digital eye strain app market). **SAM:** $54M (Dynamic Island iPhone users in US/JP/EU). **SOM Y1:** $18K.

| Differentiator | EyeBreakIsland | Top Competitor |
|---------------|---------------|----------------|
| Dynamic Island timer | YES | NO (0 of 6 competitors) |
| Background timer (reliable) | YES | NO (★1 reviews confirm failures) |
| Login required | NO | YES (Eye Care 20 20 20) |
| Monthly price | $4.99 | $9.99+ (EyeMed) |

Source: market-research.md — TAM=$280M, SAM=$54M, SOM Y1=$18K. POEM score 21/25.
Source: competitive-analysis.md — Feature Matrix 74 symbols. Dynamic Island gap: 0 of 6 competitors.

---

## 10. Privacy & Compliance

| Item | Value |
|------|-------|
| Data collected | None (no PII, no analytics) |
| ATT (AppTrackingTransparency) | NOT USED — Rule 20b |
| Analytics SDK | NOT USED — Rule 17 (Mixpanel/Firebase/etc. prohibited) |
| AI API | NOT USED — Rule 21 (OpenAI/Anthropic/Gemini/FoundationModels prohibited) |
| PrivacyInfo.xcprivacy | Required — UserDefaults = NSPrivacyAccessedAPICategoryUserDefaults (CA92.1) |
| Encryption | usesNonExemptEncryption = false (no custom crypto) |
| COPPA | 4+ rating, no data collection |

---

## 11. Localization

| Language | Code | Required |
|----------|------|---------|
| English (US) | en-US | YES |
| Japanese | ja | YES |

String file: `Localizable.xcstrings` (String Catalog, Xcode 15+)

---

## 12. Technical Constraints

| Rule | Constraint |
|------|-----------|
| Rule 17 | No Mixpanel, Firebase, or any analytics SDK. Greenlight will fail if detected. |
| Rule 20 | Custom SwiftUI PaywallView only. import RevenueCatUI is PROHIBITED. |
| Rule 20b | No AppTrackingTransparency. No NSUserTrackingUsageDescription. |
| Rule 21 | No OpenAI, Anthropic, Google Generative AI, or Apple FoundationModels. App is fully self-contained. Static/local content only. Monthly revenue $29 vs API cost $300+. |
| Dynamic Island | ActivityKit. Requires iPhone 14 Pro+. Graceful fallback to lock screen notification on older devices. |
| Background | UNUserNotificationCenter for background operation. No BGTaskScheduler required. |

---

## 13. Out of Scope (v1.0)

| Feature | Target Version |
|---------|---------------|
| Apple Watch companion app | v1.1 |
| Screen Time API integration | v1.1 |
| HealthKit (eye strain vs HRV) | v1.2 |
| Advanced statistics (charts, export) | v1.1 |
| Custom break duration (per-second) | v1.1 |
| Lock Screen widget | Replaced by Live Activities |
| Social sharing / streaks public | v1.2 |

---

## 14. App Store Metadata

### en-US

| Field | Value |
|-------|-------|
| App Name | Eye Break - EyeBreakIsland |
| Subtitle | 20-20-20 Rule, Dynamic Island |
| Keywords | eye strain,20 20 20 rule,eye break timer,digital eye strain,eye rest reminder,screen break,eye care,focus timer |
| Promotional Text | Protect your eyes. Dynamic Island keeps the countdown visible — always. |
| Description | Eye Break uses the proven 20-20-20 rule to protect your eyes from digital strain. Every 20 minutes, take a 20-second break and look 20 feet away. EyeBreakIsland keeps the countdown in your Dynamic Island — impossible to ignore, impossible to forget. No account required. Works in the background. Start your eye health habit today. |

### ja

| Field | Value |
|-------|-------|
| App Name | Eye Break - EyeBreakIsland |
| Subtitle | 20-20-20ルール、ダイナミックアイランド |
| Keywords | 眼精疲労,目の疲れ,20-20-20ルール,目休み,デジタルアイストレイン,スクリーン休憩,視力ケア |
| Promotional Text | 目を守る。ダイナミックアイランドでカウントダウンを常時表示。無視できない、忘れない。 |
| Description | Eye Breakは実証済みの20-20-20ルールで目を保護します。20分ごとに20秒間、6メートル先を見てください。EyeBreakIslandはカウントダウンをダイナミックアイランドに常駐させます。アカウント不要。バックグラウンドで動作。今日から目の健康習慣を始めましょう。 |
