# US-001: Trend Research + Idea Selection

## Developer Profile

| Item | Value |
|------|-------|
| Skills | Swift, SwiftUI, iOS 15+ |
| Platform | iOS |
| Time | 1 day (factory build) |
| Constraints | Solo dev, subscription model, no analytics SDK |
| Monetization | Subscription ($3.99/mo, $29.99/yr) |

## Brainstorming Lenses Applied

| # | Lens | Ideas Generated |
|---|------|----------------|
| 1 | Skills & Interests | 6 ideas (timer apps, wellness utilities, AI-powered tools) |
| 2 | Problem-First | 7 ideas (desk pain, screen fatigue, morning struggles, focus) |
| 3 | Technology-First | 5 ideas (Foundation Models AI, WidgetKit, Live Activities) |
| 4 | Market Gap | 6 ideas (stretching, eye care, hydration, posture) |
| 5 | Trend-Based | 8 ideas (going analogue, quiet flex, dopamine detox, cold exposure) |

**Total raw ideas: 32 → Filtered to 7 → Scored top 5**

## Feasibility Filtering (5 Filters Applied)

| Filter | Threshold | Ideas Removed |
|--------|-----------|---------------|
| Solo Dev Scope | Must ship in 1 day | 12 removed (too complex) |
| Platform API Fit | Must leverage iOS APIs | 3 removed (generic/cross-platform) |
| Monetization Viability | Clear subscription path | 4 removed (one-time purchase only) |
| Competition Density | Not dominated by incumbents | 4 removed (Calm, Headspace, Zero dominate) |
| Technical Complexity | SwiftUI + simple backend | 2 removed (needs HealthKit/CoreMotion heavy integration) |

**Excluded existing factory categories:** breathing, meditation, sleep, gratitude, cortisol/stress

## Shortlist (Ranked by Overall Score)

### Rank 1: StretchFlow — AI Desk Stretching & Break Timer ⭐ SELECTED

| Field | Value |
|-------|-------|
| **one_liner** | AI-powered desk stretching timer that reminds you to move and guides personalized stretch routines |
| **lens** | problem_first + market_gap |
| **platform** | iOS |
| **problem_statement** | 1.5B+ desk workers suffer from back/neck pain due to prolonged sitting. They know they should stretch but forget, don't know what to do, or skip it. Existing stretch apps are either abandoned, too complex (full workout apps), or lack personalization. No app combines simple break timers with AI-generated personalized stretch guidance. |
| **target_user** | Remote/office workers (25-45) who sit 6+ hours daily, experience back/neck/wrist pain, and want a simple nudge to move |
| **feasibility** | |
| — Solo Dev Scope | **EXCELLENT (9)** — Timer + card UI + stretch library + AI text. 1-day buildable |
| — Platform API Fit | **STRONG (7)** — Foundation Models for personalized stretch suggestions, Notifications for reminders, WidgetKit for glanceable next-break |
| — Monetization | **STRONG (8)** — Subscription justified: daily AI-personalized routines, expanded stretch library, custom schedules |
| — Competition Density | **STRONG (8)** — StretchMinder exists but basic (no AI). Stand Up! is reminder-only. No quality AI-powered stretch companion |
| — Technical Fit | **EXCELLENT (9)** — SwiftUI timer + list + Foundation Models. Perfect skill match |
| **overall_score** | **8.5** (Solo Dev 9×1.5 + API 7 + Monetization 8 + Competition 8 + Tech 9×1.5 = 54 / 7 = 8.5 weighted) |
| **monetization_model** | Freemium — 3 free stretches/day + basic timer. $3.99/mo or $29.99/yr for AI personalization + full library + custom schedules |
| **competition_notes** | StretchMinder (basic timer, no AI, last updated 2024). Stand Up! (reminder only). Wakeout (full workout app, $49.99/yr — overpriced for stretching). NO app combines break timer + AI-personalized stretch guidance |
| **mvp_scope** | Break timer with configurable intervals, 20+ stretch exercises with illustrations (SF Symbols + text), Foundation Models generates personalized stretch suggestions based on reported pain areas, notification reminders, simple progress tracking |
| **next_step** | `product-agent discover --idea "AI-powered desk stretching timer that reminds workers to move and guides personalized stretch routines" --platform iOS --output-format json` |

**Sources:**
- ソース: [Niches Hunter — App Ideas for Indie Hackers 2026](https://nicheshunter.app/blog/app-ideas-indie-hackers-solo-devs-studios) / 核心の引用: 「The opportunity for small teams is serving underserved niches within health. A solo developer who understands their specific audience can build a better app than a generic app from a big company.」
- ソース: [Apple Foundation Models](https://developer.apple.com/documentation/FoundationModels) / 核心の引用: 「The Foundation Models framework gives developers access to create production-quality generative AI features with the ~3B parameter on-device language model.」
- ソース: [TikTok Trends 2026 — Going Analogue](https://www.home.shooglebox.com/tiktok-trends-2026) / 核心の引用: 「Going analogue is one of the biggest trends, with more people saying they want to reduce screen time and take up offline hobbies.」

---

### Rank 2: FocusGarden — Pomodoro Timer with Growing Virtual Garden

| Field | Value |
|-------|-------|
| **one_liner** | Focus timer where your concentration grows a virtual garden — lose focus, plants wilt |
| **lens** | trend_based (gamification + "quiet flex" calm aesthetic) |
| **platform** | iOS |
| **problem_statement** | Knowledge workers struggle to maintain deep focus. Gamified focus apps exist (Forest) but Forest is $3.99 upfront with no subscription, and the garden metaphor is stale. A calm, beautiful garden with seasonal themes and AI-generated focus tips could differentiate |
| **target_user** | Students and remote workers (18-35) who want gentle accountability for focus sessions |
| **feasibility** | Solo Dev: STRONG (7), API Fit: MODERATE (6), Monetization: STRONG (7), Competition: MODERATE (5 — Forest is strong), Tech: STRONG (7) |
| **overall_score** | **6.7** |
| **monetization_model** | $3.99/mo — seasonal garden themes, AI focus insights, detailed stats |
| **competition_notes** | Forest (dominant, 4.8★, but one-time purchase). Flora (similar). Differentiation needed via calm aesthetic + AI |
| **mvp_scope** | Pomodoro timer, basic garden growth animation, streak tracking |

**Source:** [Shopify TikTok Trends 2026](https://www.shopify.com/blog/tiktok-trends) / 核心の引用: 「The 'quiet flex' is a major trend — a softer, more aspirational aesthetic focused on calmness, confidence, and intentionality.」

---

### Rank 3: EyeRest — 20-20-20 Screen Break & Eye Care

| Field | Value |
|-------|-------|
| **one_liner** | Smart screen break timer based on the 20-20-20 rule with guided eye exercises |
| **lens** | problem_first + technology_first |
| **platform** | iOS |
| **problem_statement** | Digital eye strain affects 65% of adults. The 20-20-20 rule (every 20 min, look 20 ft away for 20 sec) is simple but nobody follows it. Few quality apps exist for this specific use case |
| **target_user** | Screen-heavy workers and students (20-50) experiencing eye fatigue, dry eyes, headaches |
| **feasibility** | Solo Dev: EXCELLENT (9), API Fit: MODERATE (6), Monetization: MODERATE (6), Competition: STRONG (8 — very few competitors), Tech: EXCELLENT (9) |
| **overall_score** | **7.4** |
| **monetization_model** | $2.99/mo — advanced eye exercise library, dark mode scheduling, AI tips |
| **competition_notes** | EyeCare 20 20 20 (basic, low ratings). No AI-powered eye care app |
| **mvp_scope** | 20-20-20 timer, 10 eye exercises, notification reminders, daily streak |

**Source:** [Developer Tech — iOS Trends 2025-2026](https://www.developer-tech.com/news/5-ios-app-development-trends-for-2025-2026/) / 核心の引用: 「Health and wellness apps see 2-3x higher adoption」

---

### Rank 4: MicroJournal — 1-Minute AI Daily Reflection

| Field | Value |
|-------|-------|
| **one_liner** | Answer one AI-generated question per day in 60 seconds — get weekly AI insights on your patterns |
| **lens** | technology_first (Foundation Models) + trend_based (wellness) |
| **platform** | iOS |
| **problem_statement** | People want to journal but traditional apps are overwhelming. Day One is feature-bloated. Most journaling apps require 10+ minutes. Nobody has built a micro-journaling app with on-device AI that generates contextual prompts and pattern recognition |
| **target_user** | Busy professionals (25-40) who want self-reflection but don't have time for traditional journaling |
| **feasibility** | Solo Dev: STRONG (7), API Fit: EXCELLENT (9 — Foundation Models), Monetization: STRONG (7), Competition: MODERATE (6 — Day One, Jour exist), Tech: STRONG (8) |
| **overall_score** | **7.3** |
| **monetization_model** | $4.99/mo — AI weekly insights, unlimited history, custom prompt themes |
| **competition_notes** | Day One (dominant but complex). Jour (AI but cloud-based). No on-device AI micro-journal exists |
| **mvp_scope** | 1 AI question/day, text input, weekly AI summary, streak tracking |

**Source:** [Apple Foundation Models Framework](https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/) / 核心の引用: 「developers can bring intelligent experiences into their apps using Apple's on-device large language model, with free AI inference and offline availability」

---

### Rank 5: NatureTimer — Forest Bathing / Outdoor Mindfulness

| Field | Value |
|-------|-------|
| **one_liner** | Guided outdoor mindfulness sessions with nature sounds and AI-personalized prompts for forest bathing (shinrin-yoku) |
| **lens** | trend_based ("going analogue" + wellness) + market_gap |
| **platform** | iOS |
| **problem_statement** | Forest bathing (shinrin-yoku) is trending as a stress reduction practice backed by research. No quality iOS app exists specifically for guided forest bathing sessions. The "going analogue" TikTok trend drives interest in nature-based wellness |
| **target_user** | Wellness-conscious adults (25-45) who want to disconnect from screens and connect with nature |
| **feasibility** | Solo Dev: STRONG (8), API Fit: MODERATE (6), Monetization: MODERATE (6 — niche audience), Competition: EXCELLENT (9 — almost no competitors), Tech: STRONG (8) |
| **overall_score** | **7.1** |
| **monetization_model** | $3.99/mo — extended session library, AI nature prompts, seasonal content |
| **competition_notes** | Shinrin-Yoku app (basic, poor ratings). No quality AI-powered forest bathing app |
| **mvp_scope** | Guided session timer, 10 nature mindfulness prompts, ambient nature sounds, session log |

**Source:** [Marie Claire — Dopamine Fasting / Going Analogue](https://www.marieclaire.co.uk/life/health-fitness/dopamine-fasting) / 核心の引用: 「A more realistic and sustainable approach is to identify specific behaviours that trigger compulsive use and take intentional breaks from those」

---

## Ideas Filtered Out

| Idea | Lens | Reason |
|------|------|--------|
| AI Morning Routine | problem_first | Fabulous ($59.99/yr, 4.6★) and Routinery dominate. Failed competition filter |
| Dopamine Detox App | trend_based | 7+ dopamine detox apps already exist (Lighthouse, DopaPause, Elqi). Market saturated |
| Cold Plunge Timer | trend_based | Too niche. Wim Hof app exists. Small TAM for subscription |
| AI Walking Companion | skills_interests | Requires HealthKit/step counting — too complex for 1-day build. Failed scope filter |
| Sleep Stories Generator | technology_first | Calm/Headspace dominate. Failed competition filter |
| Hydration Tracker | problem_first | WaterMinder, Plant Nanny dominate. Failed competition filter |

## Recommendation

**StretchFlow（Rank 1, Score 8.5）を選定。**

理由:
1. **問題の普遍性** — 15億人以上のデスクワーカーが腰/首の痛みを抱える
2. **競合の弱さ** — 既存ストレッチアプリは基本的（AI なし、更新停止）
3. **AI差別化** — Foundation Models でパーソナライズされたストレッチ提案（競合ゼロ）
4. **TikTokトレンド適合** — 「Going analogue」（画面から離れて体を動かす）
5. **1日ビルド可能** — タイマー + カードUI + ストレッチライブラリ + AI テキスト生成
6. **サブスク正当化** — 日々のAIパーソナライズ + 拡張ライブラリが継続価値を提供
7. **既存ファクトリーアプリと非重複** — 呼吸/瞑想/睡眠/感謝/ストレスは全て対応済み

**Next step:** `product-agent discover --idea "AI-powered desk stretching timer that reminds workers to move and guides personalized stretch routines" --platform iOS --output-format json`
