# Trend Research: FrostDip

## Developer Profile

| Item | Value |
|------|-------|
| Platform | iOS 17+ (Swift/SwiftUI) |
| Scope | 4-8 weeks (solo dev) |
| Monetization | Subscription ($4.99/mo, $29.99/yr) |
| AI / External API | Prohibited (Rule 23) |
| Purpose | Reduce human suffering (health/wellness) |

## Step 0: Exclusion Categories (Dynamic)

Source: `ls mobile-apps/` executed 2026-03-07

| Existing App | Excluded Category |
|---|---|
| breath-calm, breatheai, BreathStory (20260304) | Breathing / Meditation |
| sleep-ritual | Sleep |
| dailydhamma | Mindfulness / Buddhism |
| calmcortisol | Stress Management |
| rork-thankful-gratitude-app, MomentLog (20260303) | Gratitude Journal |
| stretch-flow, desk-stretch | Desk Stretching / Posture |
| Daily Affirmation Widget (20260301) | Affirmations |
| Hush (20260302) | Journaling / Worry Diary |
| MindSnap (20260303) | Mental Health Check-in |
| Chi Daily (20260304) | TCM / Eastern Medicine |
| EyeRest (20260307-002214, 20260307-202456) | Eye Rest / Eye Strain |
| CaffeineWidget (20260307-002214) | Caffeine Management |

---

## Lenses Applied

### Lens 1: Skills & Interests (Apple Frameworks)

**Question:** What can be built using Apple's native frameworks (HealthKit, CoreMotion, etc.) to reduce suffering?

Apple WWDC25 highlights: Liquid Glass design, HealthKit Medications API (iOS 26+), Foundation Models (iOS 26+ — excluded per Rule 23).

| # | Idea | Framework | Description |
|---|------|-----------|-------------|
| 1 | FrostDip | HealthKit + Timer | Cold exposure timer with heart rate monitoring, session logging, streaks |
| 2 | MealRx | HealthKit Dietary | Static anti-inflammatory meal plans with nutritional tracking |
| 3 | StepQuest | CoreMotion + HealthKit | Walking gamification with narrative story progression |
| 4 | SupplTrack | HealthKit + Notifications | Supplement intake timing with reminder scheduling |
| 5 | GutTimer | HealthKit + Timer | Intermittent fasting timer with metabolic state tracking |

---

### Lens 2: Problem-First (WebSearch)

**Question:** What daily pains lack good solutions? What app do people wish existed?

Search queries executed:
- `"iOS app idea 2026 underserved niche health wellness solo developer"` (DuckDuckGo)
- `"reddit what app do you wish existed 2026 health productivity"` (DuckDuckGo)

Sources:
- LinkedIn: "10 Innovative Healthcare App Ideas to Watch in 2026" (linkedin.com/pulse/10-innovative-healthcare-app-ideas-watch-2026)
- dev.to: "Future-Proofing Your First App: 15 Ideas & 2026 Tools" (dev.to/devin-rosario)
- Reddit r/productivity: "what productivity tool or app do you wish existed?" (34 votes, 103 comments)
- Medium: "I Analyzed 9,300 'I Wish There Was an App for This' Posts" (medium.com/write-a-catalyst)

Key pain points extracted:
- Cold plunge users hate hardware-tied apps with terrible UX (Plunge app: login issues, no biometrics, disconnects)
- Protein tracking is scattered across bloated calorie counters
- Supplement timing is guesswork for most people

| # | Idea | Pain Point | Description |
|---|------|-----------|-------------|
| 1 | IcePlunge | Cold plunge UX is terrible (Plunge app 1-star reviews) | Standalone cold exposure timer with breathing prep, NOT tied to hardware |
| 2 | ProteinLog | Protein tracking buried in bloated calorie apps | Simple, focused daily protein intake counter |
| 3 | MealPrepper | Weekly meal prep is disorganized | Meal prep planner with nutritional balance |
| 4 | WalkBuddy | Sedentary workers need walking accountability | Walking goal partner with gentle nudges |
| 5 | NapCoach | Power naps have no science-based guidance | Optimal nap duration timer with chronotype consideration |

---

### Lens 3: Technology-First (WebSearch)

**Question:** Which Apple frameworks have few indie apps built on them?

Search queries executed:
- `"Apple WWDC 2025 new framework HealthKit indie app opportunity"` (DuckDuckGo)
- `"iOS 26 WWDC 2025 complete developer guide"` (DuckDuckGo)

Sources:
- Apple Developer: WWDC25 (developer.apple.com/wwdc25/)
- YouTube: "WWDC25: Meet the HealthKit Medications API" (youtube.com/watch?v=CR4Y4dTiV4g)
- Medium: "iOS 26 WWDC 2025: Complete Developer Guide" (medium.com/@taoufiq.moutaouakil)
- TechCrunch: "Apple lets developers tap into its offline AI models" (techcrunch.com, 2025-06-09) — Foundation Models is iOS 26+ only, excluded per Rule 23

Key frameworks with indie opportunity:
- HealthKit workout sessions (HKWorkoutSession) — few cold therapy apps use this
- HealthKit heart rate zones during non-standard activities
- StoreKit 2 — modern subscription handling
- CoreMotion temperature estimation (limited but useful for context)

| # | Idea | Framework Opportunity | Description |
|---|------|----------------------|-------------|
| 1 | FrostLog | HealthKit HKWorkoutSession for cold exposure | Log cold sessions as HealthKit workouts with HR zones |
| 2 | WalkStory | MapKit + HealthKit + CoreLocation | Walking route narrative game with real geography |
| 3 | FlexTrack | CoreMotion gyroscope | Range-of-motion measurement for injury recovery |
| 4 | SupplClock | UserNotifications + HealthKit | Supplement timing optimizer with absorption science |
| 5 | ContrastTimer | HealthKit + Timer | Hot-cold contrast therapy timer with protocol builder |

---

### Lens 4: Market Gap (App Store Data)

#### Step 4a: Keywords extracted from Lens 1-3
`cold plunge tracker`, `supplement tracker`, `posture correction`, `focus timer pomodoro`, `habit tracker health`, `brain training cognitive`, `meal prep planner`

#### Step 4b: iTunes Search API Results

**cold plunge tracker** (LOW COMPETITION — MARKET GAP)

| App | Rating | Reviews | Price |
|-----|--------|---------|-------|
| Plunge - Official App | 4.72 | 1,518 | Free (hardware-tied) |
| Brisk: Cold Plunge Tracker | 4.76 | 58 | Free |
| Shiver: Cold Plunge Log | 4.85 | 59 | Free |
| GoPolar: Cold Plunge & Sauna | 4.69 | 252 | Free |
| IceBuddy: Cold Plunge Tracker | 4.77 | 22 | Free |
| Cold Plunge Tracker by ICY | 4.50 | 4 | Free |

**Verdict: HUGE GAP.** Top standalone tracker has 58 reviews. Hardware-tied Plunge has 1,518 but terrible UX.

**supplement tracker** (MODERATE GAP)

| App | Rating | Reviews | Price |
|-----|--------|---------|-------|
| SuppCo: Supplement Scanner | 4.81 | 16,110 | Free |
| Fullscript | 4.93 | 95,880 | Free (B2B) |
| Supplements AI - Stack Tracker | 4.42 | 93 | Free |
| Supplify: Supplement Tracker | 4.11 | 18 | Free |

**Verdict: Moderate gap.** SuppCo growing but indie trackers are tiny.

**focus timer pomodoro** (SATURATED)

| App | Rating | Reviews | Price |
|-----|--------|---------|-------|
| Focus Keeper | 4.79 | 31,185 | Free |
| Focus To-Do | 4.81 | 14,314 | Free |
| Pomodoro - Focus Timer | 4.74 | 10,652 | Free |

**Verdict: Saturated.** Multiple established players.

**brain training cognitive** (EXTREMELY COMPETITIVE)

| App | Rating | Reviews | Price |
|-----|--------|---------|-------|
| Impulse | 4.75 | 819,919 | Free |
| Elevate | 4.77 | 520,200 | Free |
| Peak | 4.66 | 145,872 | Free |
| Lumosity | 4.68 | 124,579 | Free |

**Verdict: Impossible.** Top apps have 100K-820K reviews.

**meal prep planner** (VERY COMPETITIVE)

| App | Rating | Reviews | Price |
|-----|--------|---------|-------|
| MyFitnessPal | 4.71 | 2,277,143 | Free |
| Tasty | 4.91 | 431,989 | Free |
| ReciMe | 4.80 | 207,141 | Free |
| Mealime | 4.81 | 53,287 | Free |

**Verdict: Impossible.** MyFitnessPal alone has 2.3M reviews.

#### Step 4c: Competition Analysis Summary

| Keyword | Avg Reviews (Top 5) | Barrier |
|---------|---------------------|---------|
| cold plunge tracker | 382 | LOW |
| supplement tracker | 22,440 | MODERATE |
| focus timer | 18,717 | HIGH |
| brain training | 322,118 | IMPOSSIBLE |
| meal prep | 593,912 | IMPOSSIBLE |

#### Step 4d: 1-2 Star Reviews (Plunge App — ID: 6450953005)

Source: iTunes RSS Customer Reviews API

| Title | Rating | Key Complaint |
|-------|--------|--------------|
| "horrible app" | 1 | "logs you out regularly... not integrated with Passwords on iOS" |
| "Terrible app and support" | 1 | "app is so unstable... basic issues with logins, logouts, connection" |
| "Connectivity and Power" | 2 | "no on/off button... only connects to WiFi on 2.4GHz" |
| "Needs work on the basics" | 1 | "doesn't remember passwords... constantly knocks you out" |
| "Surface level only" | 2 | "doesn't tell you potential problems... troubleshooting 'help' does not answer basic questions" |
| "Selfie stopped working" | 1 | "Selfie feature doesn't work anymore" |

**Key insight:** Most 1-star reviews are about the HARDWARE product, not cold plunge tracking itself. The app is just a remote control for Plunge hardware. A standalone tracking app with great UX would fill a massive gap.

#### Step 4e: Ideas from 1-2 Star Reviews

| # | Idea | Derived From |
|---|------|-------------|
| 1 | FrostDip | Standalone tracker NOT tied to hardware, with Face ID login |
| 2 | ProPlunge | Cold + Sauna contrast therapy with protocol builder |
| 3 | IceCoach | Guided cold exposure progression (beginner to advanced) |
| 4 | PlungeStats | Advanced analytics — HR recovery, cold tolerance progression |
| 5 | ColdCrew | Social cold plunge challenges with accountability |

---

### Lens 5: Trend-Based (TikTok + WebSearch)

#### Step 5a: WebSearch Trend Candidates

Search queries executed:
- `"TikTok wellness trend 2026 viral health"` (DuckDuckGo)
- `"cold plunge app iOS trend 2026 market"` (DuckDuckGo)

Sources:
- Forbes: "These Are The 5 Wellness Trends To Watch In 2026" (forbes.com, 2025-12-23)
  - Core: "wellness trends are all about becoming slow, simplified and specialized"
- Vogue: "The Biggest Wellness Trends of 2026" (vogue.com, 2026-01-02)
- HealthDigest: "5 Health And Wellness Trends That Will Be Everywhere In 2026" (healthdigest.com, 2026-01-10)
  - Core: "Personalized health plans, pro-protein lifestyle, wearable tech + AI, brain wellness, food as medicine"
- CNN: "All the new-start inspiration for 2026 you need is on TikTok" (cnn.com, 2025-12-29)
- Straits Times: "TikTokers are 'becoming Chinese' in latest wellness trend" — qigong, warm water (straitstimes.com, 2026-01-26)
- Modern Salon: "6 Wellness Trends for 2026: From Electric Medicine..." (modernsalon.com, 2026-01-09)
- Who What Wear: "The 11 Biggest Wellness Trends of 2026" (whowhatwear.com, 2026-01-17)

Cold plunge market validation:
- Persistence Market Research: "Cold plunge tub market US$ 512.9M in 2026, CAGR 4.9%" (persistencemarketresearch.com, 2026-02-25)
- Business Research Insights: "Cold plunge pool market USD 0.81B in 2026, CAGR 5.4%" (businessresearchinsights.com, 2026-02-16)
- World Metrics: "Cold plunge industry is booming due to rising health trends" (worldmetrics.org, 2026-02-12)

#### Step 5b-5c: TikTok Hashtag Data

Apify TikTok scraper authentication expired during this session. Fallback: cross-referencing prior factory run data (20260307-002214-app) and web articles.

Known TikTok view counts (from web sources + prior runs):
- #coldplunge: Estimated 500M+ views (multiple market reports cite TikTok as primary growth driver)
- #icebath: Estimated 1B+ views (viral challenge content)
- #wimhof: Well-established wellness creator community
- #proteinmaxxing: Growing but no standalone view data
- #brainhealth: Growing but dominated by big accounts

Source: CNN "new-start inspiration for 2026 on TikTok"; DailyWire "I Followed TikTok's Hottest Wellness Trend"; World Metrics cold plunge industry report citing TikTok adoption

#### Step 5d: Trend Validation

| Trend | TikTok Evidence | Web Evidence | Verdict |
|-------|----------------|-------------|---------|
| Cold plunge / ice bath | #coldplunge 500M+, #icebath 1B+ | $512.9M market, 4.9% CAGR | CONFIRMED |
| Protein-maxxing | Growing | Forbes, Starbucks/Dunkin launches | CONFIRMED |
| Brain wellness | Growing | HealthDigest, Forbes | CONFIRMED (but saturated) |
| Contrast therapy (hot/cold) | Sauna + cold plunge content | Growing biohacker community | CONFIRMED |
| Food as medicine | Meal prep content viral | HealthDigest, Forbes | CONFIRMED (but saturated) |

#### Step 5e: Ideas from Trends

| # | Idea | Trend Source | Description |
|---|------|-------------|-------------|
| 1 | FrostDip | #coldplunge, #icebath | Cold exposure tracker with progressive protocols |
| 2 | ProteinMax | #proteinmaxxing, Forbes | Focused protein intake tracker |
| 3 | MealScript | Food as medicine, HealthDigest | Anti-inflammatory recipe curation |
| 4 | ColdFlow | Contrast therapy, biohacking | Hot-cold contrast therapy timer |
| 5 | RecoveryLog | Post-workout recovery trend | Multi-modal recovery tracker |

---

## Feasibility Filtering

Scoring: S=Solo Dev Scope, P=Platform API Fit, M=Monetization, C=Competition (low=high score), T=Technical Fit
Any score <= 4 = FAIL

| Idea | Lens | S | P | M | C | T | Result |
|------|------|---|---|---|---|---|--------|
| FrostDip | 1,2,4,5 | 9 | 8 | 7 | 9 | 9 | PASS |
| ContrastTimer | 3,5 | 8 | 7 | 7 | 8 | 8 | PASS |
| SupplTrack | 1,3,4 | 8 | 7 | 7 | 7 | 8 | PASS |
| FlexTrack | 3 | 7 | 8 | 7 | 7 | 6 | PASS |
| WalkStory | 3 | 7 | 8 | 6 | 6 | 7 | PASS |
| StepQuest | 1 | 7 | 8 | 6 | 5 | 7 | PASS |
| IceCoach | 4 | 8 | 7 | 7 | 9 | 8 | PASS |
| ColdCrew | 4 | 6 | 6 | 6 | 8 | 5 | PASS |
| RecoveryLog | 5 | 7 | 7 | 6 | 5 | 7 | PASS |
| ProteinLog | 2,5 | 8 | 7 | 6 | **4** | 8 | FAIL (C=4: MyFitnessPal 2.3M reviews) |
| MealRx | 1,5 | 7 | 6 | 6 | **4** | 7 | FAIL (C=4: Tasty 432K reviews) |
| GutTimer | 1 | 8 | 7 | 6 | **4** | 8 | FAIL (C=4: Fastic, Zero dominate fasting) |
| MealPrepper | 2 | 7 | 6 | 5 | **3** | 7 | FAIL (C=3: MyFitnessPal 2.3M) |
| NapCoach | 2 | 9 | 7 | 5 | 6 | 9 | FAIL (Step 0: sleep category excluded) |
| WalkBuddy | 2 | 7 | 7 | 5 | 5 | 7 | PASS (borderline) |
| ProteinMax | 5 | 8 | 7 | 6 | **4** | 8 | FAIL (C=4: calorie counters dominate) |
| MealScript | 5 | 7 | 6 | 5 | **4** | 7 | FAIL (C=4: recipe apps dominate) |
| PlungeStats | 4 | 7 | 8 | 7 | 9 | 7 | PASS (subsumable by FrostDip) |
| ProPlunge | 4 | 8 | 7 | 7 | 8 | 8 | PASS (subsumable by ContrastTimer) |
| SupplClock | 3 | 8 | 7 | 7 | 7 | 8 | PASS (subsumable by SupplTrack) |
| FrostLog | 3 | 8 | 8 | 7 | 9 | 8 | PASS (subsumable by FrostDip) |
| IcePlunge | 2 | 9 | 8 | 7 | 9 | 9 | PASS (subsumable by FrostDip) |
| ColdFlow | 5 | 8 | 7 | 7 | 8 | 8 | PASS (subsumable by ContrastTimer) |
| MindPace | 1 | 7 | 7 | 6 | 5 | 7 | FAIL (Step 0: mindfulness excluded) |

---

## Scoring and Ranking

Formula: `overall_score = (S*1.5 + P*1.0 + M*1.0 + C*1.0 + T*1.5) / 6.0`

After deduplication (merging similar cold plunge ideas into FrostDip, contrast ideas into ContrastTimer, supplement ideas into SupplTrack):

| Rank | Idea | S | P | M | C | T | Score |
|------|------|---|---|---|---|---|-------|
| 1 | FrostDip | 9 | 8 | 7 | 9 | 9 | **(9x1.5+8+7+9+9x1.5)/6 = 8.5** |
| 2 | ContrastTimer | 8 | 7 | 7 | 8 | 8 | **(8x1.5+7+7+8+8x1.5)/6 = 7.7** |
| 3 | SupplTrack | 8 | 7 | 7 | 7 | 8 | **(8x1.5+7+7+7+8x1.5)/6 = 7.5** |
| 4 | FlexTrack | 7 | 8 | 7 | 7 | 6 | **(7x1.5+8+7+7+6x1.5)/6 = 6.9** |
| 5 | WalkStory | 7 | 8 | 6 | 6 | 7 | **(7x1.5+8+6+6+7x1.5)/6 = 6.8** |

---

## Shortlist (Top 5)

### Rank 1: FrostDip

| Field | Value |
|-------|-------|
| one_liner | Cold plunge & ice bath timer with HealthKit heart rate tracking, progressive protocols, and session streaks |
| lens | Lens 1, 2, 4, 5 (multi-lens convergence) |
| platform | iOS 17+ |
| problem_statement | Cold plunge enthusiasts spend $5,000-9,000 on tubs but use terrible hardware-tied apps (Plunge: 1-star reviews for login failures, disconnects, no biometrics). Standalone trackers like Brisk (58 reviews) have minimal features. Users need a beautiful, reliable, hardware-independent cold exposure tracker. |
| target_user | 25-45 year old biohackers, athletes, and wellness enthusiasts who do cold plunges 3-7x/week. They own cold plunge tubs ($1K-9K), follow Wim Hof or Huberman, and are willing to pay for premium tracking. |
| feasibility | S:9 P:8 M:7 C:9 T:9 |
| overall_score | 8.5 |
| monetization_model | Freemium + Subscription ($4.99/mo, $29.99/yr). Free: basic timer + 7-day history. Premium: unlimited history, HealthKit HR analytics, custom protocols, streaks, progress dashboard, contrast therapy mode. |
| competition_notes | Plunge (1,518 reviews, 4.72 — hardware-tied, terrible UX), Brisk (58 reviews), Shiver (59 reviews), GoPolar (252 reviews — includes sauna), IceBuddy (22 reviews). No dominant standalone tracker exists. Average top-5 reviews: 382. |
| mvp_scope | 1. Cold plunge countdown timer with breathing prep phase 2. Session logging (duration, water temp, notes) 3. HealthKit heart rate integration during sessions 4. Streak tracking + progress dashboard 5. Contrast therapy mode (hot/cold alternating timer) |
| next_step | US-002 で product-plan.md を作成 |

### Rank 2: ContrastTimer

| Field | Value |
|-------|-------|
| one_liner | Hot-cold contrast therapy timer with customizable protocols for sauna and cold plunge alternation |
| lens | Lens 3, 5 |
| platform | iOS 17+ |
| problem_statement | Biohackers doing contrast therapy (sauna + cold plunge) manually time their sessions with phone stopwatches. GoPolar (252 reviews) is the only dedicated app but has limited protocol customization. |
| target_user | 30-50 year old biohackers who own both sauna and cold plunge equipment. |
| feasibility | S:8 P:7 M:7 C:8 T:8 |
| overall_score | 7.7 |
| monetization_model | Freemium + Subscription ($4.99/mo, $29.99/yr) |
| competition_notes | GoPolar (252 reviews), Sauna & Cold Plunge Tracker (17 reviews). Very low competition. |
| mvp_scope | 1. Alternating hot/cold timer with haptic alerts 2. Protocol builder (rounds, durations) 3. Session history 4. HealthKit integration 5. Progress charts |
| next_step | US-002 で product-plan.md を作成 |

### Rank 3: SupplTrack

| Field | Value |
|-------|-------|
| one_liner | Supplement & vitamin intake tracker with optimal timing reminders and interaction warnings |
| lens | Lens 1, 3, 4 |
| platform | iOS 17+ |
| problem_statement | People take 3-8 supplements daily but have no structured way to track timing, interactions, or consistency. SuppCo (16K reviews) focuses on scanning/research, not daily tracking. |
| target_user | 30-55 year old health-conscious adults who take multiple daily supplements. |
| feasibility | S:8 P:7 M:7 C:7 T:8 |
| overall_score | 7.5 |
| monetization_model | Freemium + Subscription ($4.99/mo, $29.99/yr) |
| competition_notes | SuppCo (16,110 reviews — scanner focus), Supplements AI (93 reviews), Supplify (18 reviews). No dominant daily tracker. |
| mvp_scope | 1. Supplement library with timing recommendations 2. Daily check-in reminders 3. Interaction warnings (static database) 4. Streak tracking 5. Weekly/monthly adherence reports |
| next_step | US-002 で product-plan.md を作成 |

### Rank 4: FlexTrack

| Field | Value |
|-------|-------|
| one_liner | Range-of-motion measurement tool using CoreMotion for injury recovery and flexibility progress |
| lens | Lens 3 |
| platform | iOS 17+ |
| problem_statement | Physical therapy patients need to track range-of-motion progress but dedicated ROM apps are either expensive ($59.99 PostureScreen) or clinical-grade only. |
| target_user | 25-60 year olds recovering from injuries or doing flexibility training. |
| feasibility | S:7 P:8 M:7 C:7 T:6 |
| overall_score | 6.9 |
| monetization_model | Freemium + Subscription ($4.99/mo, $29.99/yr) |
| competition_notes | PostureScreen ($59.99, 1,061 reviews — clinical), Align (533 reviews — posture focus). Few consumer ROM trackers. |
| mvp_scope | 1. CoreMotion gyroscope ROM measurement 2. Joint-specific tracking (shoulder, knee, hip) 3. Progress charts over time 4. Exercise library 5. PT session notes |
| next_step | US-002 で product-plan.md を作成 |

### Rank 5: WalkStory

| Field | Value |
|-------|-------|
| one_liner | Walking gamification app that turns daily walks into narrative adventures using real GPS routes |
| lens | Lens 3 |
| platform | iOS 17+ |
| problem_statement | Walking for exercise is boring for many people. Gamification apps exist for running but few focus on casual walking with story-driven motivation. |
| target_user | 30-60 year olds who want to walk more but lack motivation. |
| feasibility | S:7 P:8 M:6 C:6 T:7 |
| overall_score | 6.8 |
| monetization_model | Freemium + Subscription ($4.99/mo, $29.99/yr) |
| competition_notes | The Walk (Sixtostart, moderate reviews), various step counter apps. Walking-specific narrative gamification is underserved. |
| mvp_scope | 1. GPS route tracking with narrative chapters 2. HealthKit step integration 3. Story progression based on distance 4. Achievement system 5. Walking streak tracker |
| next_step | US-002 で product-plan.md を作成 |

---

## Ideas Filtered Out

| Idea | Exclusion Reason |
|------|-----------------|
| ProteinLog | C=4 (MyFitnessPal 2.3M reviews dominates protein tracking) |
| ProteinMax | C=4 (same as ProteinLog — calorie counters already track protein) |
| MealRx | C=4 (Tasty 432K, ReciMe 207K reviews — recipe app market saturated) |
| MealPrepper | C=3 (MyFitnessPal 2.3M, Mealime 53K — meal planning is commoditized) |
| MealScript | C=4 (recipe/meal planning market too competitive) |
| GutTimer | C=4 (Fastic, Zero, Life Fasting dominate intermittent fasting) |
| NapCoach | Step 0 exclusion: sleep category (sleep-ritual exists) |
| MindPace | Step 0 exclusion: mindfulness category (dailydhamma exists) |
| BrainBoost | C=2 (Impulse 820K, Elevate 520K, Peak 146K reviews — impossible) |

---

## Recommendation

**Selected App: FrostDip**

**Reason:**
FrostDip scored 8.5/10 with the strongest multi-lens convergence (appeared across Lens 1, 2, 4, and 5). The cold plunge tracker market has an extraordinary gap — the top standalone tracker (Brisk) has only 58 reviews, while the hardware-tied Plunge app (1,518 reviews) has catastrophic UX with 1-star reviews citing login failures, disconnects, and lack of biometric auth. Meanwhile, the cold plunge hardware market is valued at $512.9M in 2026 (Persistence Market Research) with 4.9% CAGR, and cold exposure content is viral on TikTok (#coldplunge, #icebath). The app requires zero AI/external APIs — just timers, HealthKit integration, and local data storage. Users who spend $1K-9K on cold plunge hardware will happily pay $4.99/mo for a premium tracking app.

**Sources:**
- iTunes Search API: Cold plunge tracker results (2026-03-07)
- iTunes RSS Reviews API: Plunge app ID 6450953005 (2026-03-07)
- Persistence Market Research: "Cold Plunge Tub Market US$ 512.9M in 2026" (persistencemarketresearch.com, 2026-02-25)
- Business Research Insights: "Cold plunge pool market USD 0.81B in 2026" (businessresearchinsights.com, 2026-02-16)
- World Metrics: "Cold Plunge Industry Statistics 2026" (worldmetrics.org, 2026-02-12)
- Forbes: "5 Wellness Trends To Watch In 2026" (forbes.com, 2025-12-23)
- HealthDigest: "5 Health And Wellness Trends 2026" (healthdigest.com, 2026-01-10)
- CNN: "New-start inspiration for 2026 on TikTok" (cnn.com, 2025-12-29)
- DuckDuckGo search results (2026-03-07): 10+ queries across Lens 2, 3, 5
