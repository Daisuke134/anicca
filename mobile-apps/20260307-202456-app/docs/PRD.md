# Product Requirements Document: EyeRest

## 1. App Overview

| Field | Value |
|-------|-------|
| app_name | EyeRest |
| bundle_id | com.aniccafactory.eyerest |
| one_liner | A reliable, no-login 20-20-20 eye care timer that actually works in the background |
| platform | iOS 17+ (Swift/SwiftUI) |
| iOS minimum version | 17.0 |
| category | Health & Fitness (Primary), Medical (Secondary) |
| app_title (ASO) | Eye Care 20-20-20 - EyeRest |

Source: spec/01-trend.md — Rank 1 selection with overall_score 8.2

---

## 2. Target User

**ICP:** Knowledge workers aged 25-45 who spend 6-10+ hours daily on screens and experience eye fatigue, headaches, or dry eyes.

| Attribute | Value |
|-----------|-------|
| Persona | Software engineers, designers, students, remote workers |
| Age | 25-45 |
| Daily Screen Time | 6-10+ hours (computer + smartphone) |
| Pain Point | Eye fatigue, headaches, dry eyes, blurred vision |
| Willingness to Pay | $5-10/mo for reliable eye strain prevention |
| Platform | iPhone (iOS 17+) |

### Demographics

| Segment | Value | Source |
|---------|-------|--------|
| US adults with DES symptoms | 65% | [Vision Council 2016](https://www.thevisioncouncil.org/content/digital-eye-strain) — "65% of Americans report experiencing symptoms of digital eye strain" |
| Global DES prevalence | 50%+ | [Sheppard & Wolffsohn, BMJ Open Ophthalmology 2018](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6020759/) — "estimates suggest its prevalence may be 50% or more among computer users" |
| US worker avg screen time | 7 hours/day | [AOA](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) — "The average American worker spends seven hours a day on the computer" |

---

## 3. Problem Statement

Digital eye strain (DES) affects 50-65% of screen workers, causing eye fatigue, headaches, dry eyes, and blurred vision. The American Optometric Association officially recommends the 20-20-20 rule: every 20 minutes, look at something 20 feet away for 20 seconds.

The only dedicated iOS 20-20-20 app — Eye Care 20 20 20 (365 reviews, 4.34 rating) — fails users with forced login, broken background timers, and unreliable notifications. 16 star-1-2 reviews document specific, fixable failures. No reliable, no-login, customizable 20-20-20 eye break timer exists on iOS.

Source: [iTunes Reviews API](https://itunes.apple.com/us/rss/customerreviews/page=1/id=967901219/sortby=mostrecent/json) — 16 star-1-2 reviews documenting Eye Care 20 20 20 failures
Source: [AOA Computer Vision Syndrome](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) — 20-20-20 rule official recommendation

---

## 4. Goals & Success Metrics

| Metric | Target (Y1) | Measurement Method |
|--------|------------|-------------------|
| Monthly Downloads | 2,000-5,000 | App Store Connect dashboard |
| Trial Start Rate | 8-10% | RevenueCat dashboard |
| Trial-to-Paid Conversion | 15-20% | RevenueCat dashboard |
| Monthly Recurring Revenue | $120-$500 | RevenueCat dashboard |
| Day 7 Retention | 30%+ | App Store Connect retention |
| App Store Rating | 4.5+ | App Store Connect |
| Daily Breaks Completed (avg) | 4+ per active user | Local SwiftData aggregation |

Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — H&F download-to-trial median ~8-10%

---

## 5. Solution Overview

EyeRest is a privacy-first, no-login 20-20-20 eye care timer that reliably runs in the background and delivers timely notifications to take eye breaks. It solves every documented failure of the leading competitor: no forced account, reliable background operation via BackgroundTasks framework, customizable intervals (10-30 min), and respectful notifications. Premium users get 8 guided eye exercises, fatigue tracking, working hours scheduling, and weekly eye health insights.

---

## 6. MVP Features

| Feature ID | Feature | Priority | Tier | Description |
|-----------|---------|----------|------|-------------|
| F-001 | 20-20-20 Timer | MUST | Free | Configurable interval timer (default 20 min, range 10-30 min). Runs reliably in background via BackgroundTasks + local notifications |
| F-002 | Eye Rest Screen | MUST | Free | Guided 20-second rest countdown with calming animation. Shows "look 20 feet away" instruction |
| F-003 | Push Notifications | MUST | Free | Local notifications when timer fires. Works on lock screen. Respects device silent mode |
| F-004 | Daily Break Stats | MUST | Free | Breaks completed today counter + streak tracker |
| F-005 | Demo Eye Exercise | MUST | Free | Single palming exercise with static instruction |
| F-006 | Onboarding Flow | MUST | Free | 3-screen: welcome → notification permission → PaywallView (soft, [Maybe Later] dismissal) |
| F-007 | Custom Intervals | MUST | Premium | Adjust timer from 10-30 min in 5-min increments |
| F-008 | Eye Exercise Library | MUST | Premium | 8 guided exercises: palming, figure-8, near-far focus, 20-20-20 extended, blink drill, pencil push-up, eye rolling, temple massage |
| F-009 | Fatigue Tracking | MUST | Premium | Self-report eye fatigue level (1-5) after each session. Weekly chart visualization |
| F-010 | Working Hours Schedule | MUST | Premium | Set active hours (e.g. 9am-6pm). Timer only runs during work hours |
| F-011 | Weekly Eye Health Insights | MUST | Premium | Summary card: breaks completed, fatigue trend, streak |
| F-012 | Settings Screen | MUST | Free | Timer interval, notification sound, working hours, upgrade to premium |
| F-013 | PaywallView | MUST | Free | Self-built SwiftUI. Monthly/Annual toggle. [Maybe Later] dismissal. RevenueCat purchase flow (Rule 20) |

### free_tier_limit

Free users get: basic 20-20-20 timer (fixed 20 min interval only), 1 eye exercise (palming), daily break count. Premium features (custom intervals, 8 exercises, fatigue tracking, schedule, insights) locked behind paywall. Paywall trigger: tapping any Premium feature or completing onboarding.

---

## 7. User Stories

| ID | As a | I want to | So that |
|----|------|-----------|---------|
| US-01 | screen worker | receive reliable break reminders every 20 min | I reduce eye strain throughout my work day |
| US-02 | new user | start using the timer immediately without login | I don't abandon the app due to friction |
| US-03 | screen worker | see a guided 20-sec rest countdown | I know exactly what to do during my break |
| US-04 | health-conscious user | track how many breaks I complete daily | I build a consistent eye care habit |
| US-05 | premium user | customize my break interval to 10-15 min | I follow my doctor's recommendation for shorter intervals |
| US-06 | premium user | do guided eye exercises | I actively strengthen my eye health beyond just taking breaks |
| US-07 | premium user | log my eye fatigue level after each session | I track whether my eye health is improving over time |
| US-08 | premium user | set working hours for my timer | my phone doesn't buzz outside of work hours |
| US-09 | premium user | see weekly eye health insights | I understand my progress and stay motivated |
| US-10 | free user | upgrade to premium via the paywall | I unlock all eye care features |

---

## 8. Monetization

| Tier | Price | Trial | Features |
|------|-------|-------|----------|
| Free | $0 | — | Basic 20-20-20 timer (fixed 20 min), 1 eye exercise, daily break count |
| monthly_price | $4.99/mo | No trial | Custom intervals, 8 exercises, fatigue tracking, working hours schedule, weekly insights |
| annual_price | $29.99/yr ($2.50/mo) | 3-day free trial | Same as Monthly — 50% apparent discount |

### RevenueCat Configuration

| Item | Value |
|------|-------|
| Entitlement | `premium` |
| Offering | `default` |
| Product IDs | `eyerest_monthly_499`, `eyerest_annual_2999` |
| trial_days | 3 (annual only) |
| SDK | RevenueCat Purchases (Swift) — NO RC UI module (Rule 20) |

### Pricing Justification

| Source | Data Point |
|--------|-----------|
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | H&F median: $7.73/mo, $29.65/yr — EyeRest $4.99/mo = 65% of median (accessible) |
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | "Higher prices correlate with higher trial conversion rates" |
| jake-mor.md #17 | "Two-product strategy: trial-less monthly + trialed annual at 50% apparent discount" |

---

## 9. Market Context

**TAM:** $181.6M (bottom-up, app-only — 45.4M iOS screen workers in US+JP × $4.00 blended ARPU)
**SAM:** $27.2M (15% actively seek timer solution)
**SOM Year 1:** $2,720 | **Year 3:** $54,400

**Competitive Differentiation:** EyeRest is the only 20-20-20 timer that combines reliable background operation, no login requirement, customizable intervals (10-30 min), guided eye exercises, and fatigue tracking. The leading competitor (Eye Care 20 20 20, 365 reviews, 4.34 rating) has failed to fix documented issues for 2+ years.

Source: market-research.md — POEM score 20/25 (Strong Opportunity)

---

## 10. Privacy & Compliance

| Item | Value |
|------|-------|
| Data Collection | None — all data stored locally via SwiftData |
| ATT (AppTrackingTransparency) | NO — Rule 20b: ATT is prohibited |
| PrivacyInfo.xcprivacy | NSPrivacyAccessedAPICategoryUserDefaults (CA92.1) — reason: app functionality |
| Third-party SDKs | RevenueCat only — no tracking SDK (Rule 17) |
| Network requests | RevenueCat subscription verification only |
| User accounts | None — no login, no sign-up, no authentication |
| GDPR/CCPA | No personal data collected — no consent required |

---

## 11. Localization

| Language | Code | Status |
|----------|------|--------|
| English (US) | en-US | Primary |
| Japanese | ja | Secondary |

All UI strings managed via String Catalogs (.xcstrings). App name "EyeRest" is used in both locales (no translation needed).

---

## 12. Technical Constraints

| Rule | Constraint | Impact |
|------|-----------|--------|
| Rule 17 | Third-party tracking SDK prohibited | No telemetry SDKs of any kind. Greenlight detects violations = CRITICAL |
| Rule 20 | Custom PaywallView required | Self-built SwiftUI PaywallView + `Purchases.shared.purchase(package:)`. RC UI module import prohibited |
| Rule 20b | ATT prohibited | No app tracking transparency framework. No NSUserTrackingUsageDescription in Info.plist |
| Rule 23 | AI API / external API costs prohibited | No third-party AI vendor SDKs. No Apple on-device ML (iOS 26+ only). App is fully self-contained with local/static content only. Reason: monthly revenue $29 vs API costs $300+ |

---

## 13. Out of Scope

| Feature | Reason |
|---------|--------|
| Dynamic Island / Live Activities | PROHIBITED — WidgetKit Extension required, Maestro E2E testing impossible |
| Home Screen Widget | PROHIBITED — WidgetKit Extension target, testing complexity |
| HealthKit Integration | PROHIBITED — Complex permissions, additional App Review scrutiny |
| Sign in with Apple | PROHIBITED — Auth flow testing impossible with Maestro E2E |
| CloudKit Sync | PROHIBITED — Complexity, debugging difficulty. SwiftData local-only sufficient |
| AI-powered recommendations | PROHIBITED — Rule 23: AI API costs prohibited |
| Camera-based eye tracking | PROHIBITED — Privacy review concerns, NSUsageDescription |
| Social features / leaderboards | Scope overflow — v1.1 candidate |
| Apple Watch companion | Scope overflow — v1.1 candidate |
| Custom notification sounds | Scope overflow — v1.1 candidate |

---

## 14. App Store Metadata

### en-US

| Field | Value |
|-------|-------|
| app_name | EyeRest |
| subtitle | Rest Your Eyes, Protect Your Vision |
| keywords | eye care,20-20-20,eye strain relief,eye break,digital eye strain,eye exercise,screen break timer,eye health |
| promotional_text | The 20-20-20 eye care timer that actually works. No login. Reliable background reminders. Guided eye exercises. |
| description | EyeRest helps you follow the 20-20-20 rule recommended by the American Optometric Association: every 20 minutes, look at something 20 feet away for 20 seconds. Unlike other eye care apps, EyeRest works reliably in the background — no login required, no ads, no account creation. Just open and go. FREE FEATURES: - 20-20-20 timer with reliable background notifications - Guided 20-second eye rest countdown - Daily break completion tracking - Palming eye exercise demo PREMIUM FEATURES ($4.99/mo or $29.99/yr): - Custom timer intervals (10-30 minutes) - 8 guided eye exercises (palming, figure-8, near-far focus, blink drill, and more) - Eye fatigue tracking with weekly charts - Working hours schedule (timer pauses after work) - Weekly eye health insights dashboard Whether you're a developer, designer, student, or anyone who spends hours on screens — EyeRest is the simplest way to protect your eyes every day. |

### ja

| Field | Value |
|-------|-------|
| app_name | EyeRest |
| subtitle | 目を休めて、視力を守る |
| keywords | アイケア,20-20-20,眼精疲労,目の休憩,デジタルアイストレイン,目の体操,スクリーンブレイク,目の健康 |
| promotional_text | 20-20-20ルールに基づくアイケアタイマー。ログイン不要。バックグラウンドで確実に通知。目の体操付き。 |
| description | EyeRestはアメリカ検眼協会が推奨する20-20-20ルールを実践するためのアプリです。20分ごとに6メートル先を20秒間見ることで、デジタルアイストレインを予防します。他のアイケアアプリと違い、EyeRestはバックグラウンドで確実に動作します。ログイン不要、広告なし、アカウント作成不要。開いてすぐ使えます。無料機能: - 20-20-20タイマー（バックグラウンド通知対応） - ガイド付き20秒アイレスト - 1日の休憩回数トラッキング - パーミング体操デモ プレミアム機能（$4.99/月 または $29.99/年）: - カスタムタイマー間隔（10-30分） - 8種類のガイド付き目の体操 - 眼精疲労トラッキング（週間チャート） - 勤務時間スケジュール設定 - 週間アイヘルスインサイト エンジニア、デザイナー、学生、長時間画面を見るすべての方に — EyeRestは毎日の目の健康を守る最もシンプルな方法です。 |
