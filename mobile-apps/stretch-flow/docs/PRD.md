# Product Requirements Document: DeskStretch

> **Version:** 1.0 | **Date:** 2026-03-05 | **Status:** Draft

---

## 1. Product Overview

| Field | Value |
|-------|-------|
| **App Name** | DeskStretch |
| **Bundle ID** | `com.aniccafactory.deskstretch` |
| **Subtitle** | Desk Stretching & Break Timer |
| **Category** | Health & Fitness |
| **Platform** | iOS 15+ (SwiftUI) |
| **Pricing** | Freemium |
| **Monthly** | **$3.99/mo** |
| **Annual** | **$29.99/yr** (~$2.50/mo, 37% savings) |
| **Free Trial** | 7 days |
| **Localization** | en-US (primary), ja (secondary) |
| **Age Rating** | 4+ |

### One-Liner

**Smart desk stretching timer that reminds you to move and guides personalized stretch routines based on your pain areas.**

### Problem Statement

デスクワーカーは1日6-8時間座り続け、80.81%が筋骨格系障害(MSD)を経験する。ストレッチすべきだと分かっているが、忘れる・何をすればいいか分からない・面倒で続かない。既存ソリューションは「リマインダーだけ」(Stand Up!)か「本格ワークアウト」(Wakeout)の二極化で、痛みエリア特化型のデスク向けストレッチガイドが存在しない。

### Key Differentiator

**痛みエリアターゲティング + ブレイクタイマー統合 + キュレーションされたストレッチ = 全競合ゼロの組み合わせ。** 痛みエリアと履歴に基づく静的フィルタリングでパーソナライズされたストレッチを提供。

---

## 2. Target Personas

### Primary: Office Worker Oliver

| Attribute | Value |
|-----------|-------|
| Age | 25-45 |
| Occupation | Remote/office worker (engineer, designer, writer, accountant) |
| Daily Sitting | 6-8 hours |
| Pain Areas | Neck (58.6%), Lower back (52.5%), Shoulders (37.4%), Wrists |
| Behavior | Uses iPhone daily, open to health apps, tried reminder apps but found them too generic |
| Willingness to Pay | $3-8/mo for health tools that provide daily value |

**Core Pain:**
> 「Back pain is killing me but I keep forgetting to stretch. I've tried reminder apps but they just tell me to stand up — they don't tell me WHAT to do.」

### Secondary: Health-Conscious Hannah

| Attribute | Value |
|-----------|-------|
| Age | 22-35 |
| Occupation | Student / freelancer |
| Daily Sitting | 4-6 hours |
| Motivation | Preventive — wants to avoid future back problems |
| Behavior | Uses fitness apps, tracks health metrics, follows wellness TikTok |

---

## 3. Features (MVP v1.0)

### F-001: Onboarding Flow

| Field | Value |
|-------|-------|
| Priority | P0 (Critical) |
| Screens | 3: Problem Empathy → Pain Area Selection → Soft Paywall |

**Given/When/Then:**

| # | Given | When | Then |
|---|-------|------|------|
| 1 | User opens app for first time | App launches | Show onboarding screen 1 (problem empathy) |
| 2 | User is on screen 1 | Taps "Next" | Show screen 2 (pain area selection: Neck/Back/Shoulders/Wrists) |
| 3 | User selects pain areas on screen 2 | Taps "Continue" | Save selections to UserDefaults, show screen 3 (soft paywall) |
| 4 | User is on paywall screen | Taps "Maybe Later" | Dismiss paywall, enter main app with free tier |
| 5 | User is on paywall screen | Taps subscription option | Call `Purchases.shared.purchase(package:)`, on success enter main app with premium |

### F-002: Break Timer

| Field | Value |
|-------|-------|
| Priority | P0 (Critical) |
| Intervals | 30 / 45 / 60 / 90 minutes (user-configurable) |

**Given/When/Then:**

| # | Given | When | Then |
|---|-------|------|------|
| 1 | Timer is configured | Timer reaches 0 | Send local notification with stretch suggestion |
| 2 | User taps notification | Opens app | Navigate to stretch session for their pain area |
| 3 | Timer is running | User opens app | Show countdown with remaining time |
| 4 | User is in settings | Changes interval | Save new interval, restart timer |

### F-003: Stretch Library

| Field | Value |
|-------|-------|
| Priority | P0 (Critical) |
| Content | 20+ exercises across 4 categories |
| Visual | SF Symbols + text descriptions (no video in MVP) |

**Categories:**

| Category | Exercise Count | Examples |
|----------|---------------|----------|
| Neck | 5+ | Neck rolls, chin tucks, side stretches |
| Lower Back | 5+ | Cat-cow (seated), spinal twist, hip flexor stretch |
| Shoulders | 5+ | Shoulder shrugs, cross-body stretch, doorway stretch |
| Wrists | 5+ | Wrist circles, prayer stretch, finger spreads |

**Given/When/Then:**

| # | Given | When | Then |
|---|-------|------|------|
| 1 | User navigates to library | Views stretch list | Show exercises filtered by selected pain areas |
| 2 | Free tier user | Tries to access 4th+ stretch/day | Show paywall upsell |
| 3 | Premium user | Views library | Show all exercises, all categories |

### F-004: Stretch Recommendations

| Field | Value |
|-------|-------|
| Priority | P0 (Critical) |
| Technology | Static filtering (pain area + history-based) |
| Content | 20+ curated exercises, filtered by pain area and deduped by history |

**Given/When/Then:**

| # | Given | When | Then |
|---|-------|------|------|
| 1 | User has selected pain areas | Break timer fires | Generate personalized 1-3 min routine based on pain areas + history (static filtering) |
| 2 | User has stretch history | Routine requested | Avoid repeating same exercises within 3 days |
| 3 | Premium user | Routine requested | Access all exercises across all pain areas |
| 4 | Free tier user | Routine requested | Limited to 3 stretches/day from 1 pain area |

### F-005: Guided Stretch Session

| Field | Value |
|-------|-------|
| Priority | P0 (Critical) |
| Duration | 1-3 minutes |
| UI | Step-by-step cards with countdown timer per exercise |

**Given/When/Then:**

| # | Given | When | Then |
|---|-------|------|------|
| 1 | User starts session | Session begins | Show first exercise with countdown (15-30 sec/exercise) |
| 2 | Exercise countdown reaches 0 | Auto-advance | Show next exercise or completion screen |
| 3 | User completes session | Session ends | Log completion, update streak, show summary |
| 4 | User taps skip | During exercise | Advance to next exercise |

### F-006: Progress Tracking

| Field | Value |
|-------|-------|
| Priority | P1 (Important) |
| Metrics | Daily stretch count, streak (consecutive days), total sessions |
| Storage | UserDefaults (no backend needed for MVP) |

**Given/When/Then:**

| # | Given | When | Then |
|---|-------|------|------|
| 1 | User completes a stretch session | Session logged | Increment today's count, update streak if first of day |
| 2 | User opens progress tab | Views dashboard | Show today's count, current streak, total sessions |
| 3 | User misses a day | Opens app next day | Reset streak to 0 |

### F-007: Notifications

| Field | Value |
|-------|-------|
| Priority | P0 (Critical) |
| Types | Break reminders (recurring), morning stretch suggestion |
| Framework | UserNotifications |

**Given/When/Then:**

| # | Given | When | Then |
|---|-------|------|------|
| 1 | App first launch | After onboarding | Request notification permission |
| 2 | User grants permission | Timer configured | Schedule recurring local notifications at interval |
| 3 | Notification fires | User taps | Deep link to stretch session |
| 4 | Work hours ended | After configured end time | Suppress notifications until next work day |

### F-008: Paywall

| Field | Value |
|-------|-------|
| Priority | P0 (Critical) |
| SDK | RevenueCat Swift SDK |
| UI | Self-built SwiftUI `PaywallView` (RevenueCatUI FORBIDDEN — Rule 20) |
| Offering | `default` — Monthly ($3.99) + Annual ($29.99) |
| Entitlement | `premium` |
| Soft Gate | [Maybe Later] button on onboarding paywall |

**Given/When/Then:**

| # | Given | When | Then |
|---|-------|------|------|
| 1 | User taps premium feature | Not subscribed | Show PaywallView with Monthly + Annual options |
| 2 | User taps "Monthly $3.99" | Purchase flow | Call `Purchases.shared.purchase(package:)` |
| 3 | Purchase succeeds | Entitlement granted | Dismiss paywall, unlock premium features |
| 4 | User taps "Maybe Later" | On onboarding paywall | Dismiss, enter free tier |
| 5 | User taps "Restore Purchases" | On paywall | Call `Purchases.shared.restorePurchases()` |

### F-009: Settings

| Field | Value |
|-------|-------|
| Priority | P1 (Important) |
| Options | Timer interval, pain areas, work hours (start/end), notification toggle |

**Given/When/Then:**

| # | Given | When | Then |
|---|-------|------|------|
| 1 | User changes timer interval | Saves setting | Reschedule notifications with new interval |
| 2 | User updates pain areas | Saves selection | Stretch suggestions reflect new areas from next session |
| 3 | User sets work hours | 9:00-18:00 | Notifications only fire within this window |

---

## 4. User Flows

### Primary Flow: Break → Stretch → Done

```
App Background (timer running)
    ↓
Break Timer fires → Local Notification
    ↓
User taps notification
    ↓
App opens → Stretch Session (pain-area personalized)
    ↓
Exercise 1 (15-30 sec countdown)
    ↓
Exercise 2 (15-30 sec countdown)
    ↓
Exercise 3 (15-30 sec countdown)
    ↓
Session Complete → Progress updated → Back to timer
```

### Onboarding Flow

```
First Launch
    ↓
Screen 1: "Back pain from sitting all day?" (empathy)
    ↓
Screen 2: Select pain areas [Neck] [Back] [Shoulders] [Wrists]
    ↓
Screen 3: Soft Paywall (Monthly $3.99 / Annual $29.99 / [Maybe Later])
    ↓
Main App (Tab View: Timer | Library | Progress | Settings)
```

### Subscription Flow

```
Free user hits paywall gate (4th stretch/day)
    ↓
PaywallView shows
    ↓
[Monthly $3.99] / [Annual $29.99] / [Restore] / [Maybe Later]
    ↓
Purchase → RevenueCat SDK → Entitlement check → Unlock premium
```

---

## 5. Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| **App Launch** | < 2 seconds | Cold start to timer view |
| **Session Start** | < 1 second | From notification tap to first exercise |
| **Stretch Selection** | < 500 ms | Static filtering, no network needed |
| **Offline Support** | 100% core features | Timer, library, sessions work offline. All content local |
| **App Size** | < 30 MB | No video/audio assets. SF Symbols + text only |
| **Battery Impact** | Negligible | Timer uses scheduled notifications, not background processing |
| **Privacy** | No data collection | No analytics SDK (Rule 17), no ATT (Rule 20b), UserDefaults only |
| **Accessibility** | VoiceOver full support | All exercises have text descriptions |

---

## 6. Out of Scope (v1.0)

| Feature | Reason | Future Version |
|---------|--------|---------------|
| Apple Watch | Scope overflow | v1.1 |
| HealthKit integration | Complexity | v1.1 |
| Video exercises | Storage/hosting cost | v1.1 |
| Social features | Unnecessary for MVP | v2.0 |
| Gamification (badges) | Beyond core | v1.1 |
| Live Activities | Nice-to-have | v1.1 |
| Backend / user accounts | UserDefaults sufficient for MVP | v2.0 |
| Widget | WidgetKit next-break countdown | v1.1 |

---

## 7. Technical Constraints

| Constraint | Detail |
|------------|--------|
| **No Mixpanel** | Rule 17: Analytics SDK = CRITICAL rejection |
| **No RevenueCatUI** | Rule 20: Self-built SwiftUI PaywallView only |
| **No ATT** | Rule 20b: No AppTrackingTransparency |
| **RevenueCat SDK** | Real SDK with `Purchases.shared.purchase(package:)` |
| **No AI APIs** | Rule 21: OpenAI, Anthropic, Gemini, Apple FoundationModels 一切禁止。月額 $3.99 vs API コスト $300+。静的コンテンツのみ |
| **UserDefaults** | All local storage. No backend database for MVP |
| **Localization** | en-US + ja. All user-facing strings in Localizable.strings |

---

## 8. Competitive Context

| Competitor | Weakness | DeskStretch Advantage |
|-----------|----------|----------------------|
| **Wakeout!** ($59.99/yr) | Too expensive, generic | Pain-area personalized, $3.99/mo, desk-specific |
| **Stand Up!** ($1.99) | Timer only, no stretch guidance | Timer + guided stretches |
| **Moova** (~$7.99/mo) | Low differentiation | Pain area targeting + break timer |
| **Bend** (~$9.99/mo) | No break timer, generic stretching | Break timer + desk focus |

**Market Position:** Low Price + Desk-Specific + Pain Area Targeting = unoccupied quadrant.

---

## 9. Market Context

| Metric | Value |
|--------|-------|
| TAM | $12.12B (H&F App Market 2025) |
| SAM | $262M (iOS stretching/wellness, en+ja) |
| SOM Year 1 | $26K (0.01% of SAM) |
| SOM Year 3 | $524K (0.2% of SAM) |
| CAGR | 13-14.1% |
| MSD Prevalence | 80.81% of office workers |
| Opportunity Score | 7.9/10 (Strong) |

---

## 10. Success Criteria

| Metric | Month 1 | Month 3 | Month 6 |
|--------|---------|---------|---------|
| Installs | 500 | 2,000 | 5,000 |
| Trial Starts | 150 (30%) | 600 (30%) | 1,500 (30%) |
| Paid Conversions | 23 (15%) | 90 (15%) | 225 (15%) |
| MRR | $69 | $270 | $675 |
| App Store Rating | 4.5+ | 4.5+ | 4.5+ |
| Daily Active Sessions | 50 | 200 | 500 |
| D7 Retention | 30% | 35% | 40% |

---

## 11. Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| US-001: Trend Research | Done | Idea selected (DeskStretch) |
| US-002: Product Planning | Done | product-plan.md |
| US-003: Market Research | Done | competitive-analysis.md + market-research.md |
| US-004: Spec Generation | Done | 7 docs files (this document) |
| US-005a: Infrastructure | 1 iteration | Xcode project, signing, CI |
| US-005b: Monetization | 1 iteration | RevenueCat + IAP + PaywallView |
| US-006: Implementation | 1 iteration | Full app build |
| US-007: Testing + TestFlight | 1 iteration | E2E tests, TestFlight build |
| US-008: Screenshots + Metadata | 1 iteration | App Store assets |
| US-009: Submission | 1 iteration | App Store review submission |

---

## 12. Stakeholders

| Role | Name | Responsibility |
|------|------|---------------|
| Product Owner | Dais | Final approval on features and design |
| Developer | mobileapp-builder (AI) | Implementation, testing, submission |
| QA | Maestro E2E + manual | Automated and manual testing |

---

## 13. References

| # | Document | Purpose |
|---|----------|---------|
| 1 | `spec/01-trend.md` | Idea selection rationale |
| 2 | `product-plan.md` | Product plan (pricing, features, architecture) |
| 3 | `competitive-analysis.md` | 7 competitor analysis |
| 4 | `market-research.md` | TAM/SAM/SOM, growth analysis |
| 5 | — | (removed: Rule 21 — no AI APIs) |
| 6 | [RevenueCat iOS SDK](https://www.revenuecat.com/docs/getting-started/installation/ios) | Subscription SDK |
| 7 | [Apple HIG](https://developer.apple.com/design/human-interface-guidelines/) | Design guidelines |

---

## 14. Open Questions

| # | Question | Status | Decision |
|---|----------|--------|----------|
| 1 | AI APIs needed? | Resolved | No. Rule 21: 月額 $3.99 vs API コスト $300+。静的フィルタリングのみ |
| 2 | Exercise illustrations: SF Symbols vs custom? | Resolved | SF Symbols + text for MVP. Custom illustrations v1.1 |
| 3 | Backend needed for MVP? | Resolved | No. UserDefaults only. Backend in v2.0 |
| 4 | Free tier limit? | Resolved | 3 stretches/day, 1 pain area, basic timer |
