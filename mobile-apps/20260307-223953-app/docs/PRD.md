# Product Requirements Document: FrostDip

## 1. App Overview

| Field | Value |
|-------|-------|
| app_name | FrostDip |
| app_title (ASO) | Cold Plunge Timer - FrostDip |
| bundle_id | com.aniccafactory.frostdip |
| one_liner | Cold plunge & ice bath timer with progressive protocols, session logging, streak tracking, and HealthKit heart rate integration |
| platform | iOS 17+ |
| ios_minimum | 17.0 |
| swift_version | 5.9+ |
| category | Health & Fitness |
| age_rating | 4+ |

Source: product-plan.md §6 App Identity

---

## 2. Target User

**ICP:** 25-45歳のバイオハッカー、アスリート、ウェルネス愛好家。$1K-9Kのコールドプランジ機器を所有し、週3-7回冷水浴を行う。

| Attribute | Value |
|-----------|-------|
| Age | 25-45 |
| Gender | Male-skewed (65/35 M/F) |
| Income | $75K-150K+ |
| Behavior | Cold plunges 3-7x/week, follows Huberman/Wim Hof |
| Pain Point | Phone stopwatch or hardware-tied apps with terrible UX |
| WTP | High — already spends $1K-9K on hardware + $50-200/mo on wellness subscriptions |

Source: product-plan.md §1 Target User, spec/01-trend.md target_user

---

## 3. Problem Statement

コールドプランジ愛好者は$1,000-9,000の機器に投資しているにもかかわらず、セッション記録にはiPhoneのストップウォッチか、ハードウェアに紐付いた低品質アプリしか選択肢がない。

| Evidence | Source |
|----------|--------|
| Plunge app: "logs you out regularly", "app is so unstable" (1-star reviews x4) | iTunes RSS Reviews API (ID: 6450953005, 2026-03-07) |
| Brisk: timer supports minutes only, no second-level precision | iTunes RSS Reviews API — "timer is only by minutes" (2-star) |
| GoPolar: "not a single activity has synced since July. I pay every month." | iTunes RSS Reviews API (2026-03-07) |
| Top standalone tracker (Brisk) has only 58 reviews in entire category | iTunes Search API (2026-03-07) |

**Gap:** スタンドアロンのプレミアム冷水浴トラッカーが存在しない。$512.9Mのハードウェア市場に対して、ソフトウェアのギャップが巨大。

Source: [Persistence Market Research](https://www.persistencemarketresearch.com/) — "Cold plunge tub market US$ 512.9M in 2026, CAGR 4.9%"

---

## 4. Goals & Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| App Store Rating | >= 4.5 | App Store Connect |
| Day 7 Retention | >= 30% | Manual session log frequency analysis |
| Trial-to-Paid Conversion | >= 5% | RevenueCat Dashboard |
| Monthly Active Users (Month 6) | >= 2,000 | App launch count (UserDefaults) |
| MRR (Month 12) | >= $1,375 | RevenueCat Dashboard |
| Session Completion Rate | >= 80% | Timer start vs. session saved ratio (local) |
| Streak Engagement | >= 40% of active users maintain 7+ day streak | UserDefaults streak data |

Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — "H&F median conversion 3-5%"

---

## 5. Solution Overview

FrostDipは、ハードウェアに依存しないスタンドアロンの冷水浴トラッカー。呼吸準備フェーズ付きカウントダウンタイマー、セッションログ、HealthKit心拍数統合、プログレッシブプロトコル、ストリーク追跡、コントラストセラピーモードを提供する。SwiftData によるオフラインファースト設計で、ログイン不要。

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Breathing   │────>│  Cold Plunge │────>│   Session   │
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

Source: product-plan.md §3 Solution

---

## 6. MVP Features

| Feature ID | Feature | Priority | Tier | Description |
|------------|---------|----------|------|-------------|
| F-001 | Cold Plunge Timer | Must Have | Free | Countdown timer with second-level precision, configurable duration (30s-20min), haptic alerts at intervals, background mode support |
| F-002 | Breathing Prep Phase | Must Have | Free | Pre-plunge breathing exercise (30-120s configurable), guided inhale/exhale animation, skip option |
| F-003 | Session Logging | Must Have | Free | Record duration, water temperature (manual input, C/F toggle), personal notes, auto-save on timer completion |
| F-004 | 7-Day History | Must Have | Free | View last 7 sessions with basic stats (avg duration, avg temp). Paywall gate for older sessions |
| F-005 | Default Protocol | Must Have | Free | "Beginner" protocol: 30s breathing prep + 2min cold. Visible but locked protocols for premium upsell |
| F-006 | Onboarding Flow | Must Have | Free | 3-4 screens: app intro, experience level selection, notification permission, soft paywall (Rule 20) |
| F-007 | HealthKit HR Integration | Must Have | Premium | Read heart rate during active session via HealthKit, display live BPM on timer screen, save avg/max HR to session log |
| F-008 | Unlimited Session History | Must Have | Premium | Full history with search by date, filter by duration/temperature, export capability |
| F-009 | Custom Protocols | Must Have | Premium | Create/edit protocols: prep time, cold time, number of rounds, rest between rounds |
| F-010 | Streak Tracking | Must Have | Premium | Daily streak with visual calendar view, "current" and "longest" streak counters, streak freeze (1 per week) |
| F-011 | Progress Dashboard | Must Have | Premium | Charts: duration progression over time, avg HR trend, temperature trend, total sessions count, total cold time |
| F-012 | Contrast Therapy Mode | Must Have | Premium | Alternating hot/cold timer with configurable rounds and durations, haptic transition alerts |
| F-013 | Subscription Paywall | Must Have | Premium | Self-built SwiftUI PaywallView with [Maybe Later] button. Purchases.shared.purchase(package:). No RevenueCatUI (Rule 20) |
| F-014 | Settings | Must Have | Free | Temperature unit (C/F), notification preferences, upgrade to premium, restore purchases, about/privacy policy |
| F-015 | Local Notifications | Must Have | Free | Configurable reminder to cold plunge (morning/afternoon/evening), streak-at-risk warning |

Source: product-plan.md §5 MVP Scope, competitive-analysis.md §6 Feature Gap Analysis

---

## 7. User Stories

| US ID | As a | I want to | So that |
|-------|------|-----------|---------|
| US-001 | cold plunge user | start a countdown timer with second-level precision | I can time my cold plunge sessions accurately (unlike Brisk's minute-only timer) |
| US-002 | beginner | do a guided breathing prep before my plunge | I can calm my nervous system and enter the cold water prepared |
| US-003 | regular plunger | log my session with duration, water temp, and notes | I can track my cold exposure history over time |
| US-004 | free user | see my last 7 sessions | I can review my recent progress without paying |
| US-005 | premium user | access my full session history with search and filters | I can analyze my long-term cold exposure patterns |
| US-006 | premium user | create custom protocols with prep time and rounds | I can follow structured progression programs |
| US-007 | premium user | see my heart rate during a plunge via HealthKit | I can monitor my physiological response to cold |
| US-008 | motivated user | track my daily plunge streak | I stay motivated through gamification and consistency |
| US-009 | premium user | view charts of my duration and HR progression | I can see measurable improvement over weeks/months |
| US-010 | biohacker | use contrast therapy mode (hot/cold alternating) | I can do structured contrast therapy sessions |
| US-011 | new user | go through onboarding that explains the app | I understand the app's value and can set my preferences |
| US-012 | user | adjust settings like temp unit and notifications | the app works the way I prefer |

---

## 8. Monetization

### Subscription Pricing

| Tier | Price | Trial | Product ID |
|------|-------|-------|------------|
| Free | $0 | — | — |
| Monthly | $6.99/mo | None | frostdip_monthly_699 |
| Annual | $29.99/yr ($2.50/mo) | 3-day free trial | frostdip_annual_2999 |

**trial_days:** 3 (annual plan only)

### Free Tier Limitations

| Feature | Free Limit | Premium |
|---------|-----------|---------|
| Session history | 7 days only | Unlimited |
| Protocols | 1 default ("Beginner") | Unlimited custom |
| HealthKit HR | Not available | Live HR during session |
| Streak tracking | Not available | Full streak + calendar |
| Progress dashboard | Not available | Full charts |
| Contrast therapy | Not available | Full mode |

**free_tier_limit:** 7-day session history + 1 default protocol. Premium features visible but gated with lock icon.

### Pricing Justification

| Source | Key Finding | Application |
|--------|-------------|-------------|
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | H&F median: $7.73/mo, $29.65/yr | Monthly $6.99 = 90% of median. Annual $29.99 = 101% of median |
| [Jake Mor #17](https://jakemor.com/) | Trial-less monthly + trialed annual at 50%+ apparent discount | Monthly no trial, Annual 3-day trial, 64% apparent discount |
| [Jake Mor #15](https://jakemor.com/) | Prices convert to clean weekly/monthly amounts | $6.99/mo = $1.62/week. $29.99/yr = $2.50/mo |
| [RevenueCat 2025 Trends](https://www.revenuecat.com/blog/growth/2025-subscription-app-monetization-trends/) | Premium pricing is the new norm | Premium positioning for users spending $1K-9K on hardware |

### RevenueCat Configuration

| Item | Value |
|------|-------|
| SDK | RevenueCat Purchases (SPM) |
| RevenueCatUI | PROHIBITED (Rule 20) |
| Offering | "default" |
| Entitlement | "premium" |
| Paywall | Self-built SwiftUI PaywallView |

### Paywall Design Requirements

Source: [Funnelfox Paywall Guide](https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/), [Adapty iOS Paywall Guide](https://adapty.io/blog/how-to-design-ios-paywall/), [Appagent Paywall Optimization](https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/)

| Element | Requirement | Conversion Impact |
|---------|------------|-------------------|
| Pricing Plans | 2 plans: monthly + annual | Clear comparison |
| Discount Badge | "Save 64%" badge + strikethrough monthly-equivalent price | +20-30% (Adapty) |
| CTA Copy | "Start My Cold Journey" (benefit-driven, not "Subscribe") | Outperforms generic CTAs |
| Placement | Onboarding final screen (100% visibility) + Settings > Upgrade | Up to +234% (Appagent) |
| Social Proof | "Join 1,000+ cold plungers" + app rating | Boosts credibility |
| Benefits | 3-5 bullet points with tangible outcomes | Clarity converts |
| [Maybe Later] | REQUIRED — soft paywall, dismissible | Rule 20 compliance |
| Legal Links | Privacy Policy + Terms of Use | App Store requirement |

---

## 9. Market Context

**TAM:** ~228K potential cold plunge app users globally (bottom-up: 600K tub owners x 95% smartphone x 40% would track)
**SAM:** ~75K iOS users in US + JP
**SOM Year 3:** ~6,000 users, ~420 paid, ~$28K ARR

**Competitive Differentiator:** FrostDipは唯一のスタンドアロン冷水浴トラッカーで、HealthKit心拍数統合、呼吸準備フェーズ、コントラストセラピーモード、プログレッシブプロトコル、オフラインファーストアーキテクチャを全て備える。

Source: market-research.md §2 TAM/SAM/SOM, competitive-analysis.md §6 Strategic Differentiation

---

## 10. Privacy & Compliance

| Item | Value |
|------|-------|
| Data Collection | HealthKit heart rate (read-only, on-device), UserDefaults preferences |
| Cloud Sync | None — all data stored locally via SwiftData |
| ATT (AppTrackingTransparency) | NOT USED (Rule 20b) |
| NSUserTrackingUsageDescription | NOT INCLUDED (Rule 20b) |
| Analytics SDK | NONE (Rule 17 — Mixpanel/Firebase/Analytics prohibited) |
| AI / External API | NONE (Rule 21 — no OpenAI, Anthropic, Gemini, FoundationModels) |
| PrivacyInfo.xcprivacy | Required — NSPrivacyAccessedAPICategoryUserDefaults (CA92.1) |
| HealthKit Usage Description | "FrostDip reads your heart rate during cold plunge sessions to track your physiological response." |
| Privacy Policy | Deployed to GitHub Pages before submission |

Source: [Apple Privacy Manifest](https://developer.apple.com/documentation/bundleresources/privacy_manifest_files), Rule 17, Rule 20b, Rule 21

---

## 11. Localization

| Language | Code | Coverage |
|----------|------|----------|
| English (US) | en-US | Primary — all strings |
| Japanese | ja | Full — all strings |

**Notes:**
- Japanese strings are typically 30-50% shorter than English; UI layout must accommodate both
- App name "FrostDip" is universal (not translated)
- Subtitle localized: "Ice Bath Tracker & Streaks" / "アイスバストラッカー＆ストリーク"

---

## 12. Technical Constraints

| Constraint | Rule | Detail |
|------------|------|--------|
| No analytics SDK | Rule 17 | Mixpanel, Firebase Analytics, any tracking SDK prohibited. Greenlight will flag as CRITICAL |
| Custom PaywallView | Rule 20 | Self-built SwiftUI paywall using Purchases.shared.purchase(package:). RevenueCatUI import prohibited |
| No ATT | Rule 20b | AppTrackingTransparency framework not used. No tracking dialog |
| No AI / External API | Rule 21 | OpenAI, Anthropic, Google Generative AI, Apple FoundationModels all prohibited. App is fully self-contained. Monthly revenue $29 vs API cost $300+ makes external APIs economically impossible. FoundationModels requires iOS 26+ with negligible user base |
| Offline-first | Architecture | All data stored locally via SwiftData. No backend server. No login required |
| iOS 17+ minimum | SwiftData | SwiftData requires iOS 17.0+. Covers 95%+ of active devices |
| RevenueCat only dependency | SPM | Only external SPM package is RevenueCat Purchases. No other third-party dependencies |

---

## 13. Out of Scope

| Feature | Reason |
|---------|--------|
| Apple Watch companion | watchOS target adds complexity, Maestro untestable — v1.1 |
| Social/community features | Scope overflow — v1.1 candidate |
| HealthKit write (workout logging) | HKWorkoutSession adds review scrutiny — v1.1 |
| Dynamic Island / Live Activities | WidgetKit extension, Maestro untestable — PROHIBITED |
| Widgets | Extension target — PROHIBITED |
| LLM / AI features | Rule 21 — API cost prohibited |
| Backend server | Rule 21 — infra cost prohibited |
| CloudKit sync | Complexity — SwiftData local sufficient |
| Camera / Photo | Privacy review complexity |
| Sign in with Apple | Maestro untestable |
| Guided audio coaching | Requires audio assets — v1.1 |
| HealthKit body temperature | Permission complexity |

Source: product-plan.md §5 Won't Have

---

## 14. App Store Metadata

### en-US

| Field | Value |
|-------|-------|
| app_name | Cold Plunge Timer - FrostDip |
| subtitle | Ice Bath Tracker & Streaks |
| keywords | cold plunge,ice bath,cold exposure,plunge timer,cold therapy,ice bath tracker,wim hof,contrast therapy,cold water,streak |
| promotional_text | Track your cold plunge sessions with precision timing, heart rate monitoring, and progressive protocols. Join thousands of cold plungers building consistency. |
| description | FrostDip is the ultimate cold plunge and ice bath tracking app designed for serious cold exposure enthusiasts.\n\nTIMER WITH PRECISION\n- Second-level countdown timer (not just minutes)\n- Breathing preparation phase before each plunge\n- Haptic alerts at custom intervals\n- Background mode support\n\nTRACK YOUR PROGRESS\n- Log every session: duration, water temperature, notes\n- View your complete session history\n- Track daily streaks and longest streaks\n- Progress dashboard with charts\n\nHEART RATE MONITORING\n- Live heart rate from HealthKit during sessions\n- Average and max HR saved per session\n- Track your HR adaptation over time\n\nPROGRESSIVE PROTOCOLS\n- Start with beginner protocols\n- Create custom protocols with rounds and rest periods\n- Contrast therapy mode (hot/cold alternating)\n\nPRIVACY FIRST\n- All data stored on your device\n- No account required\n- No tracking or analytics\n\nFree: Basic timer + 7-day history\nPremium: Unlimited history, HealthKit HR, custom protocols, streaks, progress dashboard, contrast therapy\n\nSubscription pricing:\n- Monthly: $6.99/month\n- Annual: $29.99/year (save 64%)\n\nPayment will be charged to your Apple ID account at confirmation of purchase. Subscription automatically renews unless canceled at least 24 hours before the end of the current period. |

### ja

| Field | Value |
|-------|-------|
| app_name | Cold Plunge Timer - FrostDip |
| subtitle | アイスバストラッカー＆ストリーク |
| keywords | コールドプランジ,アイスバス,冷水浴,プランジタイマー,冷水療法,冷水シャワー,ヴィムホフ,コントラストセラピー,冷水,ストリーク |
| promotional_text | 精密なタイミング、心拍数モニタリング、プログレッシブプロトコルで冷水浴セッションを記録。一貫性を築く数千人のコールドプランジャーに参加しよう。 |
| description | FrostDipは、本格的な冷水浴愛好家のために設計された究極のコールドプランジ＆アイスバストラッキングアプリです。\n\n精密タイマー\n- 秒単位のカウントダウンタイマー\n- プランジ前の呼吸準備フェーズ\n- カスタム間隔での触覚アラート\n- バックグラウンドモード対応\n\n進捗を記録\n- 全セッションを記録：時間、水温、メモ\n- 完全なセッション履歴を表示\n- デイリーストリークと最長ストリークを追跡\n- チャート付きプログレスダッシュボード\n\n心拍数モニタリング\n- HealthKitからのリアルタイム心拍数\n- セッションごとの平均・最大HRを保存\n- HR適応の変化を追跡\n\nプログレッシブプロトコル\n- 初心者プロトコルからスタート\n- ラウンドと休憩時間のカスタムプロトコル作成\n- コントラストセラピーモード（温冷交互）\n\nプライバシーファースト\n- 全データはデバイスに保存\n- アカウント不要\n- トラッキングやアナリティクスなし\n\n無料：基本タイマー＋7日間の履歴\nプレミアム：無制限の履歴、HealthKit HR、カスタムプロトコル、ストリーク、プログレスダッシュボード、コントラストセラピー\n\nサブスクリプション価格：\n- 月額：$6.99/月\n- 年額：$29.99/年（64%お得）\n\nお支払いは購入確認時にApple IDアカウントに請求されます。サブスクリプションは、現在の期間終了の24時間前までにキャンセルしない限り自動的に更新されます。 |
