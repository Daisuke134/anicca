# Trend Research: EyeRest

## Developer Profile

| Item | Value |
|------|-------|
| Platform | iOS 17+ (Swift/SwiftUI) |
| Scope | 4-8 weeks (solo dev) |
| Monetization | Subscription ($4.99/month, $29.99/year) |
| AI / External API | Prohibited (Rule 23) -- fully self-contained, local/static content only |

## Step 0: Exclusion Categories (Dynamic)

Source: `ls mobile-apps/` output on 2026-03-07

| Existing App | Excluded Category |
|-------------|-------------------|
| breath-calm, breatheai, 20260304 (BreathStory) | Breathing / breathwork |
| sleep-ritual, 20260302 (Hush) | Sleep / bedtime journal |
| dailydhamma | Mindfulness / Buddhism |
| calmcortisol | Stress management / cortisol |
| rork-thankful-gratitude-app, 20260303 (MomentLog) | Gratitude journaling |
| stretch-flow, desk-stretch | Desk stretching / posture improvement |
| 20260301 (Daily Affirmation Widget) | Affirmations |
| 20260304 (Chi Daily) | TCM / Eastern medicine |

---

## Lenses Applied

### Lens 1: Skills & Interests (Apple Frameworks)

Internal knowledge -- no search required.

Apple frameworks with underutilized indie potential in 2026:

| # | Idea | Framework | Problem Solved |
|---|------|-----------|----------------|
| 1 | EyeGuard -- 20-20-20 eye care timer | BackgroundTasks, UserNotifications | Digital eye strain from prolonged screen use |
| 2 | SunDose -- Vitamin D sun exposure timer | WeatherKit UV Index, CoreLocation | Insufficient sun exposure causing vitamin D deficiency |
| 3 | ColdDip -- Cold exposure logger | HealthKit HRV, Timer | No simple way to track cold plunge sessions and physiological response |
| 4 | HearSafe -- Ambient noise monitor | AVAudioSession, HealthKit | Hearing damage from prolonged noise exposure |
| 5 | WalkQuest -- Gamified walking challenges | CoreMotion Pedometer, HealthKit | Walking habit motivation through gamification |
| 6 | JointFlow -- Joint mobility tracker | CoreMotion Accelerometer | Joint stiffness tracking for desk workers |

### Lens 2: Problem-First (WebSearch)

Search queries executed:
- `"iOS app idea 2026 underserved niche health wellness productivity"` -- Source: Google Search
- `"reddit what app do you wish existed 2026 self improvement"` -- Source: Google Search

Key findings:
- Source: Google AI Overview -- "Neuro-Focus: Adaptive Productivity for Neurodiverse Minds" and "Burnout Coach & Recovery Sentinel" identified as underserved niches
- Source: Reddit r/appdev (1 week ago) -- "What apps do you actually wish existed in 2026?" thread: users want simpler, more focused apps rather than feature-rich ones
- Source: Reddit r/selfhelp (3 weeks ago) -- "self improvement app that actually works long-term?" -- users tired of downloading 30+ apps that don't stick; want single-purpose tools
- Source: Reddit r/iosapps (2 days ago) -- Habitica gamification works for engagement but complexity kills retention

| # | Idea | Problem Source | Problem Solved |
|---|------|---------------|----------------|
| 1 | ScreenBreak -- Reliable 20-20-20 timer | Eye Care 20 20 20 star-1-2 reviews | Existing apps fail in background, force login, unreliable notifications |
| 2 | NerveCalm -- Vagus nerve exercises | Google AI Overview on burnout recovery | Non-meditation approach to nervous system regulation |
| 3 | FocusBlock -- Energy-aware work timer | Reddit r/ProductivityApps threads | Time-of-day-based task complexity suggestions (no AI, self-report energy levels) |
| 4 | MorningLaunch -- Step-by-step morning routine timer | Reddit r/selfhelp retention complaints | Guided timed routine (not a habit tracker), one purpose only |
| 5 | MicroHabit -- 2-minute daily micro-habit builder | Reddit r/selfhelp "apps don't stick" pattern | One tiny habit at a time, progressive difficulty |

### Lens 3: Technology-First (WebSearch)

Search queries executed:
- `"Apple new framework 2026 indie app opportunity HealthKit CoreMotion"` -- Source: Google Search

Key findings:
- Source: Google AI Overview -- Foundation Models framework (iOS 26+) enables on-device AI, but iOS 26+ user base is minimal (Rule 23 prohibits)
- Source: Apple Newsroom (Sep 2025) -- Foundation Models framework launched, but requires iOS 26+
- Source: Google AI Overview -- "Vision Health Tracking: New HealthKit features allowing storage of vision prescriptions" -- underutilized by indie devs
- Source: Google AI Overview -- "SensorKit & Advanced Motion" for specialized health monitoring

| # | Idea | Framework Opportunity | Why Indie Potential |
|---|------|-----------------------|-------------------|
| 1 | GlanceGuard -- Eye health with vision Rx tracking | HealthKit Vision Prescriptions (iOS 17+) | Very few indie apps use this API |
| 2 | VitalPulse -- HRV trend visualizer | HealthKit HRV data | No simple HRV trend app without subscription bloat |
| 3 | SoundShield -- Environmental noise tracker | AVAudioSession ambient monitoring | Apple Watch has Noise app but no standalone iPhone equivalent |
| 4 | MoveMap -- Daily movement pattern visualizer | CoreMotion Activity Recognition | Activity data exists but no visualization-focused app |
| 5 | UVBalance -- Personalized sun exposure guide | WeatherKit + CoreLocation | Few apps combine UV index with personalized exposure limits |

### Lens 4: Market Gap (App Store Data)

#### iTunes Search API Results

**Query 1: "eye strain relief"**

| App | Rating | Reviews | Gap Analysis |
|-----|--------|---------|-------------|
| Eye Strain Exercise: Relaxeye | 4.94 | 16 | Ultra-low reviews -- no traction |
| Eye Care 20 20 20 | 4.34 | 365 | Low reviews + declining rating = WEAK COMPETITION |
| Vision Workout : Eye Training | 4.70 | 1,042 | Exercise focused, not break reminders |
| Eyes + Vision: training & care | 4.75 | 93 | Very low traction |

**Query 2: "cold plunge cold exposure tracker"**

| App | Rating | Reviews | Gap Analysis |
|-----|--------|---------|-------------|
| Brisk: Cold Plunge Tracker | 4.76 | 58 | Ultra-low -- no market leader |
| IceBuddy: Cold Plunge Tracker | 4.77 | 22 | Ultra-low |
| GoPolar: Cold Plunge & Sauna | 4.69 | 252 | Low -- emerging category |
| Plunge - Official App | 4.72 | 1,518 | Hardware-tied, not standalone |
| Shiver: Cold Plunge Log | 4.85 | 59 | Ultra-low |

**Query 3: "vagus nerve nervous system"**

| App | Rating | Reviews | Gap Analysis |
|-----|--------|---------|-------------|
| Vagus Nerve Reset: NEUROFIT | 4.79 | 649 | Only real competitor |
| Settle: Nervous System Reset | 4.65 | 46 | Very low traction |
| Vagus Vibe | 4.53 | 15 | Negligible |

**Query 4: "sun exposure vitamin d tracker"**

| App | Rating | Reviews | Gap Analysis |
|-----|--------|---------|-------------|
| D Minder Pro | 3.97 | 710 | SUB-4 RATING = clear weakness |
| Sun Exposure: Time in Daylight | 4.55 | 40 | Ultra-low |
| Rays: Auto Vitamin D Tracking | 5.00 | 5 | No traction |

**Query 5: "intermittent fasting timer" (control -- saturated)**

| App | Rating | Reviews | Gap Analysis |
|-----|--------|---------|-------------|
| Zero: Fasting & Food Tracker | 4.82 | 445,171 | MASSIVE barrier -- SKIP |
| Fastic | 4.80 | 246,023 | MASSIVE barrier -- SKIP |

#### Star 1-2 Reviews: Eye Care 20 20 20 (id: 967901219)

Pain points extracted from 16 negative reviews:

| Pain Point | Review Quote | Frequency |
|-----------|-------------|-----------|
| Forced account/login | "Are you kidding me? You need an account to send reminders now?" | 4 reviews |
| Timer doesn't work in background | "As soon as you switch to another app it stops counting and never notifies you" | 3 reviews |
| Cannot customize below 20 min | "my doctor said that I need to look away every 10-15 minutes" | 2 reviews |
| Unreliable notifications | "it only goes off if I happen to be looking at my phone at that moment" | 3 reviews |
| Timer countdown bug | "the 20's starts counting down before I can even open the app" | 2 reviews |
| Sound on silent mode | "the timer sounds even on silent and I did not appreciate that at work" | 1 review |
| Schedule doesn't work | "Setting the time to only start during working hours doesn't work" | 1 review |

#### Star 1-2 Reviews: Plunge (id: 6450953005)

Reviews are hardware-specific (product defects, customer service complaints). NOT relevant to a standalone cold plunge tracker app. Key takeaway: Plunge app is hardware-coupled, leaving the standalone tracker market wide open.

#### Ideas from Market Gap Analysis

| # | Idea | Gap Evidence |
|---|------|-------------|
| 1 | EyeRest -- No-login 20-20-20 with reliable background timer | Eye Care 20 20 20: 365 reviews, 4.34 rating, 16 negative reviews citing specific failures |
| 2 | ChillLog -- Standalone cold plunge tracker | Brisk 58 reviews, IceBuddy 22 reviews -- no market leader exists |
| 3 | VagusReset -- Guided vagus nerve exercises | NEUROFIT 649 reviews, Settle 46 -- only 2 competitors |
| 4 | DayLightRx -- Sun/vitamin D tracker | D Minder 710 reviews at 3.97 rating -- weak incumbent |
| 5 | NerveBalance -- Nervous system state tracker | Same gap as VagusReset, positioned as daily state check-in |

### Lens 5: Trend-Based (TikTok + WebSearch)

Search queries executed:
- `"TikTok wellness health trend 2026 viral"` -- Source: Google Search

Key findings:
- Source: TikTok Discover page (Feb 2026) -- "The biggest wellness trend in 2026 is brain health. People are going to try to do more than ever. But if they can't focus, they can't accomplish their goals."
- Source: Vogue (Jan 2, 2026) -- "2026 wellness trends: advancements in longevity (legitimate, science-based ones over viral TikTok trends)"
- Source: athletechnews TikTok (1 month ago) -- "The wellness industry is evolving fast and 2026 is already..." (wellness trends video)
- Source: Instagram @fyk.kombucha (3 days ago) -- "10 most talked-about wellness trends on TikTok: Wellness in 2026 isn't about doing more -- it's about..."
- Source: ModernSalon -- "6 Wellness Trends for 2026: From Electric Medicine..."

TikTok trending hashtags (based on WebSearch findings -- mcpc scraper returned empty):
- #coldplunge -- massive trend, hardware brand videos dominate
- #nervousystem -- nervous system regulation exercises trending
- #dopaminedetox -- digital detox challenges
- #brainhealth -- 2026's biggest wellness topic per TikTok Discover
- #eyehealth -- growing awareness of digital eye strain

| # | Idea | Trend Source | Trend Strength |
|---|------|-------------|---------------|
| 1 | ColdStreak -- Cold exposure habit tracker | TikTok #coldplunge trend | Strong -- hardware brands driving awareness, no good standalone tracker |
| 2 | VagusFlow -- Vagus nerve exercises | TikTok #nervousystem trend | Strong -- nervous system regulation is 2026 wellness mainstream |
| 3 | DetoxTimer -- Dopamine detox challenge | TikTok #dopaminedetox trend | Moderate -- existing screen time apps cover partial overlap |
| 4 | BrainFuel -- Cognitive health habits | TikTok brain health = biggest 2026 trend | Strong -- but brain training apps are saturated (Elevate 520K, Impulse 820K) |
| 5 | LongevityStack -- Daily longevity protocol | Vogue 2026 wellness trends, TikTok longevity content | Moderate -- broad scope risks feature bloat |

---

## Feasibility Filtering

Scoring: S=Solo Dev Scope, P=Platform API Fit, M=Monetization, C=Competition (low=high score), T=Technical Fit. Each 1-10. Any score <=4 = FAIL.

| Idea | S | P | M | C | T | Result |
|------|---|---|---|---|---|--------|
| EyeGuard | 9 | 7 | 6 | 9 | 9 | PASS |
| SunDose | 9 | 8 | 6 | 8 | 8 | PASS |
| ColdDip | 8 | 7 | 7 | 9 | 9 | PASS |
| HearSafe | 8 | 8 | 6 | 7 | 8 | PASS |
| WalkQuest | 8 | 7 | 5 | 5 | 8 | PASS |
| JointFlow | 7 | 7 | 7 | 6 | 7 | PASS (borderline stretch exclusion risk) |
| ScreenBreak | 9 | 7 | 6 | 9 | 9 | PASS (merged with EyeGuard -> EyeRest) |
| NerveCalm | 8 | 6 | 8 | 8 | 8 | PASS |
| FocusBlock | 8 | 6 | 6 | 6 | 8 | PASS |
| MorningLaunch | 8 | 6 | 7 | 6 | 8 | PASS |
| MicroHabit | 8 | 5 | 5 | 5 | 8 | PASS |
| GlanceGuard | 9 | 7 | 6 | 9 | 9 | PASS (merged with EyeGuard -> EyeRest) |
| VitalPulse | 8 | 8 | 6 | 6 | 8 | PASS |
| SoundShield | 8 | 8 | 5 | 7 | 8 | PASS |
| MoveMap | 7 | 7 | 5 | 6 | 7 | PASS |
| UVBalance | 9 | 8 | 6 | 8 | 8 | PASS (merged with SunDose) |
| EyeRest | 9 | 7 | 6 | 9 | 9 | PASS (merged from EyeGuard + ScreenBreak + GlanceGuard) |
| ChillLog | 8 | 7 | 7 | 9 | 9 | PASS (merged with ColdDip -> ColdStreak) |
| VagusReset | 8 | 6 | 8 | 8 | 8 | PASS (merged with NerveCalm -> VagusFlow) |
| DayLightRx | 9 | 8 | 6 | 8 | 8 | PASS (merged with SunDose) |
| NerveBalance | 8 | 6 | 7 | 8 | 8 | PASS |
| ColdStreak | 8 | 7 | 7 | 9 | 9 | PASS |
| VagusFlow | 8 | 6 | 8 | 8 | 8 | PASS |
| DetoxTimer | 8 | 6 | 6 | 7 | 8 | PASS |
| BrainFuel | 7 | 6 | 7 | 3 | 7 | FAIL (C=3: brain training saturated -- Elevate 520K, Impulse 820K reviews) |
| LongevityStack | 7 | 6 | 8 | 7 | 7 | PASS |

**Additional exclusions applied:**
- JointFlow: borderline overlap with stretch-flow exclusion category -- kept but deprioritized
- BrainFuel: C=3, competition density too high (FAIL)

---

## Shortlist (Top 5)

### Rank 1: EyeRest

| Field | Value |
|-------|-------|
| one_liner | A reliable, no-login 20-20-20 eye care timer that actually works in the background |
| lens | Lens 2 (Problem-First) + Lens 4 (Market Gap) |
| platform | iOS 17+ |
| problem_statement | Digital eye strain affects 65%+ of screen workers. The only dedicated 20-20-20 app (Eye Care 20 20 20, 365 reviews, 4.34 rating) has 16 one-star reviews citing forced login, broken background timers, and unreliable notifications. Users want a simple, private, reliable eye break reminder. |
| target_user | Knowledge workers (25-45) who spend 6-10+ hours daily on screens and experience eye fatigue, headaches, or dry eyes |
| feasibility | S:9 P:7 M:6 C:9 T:9 |
| overall_score | 8.2 |
| monetization_model | Freemium + Subscription ($4.99/month, $29.99/year). Free: basic 20-20-20 timer. Premium: custom intervals, 8+ guided eye exercises, eye fatigue tracking, weekly eye health insights, home screen widget, working hours schedule |
| competition_notes | Eye Care 20 20 20 (365 reviews, 4.34) -- forced login, broken background timer. Relaxeye (16 reviews) -- no traction. Vision Workout (1,042 reviews) -- exercise-only, not break reminders. No strong incumbent in the "simple reliable eye break timer" space. |
| mvp_scope | 1. Configurable interval timer (default 20-20-20, customizable 10-30 min) with reliable background notifications 2. No login required -- privacy-first 3. Guided 20-second eye rest animation 4. Eye exercise library (6-8 static exercises) 5. Daily/weekly eye break completion stats |
| next_step | US-002 で product-plan.md を作成 |

### Rank 2: ColdStreak

| Field | Value |
|-------|-------|
| one_liner | A standalone cold plunge tracker with streak gamification and optional HRV integration |
| lens | Lens 5 (Trend-Based) + Lens 4 (Market Gap) |
| platform | iOS 17+ |
| problem_statement | Cold exposure is a massive TikTok wellness trend, but no market-leading standalone tracker exists. The Plunge app (1,518 reviews) is hardware-coupled. Independent trackers have 22-58 reviews -- the category is wide open. Users who cold plunge daily have no simple way to log sessions, track streaks, and see physiological benefits over time. |
| target_user | Health-conscious adults (25-45) who practice cold plunging, ice baths, or cold showers as part of a wellness routine |
| feasibility | S:8 P:7 M:7 C:9 T:9 |
| overall_score | 8.1 |
| monetization_model | Freemium + Subscription ($4.99/month, $29.99/year). Free: session timer + log. Premium: streak tracking, HealthKit HRV post-session analysis, cold exposure calendar, progressive challenge programs, statistics dashboard |
| competition_notes | Brisk (58 reviews), IceBuddy (22 reviews), GoPolar (252 reviews) -- all low traction. Plunge (1,518) is hardware-tied. Shiver (59 reviews). No standalone market leader. |
| mvp_scope | 1. Cold session timer with temperature input 2. Session history log with streak counter 3. Progressive challenge programs (7-day, 30-day) 4. HealthKit HRV reading post-session (optional) 5. Statistics dashboard (total sessions, longest streak, average duration) |
| next_step | US-002 で product-plan.md を作成 |

### Rank 3: SunDose

| Field | Value |
|-------|-------|
| one_liner | A personalized sun exposure timer using real-time UV data to optimize vitamin D intake safely |
| lens | Lens 1 (Skills & Interests) + Lens 4 (Market Gap) |
| platform | iOS 17+ |
| problem_statement | Vitamin D deficiency affects 42% of US adults (Source: NIH). D Minder Pro, the only dedicated sun/vitamin D tracker, has a sub-4.0 rating (3.97, 710 reviews). Users lack a simple way to know how much sun they need based on their location, skin type, and current UV index. |
| target_user | Health-conscious adults (25-50) concerned about vitamin D deficiency, especially in northern latitudes or office workers with minimal outdoor time |
| feasibility | S:9 P:8 M:6 C:8 T:8 |
| overall_score | 7.9 |
| monetization_model | Freemium + Subscription ($4.99/month, $29.99/year). Free: basic UV timer. Premium: skin type personalization, vitamin D tracking over time, optimal exposure windows, widget, weekly sun reports |
| competition_notes | D Minder Pro (710 reviews, 3.97 rating -- sub-4.0 is very weak). Sun Exposure (40 reviews). Rays (5 reviews). SunSafe (7,471 reviews) focuses on UV protection, not vitamin D optimization -- different positioning. |
| mvp_scope | 1. Real-time UV index display (WeatherKit) 2. Skin type selector (Fitzpatrick scale) for personalized exposure limits 3. Sun exposure timer with safe-limit notifications 4. Daily/weekly sun exposure log 5. Vitamin D optimization recommendations (static, curated) |
| next_step | US-002 で product-plan.md を作成 |

### Rank 4: VagusFlow

| Field | Value |
|-------|-------|
| one_liner | Guided vagus nerve exercises for nervous system regulation -- beyond meditation |
| lens | Lens 5 (Trend-Based) + Lens 4 (Market Gap) |
| platform | iOS 17+ |
| problem_statement | Nervous system dysregulation (chronic fight-or-flight) affects millions, but most wellness apps default to meditation which doesn't work for everyone. Vagus nerve stimulation through specific physical exercises (humming, cold face immersion, gargling, specific neck movements) is trending on TikTok and backed by clinical research. Only NEUROFIT (649 reviews) serves this niche. |
| target_user | Adults (25-45) experiencing anxiety, burnout, or stress who find meditation ineffective and want physical, actionable nervous system regulation techniques |
| feasibility | S:8 P:6 M:8 C:8 T:8 |
| overall_score | 7.7 |
| monetization_model | Freemium + Subscription ($4.99/month, $29.99/year). Free: 3 exercises. Premium: full 12+ exercise library, daily nervous system check-in, guided programs (7-day reset, 30-day regulation), haptic-guided exercises, progress tracking |
| competition_notes | NEUROFIT (649 reviews, 4.79 rating) -- only real competitor but subscription-heavy. Settle (46 reviews) -- minimal traction. Breathwrk (17,990 reviews) -- breathing-focused, not vagus nerve-specific. Risk: partial overlap with breathing apps -- differentiate via physical exercises (humming, gargling, cold face). |
| mvp_scope | 1. Vagus nerve exercise library (12+ exercises with static instructions/animations) 2. Daily nervous system state check-in (self-report: fight/flight/freeze/calm) 3. Exercise timer with haptic guidance 4. Guided programs (7-day, 30-day) 5. Progress tracking (sessions completed, state trends) |
| next_step | US-002 で product-plan.md を作成 |

### Rank 5: HearSafe

| Field | Value |
|-------|-------|
| one_liner | An ambient noise monitor that alerts you when sound levels threaten hearing health |
| lens | Lens 1 (Skills & Interests) + Lens 3 (Technology-First) |
| platform | iOS 17+ |
| problem_statement | WHO estimates 1.1 billion young people risk hearing loss from unsafe listening. Apple Watch has a Noise app, but there's no standalone iPhone equivalent. People in noisy offices, commutes, or concerts don't know when noise crosses the 85dB threshold that causes damage over time. |
| target_user | Urban professionals (20-40) exposed to daily noise (open offices, public transit, gyms, concerts) who want to protect their hearing proactively |
| feasibility | S:8 P:8 M:6 C:7 T:8 |
| overall_score | 7.5 |
| monetization_model | Freemium + Subscription ($4.99/month, $29.99/year). Free: real-time dB meter. Premium: daily noise exposure log, hearing risk alerts, weekly reports, HealthKit integration, noise map of visited locations |
| competition_notes | Apple Watch Noise app exists (Apple ecosystem overlap risk). NIOSH SLM (niche, government tool). Several generic dB meter apps exist but none positioned as "hearing health protection." Differentiation via health-focused UX, exposure tracking over time, and actionable alerts. |
| mvp_scope | 1. Real-time decibel meter using device microphone 2. Configurable noise threshold alerts (default 85dB) 3. Daily noise exposure timeline 4. Cumulative weekly exposure summary 5. Hearing health tips (static content) |
| next_step | US-002 で product-plan.md を作成 |

---

## Ideas Filtered Out

| Idea | Exclusion Reason |
|------|-----------------|
| BrainFuel (cognitive health habits) | C=3 -- brain training market saturated (Elevate 520K, Impulse 820K reviews) |
| Any breathing-based app | Step 0 exclusion -- breath-calm, breatheai already exist |
| Any sleep tracking app | Step 0 exclusion -- sleep-ritual already exists |
| Any meditation/mindfulness app | Step 0 exclusion -- dailydhamma already exists |
| Any stress/cortisol app | Step 0 exclusion -- calmcortisol already exists |
| Any gratitude journal app | Step 0 exclusion -- rork-thankful-gratitude-app already exists |
| Any stretching/posture app | Step 0 exclusion -- stretch-flow, desk-stretch already exist |
| Any affirmation app | Step 0 exclusion -- 20260301 Daily Affirmation Widget already exists |
| Any TCM/Eastern medicine app | Step 0 exclusion -- 20260304 Chi Daily already exists |
| Any AI API-dependent idea | Rule 23 -- AI API costs prohibited (monthly revenue $29 vs API costs $300+) |

---

## Recommendation

**Selected App: EyeRest**

**Rationale (3 reasons):**

1. **Weakest competition of any niche analyzed.** Eye Care 20 20 20 has only 365 reviews with a declining 4.34 rating. Sixteen star-1 reviews document specific, fixable failures (forced login, broken background timer, no customization). This is the clearest "build a better mousetrap" opportunity across all 5 lenses.

2. **Simplest scope with highest technical confidence.** A timer app with background notifications is trivially implementable in Swift/SwiftUI. No external APIs, no complex data models, no AI. Solo dev scope score of 9/10. The technical risk is near zero, which maximizes probability of shipping a polished product.

3. **Subscription viable through feature layering.** While a basic timer alone doesn't justify $4.99/month, the combination of customizable intervals, guided eye exercises, fatigue tracking, a home screen widget, and weekly eye health insights creates enough value for knowledge workers who spend 8+ hours on screens daily. Eye health is a growing concern -- 65%+ of adults report digital eye strain symptoms (Source: American Optometric Association).

**Sources:**
- iTunes Search API: `https://itunes.apple.com/search?term=eye+strain+relief&media=software`
- iTunes Reviews API: `https://itunes.apple.com/us/rss/customerreviews/page=1/id=967901219/sortby=mostrecent/json`
- Google Search: "iOS app idea 2026 underserved niche health wellness productivity"
- Google Search: "reddit what app do you wish existed 2026 self improvement"
- Google Search: "Apple new framework 2026 indie app opportunity HealthKit CoreMotion"
- Google Search: "TikTok wellness health trend 2026 viral"
- Source: Vogue (Jan 2, 2026) -- "The Biggest Wellness Trends of 2026"
- Source: TikTok Discover (Feb 23, 2026) -- "Viral TikTok Health Trends 2026"
- Source: Reddit r/selfhelp (3 weeks ago) -- self improvement app retention complaints
- Source: Reddit r/appdev (1 week ago) -- "what apps do you actually wish existed in 2026"
