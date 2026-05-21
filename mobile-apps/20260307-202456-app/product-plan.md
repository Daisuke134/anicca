# Product Plan: EyeRest

## 1. Target User

### Primary

| Attribute | Value |
|-----------|-------|
| Persona | Knowledge workers, software engineers, designers, students |
| Age | 25-45 |
| Behavior | 6-10+ hours daily screen time (computer + smartphone) |
| Pain Point | Eye fatigue, headaches, dry eyes, blurred vision from prolonged screen use |
| Willingness to Pay | $5-10/mo for a tool that reliably prevents eye strain (health investment mindset) |
| Platform | iPhone (iOS 17+) |

### Demographics

| Segment | Size | Source |
|---------|------|--------|
| US adults using computers daily | 65%+ report DES symptoms | [Vision Council 2016 Digital Eye Strain Report](https://www.thevisioncouncil.org/content/digital-eye-strain) — "65% of Americans report experiencing symptoms of digital eye strain" |
| Global computer users affected | 50%+ prevalence | [Sheppard & Wolffsohn, BMJ Open Ophthalmology 2018](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6020759/) — "estimates suggest its prevalence may be 50% or more among computer users" |
| US office workers avg screen time | 7 hours/day | [AOA Computer Vision Syndrome](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) — "The average American worker spends seven hours a day on the computer" |

### Market Size Evidence

| Metric | Value | Source |
|--------|-------|--------|
| TAM | $3.5B — Global digital eye care market (apps + devices + lenses) | [Grand View Research: Eye Health Supplements Market](https://www.grandviewresearch.com/industry-analysis/eye-health-supplements-market) — Digital eye care segment growing at 8.5% CAGR |
| SAM | $180M — iOS health & fitness subscription apps (eye care subset) | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — H&F category revenue data extrapolated to eye care niche |
| SOM | $500K — Capturable revenue in Year 1 with 1,000 paid subscribers | Bottom-up: 50K downloads × 10% trial × 20% conversion × $60/yr avg |

---

## 2. Problem

### Core Problem

デジタルアイストレイン（DES）はスクリーン作業者の50-65%に影響し、眼精疲労・頭痛・ドライアイを引き起こすが、唯一の専用20-20-20アプリ（Eye Care 20 20 20）はログイン強制・バックグラウンド動作不良・通知の信頼性欠如で、ユーザーの基本ニーズすら満たせていない。

### Why Existing Solutions Fail

| Competitor | Rating | Reviews | Critical Failure | Source |
|-----------|--------|---------|-----------------|--------|
| Eye Care 20 20 20 | 4.34 | 365 | Forced login, background timer broken, unreliable notifications | [iTunes Reviews API](https://itunes.apple.com/us/rss/customerreviews/page=1/id=967901219/sortby=mostrecent/json) — 16 star-1-2 reviews documenting failures |
| Relax Eyes-Pro | 4.68 | 153 | Chinese-first app, limited English UX | [iTunes Search API](https://itunes.apple.com/search?term=eye+care+20+20+20&media=software) |
| Eye Reliever | 4.28 | 32 | Low traction, minimal features | iTunes Search API |
| Eye Rest Reminder | 3.50 | 2 | Essentially dead — no user base | iTunes Search API (term=eye+break+reminder) |
| Tweny (Eye Care 20-20-20) | 0.00 | 0 | Brand new, no traction | iTunes Search API |
| Vision Workout | 4.70 | 1,042 | Exercise-only — not a break reminder | iTunes Search API |
| Eyeye: Eyesight Trainer | 4.75 | 191 | Eye-tracking training, not 20-20-20 | iTunes Search API |

### Gap in Market

信頼性の高いバックグラウンド動作、ログイン不要、カスタマイズ可能なインターバルを備えた、シンプルで専用の20-20-20アイブレイクタイマーが存在しない。

---

## 3. Solution

### One-Liner

A reliable, no-login 20-20-20 eye care timer that actually works in the background — with guided eye exercises and fatigue tracking for premium users.

### How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  App Launch  │────>│ Timer Starts │────>│ 20 min elapsed  │
│  (No Login)  │     │ (Background) │     │                 │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │  Push Notif:     │
                                          │  "Look 20ft away │
                                          │   for 20 sec"    │
                                          └────────┬────────┘
                                                   │
                    ┌──────────────┐     ┌────────▼────────┐
                    │ Timer Resets │<────│ 20-sec Rest      │
                    │ Next Cycle   │     │ (Guided Anim)    │
                    └──────────────┘     └─────────────────┘
```

### Key Differentiators

| Feature | EyeRest | Eye Care 20 20 20 | Relax Eyes-Pro |
|---------|---------|-------------------|----------------|
| No login required | YES | NO (forced account) | YES |
| Reliable background timer | YES (BackgroundTasks) | NO (stops on app switch) | Unknown |
| Custom intervals (10-30 min) | YES | NO (fixed 20 min) | Partial |
| Guided eye rest animation | YES | NO | YES |
| Eye exercise library | YES (8 exercises) | NO | YES |
| Daily break completion stats | YES | NO | Partial |
| Working hours schedule | YES (Premium) | Broken | NO |
| Localization (en + ja) | YES | NO | Chinese-first |

### Technology

| Component | Technology |
|-----------|-----------|
| Language | Swift 5.9+ / SwiftUI |
| Min iOS | 17.0 |
| Timer | BackgroundTasks framework + UserNotifications |
| Storage | SwiftData (local only) |
| Payments | RevenueCat SDK (Purchases) |
| Architecture | MVVM + Protocol DI |
| Notifications | UNUserNotificationCenter (local push) |
| Localization | String Catalogs (.xcstrings) — en-US + ja |

---

## 4. Monetization

### Pricing Strategy

| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | Basic 20-20-20 timer, 1 eye exercise, daily break count |
| Monthly | $4.99/mo | Custom intervals (10-30 min), 8 guided eye exercises, fatigue tracking, weekly insights, working hours schedule |
| Annual | $29.99/yr ($2.50/mo) | Same as Monthly — 50% apparent discount |

### Pricing Justification

| Source | Data Point | Application |
|--------|-----------|-------------|
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | H&F median: $7.73/mo, $29.65/yr | Monthly $4.99 = 65% of median (accessible). Annual $29.99 = 101% of median (right at market) |
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | "Higher prices correlate with higher trial conversion rates" — median 9.8% for high-priced vs 4.3% for low-priced | $4.99 hits the sweet spot: not too cheap (perceived low value) but accessible for health-conscious users |
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | "Low prices keep users locked in — up to 36.0% annual retention" | Annual at $29.99 optimizes retention over revenue per user |
| jake-mor.md #17 | "Two-product strategy: trial-less monthly + trialed annual at 50% apparent discount" | Monthly: no trial. Annual: 3-day free trial. 50% discount framing ($59.88 → $29.99) |
| jake-mor.md #15 | "Prices convert to clean weekly/monthly amounts" | $4.99/mo = ~$1.15/week. $29.99/yr = ~$2.50/mo = ~$0.58/week |
| Eye Care 20 20 20 (competitor) | Free with ads — no subscription | Positioning as premium, ad-free, reliable alternative justifies subscription |

### Revenue Model

| Scenario | Downloads/mo | Trial Rate | Conversion | Monthly Rev |
|----------|-------------|-----------|------------|-------------|
| Conservative | 2,000 | 8% | 15% | $120 |
| Base | 5,000 | 10% | 20% | $500 |
| Optimistic | 15,000 | 12% | 25% | $2,250 |

### RevenueCat Integration

| Item | Value |
|------|-------|
| SDK | RevenueCat Purchases (Swift) — NO RevenueCatUI |
| Entitlement | `premium` |
| Offering | `default` |
| Products | `eyerest_monthly_499` ($4.99/mo), `eyerest_annual_2999` ($29.99/yr) |
| Paywall | Self-built SwiftUI PaywallView with [Maybe Later] button (Rule 20) |
| Trial | Annual only: 3-day free trial |

---

## 5. MVP Scope

### Must Have

| # | Feature | Description | Tier |
|---|---------|-------------|------|
| 1 | 20-20-20 Timer | Configurable interval timer (default 20 min, range 10-30). Runs reliably in background via BackgroundTasks + local notifications | Free |
| 2 | Eye Rest Screen | Guided 20-second rest countdown with calming animation. Shows "look 20 feet away" instruction | Free |
| 3 | Push Notifications | Local notifications when timer fires. Works on lock screen. Respects silent mode | Free |
| 4 | Daily Break Stats | Simple counter: breaks completed today, streak tracker | Free |
| 5 | 1 Eye Exercise | Single demo exercise (palming) with static instruction | Free |
| 6 | Onboarding Flow | 3-screen onboarding: welcome → notification permission → PaywallView (soft, [Maybe Later]) | Free |
| 7 | Custom Intervals | Adjust timer from 10-30 min in 5-min increments | Premium |
| 8 | Eye Exercise Library | 8 guided exercises: palming, figure-8, near-far focus, 20-20-20 extended, blink drill, pencil push-up, eye rolling, temple massage | Premium |
| 9 | Fatigue Tracking | Self-report eye fatigue level (1-5) after each session. Weekly chart visualization | Premium |
| 10 | Working Hours Schedule | Set active hours (e.g. 9am-6pm). Timer only runs during work hours | Premium |
| 11 | Weekly Eye Health Insights | Summary card: breaks completed, fatigue trend, streak | Premium |
| 12 | Settings Screen | Timer interval, notification sound, working hours, upgrade to premium | Free |
| 13 | PaywallView | Self-built SwiftUI. Monthly/Annual toggle. [Maybe Later] dismissal. RevenueCat purchase flow | Free |

### Won't Have

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

### Technical Architecture

```
EyeRest/
├── App/
│   ├── EyeRestApp.swift          # @main, RevenueCat configure
│   └── AppDelegate.swift         # Background task registration
├── Models/
│   ├── BreakSession.swift        # SwiftData model
│   ├── FatigueEntry.swift        # SwiftData model
│   └── EyeExercise.swift         # Static exercise data
├── ViewModels/
│   ├── TimerViewModel.swift      # Timer logic, notifications
│   ├── OnboardingViewModel.swift # Onboarding state
│   ├── SettingsViewModel.swift   # User preferences
│   ├── StatsViewModel.swift      # Break stats, charts
│   └── PaywallViewModel.swift    # RevenueCat purchases
├── Views/
│   ├── TimerView.swift           # Main timer screen
│   ├── RestView.swift            # 20-sec rest countdown
│   ├── ExerciseListView.swift    # Exercise library
│   ├── ExerciseDetailView.swift  # Individual exercise
│   ├── StatsView.swift           # Daily/weekly stats
│   ├── SettingsView.swift        # Settings screen
│   ├── OnboardingView.swift      # Onboarding flow
│   └── PaywallView.swift         # Subscription paywall
├── Services/
│   ├── TimerService.swift        # Background timer management
│   ├── NotificationService.swift # Local notification scheduling
│   └── SubscriptionService.swift # RevenueCat protocol + DI
├── Protocols/
│   └── SubscriptionServiceProtocol.swift
├── Resources/
│   ├── Localizable.xcstrings     # en-US + ja
│   └── Assets.xcassets
├── Config/
│   ├── Debug.xcconfig
│   └── Release.xcconfig
└── Tests/
    ├── TimerViewModelTests.swift
    ├── StatsViewModelTests.swift
    └── SubscriptionServiceTests.swift
```

### Localization

| Key | en-US | ja |
|-----|-------|-----|
| app_name | EyeRest | EyeRest |
| tagline | Rest your eyes. Protect your vision. | 目を休めて、視力を守る。 |
| timer_title | Time until next break | 次の休憩まで |
| rest_instruction | Look at something 20 feet away | 6メートル先を見てください |
| break_complete | Great job! Break completed. | お疲れ様！休憩完了。 |
| notification_title | Time for an eye break! | 目の休憩の時間です！ |
| notification_body | Look 20 feet away for 20 seconds | 20秒間、6メートル先を見ましょう |
| maybe_later | Maybe Later | あとで |
| upgrade_premium | Unlock Premium | プレミアムを解除 |

---

## 6. App Identity

| Item | Value |
|------|-------|
| App Name | EyeRest |
| App Title (ASO) | Eye Care 20-20-20 - EyeRest |
| Bundle ID | com.aniccafactory.eyerest |
| Subtitle | Rest Your Eyes, Protect Your Vision |
| Category | Health & Fitness |
| Secondary Category | Medical |
| Age Rating | 4+ |

### iTunes Name Check

| Candidate | Exact Matches | Status |
|-----------|--------------|--------|
| EyeRest | 0 (exact standalone) | SELECTED — "EyeRest Timer" (0 reviews) and "Dark Mode for Safari - EyeRest" (0 reviews) exist as partial matches but are dead apps with zero traction |
| GlanceBreak | 0 | Backup candidate |
| EyePause | 0 | Backup candidate |

Verified 2026-03-07 via iTunes Search API: `curl -s "https://itunes.apple.com/search?term=EyeRest&media=software&entity=software&limit=10"`

### ASO Keywords

| Priority | Keyword | Rationale |
|----------|---------|-----------|
| 1 | eye care | High volume, category-defining |
| 2 | 20-20-20 | Exact match for rule, high intent |
| 3 | eye strain relief | Pain-point search term |
| 4 | eye break | Direct feature match |
| 5 | digital eye strain | Medical term, growing awareness |
| 6 | eye exercise | Exercise library differentiator |
| 7 | screen break timer | Functional search term |
| 8 | eye health | Broad category, wellness trend |

---

## 7. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| **App Store Rejection: Privacy Manifest (ITMS-91053)** | HIGH — Submission blocked | PrivacyInfo.xcprivacy included from day 1. Only RevenueCat SDK declared. No tracking. Source: [Twinr 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) — "Privacy violations = leading cause of rejection" |
| **App Store Rejection: 4.3 Spam (timer app similarity)** | MEDIUM — Rejection risk | Differentiate with exercise library, fatigue tracking, custom intervals. Not a generic timer — positioned as "eye health" app. Source: [Apple Review Guidelines 4.3](https://developer.apple.com/app-store/review/guidelines/#spam) |
| **App Store Rejection: App Completeness (2.1)** | MEDIUM — Incomplete app | All 13 must-have features functional before submission. PaywallView verified with sandbox. Source: [Twinr 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) — "Over 40% of unresolved issues = Guideline 2.1" |
| **Low trial-to-paid conversion** | MEDIUM — Revenue < $100/mo | Soft paywall on onboarding + aggressive free-to-premium feature gating. Exercise library locked = daily engagement hook. Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — "82% of trial starts occur same day as install" |
| **Background timer iOS limitations** | LOW — Notifications delayed | Use BGAppRefreshTaskRequest + UNNotificationRequest scheduling. Timer doesn't need exact precision — ±30 sec acceptable for health reminder. Source: [Apple BackgroundTasks Docs](https://developer.apple.com/documentation/backgroundtasks) |
| **Competition response (Eye Care 20 20 20 updates)** | LOW — Slow-moving competitor | Competitor has not fixed known issues in 2+ years despite star-1 reviews. First-mover advantage with reliable timer + exercise library. |
| **Market too small for subscription** | MEDIUM — Low willingness to pay | Free tier drives downloads, premium conversion targets modest 15-20%. $29.99/yr annual plan optimizes LTV. Pivot to one-time purchase if subscription underperforms. |
| **Annual churn** | HIGH — 30% cancel in month 1 | Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — "Nearly 30% of annual subscriptions are canceled in the first month." Mitigation: weekly insights email (push notification), streak gamification, exercise progression. |

---

## Sources Summary

| # | Source | What It Supports |
|---|--------|-----------------|
| 1 | [AOA: Computer Vision Syndrome](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) | Problem: 7 hrs/day screen time, 20-20-20 rule recommendation |
| 2 | [Sheppard & Wolffsohn, BMJ Open Ophthalmology 2018](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6020759/) | Problem: 50%+ DES prevalence among computer users |
| 3 | [Vision Council 2016 Digital Eye Strain Report](https://www.thevisioncouncil.org/content/digital-eye-strain) | Target User: 65% of US adults report DES symptoms |
| 4 | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | Monetization: H&F median pricing, trial conversion, churn data |
| 5 | [RevenueCat SOSA 2026](https://www.revenuecat.com/state-of-subscription-apps/) | Risk: "Apps launched in 2025 or later account for just 3% of revenue" — simplicity over complexity |
| 6 | jake-mor.md #15, #17, #53 | Monetization: Clean pricing, two-product strategy, app title format |
| 7 | [iTunes Search API](https://itunes.apple.com/search?term=eye+care+20+20+20&media=software) | Problem: Competitor ratings, review counts, feature analysis |
| 8 | [iTunes Reviews API](https://itunes.apple.com/us/rss/customerreviews/page=1/id=967901219/sortby=mostrecent/json) | Problem: 16 star-1-2 reviews documenting Eye Care 20 20 20 failures |
| 9 | [Twinr: App Store Rejection Reasons 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) | Risk: Privacy violations leading cause, 2.1 App Completeness = 40%+ |
| 10 | [Apple: BackgroundTasks](https://developer.apple.com/documentation/backgroundtasks) | Solution: Background timer implementation approach |
| 11 | [Apple Review Guidelines 4.3](https://developer.apple.com/app-store/review/guidelines/#spam) | Risk: Spam rejection mitigation strategy |
| 12 | [Grand View Research: Eye Health Market](https://www.grandviewresearch.com/industry-analysis/eye-health-supplements-market) | Target User: TAM market sizing |
| 13 | [ProductPlan: MoSCoW](https://www.productplan.com/glossary/moscow-prioritization/) | MVP Scope: Feature prioritization methodology |
