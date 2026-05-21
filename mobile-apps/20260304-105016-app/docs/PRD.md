# Product Requirements Document: Chi Daily — TCM Wellness Coach

**Version:** 1.0
**Date:** 2026-03-04
**App Name:** Chi Daily
**Bundle ID:** com.aniccafactory.chidaily
**bundle_id:** com.aniccafactory.chidaily
**Platform:** iOS 26+
**Subscription:** $4.99/month / $34.99/year (7-day free trial)
**Markets:** United States (English) + Japan (Japanese)

---

## 1. Executive Summary

Chi Daily is a consumer-facing daily TCM (Traditional Chinese Medicine) constitutional check-in app. Users answer 5 questions each morning; the app uses Apple's Foundation Models framework (on-device AI) to generate personalized food, movement, and rest recommendations aligned with TCM principles. No backend, no cloud — 100% private.

**Market opportunity:** The "Chinese Baddie" TCM wellness trend has 100M+ views on TikTok in 2026. Zero consumer-facing daily TCM apps exist on the App Store. All existing TCM apps are practitioner tools.

---

## 2. Target User

| Attribute | Value |
|-----------|-------|
| Primary persona | Women 20–35, wellness-forward, TikTok/Instagram consumer |
| Geography | United States (en-US) + Japan (ja) |
| Core behavior | Follows Chinese Baddie TCM trend; curious about constitution-based eating/living |
| Pain point | Wants daily TCM guidance but all apps are for practitioners |
| WTP | $4.99/month (below Headspace $12.99, Calm $14.99) |

**Anti-persona:** TCM practitioners seeking clinical reference tools.

---

## 3. Features

### P0 — Must Have (MVP v1.0)

| # | Feature | Description | Acceptance Criteria |
|---|---------|-------------|---------------------|
| F-01 | Daily 5-question check-in | SwiftUI form: energy, sleep, digestion, emotions, physical sensations | Form completes in <2 min; data persists to SwiftData |
| F-02 | On-device TCM analysis | Foundation Models generates personalized TCM day plan | Response in <3 sec; no network call; 3 recommendation cards shown |
| F-03 | Recommendation cards | Food / Movement / Rest cards with TCM reasoning | Cards display within main view after check-in |
| F-04 | Check-in history | Last 7 days list view | Dates shown; tap to view past recommendations |
| F-05 | Onboarding (3 screens) | Welcome → constitution intro → paywall | 3 screens; Skip on screen 1 allowed; paywall on screen 3 |
| F-06 | Soft paywall | 7-day trial + subscribe; [Maybe Later] exits to app | RevenueCat SDK; [Maybe Later] always visible; no hard gate |
| F-07 | HealthKit integration | Write mood + energy to HealthKit after check-in | HKHealthStore authorization requested; silent fail if denied |
| F-08 | English + Japanese | All UI strings localized | Localizable.strings for en / ja; no untranslated strings |

### P1 — Should Have (v1.1 post-launch)

| # | Feature | Description |
|---|---------|-------------|
| F-09 | Weekly pattern summary | Foundation Models trend analysis across 7+ check-ins |
| F-10 | Push notifications | Daily 7:00 AM reminder to check in |
| F-11 | Widget | Small widget showing today's constitution tip |

### Deferred (Not in MVP)

| Feature | Reason |
|---------|--------|
| Apple Watch complication | Nice-to-have; low priority |
| Practitioner mode | Anti-persona |
| Social sharing | Privacy-first positioning conflicts |

---

## 4. User Stories

### US-01: First Launch Onboarding

**As a** new user,
**I want to** see a welcoming intro to Chi Daily,
**So that** I understand what the app does before committing.

**Acceptance Criteria (Given/When/Then):**
- Given I open the app for the first time, When the app loads, Then I see OnboardingScreen1 (welcome + tagline)
- Given I tap "Get Started", When the transition occurs, Then I see OnboardingScreen2 (TCM constitution explanation)
- Given I tap "Continue", When the transition occurs, Then I see OnboardingScreen3 (soft paywall with trial offer)
- Given I tap "Maybe Later", When the dismissal occurs, Then I proceed to HomeView with free-tier access

### US-02: Daily Check-in

**As a** subscribed user,
**I want to** answer 5 quick questions about how I feel today,
**So that** the app can generate my personalized daily TCM plan.

**Acceptance Criteria:**
- Given I open the app, When I tap "Start Today's Check-in", Then a 5-question form appears
- Given I complete all 5 questions, When I tap "Get My Plan", Then Foundation Models generates recommendations within 3 seconds
- Given the analysis completes, When I view the results, Then I see 3 cards: Food, Movement, Rest

### US-03: View Past Check-ins

**As a** returning user,
**I want to** see my past 7 days of check-ins,
**So that** I can track patterns in my wellness.

**Acceptance Criteria:**
- Given I have completed at least 1 past check-in, When I tap the History tab, Then I see a chronological list of past entries
- Given I tap a past entry, When the detail view opens, Then I see the answers given and recommendations received that day

### US-04: Subscribe

**As a** user who has used my 3 free check-ins,
**I want to** subscribe to unlock unlimited check-ins,
**So that** I can continue using Chi Daily.

**Acceptance Criteria:**
- Given I have used 3 free check-ins, When I tap "Start Check-in", Then the paywall is shown
- Given I tap the monthly option, When RevenueCat processes the purchase, Then I get unlimited access
- Given I tap "Start 7-Day Free Trial", When the trial begins, Then I have 7 days of full access

### US-05: HealthKit Logging

**As a** user who completes a check-in,
**I want to** have my mood and energy automatically logged to Apple Health,
**So that** I can see trends across my other health data.

**Acceptance Criteria:**
- Given I complete a check-in, When the app writes to HealthKit, Then mood and energy HKQuantitySamples appear in Apple Health
- Given HealthKit authorization is denied, When the app attempts to write, Then the app continues silently without crashing

---

## 5. User Flows

### Flow 1: First Launch

```
App Launch
  → OnboardingScreen1 (Welcome)
    → "Get Started" → OnboardingScreen2 (TCM Intro)
      → "Continue" → OnboardingScreen3 (Soft Paywall)
        → "Start Free Trial" → Subscribe → HomeView
        → "Maybe Later" → HomeView (free tier: 3 check-ins)
```

### Flow 2: Daily Check-in (Subscriber)

```
HomeView
  → "Start Today's Check-in" button
    → CheckInView (5 questions, progress bar)
      → "Get My Plan" button
        → Foundation Models analysis (loading state <3 sec)
          → ResultView (3 recommendation cards)
            → "Save to History" → HomeView updated
```

### Flow 3: Paywall Trigger (Free Tier Exhausted)

```
HomeView (3 check-ins used)
  → "Start Today's Check-in" button
    → PaywallView (soft gate)
      → "Start 7-Day Trial" → RevenueCat → CheckInView
      → "Maybe Later" → HomeView (locked state shown)
```

---

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | App launch < 2 sec cold start |
| Performance | Foundation Models response < 3 sec |
| Privacy | Zero network calls for core features; no analytics SDK |
| Accessibility | Dynamic Type support; VoiceOver labels on all interactive elements |
| Localization | en-US + ja from day 1 |
| Compatibility | iOS 26+ (Foundation Models requires iOS 26) |
| Offline | All features work offline (on-device AI) |

---

## 7. Out of Scope

- Backend API
- Server-side analytics (Mixpanel, Firebase, etc.) — CRITICAL RULE: banned
- User accounts / cloud sync
- Social features
- Apple Watch app

---

## 8. ASO Metadata

| Field | Value |
|-------|-------|
| **App Name** | Chi Daily: TCM Wellness Coach |
| **Subtitle** | Daily Check-in, AI Guidance |
| **Keywords (en)** | tcm wellness,chinese medicine,daily check-in,constitution,yin yang,qi gong,herbal,feng shui health,meridian,wellbeing |
| **Keywords (ja)** | 中医学,漢方,体質チェック,毎日ウェルネス,中国医学,気功,陰陽,ウェルネスアプリ,体質診断,健康習慣 |
| **Description (en)** | Chi Daily is your personal TCM wellness coach. Answer 5 questions each morning and receive personalized food, movement, and rest guidance based on Traditional Chinese Medicine — powered by on-device AI. No cloud, no data shared. |
| **Description (ja)** | Chi Dailyはあなたの毎日の中医学ウェルネスコーチです。毎朝5つの質問に答えるだけで、体質に合った食事・運動・休息のアドバイスを受けられます。すべてデバイス上のAIで処理。クラウド不使用。 |

---

## 9. Success Metrics (30-day post-launch targets)

| Metric | Target | Benchmark |
|--------|--------|-----------|
| Installs | 500+ | Organic + ASO |
| Day-1 retention | 40%+ | Revenuecat 2025: top quartile health = 45% |
| Trial start rate | 15%+ | Industry average 12–20% |
| Trial-to-paid conversion | 30%+ | Revenuecat 2025: median health = 38% |
| MRR (month 1) | $200+ | Conservative estimate |
| App Store rating | 4.5+ | Target |

---

## 10. Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Spec (US-004) | Day 1 AM | All 7 docs complete |
| Infra + IAP (US-005a/b) | Day 1 | ASC app created, RevenueCat configured |
| Implementation (US-006) | Day 1–2 | iOS app builds, no Mocks |
| Testing (US-007) | Day 2 | Tests pass |
| App Store prep (US-008) | Day 2–3 | Screenshots, metadata, build uploaded |
| Submission (US-009) | Day 3 | WAITING_FOR_REVIEW |
