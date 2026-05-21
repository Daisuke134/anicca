# US-001: Trend Research + Idea Selection

**Date:** 2026-03-02
**Developer Profile (Fixed):** iOS/Swift/SwiftUI, solo dev, 1-day build target, subscription model

---

## Developer Profile

| Item | Value |
|------|-------|
| Skills | Swift, SwiftUI, HealthKit, Foundation Models, RevenueCat, Mixpanel |
| Platform | iOS 18+ |
| Time | 1 day (solo) |
| Backend | None (SwiftData / UserDefaults only) |
| Model | Subscription ($4.99/mo, $29.99/yr) |

---

## Five Brainstorming Lenses Applied

### Lens 1: Skills & Interests
*What can a Swift/SwiftUI solo dev uniquely build?*

- SwiftUI + Foundation Models → private on-device AI journaling
- HealthKit + SwiftUI → sleep insight explainer
- RevenueCat + SwiftUI → simple subscription utility

Source: [idea-generator SKILL.md](../../.claude/skills/idea-generator/SKILL.md)

### Lens 2: Problem-First
*What takes too long / frustrates users daily?*

- Sleep anxiety: racing thoughts before bed disrupt sleep quality. No simple app addresses pre-sleep mental offload.
- Apple Health sleep data: users find it confusing, scattered, and actionable insights are buried.

Source: [Apple Community – Sleep Tracking Complaints](https://discussions.apple.com/thread/254841815), [Apple Community – UX Issues](https://discussions.apple.com/thread/256217192)

### Lens 3: Technology-First
*Which Apple frameworks have few quality indie apps?*

- **Foundation Models** (iOS 18+): on-device LLM, free inference, no API key, offline. Few apps use it yet outside journaling giants.
- **HealthKit sleep data read**: simple read-only integration, no complex permissions.

Source: [Apple Foundation Models Framework](https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/), [TechCrunch – Developers using local AI](https://techcrunch.com/2025/10/03/how-developers-are-using-apples-local-ai-models-with-ios-26/)

### Lens 4: Market Gap
*Where are App Store categories underserved or stale?*

- Sleep + mental wellness intersection: Sleep Cycle (UX degraded), Calm (too broad), no app combining pre-sleep worry offload + sleep data correlation.
- Journaling: Day One (complex, expensive), Daylio (mood only) — gap for dead-simple + AI insights.

Source: [RevenueCat State of Subscription Apps 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/), [iOS App Trends 2026](https://asappstudio.com/ios-app-trends-2026/)

### Lens 5: Trend-Based
*Macro trends creating new app opportunities?*

- **AI-native + privacy-first**: Foundation Models processes everything on-device. "Your data never leaves your device" is a marketing advantage in 2026.
- **Mental wellness + sleep**: Growing anxiety among 25–40 demographic; sleep apps are the fastest-growing wellness category.
- **Subscription willingness**: Health & Fitness has 2nd-highest trial-to-paid conversion (43.8%) per RevenueCat 2025 data.

Source: [RevenueCat State of Subscription Apps 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/), [iOS App Trends 2026](https://asappstudio.com/ios-app-trends-2026/), [Foundation Models Privacy](https://machinelearning.apple.com/research/introducing-apple-foundation-models)

---

## Shortlist (5 Ideas Evaluated)

### Rank 1: **Hush — Pre-Sleep Worry Journal**

| Field | Value |
|-------|-------|
| idea | Hush — Pre-Sleep Worry Journal |
| one_liner | Dump your worries before bed, let on-device AI reframe them, sleep better |
| lens | Problem-First + Technology-First (Foundation Models + HealthKit) |
| platform | iOS 18+ |
| problem_statement | 40% of adults lie awake with racing thoughts. No app addresses the root cause: unprocessed worries. Journaling apps are complex; sleep apps track but don't intervene. |
| target_user | 25–40 yo professionals, anxiety-prone, know journaling helps but hate complex apps |
| monetization_model | Freemium: 7-day free trial, then $4.99/mo or $29.99/yr |
| competition_notes | Sleep Cycle: tracks sleep, no mental wellness. Calm: meditation only, no journaling. Day One: too complex. Reflectly: discontinued. Gap is clear. |
| mvp_scope | Pre-sleep worry entry (text bullets), Foundation Models reframe each worry as "parking lot" item + 1 calming sentence, morning resolution check, weekly pattern summary |
| sources | Apple Foundation Models (https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/), RevenueCat conversion data (https://www.revenuecat.com/state-of-subscription-apps-2025/) |

**Feasibility Scores:**

| Dimension | Score | Reason |
|-----------|-------|--------|
| Solo Dev Scope | 9 | EXCELLENT — SwiftUI + SwiftData + Foundation Models. No backend. 1-day feasible. |
| Platform API Fit | 9 | EXCELLENT — Foundation Models (on-device LLM) + HealthKit read (optional sleep correlation) |
| Monetization Viability | 8 | STRONG — Health & Fitness 43.8% trial-to-paid. Clear value: better sleep. |
| Competition Density | 8 | STRONG — No direct competitor combines pre-sleep worry offload + on-device AI |
| Technical Fit | 9 | EXCELLENT — Swift/SwiftUI/Foundation Models is exactly the skill set |

**overall_score: 8.7** (Solo Dev Scope + Technical Fit weighted 1.5x)

`next_step: product-agent discover --idea "iOS app that helps users dump pre-sleep worries, reframes them with on-device AI, and shows weekly sleep-worry correlation" --platform iOS --output-format json`

---

### Rank 2: **Dream Decoder — AI Dream Journal**

| Field | Value |
|-------|-------|
| idea | Dream Decoder |
| one_liner | Log dreams in 30 seconds, on-device AI finds recurring symbols and emotions |
| lens | Technology-First (Foundation Models) |
| platform | iOS 18+ |
| problem_statement | Dream journaling requires effort; people give up. Existing apps are manual with no intelligence. |
| target_user | 20–35 yo curious about psychology, self-improvement |
| monetization_model | $3.99/mo or $24.99/yr |
| competition_notes | Shadow (popular but subscription only for insights), Reflectly (discontinued), DreamBook (no AI) |
| mvp_scope | Morning voice/text dream entry, Foundation Models symbol detection, weekly emotion pattern, sleep quality badge from HealthKit |

**Feasibility Scores:**

| Dimension | Score | Reason |
|-----------|-------|--------|
| Solo Dev Scope | 9 | Simple UI + Foundation Models |
| Platform API Fit | 8 | Foundation Models strong fit |
| Monetization Viability | 7 | MODERATE — dream journals are niche |
| Competition Density | 7 | Shadow is strong competitor |
| Technical Fit | 9 | Matches skills |

**Overall Score: 8.1**

---

### Rank 3: **Screen Mindful — AI Phone Coaching**

| Field | Value |
|-------|-------|
| idea | Screen Mindful |
| one_liner | Weekly AI coaching on your phone usage patterns — not just data, actionable change |
| lens | Technology-First (DeviceActivity + Foundation Models) |
| platform | iOS 16+ |
| problem_statement | Screen Time shows data but gives no coaching. Users know they scroll too much but don't change. |
| target_user | 25–40 yo knowledge workers trying to reduce phone dependency |
| monetization_model | $4.99/mo |
| competition_notes | One Sec (friction-based), YourHour (Android-first), ScreenZen — none with AI coaching |
| mvp_scope | DeviceActivity usage read, Foundation Models weekly coaching letter, goal setting |

**Feasibility Scores:**

| Dimension | Score | Reason |
|-----------|-------|--------|
| Solo Dev Scope | 7 | DeviceActivity permission flow is complex (Family Controls entitlement required) |
| Platform API Fit | 8 | DeviceActivity + Foundation Models fit |
| Monetization Viability | 8 | STRONG digital wellness market |
| Competition Density | 7 | Some quality competitors |
| Technical Fit | 7 | DeviceActivity is less familiar |

**Overall Score: 7.5** (Family Controls entitlement = extra review risk)

---

### Rank 4: **One Line — Micro Daily Journal**

| Field | Value |
|-------|-------|
| idea | One Line |
| one_liner | One sentence per day, forever. AI shows life themes at 30/90/365 days. |
| lens | Problem-First + Technology-First |
| platform | iOS 17+ |
| problem_statement | Journaling is abandoned because it's too much work. One sentence is sustainable. |
| target_user | 25–40 yo who want to journal but never stick with it |
| monetization_model | $2.99/mo |
| competition_notes | One Line a Day (physical book brand), Momento (complex). Simple AI angle is unique. |
| mvp_scope | Daily 1-sentence entry, streak, Foundation Models quarterly life theme detection |

**Feasibility Scores:**

| Dimension | Score | Reason |
|-----------|-------|--------|
| Solo Dev Scope | 10 | Dead simple — SwiftUI list + SwiftData |
| Platform API Fit | 7 | Foundation Models, WidgetKit for daily reminder |
| Monetization Viability | 7 | Low price point needed ($2.99) — lower ARPU |
| Competition Density | 6 | One-line journaling is a known concept |
| Technical Fit | 10 | Trivially simple |

**Overall Score: 7.9** (lower monetization ceiling)

---

### Rank 5: **Sleep Lens — HealthKit Sleep Explainer**

| Field | Value |
|-------|-------|
| idea | Sleep Lens |
| one_liner | Translate Apple Health sleep data into plain English with AI-driven action tips |
| lens | Problem-First (Apple Health UX complaints) + Technology-First (HealthKit + Foundation Models) |
| platform | iOS 18+ |
| problem_statement | Apple Health shows sleep stages but users don't understand what REM%, HRV, or deep sleep means. No actionable guidance. |
| target_user | 30–50 yo Apple Watch users who check health data but don't understand it |
| monetization_model | $3.99/mo |
| competition_notes | AutoSleep (complex), Sleep Cycle (own tracker required). Sleep Lens reads existing HealthKit data. |
| mvp_scope | HealthKit sleep data read, Foundation Models plain-language daily report, 3 improvement tips |

**Feasibility Scores:**

| Dimension | Score | Reason |
|-----------|-------|--------|
| Solo Dev Scope | 8 | HealthKit read + Foundation Models — 1-day feasible |
| Platform API Fit | 9 | Deep Apple API usage (HealthKit + Foundation Models) |
| Monetization Viability | 7 | Requires Apple Watch adoption |
| Competition Density | 8 | AutoSleep targets power users, Sleep Lens targets casual users |
| Technical Fit | 8 | HealthKit is known territory |

**Overall Score: 8.1**

---

## Ideas Filtered Out

| Idea | Lens | Reason |
|------|------|--------|
| AI Personal Trainer | Trend | Extremely competitive (Fitbod, Future, Whoop). 6+ months scope. WEAK on Solo Dev Scope. |
| Gym Equipment Crowdsource | Market Gap | Backend required for crowdsourced data. Fails Solo Dev Scope filter. |
| Mood Weather | Trend | Too abstract. No clear monetization path. Fails Monetization Viability filter. |
| AR Room Planner | Technology | ARKit + LiDAR scoped for weeks. Fails Solo Dev Scope filter. |

---

## Final Ranking

| Rank | App | Score | Key Differentiator |
|------|-----|-------|--------------------|
| 1 | **Hush — Pre-Sleep Worry Journal** | **8.7** | Foundation Models + pre-sleep mental offload. No direct competitor. |
| 2 | Sleep Lens | 8.1 | HealthKit explainer, reads existing data |
| 3 | Dream Decoder | 8.1 | Dream AI journal, niche but passionate users |
| 4 | One Line | 7.9 | Micro journal, simple but lower ARPU |
| 5 | Screen Mindful | 7.5 | Digital wellness, Family Controls entitlement risk |

---

## Recommendation

**Build Hush — Pre-Sleep Worry Journal.**

Sleep anxiety is a mass-market problem (40% of adults), the pre-sleep worry journal format is underserved, and Foundation Models gives a clear technical differentiator ("all processing on your device, zero cloud"). The subscription conversion in Health & Fitness is proven (43.8% trial-to-paid per RevenueCat). The entire stack — SwiftUI + SwiftData + Foundation Models + RevenueCat — is achievable in 1 day. No backend, no complex permissions, no entitlement delays.

**App Name:** Hush
**Bundle ID:** com.anicca.hush (to be confirmed in US-002)
**Subscription:** $4.99/mo, $29.99/yr
**Minimum OS:** iOS 18 (Foundation Models requirement)

---

## Sources

| Source | URL |
|--------|-----|
| Apple Foundation Models Framework | https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/ |
| TechCrunch — Developers using Apple local AI | https://techcrunch.com/2025/10/03/how-developers-are-using-apples-local-ai-models-with-ios-26/ |
| RevenueCat State of Subscription Apps 2025 | https://www.revenuecat.com/state-of-subscription-apps-2025/ |
| Apple Machine Learning Research — Foundation Models | https://machinelearning.apple.com/research/introducing-apple-foundation-models |
| Apple Community — Sleep Tracking Complaints | https://discussions.apple.com/thread/254841815 |
| iOS App Trends 2026 | https://asappstudio.com/ios-app-trends-2026/ |
| idea-generator SKILL.md | rshankras (applied methodology) |
