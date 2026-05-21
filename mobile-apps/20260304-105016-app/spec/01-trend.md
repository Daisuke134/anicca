# Trend Research + Idea Selection

**Date:** 2026-03-04
**Developer Profile:** iOS, Swift/SwiftUI, solo dev, 1-day MVP, subscription model

---

## Developer Profile

| Attribute | Value |
|-----------|-------|
| Skills | Swift, SwiftUI, HealthKit, Foundation Models (iOS 26) |
| Platform | iOS |
| Timeline | 1 day MVP |
| Monetization | Subscription |
| Constraints | Solo dev, no backend |

---

## Brainstorming Lenses Applied

| Lens | Source | Ideas Generated |
|------|--------|----------------|
| 1: Skills & Interests | Internal | SwiftUI + HealthKit + Foundation Models combinations |
| 2: Problem-First | WebSearch | Wellness pain points, Reddit complaints |
| 3: Technology-First | Apple Developer Docs | Foundation Models (iOS 26), DeviceActivity API |
| 4: Market Gap | App Store search + WebSearch | Underserved categories with TikTok demand |
| 5: Trend-Based | TikTok Next 2026 Report, WebSearch | Viral wellness trends with no dedicated app |

---

## Shortlist (Top 5)

### Rank 1 — Chi Daily: TCM Wellness Coach

| Field | Value |
|-------|-------|
| **Idea** | Chi Daily: TCM Wellness Coach |
| **Lens** | 4: Market Gap + 5: Trend-Based |
| **One-liner** | Daily 5-question TCM constitution check-in with on-device AI recommendations — no cloud, no data leak |
| **Platform** | iOS |
| **Problem statement** | The "Chinese Baddie" TCM wellness trend is viral on TikTok with hundreds of millions of views, yet all existing TCM apps are clinical/practitioner tools. Western and Japanese users want to apply TCM principles daily (food, sleep, exercise by constitution type) but there is no consumer-facing daily check-in app. |
| **Target user** | Women 20–35 who follow wellness content on TikTok/Instagram, interested in TCM/Eastern wellness, want personalized daily guidance without complex practitioner visits |
| **Monetization model** | Freemium — 7-day trial, then $4.99/month or $34.99/year |

**Feasibility Scores:**

| Dimension | Rating | Reasoning |
|-----------|--------|-----------|
| Solo Dev Scope | STRONG (8) | SwiftUI check-in UI + Foundation Models integration — 3-week MVP |
| Platform API Fit | STRONG (7) | Foundation Models (on-device LLM), HealthKit for sleep/steps correlation |
| Monetization Viability | EXCELLENT (9) | Wellness app users pay; no backend = pure margin |
| Competition Density | EXCELLENT (9) | Zero consumer TCM daily wellness apps; only clinical tools exist |
| Technical Fit | STRONG (8) | Foundation Models (iOS 26), SwiftUI — perfect skill match |

**Overall Score: 8.2**

| Source | Quote |
|--------|-------|
| TikTok Next 2026 Report | "TikTok has discovered Traditional Chinese Medicine and wellness practices, with Chinese creators flooding FYPs with ancestral health hacks and Western audiences converting en masse" |
| TikTok 2026 Trend (WebSearch) | "'Chinese Baddie' Wellness: Chinese medicine offers something that feels more grounded, intuitive, and easier to adopt into everyday lives" |
| App Store search | TCM apps on App Store are exclusively for practitioners (TCM Clinic Aid, Acupuncture3D) — no consumer daily wellness app exists |

**MVP scope:** Daily 5-question constitutional check-in → Foundation Models generates personalized food/lifestyle tips for the day → HealthKit logs mood/energy → Weekly pattern summary

**Competition notes:** TCM Clinic Aid (practitioner reference), Acupuncture3D (educational 3D model), TcmNote (clinical notes) — all practitioner-only. Zero competition in consumer daily wellness.

**Next step:** `product-agent discover --idea "Daily TCM constitution check-in with on-device AI generating personalized food, sleep, and lifestyle recommendations based on TCM principles" --platform iOS --output-format json`

---

### Rank 2 — LongevityView: VO2 Max & Healthspan Tracker

| Field | Value |
|-------|-------|
| **Idea** | LongevityView: VO2 Max & Healthspan Tracker |
| **Lens** | 4: Market Gap + 2: Problem-First |
| **One-liner** | Apple Watch VO2 Max + HRV + resting HR aggregated into a weekly Longevity Score with Foundation Models coaching |
| **Platform** | iOS + Apple Watch |
| **Problem statement** | Apple Watch silently tracks VO2 Max, HRV, and resting HR — the three most predictive biomarkers of lifespan — but no app synthesizes these into actionable guidance. Users see raw numbers in Health but get zero coaching. |
| **Target user** | Health-conscious professionals 30–50 who wear Apple Watch and are interested in longevity/biohacking |
| **Monetization model** | $3.99/month or $24.99/year |

**Feasibility Scores:**

| Dimension | Rating | Reasoning |
|-----------|--------|-----------|
| Solo Dev Scope | STRONG (8) | HealthKit reads + Charts UI + Foundation Models tips — 2-3 weeks |
| Platform API Fit | EXCELLENT (9) | HealthKit (VO2Max, HRV, RestingHeartRate), Foundation Models, Charts |
| Monetization Viability | STRONG (8) | Longevity biohacking pays; clear premium value |
| Competition Density | STRONG (7) | Generic health aggregators exist; no VO2 Max-focused longevity coach |
| Technical Fit | EXCELLENT (9) | HealthKit queries are straightforward; perfect skill match |

**Overall Score: 7.8**

---

### Rank 3 — MoodTrace: Social Media Emotional Audit

| Field | Value |
|-------|-------|
| **Idea** | MoodTrace: Social Media Emotional Audit |
| **Lens** | 3: Technology-First (DeviceActivity API) + 4: Market Gap |
| **One-liner** | 3-second mood check before/after social media → on-device Foundation Models reveals which apps drain you |
| **Platform** | iOS |
| **Problem statement** | People intuitively feel Instagram/TikTok affects their mood but have no data to confirm it. Screen Time shows usage minutes but not emotional cost. DeviceActivity API enables mood-tagged app usage without cloud. |
| **Target user** | Digital wellness-aware users 18–35 who feel drained by social media but can't stop |
| **Monetization model** | $3.99/month |

**Feasibility Scores:**

| Dimension | Rating | Reasoning |
|-----------|--------|-----------|
| Solo Dev Scope | STRONG (8) | DeviceActivity + mood slider + Foundation Models insights — 3 weeks |
| Platform API Fit | EXCELLENT (9) | DeviceActivity API, Foundation Models, HealthKit mood |
| Monetization Viability | MODERATE (6) | Digital wellness is growing but free Screen Time competes |
| Competition Density | STRONG (8) | No mood-correlated screen time app exists on App Store |
| Technical Fit | STRONG (7) | DeviceActivity API has learning curve but manageable |

**Overall Score: 7.6**

---

### Rank 4 — Echo: Voice Evening Reflection

| Field | Value |
|-------|-------|
| **Idea** | Echo: Voice Evening Reflection |
| **Lens** | 3: Technology-First (Foundation Models) |
| **One-liner** | Talk to your iPhone for 5 minutes about your day → on-device Foundation Models returns 3 personalized insights |
| **Platform** | iOS |
| **Problem statement** | Traditional journaling requires writing (most people skip it). Therapy is expensive. AI journaling apps (Day One, Reflectly) send data to the cloud. Foundation Models enables private, voice-first self-reflection with zero data leaving the device. |
| **Target user** | Introspective adults 25–40 who tried journaling apps but found text too effortful |
| **Monetization model** | $4.99/month |

**Feasibility Scores:**

| Dimension | Rating | Reasoning |
|-----------|--------|-----------|
| Solo Dev Scope | MODERATE (6) | Speech recognition + Foundation Models + insight rendering — 4-5 weeks |
| Platform API Fit | EXCELLENT (9) | Foundation Models, Speech framework, on-device transcription |
| Monetization Viability | STRONG (8) | Self-improvement niche pays well |
| Competition Density | STRONG (7) | Cloud AI journaling apps exist; no on-device voice journaling |
| Technical Fit | STRONG (7) | Foundation Models integration is new; Speech framework is well-documented |

**Overall Score: 7.4**

---

### Rank 5 — SeasonFlow: Seasonal Living Tracker

| Field | Value |
|-------|-------|
| **Idea** | SeasonFlow: Seasonal Living Tracker |
| **Lens** | 5: Trend-Based + 4: Market Gap |
| **One-liner** | Track food, sleep, and exercise against seasonal TCM and circadian science recommendations — adapt with the earth's rhythms |
| **Platform** | iOS |
| **Problem statement** | Both TCM and modern circadian biology emphasize seasonal alignment (sleep, food, exercise vary by season). No app guides users through this. The trend toward "living in harmony with nature" is growing globally but especially in Japanese and Asian markets. |
| **Target user** | Wellness-oriented users in Japan/Asia who follow traditional seasonal practices |
| **Monetization model** | $3.99/month |

**Feasibility Scores:**

| Dimension | Rating | Reasoning |
|-----------|--------|-----------|
| Solo Dev Scope | STRONG (8) | Calendar-based content + HealthKit + Foundation Models — 3 weeks |
| Platform API Fit | STRONG (7) | HealthKit, Foundation Models, geolocation for hemisphere detection |
| Monetization Viability | STRONG (7) | Wellness niche; Japanese market has proven appetite |
| Competition Density | EXCELLENT (9) | No seasonal living app exists on App Store |
| Technical Fit | STRONG (8) | All familiar frameworks |

**Overall Score: 7.4**

---

## Ideas Filtered Out

| Idea | Lens | Reason |
|------|------|--------|
| Japanese Interval Walking | 5: Trend | 7+ apps already on App Store (JWT, JapaneseWalk, Zen Walk, etc.) — market saturated |
| Study With Me Focus Timer | 5: Trend | Extremely crowded (Be Focused, Forest, Study Bunny, Focus Buddy, etc.) |
| Habit Stacking Tracker | 4: Market Gap | Saturated (Stacked, HabitStack, Fabulous, Habitify) |
| Gut Health Symptom Diary | 2: Problem-First | Well-covered (mySymptoms, Bowelle, Cara Care, SuperBiome) |
| Fiber Tracker (Fibermaxxing) | 5: Trend | Multiple quality apps (Fiber Tracker & Counter, Simple Fiber Tracker, Fiber Tracker: Healthy Gut) |
| Red Light Therapy Tracker | 5: Trend | Apps exist (Redd, RedMed, MitoRedLight, Joovv) |
| Body Doubling (ADHD) | 4: Market Gap | Apps exist (dubbii, Flow Club, FLOWN, Deepwrk) |
| Seed Cycling | 4: Market Gap | "Seed Cycling" app already on App Store |
| Cortisol Tracker | 4: Market Gap | Apps exist (Cortisol Detox, Pardigm, StressWatch) |

---

## Selected Idea: Chi Daily — TCM Wellness Coach

**Overall Score: 8.2 / 10** — Highest ranked across all five feasibility dimensions.

**Why this wins:**

| Reason | Evidence |
|--------|----------|
| Viral TikTok demand | "Chinese Baddie" wellness trend — millions of views, TCM content flooding FYPs in 2026 |
| True blue ocean | Zero consumer-facing TCM daily wellness apps. All TCM apps are practitioner-only tools. |
| Foundation Models differentiation | On-device AI gives personalized daily guidance = privacy-first, no backend needed |
| Japanese market | TCM has deep cultural roots in Japan (漢方 kampo tradition) — dual-market opportunity |
| High emotional ROI | Aligns with TikTok 2026 trend: "substance over stunt", people want authentic wellness |
| Solo dev feasible | SwiftUI check-in UI + Foundation Models integration = 3-week MVP |

**App name:** Chi Daily
**Bundle ID candidate:** com.aniccafactory.chidaily
**Subscription:** $4.99/month / $34.99/year
**Target markets:** US (English), Japan (Japanese)

---

*Sources:*
- *TikTok Next 2026 Trend Report: https://ads.tiktok.com/business/library/TikTok_Next_2026_Trend_Report.pdf*
- *Apple Foundation Models: https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/*
- *App Store TCM search: https://apps.apple.com/search — "TCM", "traditional chinese medicine"*
- *Wellness trend (Chinese Baddie): https://theeverygirl.com/chinese-baddie-tiktok-wellness-trend/*
- *AI Companion market: https://natively.dev/blog/mobile-app-ideas-2026*
