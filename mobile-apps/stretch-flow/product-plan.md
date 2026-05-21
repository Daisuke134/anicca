# Product Plan: DeskStretch — AI Desk Stretching & Break Timer

> ⚠️ **Name Change**: 「StretchFlow」は App Store に既存（`com.nimanorouzi.stretchflow`）。「DeskStretch」に変更（iTunes Search API: 0 exact matches 確認済み）。

---

## 1. Target User

| Attribute | Value |
|-----------|-------|
| **Primary** | Remote/office workers (25-45) who sit 6+ hours daily |
| **Demographics** | Knowledge workers, engineers, designers, writers, accountants |
| **Pain Point** | Back/neck/wrist pain from prolonged sitting. Know they should stretch but forget or don't know what to do |
| **Behavior** | Already use iPhone daily. Open to health apps. Have tried reminder apps but found them too generic |
| **Willingness to Pay** | Medium — $3-8/mo for health tools that provide daily value |

**Market Size Evidence:**

| Metric | Value | Source |
|--------|-------|--------|
| Office workers with MSDs | **80.81%** | [Nature Scientific Reports 2025](https://www.nature.com/articles/s41598-025-30155-6) — 「Among office workers, 80.81% experience work-related musculoskeletal disorders」 |
| Most affected areas | Neck 58.6%, Lower back 52.5%, Shoulders 37.4% | [Nature Scientific Reports 2025](https://www.nature.com/articles/s41598-025-30155-6) |
| Workdays lost to back pain | **101.8 million/year** | [Illinois Chiropractic Society](https://ilchiro.org/impact-of-back-pain-in-the-workplace/) — 「Individuals experiencing work-related back pain lost a staggering 101.8 million workdays」 |
| Chronic LBP market size | $2.69B (2024) → $6.69B (2034), CAGR 9.52% | [Towards Healthcare](https://www.towardshealthcare.com/insights/chronic-lower-back-pain-market-sizing) |
| Remote workers at increased risk | Yes | [CDC NIOSH](https://blogs.cdc.gov/niosh-science-blog/2019/07/08/lbp/) — 「persons who work remotely at increased risk for lower back pain because of poor ergonomics」 |

---

## 2. Problem

### Core Problem
**デスクワーカーは1日6-8時間座り続け、腰・首・肩の痛みに苦しむ。ストレッチすべきだと分かっているが、忘れる・何をすればいいか分からない・面倒で続かない。**

### Why Existing Solutions Fail

| Solution | Why It Fails |
|----------|-------------|
| **StretchMinder** (Free + $7.99-$95.99) | Generic reminders, no AI personalization, no pain-area targeting. ソース: [App Store](https://apps.apple.com/us/app/stretchminder-daily-movement/id1518522560) |
| **Wakeout** ($59.99/yr) | Full workout app — overkill for desk stretching. Apple App of the Year だが高すぎる。ソース: [Wakeout Pricing](https://wakeout.app/pricing) |
| **Stand Up!** (Free/$1.99) | Timer only — tells you to stand up but doesn't guide what to do |
| **StretchIt** ($11.99/mo) | Flexibility/yoga focused — not designed for desk workers. Too advanced |
| **Generic timer apps** | No exercise guidance, no personalization |

### Gap in Market
**「デスクワーカー向け + AI パーソナライズ + ブレイクタイマー」を組み合わせたアプリが存在しない。** 既存は「リマインダーだけ」か「本格ワークアウトアプリ」の二極化。その中間（簡単なガイド付きストレッチ + 賢いリマインダー）が欠如。

---

## 3. Solution

### One-Liner
**AI-powered desk stretching timer that reminds you to move and guides personalized stretch routines based on your pain areas.**

### How It Works

```
ユーザーが痛みエリアを選択（首/腰/肩/手首）
    ↓
AI が痛みに合わせたストレッチルーティンを生成
    ↓
設定した間隔でリマインド通知
    ↓
通知タップ → 1-3分のガイド付きストレッチ
    ↓
完了 → 進捗トラッキング → 次回は改善された提案
```

### Key Differentiators

| Feature | DeskStretch | StretchMinder | Wakeout |
|---------|------------|---------------|---------|
| AI パーソナライズ | ✅ Foundation Models | ❌ | ❌ |
| 痛みエリア別ガイド | ✅ | ❌ | ❌ |
| デスクワーカー特化 | ✅ | ✅ | ⚠️ 汎用 |
| オンデバイスAI（無料推論） | ✅ | ❌ | ❌ |
| 価格 | $3.99/mo | Free-$7.99 | $59.99/yr |

### Technology

| Component | Technology | Source |
|-----------|-----------|--------|
| AI Engine | Apple Foundation Models (3B parameter, on-device) | [Apple Developer](https://developer.apple.com/documentation/FoundationModels) — 「developers can bring intelligent experiences into their apps using Apple's on-device large language model... free of cost」 |
| UI | SwiftUI (iOS 15+) | Native |
| Notifications | UserNotifications + scheduled reminders | Native |
| Widget | WidgetKit — next break countdown | Native |
| Analytics | ❌ None (Rule 17: Mixpanel 禁止) | Factory Rule |

---

## 4. Monetization

### Pricing Strategy

| Tier | Price | Content |
|------|-------|---------|
| **Free** | $0 | 3 stretches/day, basic timer, 1 pain area |
| **Premium Monthly** | **$3.99/mo** | Unlimited stretches, AI personalization, all pain areas, custom schedules, progress tracking |
| **Premium Annual** | **$29.99/yr** (~$2.50/mo, 37% savings) | Same as monthly |

### Pricing Justification

| Benchmark | Value | Source |
|-----------|-------|--------|
| H&F median monthly | $7.73/mo | [RevenueCat State of Subscription Apps 2024](https://www.revenuecat.com/state-of-subscription-apps-2024/) — 「Health & Fitness category, the median annual plan is priced at $29.65, which is 3.8x the monthly price of $7.73」 |
| H&F median annual | $29.65/yr | Same source |
| H&F trial conversion (top quartile) | 58.8% | Same source — 「notably high upper quartile rates in Health & Fitness (58.8%)」 |
| Wakeout | $59.99/yr | [Wakeout](https://wakeout.app/pricing) |
| StretchMinder Plus | $7.99-$95.99 | [App Store](https://apps.apple.com/us/app/stretchminder-daily-movement/id1518522560) |

**戦略**: $3.99/mo は H&F median ($7.73) の約半額。低価格でインストール数を最大化し、AI パーソナライズで retention を確保。$29.99/yr は median ($29.65) とほぼ同水準。

### Revenue Model

| Metric | Conservative | Target |
|--------|-------------|--------|
| Free trial | 7 days | 7 days |
| Trial → Paid conversion | 15% | 25% |
| Monthly:Annual ratio | 40:60 | 30:70 |
| Churn (monthly) | 12% | 8% |

ソース: [RevenueCat State of Subscription Apps 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「Users showed a strong preference for 1-year plans in Health & Fitness apps, indicating a trend towards long-term goals」

### RevenueCat Integration

| Item | Value |
|------|-------|
| SDK | RevenueCat Swift SDK (RevenueCatUI 禁止 — Rule 20) |
| Offering | `default` — Monthly ($3.99) + Annual ($29.99) |
| Entitlement | `premium` |
| Paywall | 自前 SwiftUI PaywallView + `Purchases.shared.purchase(package:)` |
| Soft Paywall | オンボーディング最終画面 + [Maybe Later] ボタン (Rule 20) |

---

## 5. MVP Scope

### Must Have (v1.0)

| # | Feature | Description |
|---|---------|-------------|
| 1 | **オンボーディング** | 3画面: 問題共感 → 痛みエリア選択 → ソフトペイウォール |
| 2 | **ブレイクタイマー** | 30/45/60/90分間隔で設定可能。通知でリマインド |
| 3 | **ストレッチライブラリ** | 20+ exercises — 首/腰/肩/手首の4カテゴリ。SF Symbols + テキスト説明 |
| 4 | **AIストレッチ提案** | Foundation Models で痛みエリアに基づくパーソナライズ提案 |
| 5 | **ストレッチセッション** | 1-3分のガイド付きセッション。カウントダウンタイマー + アニメーション |
| 6 | **プログレストラッキング** | 今日のストレッチ数、連続日数（ストリーク） |
| 7 | **通知** | ブレイクリマインダー + 朝の「今日のストレッチ」 |
| 8 | **ペイウォール** | 自前 SwiftUI。RevenueCat SDK。[Maybe Later] 付き |
| 9 | **設定** | 通知間隔、痛みエリア変更、勤務時間設定 |

### Won't Have (v1.0)

| Feature | Reason |
|---------|--------|
| Apple Watch | Scope overflow — v1.1 候補 |
| HealthKit integration | Complexity — v1.1 候補 |
| Video exercises | Storage/hosting cost — v1.1 候補 |
| Social features | Unnecessary for MVP |
| Gamification (streaks, badges) | Beyond timer + stretch core |
| Live Activities | Nice-to-have, not MVP |

### Technical Architecture

```
DeskStretchios/
├── App/
│   ├── DeskStretchApp.swift          # Entry point + RevenueCat configure
│   └── ContentView.swift             # Tab-based navigation
├── Views/
│   ├── Onboarding/
│   │   ├── OnboardingView.swift      # 3-step flow
│   │   └── PaywallView.swift         # Self-built (Rule 20)
│   ├── Timer/
│   │   ├── TimerView.swift           # Break countdown
│   │   └── TimerSettingsView.swift
│   ├── Stretch/
│   │   ├── StretchListView.swift     # Exercise library
│   │   ├── StretchSessionView.swift  # Guided session
│   │   └── StretchDetailView.swift
│   ├── Progress/
│   │   └── ProgressView.swift        # Daily/streak tracking
│   └── Settings/
│       └── SettingsView.swift
├── Models/
│   ├── StretchExercise.swift         # Exercise data model
│   ├── PainArea.swift                # Neck, back, shoulders, wrists
│   ├── BreakSchedule.swift           # Timer configuration
│   └── UserProgress.swift            # Streak, completed sessions
├── Services/
│   ├── AIStretchService.swift        # Foundation Models integration
│   ├── NotificationService.swift     # Break reminders
│   ├── SubscriptionService.swift     # RevenueCat wrapper
│   └── ProgressService.swift         # UserDefaults persistence
└── Resources/
    ├── StretchLibrary.json           # 20+ exercises
    └── Localizable.strings           # en + ja
```

### Localization

| Language | Scope |
|----------|-------|
| English (en-US) | Primary |
| Japanese (ja) | Secondary |

---

## 6. App Identity

| Field | Value |
|-------|-------|
| **App Name** | DeskStretch |
| **Bundle ID** | com.aniccafactory.deskstretch |
| **Subtitle** | AI Desk Stretching & Break Timer |
| **Category** | Health & Fitness |
| **Age Rating** | 4+ |
| **iTunes Name Check** | ✅ 0 exact matches (verified 2026-03-05) |

### ASO Keywords (Primary)

| Priority | Keyword | Rationale |
|----------|---------|-----------|
| 1 | desk stretching | Core use case |
| 2 | break timer | Core feature |
| 3 | back pain office | Pain-driven search |
| 4 | stretch reminder | Behavior trigger |
| 5 | desk exercises | Alternative phrasing |
| 6 | office workout | Broader reach |
| 7 | posture break | Adjacent need |
| 8 | AI stretching | Differentiator |

---

## 7. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Foundation Models requires iOS 26+ | Limits user base to newest devices | Provide fallback static stretch suggestions for older iOS |
| Low conversion rate | Revenue below target | Aggressive ASO + TikTok organic content |
| User churn after novelty | Drop in monthly subscribers | AI-generated daily variety + streak mechanics |
| App Store rejection (4.3 spam) | Delays launch | Unique AI feature differentiates from existing stretch apps |
| StretchMinder adds AI | Competitive pressure | First-mover advantage + better UX |

---

## Sources Summary

| # | Source | What It Supports |
|---|--------|-----------------|
| 1 | [Nature Scientific Reports 2025](https://www.nature.com/articles/s41598-025-30155-6) | 80.81% MSD prevalence among office workers |
| 2 | [Illinois Chiropractic Society](https://ilchiro.org/impact-of-back-pain-in-the-workplace/) | 101.8M workdays lost |
| 3 | [Towards Healthcare](https://www.towardshealthcare.com/insights/chronic-lower-back-pain-market-sizing) | LBP market $2.69B → $6.69B |
| 4 | [CDC NIOSH](https://blogs.cdc.gov/niosh-science-blog/2019/07/08/lbp/) | Remote workers increased LBP risk |
| 5 | [RevenueCat 2024](https://www.revenuecat.com/state-of-subscription-apps-2024/) | H&F median pricing $7.73/mo, $29.65/yr |
| 6 | [RevenueCat 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | Annual plan preference in H&F |
| 7 | [Apple Foundation Models](https://developer.apple.com/documentation/FoundationModels) | On-device AI, free inference, 3B parameters |
| 8 | [Apple Newsroom](https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/) | Foundation Models capabilities |
| 9 | [StretchMinder App Store](https://apps.apple.com/us/app/stretchminder-daily-movement/id1518522560) | Competitor pricing/features |
| 10 | [Wakeout Pricing](https://wakeout.app/pricing) | Competitor pricing $59.99/yr |
