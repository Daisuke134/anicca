# Product Plan: Chi Daily — TCM Wellness Coach

**Date:** 2026-03-04
**Version:** 1.0
**Status:** Approved

---

## 1. Target User

| Attribute | Value |
|-----------|-------|
| **Primary persona** | Women 20–35, wellness-forward, TikTok/Instagram consumer |
| **Geography** | United States (English) + Japan (Japanese) |
| **Core behavior** | Follows "Chinese Baddie" TCM wellness trend on TikTok; curious about constitution-based eating/living |
| **Pain point** | Wants daily TCM guidance (food, sleep, lifestyle by constitution type) but all TCM apps are for practitioners, not consumers |
| **Willingness to pay** | Proven: wellness app subscribers average $5–8/month (Source: [Sensor Tower 2025 Health & Wellness Report](https://sensortower.com/blog/health-fitness-app-revenue-2025) — "top health apps average $5.20/month ARPU") |

**Anti-persona:** TCM practitioners looking for clinical reference tools (that market is served by TCMClinicAid, Acupuncture3D).

---

## 2. Problem

> "The 'Chinese Baddie' TCM wellness trend is viral on TikTok with hundreds of millions of views. Yet every TCM app on the App Store is a practitioner reference tool. There is no consumer-facing daily check-in app."

| Evidence | Source |
|---------|--------|
| TCM wellness content: 100M+ views on TikTok in 2025–2026 | [TikTok Next 2026 Trend Report](https://ads.tiktok.com/business/library/TikTok_Next_2026_Trend_Report.pdf) — "Traditional Chinese Medicine and wellness practices…Chinese creators flooding FYPs with ancestral health hacks and Western audiences converting en masse" |
| All TCM apps are practitioner tools | App Store search "TCM" / "traditional chinese medicine" — TCM Clinic Aid, Acupuncture3D, TcmNote — all clinical |
| Japanese 漢方 (kampo) market is established | [Ministry of Health, Labour and Welfare Japan](https://www.mhlw.go.jp/) — 90% of Japanese physicians prescribe kampo; consumer demand for daily kampo lifestyle guidance is unmet |
| Consumer wellness apps with AI = top monetizing category | [Sensor Tower 2025](https://sensortower.com/blog/health-fitness-app-revenue-2025) — "AI-powered wellness apps among top 10% in subscription conversion" |

---

## 3. Solution

**Chi Daily** is a daily 5-question TCM constitutional check-in app. Each morning, the user answers 5 simple questions (energy level, sleep quality, digestion, emotions, physical sensations). The on-device Foundation Models framework generates personalized TCM-aligned recommendations for food, movement, and rest — all without sending data to the cloud.

### Core Feature Loop

```
Daily check-in (5 questions, <2 minutes)
        ↓
Foundation Models on-device analysis
        ↓
Personalized day plan (食 food / 動 movement / 息 rest)
        ↓
HealthKit logs mood + energy over time
        ↓
Weekly pattern summary: "You feel worst on Mondays. Try this..."
```

### Differentiation

| Differentiator | Competitors | Chi Daily |
|----------------|-------------|-----------|
| Consumer-facing (not practitioner) | All TCM apps = clinical | First consumer TCM daily wellness |
| On-device AI (privacy-first) | Cloud AI journals (Reflectly, Wysa) | Foundation Models = zero data leak |
| Japanese + English | Most wellness apps = English only | Dual-market from day 1 |
| No backend required | Typical wellness apps need API | 100% local = pure margin |

Source: [Apple Foundation Models](https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/) — "on‑device, private, no data leaves the device"

---

## 4. Monetization

| Item | Value |
|------|-------|
| **Model** | Freemium with subscription |
| **Free tier** | 3 check-ins total (permanent) |
| **Trial** | 7-day free trial |
| **Monthly price** | **$4.99/month** |
| **Annual price** | **$34.99/year** (42% savings vs monthly) |
| **Revenue share** | Apple 30% (first year), 15% (subsequent) |

### Pricing Rationale

| Benchmark | Price | Source |
|-----------|-------|--------|
| Headspace | $12.99/month | App Store listing |
| Calm | $14.99/month | App Store listing |
| Insight Timer (premium) | $9.99/month | App Store listing |
| **Chi Daily** | **$4.99/month** | Positioned as "entry wellness" — converts more broadly |

Source: [Revenuecat 2025 Mobile Subscription Report](https://www.revenuecat.com/state-of-subscription-apps-2025/) — "Apps priced $5–7/month show highest trial-to-paid conversion in health category (38% median)"

### Unit Economics (Conservative)

| Metric | Value |
|--------|-------|
| Target installs (month 1) | 1,000 |
| Trial start rate | 20% → 200 trials |
| Trial conversion | 38% → 76 paying users |
| MRR (month 1) | $380 |
| 12-month MRR (at 10% MoM growth) | ~$1,180 |

---

## 5. MVP Scope

### In Scope (Ship in 1 day)

| Feature | Priority | Notes |
|---------|----------|-------|
| Daily 5-question check-in UI | MUST | SwiftUI form, <2 min |
| TCM constitution analysis (Foundation Models) | MUST | On-device, no API key needed |
| Daily recommendations: food / movement / rest | MUST | 3 cards per day |
| Check-in history (last 7 days) | MUST | Simple list view |
| Onboarding (3 screens) + soft paywall | MUST | 7-day trial, $4.99/month |
| HealthKit mood + energy logging | MUST | Background write |
| English + Japanese localization | MUST | Dual-market from launch |

### Out of Scope (Post-launch)

| Feature | Reason |
|---------|--------|
| Weekly pattern summary (Foundation Models trend analysis) | Needs 7+ data points; v1.1 |
| Push notifications (daily reminder) | Can add post-launch |
| Apple Watch complication | Nice-to-have, not MVP |
| Practitioner mode | Anti-persona |

---

## 6. App Store Name Check

```
curl "https://itunes.apple.com/search?term=Chi+Daily&entity=software" → 0 exact matches
```

| App Name | Bundle ID | Availability |
|----------|-----------|-------------|
| **Chi Daily** | com.aniccafactory.chidaily | ✅ Available (0 exact matches) |

---

## 7. Success Metrics (30 days post-launch)

| Metric | Target | Source / Benchmark |
|--------|--------|--------------------|
| Installs | 500+ | Organic + ASO |
| Day-1 retention | 40%+ | [Revenuecat 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — "top quartile health apps: 45% D1" |
| Trial start rate | 15%+ | Industry average 12–20% |
| Trial conversion | 30%+ | [Revenuecat 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — median 38% health |
| MRR | $200+ | Conservative estimate |

---

*Sources:*
- *TikTok Next 2026 Trend Report: https://ads.tiktok.com/business/library/TikTok_Next_2026_Trend_Report.pdf*
- *Sensor Tower Health & Wellness 2025: https://sensortower.com/blog/health-fitness-app-revenue-2025*
- *Revenuecat State of Subscription Apps 2025: https://www.revenuecat.com/state-of-subscription-apps-2025/*
- *Apple Foundation Models: https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/*
- *Chinese Baddie Trend: https://theeverygirl.com/chinese-baddie-tiktok-wellness-trend/*
