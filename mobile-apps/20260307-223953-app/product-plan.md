# Product Plan: FrostDip

## 1. Target User

### Primary Persona

| Attribute | Value |
|-----------|-------|
| Name | "Cold Plunge Chris" |
| Age | 25-45 |
| Gender | Male-skewed (65/35 M/F) |
| Occupation | Knowledge worker, athlete, or wellness entrepreneur |
| Income | $75K-150K+ (owns $1K-9K cold plunge equipment) |
| Behavior | Cold plunges 3-7x/week, follows Huberman/Wim Hof, tracks biometrics |
| Pain Point | Uses phone stopwatch or terrible hardware-tied apps to time sessions |
| Willingness to Pay | High — already spends $1K-9K on hardware + $50-200/mo on wellness subscriptions |

### Demographics

| Segment | Description | Source |
|---------|-------------|--------|
| Home cold plungers | Own portable/inflatable tubs (45% market share for inflatable) | [Pursue Performance](https://pursueperformance.com/cold-plunge-statistics/) |
| Biohacker community | Follow Huberman Lab, Wim Hof Method (11,321 reviews on iOS) | iTunes Search API (2026-03-07) |
| Athletes & recovery | Use CWI for post-workout recovery | [PLOS ONE Meta-Analysis](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0317615) — "CWI has gained popularity as a health and wellbeing intervention" |
| Wellness enthusiasts | Part of $512.9M cold plunge tub market | [Persistence Market Research](https://www.persistencemarketresearch.com/) |

### Market Size Evidence

| Metric | Value | Source |
|--------|-------|--------|
| Cold plunge tub market (2026) | US$ 512.9M | [Persistence Market Research](https://www.persistencemarketresearch.com/) — "Cold plunge tub market US$ 512.9M in 2026, CAGR 4.9%" |
| Alternative estimate (2026) | US$ 810M | [Business Research Insights](https://www.businessresearchinsights.com/) — "Cold plunge pool market USD 0.81B in 2026, CAGR 5.4%" |
| Active cold plunge brands (US) | 200+ (up from 85 in 2019) | [World Metrics / IndustryWeek](https://worldmetrics.org/cold-plunge-industry-statistics/) |
| Google search volume growth | +220% (2020-2023) | [World Metrics / Google Trends](https://worldmetrics.org/cold-plunge-industry-statistics/) |
| TikTok #coldplunge videos | 500,000+ (120% engagement increase) | [World Metrics](https://worldmetrics.org/cold-plunge-industry-statistics/) |
| Celebrity endorsements avg views | 2.3M per post (LeBron, The Rock) | [World Metrics](https://worldmetrics.org/cold-plunge-industry-statistics/) |

### TAM / SAM / SOM

| Level | Calculation | Value |
|-------|-------------|-------|
| TAM | Cold plunge tub owners globally × software attach rate ($512.9M market ÷ avg $2,500/unit = ~205K units/yr × cumulative 3yr = ~600K owners) | ~600K potential users |
| SAM | English + Japanese iOS users with cold plunge equipment (~40% of TAM) | ~240K users |
| SOM | Year 1 realistic capture (1-2% of SAM, based on indie app benchmarks) | 2,400-4,800 users |

---

## 2. Problem

### Core Problem

コールドプランジ愛好者は$1,000-9,000の機器に投資しているにもかかわらず、セッション記録にはiPhoneのストップウォッチか、ハードウェアに紐付いた低品質アプリしか選択肢がない。

### Why Existing Solutions Fail

| Competitor | Reviews | Rating | Fatal Flaw | Source |
|-----------|---------|--------|------------|--------|
| Plunge - Official App | 1,518 | 4.72 | Hardware-tied, login failures, disconnects, no biometrics. 1-star reviews: "logs you out regularly", "app is so unstable" | iTunes Reviews API (ID: 6450953005) |
| Brisk: Cold Plunge Tracker | 58 | 4.76 | Minimal features, tiny user base, no HealthKit HR integration | iTunes Search API (2026-03-07) |
| Shiver: Cold Plunge Log | 59 | 4.85 | Basic logging only, no progressive protocols or streaks | iTunes Search API (2026-03-07) |
| GoPolar: Cold Plunge & Sauna | 252 | 4.69 | Sauna-focused, cold plunge is secondary feature | iTunes Search API (2026-03-07) |
| IceBuddy: Cold Plunge Tracker | 22 | 4.77 | Negligible user base, limited feature set | iTunes Search API (2026-03-07) |
| Wim Hof Method | 11,321 | 4.85 | Breathwork-focused, cold exposure is just one sub-feature | iTunes Search API (2026-03-07) |

### Gap in Market

スタンドアロンのプレミアム冷水浴トラッカーが存在しない。トップの独立系アプリ（Brisk）はわずか58レビュー。$512.9Mのハードウェア市場に対して、ソフトウェアのギャップが巨大。

---

## 3. Solution

### One-Liner

Cold plunge & ice bath timer with progressive protocols, session logging, streak tracking, and HealthKit heart rate integration — hardware-independent, beautiful UI.

### How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Breathing   │────▶│  Cold Plunge │────▶│   Session   │
│  Prep Phase  │     │    Timer     │     │   Summary   │
│  (30-120s)   │     │  (countdown) │     │  (HR, temp) │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │  HealthKit  │
                    │  HR Monitor │
                    └─────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     ┌────────┴────────┐    ┌──────────┴──────────┐
     │  Streak Tracker  │    │  Progress Dashboard  │
     │  (daily/weekly)  │    │  (charts, history)   │
     └─────────────────┘    └─────────────────────┘
```

### Key Differentiators

| Feature | FrostDip | Plunge (hardware-tied) | Brisk (standalone) |
|---------|----------|----------------------|-------------------|
| Hardware-independent | YES | NO (requires Plunge tub) | YES |
| HealthKit HR integration | YES | NO | NO |
| Breathing prep phase | YES | NO | NO |
| Progressive protocols | YES (beginner → advanced) | NO | NO |
| Streak tracking | YES | NO | Basic |
| Contrast therapy mode | YES (hot/cold alternating) | NO | NO |
| Offline-first (no login) | YES | NO (login required, fails) | YES |
| Beautiful SwiftUI design | YES (Liquid Glass inspired) | NO (dated UI) | Basic |

### Technology

| Component | Choice | Rationale |
|-----------|--------|-----------|
| UI Framework | SwiftUI | Native iOS, modern, fast iteration |
| Data Storage | SwiftData | Apple-native persistence, no CloudKit needed |
| Health Integration | HealthKit | Heart rate during sessions, workout logging |
| Timer | Foundation Timer + BGTaskScheduler | Background countdown with haptic alerts |
| Payments | RevenueCat SDK (StoreKit 2) | Industry standard, self-built PaywallView |
| Minimum iOS | 17.0 | SwiftData requires iOS 17+, covers 95%+ devices |
| AI / External API | NONE (Rule 23) | Fully self-contained, zero API costs |

---

## 4. Monetization

### Pricing Strategy

| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | Basic timer, 7-day session history, 1 default protocol |
| Weekly | $1.99/wk | Full access. Try it weekly — lowest commitment entry point |
| Monthly | $6.99/mo | Unlimited history, HealthKit HR, custom protocols, streaks, progress dashboard, contrast therapy |
| Annual | $29.99/yr ($2.50/mo) | Same as Monthly — 64% apparent savings |

### Pricing Justification

| Source | Key Finding | How Applied |
|--------|-------------|-------------|
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | "H&F median: $7.73/mo, $29.65/yr" | Monthly $6.99 = 90% of median (accessible for niche). Annual $29.99 = 101% of median (right at market center) |
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | "Higher prices = higher trial conversion" | Priced at premium tier, not bottom-barrel |
| [Jake Mor #17](https://jakemor.com/) | "Two-product strategy: trial-less monthly + trialed annual at 50% apparent discount" | Monthly no trial, Annual with 3-day free trial. Annual = 64% apparent discount |
| [Jake Mor #15](https://jakemor.com/) | "Prices aren't random — they convert to clean weekly/monthly amounts" | $6.99/mo = $1.62/week (clean). $29.99/yr = $2.50/mo (clean) |
| [RevenueCat 2025 Trends](https://www.revenuecat.com/blog/growth/2025-subscription-app-monetization-trends/) | "Premium pricing is the new norm" | No race-to-bottom; premium positioning for users who spend $1K-9K on hardware |

### Revenue Model

| Scenario | Users | Conversion | Monthly ARPU | MRR | ARR |
|----------|-------|------------|-------------|-----|-----|
| Conservative (Month 6) | 2,000 | 3% | $5.50 | $330 | $3,960 |
| Moderate (Month 12) | 5,000 | 5% | $5.50 | $1,375 | $16,500 |
| Optimistic (Month 18) | 10,000 | 7% | $5.50 | $3,850 | $46,200 |

### RevenueCat Integration

| Item | Value |
|------|-------|
| SDK | RevenueCat Purchases (SPM) |
| RevenueCatUI | PROHIBITED (Rule 20) |
| Offering | "default" |
| Entitlement | "premium" |
| Products | `frostdip_monthly_699` ($6.99/mo), `frostdip_annual_2999` ($29.99/yr) |
| Paywall | Self-built SwiftUI `PaywallView` |
| [Maybe Later] button | REQUIRED (Rule 20 — soft paywall) |
| Paywall placement | Onboarding final screen + Settings → Upgrade |

---

## 5. MVP Scope

### Must Have

| # | Feature | Description | Tier |
|---|---------|-------------|------|
| 1 | Cold plunge timer | Countdown timer with breathing prep phase (30-120s), configurable duration, haptic alerts | Free |
| 2 | Session logging | Record duration, water temperature (manual input), personal notes | Free |
| 3 | 7-day history | View last 7 sessions with basic stats | Free |
| 4 | Default protocol | "Beginner" protocol (2 min cold, 30s breathing prep) | Free |
| 5 | Onboarding flow | 3-4 screens introducing app + notification permission + soft paywall | Free |
| 6 | HealthKit HR integration | Read heart rate during active session, display on timer screen | Premium |
| 7 | Unlimited session history | Full history with search and filter | Premium |
| 8 | Custom protocols | Create/edit protocols (prep time, cold time, rounds) | Premium |
| 9 | Streak tracking | Daily/weekly streak with visual calendar | Premium |
| 10 | Progress dashboard | Charts showing duration progression, avg HR, temperature trends | Premium |
| 11 | Contrast therapy mode | Alternating hot/cold timer with configurable rounds | Premium |
| 12 | Subscription paywall | Self-built SwiftUI PaywallView with [Maybe Later] | Premium |
| 13 | Settings | Temperature unit (C/F), notifications, upgrade, about | Free |

### Won't Have

| Feature | Reason |
|---------|--------|
| Social/community features | Scope overflow — v1.1 candidate |
| Apple Watch companion | watchOS target adds complexity, Maestro untestable — v1.1 |
| HealthKit write (workout logging) | HKWorkoutSession adds review scrutiny — v1.1 |
| Dynamic Island / Live Activities | PROHIBITED (WidgetKit extension, Maestro untestable) |
| Widgets | PROHIBITED (extension target) |
| LLM / AI features | PROHIBITED (Rule 23 — API cost) |
| Backend server | PROHIBITED (infra cost, Rule 23) |
| HealthKit body temperature | PROHIBITED (HealthKit permission complexity) |
| Camera / Photo | PROHIBITED (privacy review) |
| Sign in with Apple | PROHIBITED (Maestro untestable) |
| CloudKit sync | PROHIBITED (complexity — SwiftData local sufficient) |
| Guided audio coaching | Scope overflow — requires audio assets — v1.1 |

### Technical Architecture

```
FrostDip/
├── App/
│   ├── FrostDipApp.swift          # @main entry, SwiftData container
│   └── AppState.swift             # Navigation state
├── Models/
│   ├── PlungeSession.swift        # SwiftData @Model
│   ├── Protocol.swift             # Timer protocol definition
│   └── UserPreferences.swift      # Settings model
├── ViewModels/
│   ├── TimerViewModel.swift       # Timer logic, HealthKit HR
│   ├── HistoryViewModel.swift     # Session history queries
│   ├── ProgressViewModel.swift    # Dashboard charts data
│   ├── OnboardingViewModel.swift  # Onboarding flow state
│   └── SettingsViewModel.swift    # Settings + subscription state
├── Views/
│   ├── Timer/
│   │   ├── TimerView.swift        # Main timer screen
│   │   └── BreathingPrepView.swift
│   ├── History/
│   │   └── HistoryView.swift
│   ├── Progress/
│   │   └── ProgressDashboardView.swift
│   ├── Settings/
│   │   └── SettingsView.swift
│   ├── Onboarding/
│   │   ├── OnboardingView.swift
│   │   └── PaywallView.swift      # Self-built (Rule 20)
│   └── Components/
│       ├── StreakCalendarView.swift
│       └── SessionCardView.swift
├── Services/
│   ├── HealthKitService.swift     # Protocol-based DI
│   ├── SubscriptionService.swift  # RevenueCat wrapper
│   ├── NotificationService.swift  # Local notifications
│   └── TimerService.swift         # Background timer
├── Design/
│   ├── Theme.swift                # DESIGN_SYSTEM tokens
│   ├── Colors.swift
│   └── Typography.swift
├── Resources/
│   ├── Localizable.xcstrings      # en-US + ja
│   └── PrivacyInfo.xcprivacy
└── Config/
    ├── Debug.xcconfig
    └── Release.xcconfig
```

### Localization

| Key | en-US | ja |
|-----|-------|----|
| App Name | FrostDip | FrostDip |
| Subtitle | Cold Plunge Timer | 冷水浴タイマー |
| Start Session | Start Session | セッション開始 |
| Breathing Prep | Breathing Prep | 呼吸準備 |
| Water Temperature | Water Temperature | 水温 |
| Session Complete | Session Complete | セッション完了 |
| Streak | Streak | ストリーク |
| Upgrade to Premium | Upgrade to Premium | プレミアムにアップグレード |
| Maybe Later | Maybe Later | あとで |

---

## 6. App Identity

### App Name & Identity

| Item | Value |
|------|-------|
| App Name | FrostDip |
| App Title (ASO) | Cold Plunge Timer - FrostDip |
| Bundle ID | com.aniccafactory.frostdip |
| Subtitle | Ice Bath Tracker & Streaks |
| Category | Health & Fitness |
| Age Rating | 4+ |
| iTunes Name Check | 0 exact matches (verified 2026-03-07) |

Source: [Jake Mor #53](https://jakemor.com/) — App title format: `"Keyword - AppName"`

### iTunes Name Uniqueness Check

```bash
curl -s "https://itunes.apple.com/search?term=FrostDip&media=software&entity=software&limit=10" | \
  jq '[.results[] | select(.trackName | ascii_downcase | contains("frostdip"))] | length'
# Result: 0
```

| Check | Result |
|-------|--------|
| "FrostDip" exact match | 0 matches |
| Verified date | 2026-03-07 |
| Status | UNIQUE — name available |

### ASO Keywords

| Priority | Keyword | Rationale |
|----------|---------|-----------|
| 1 | cold plunge | Primary category term, +220% Google search growth |
| 2 | ice bath | High-volume alternative term, 1B+ TikTok views |
| 3 | cold exposure | Scientific term, Huberman audience |
| 4 | plunge timer | Direct intent keyword |
| 5 | cold therapy | Medical/wellness crossover term |
| 6 | ice bath tracker | Long-tail, high intent |
| 7 | wim hof | Associated brand, 11K+ reviews on Wim Hof app |
| 8 | contrast therapy | Growing biohacker trend |

---

## 7. Risk Assessment

| Risk | Impact | Mitigation | Source |
|------|--------|------------|--------|
| App Store rejection: Privacy Manifest (ITMS-91053) | HIGH — submission blocked | Include PrivacyInfo.xcprivacy from day 1, declare UserDefaults + HealthKit APIs | [Twinr](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) — "Privacy violations = leading cause of rejection" |
| App Store rejection: Guideline 2.1 App Completeness | HIGH — 40% of unresolved issues | Ensure all screens functional, no placeholder content, paywall works end-to-end | [Twinr](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) — "Over 40% of unresolved issues = Guideline 2.1" |
| App Store rejection: 4.3 Spam (similar to existing apps) | MEDIUM — delays launch | Differentiate with HealthKit HR, breathing prep, contrast therapy — features no competitor has | [Apple Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) |
| Low trial-to-paid conversion | MEDIUM — revenue below projections | Aggressive free-tier limitation (7-day history only), premium features visible but gated | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — "H&F median conversion 3-5%" |
| Market too niche (small TAM) | MEDIUM — growth ceiling | Cold plunge market growing at 4.9% CAGR, TikTok driving mainstream adoption | [Persistence Market Research](https://www.persistencemarketresearch.com/) — "$512.9M in 2026" |
| Competitor adds similar features | LOW — Brisk/Shiver iterate | First-mover advantage with HealthKit HR + protocols. Hardware-tied apps (Plunge) can't pivot easily | iTunes Search API competitive data (2026-03-07) |
| HealthKit permission denied by user | LOW — feature degradation | Timer works without HealthKit. HR is premium upsell, not core dependency | [Apple Developer: HealthKit](https://developer.apple.com/documentation/healthkit) |
| Novelty churn (users stop cold plunging) | MEDIUM — retention drops | Streak gamification + progressive protocols maintain engagement beyond novelty phase | [World Metrics](https://worldmetrics.org/cold-plunge-industry-statistics/) — "85% of reviews mention improved health" |

---

## Sources Summary

| # | Source | What It Supports |
|---|--------|-----------------|
| 1 | [Persistence Market Research](https://www.persistencemarketresearch.com/) — "Cold plunge tub market US$ 512.9M in 2026, CAGR 4.9%" | Market size (TAM), growth trajectory |
| 2 | [Business Research Insights](https://www.businessresearchinsights.com/) — "Cold plunge pool market USD 0.81B in 2026, CAGR 5.4%" | Market size validation |
| 3 | [World Metrics / IndustryWeek](https://worldmetrics.org/cold-plunge-industry-statistics/) — "200+ active brands, Google +220%, TikTok 500K videos" | Market growth, social proof, industry stats |
| 4 | [Pursue Performance](https://pursueperformance.com/cold-plunge-statistics/) — "82.6% only cold showers, 6.3% plunge 5-7x/week" | User behavior data, engagement frequency |
| 5 | [PLOS ONE Meta-Analysis (2025)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0317615) — "CWI systematic review across 3,177 healthy adults" | Scientific validation of cold water immersion benefits |
| 6 | [Harvard Health (2025)](https://www.health.harvard.edu/staying-healthy/research-highlights-health-benefits-from-cold-water-immersions) — "Regular ice baths may reduce stress, improve sleep, increase quality of life" | Health benefits credibility |
| 7 | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — "H&F median: $7.73/mo, $29.65/yr" | Pricing strategy |
| 8 | [RevenueCat 2025 Trends](https://www.revenuecat.com/blog/growth/2025-subscription-app-monetization-trends/) — "Premium pricing is the new norm" | Premium positioning |
| 9 | [Jake Mor](https://jakemor.com/) — "#17 Two-product strategy, #15 Clean weekly amounts, #53 App title format" | Paywall strategy, ASO naming |
| 10 | [Twinr](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) — "Privacy violations = leading cause, 15% rejected, 40% Guideline 2.1" | Risk assessment |
| 11 | [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) — Live competitive data (2026-03-07) | Competitor analysis, name uniqueness |
| 12 | [iTunes RSS Reviews API](https://itunes.apple.com/us/rss/customerreviews/) — Plunge app 1-star reviews | Problem validation, competitor UX failures |
| 13 | [Forbes](https://www.forbes.com/health/wellness/cold-plunge-what-to-know/) — "Cold plunge wellness trend" | Trend validation |
| 14 | [ProductPlan: MoSCoW](https://www.productplan.com/glossary/moscow-prioritization/) — "Must Have: Critical for current delivery" | MVP scoping methodology |
| 15 | [Apple Developer: CFBundleIdentifier](https://developer.apple.com/documentation/bundleresources/information_property_list/cfbundleidentifier) — "Use reverse-DNS format" | Bundle ID format |
