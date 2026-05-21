# Product Plan: Zone2Daily

**Date:** 2026-03-09
**Status:** COMPLETED (US-002)
**App:** Zone2Daily — Zone 2 心拍数コーチ

---

## 1. Target User

### Primary User

| 属性 | 内容 |
|------|------|
| Demographics | 30-50代、男女問わず、Apple Watch所持者 |
| Archetype | Huberman/Attia プロトコル実践者、ランナー・サイクリスト |
| Behavior | 毎週3-5回の有酸素運動。「科学的トレーニング」に移行したいが方法がわからない |
| Pain Point | Zone 3-4 で走りすぎて疲労が抜けない。Zone 2 の目標 HR がわからない |
| Willingness to Pay | $4.99/月（ジム1回分以下）なら即決。年間 $29.99 はコーヒー1ヶ月分 |

### Market Size Evidence

| ソース | データ | 意味 |
|--------|-------|------|
| [Grand View Research — Fitness App Market 2024](https://www.grandviewresearch.com/industry-analysis/fitness-app-market) | $14.7B market, 17.6% CAGR | H&F アプリ市場は高成長中 |
| [Statista — Running App Users US 2024](https://www.statista.com/statistics/1222232/running-app-users-us/) | 88M+ US running app users | Zone 2 のターゲット層は数千万人規模 |
| [Peter Attia MD — Zone 2 Popularity](https://peterattiamd.com/zone2/) | Zone 2 training is the "most discussed longevity protocol" in 2024-2025 | 長寿・パフォーマンス文脈での急速な普及 |

---

## 2. Problem

### Core Problem

> ほとんどのランナーが Zone 3-4 で走り、Zone 2 の脂肪燃焼・長寿効果を得られていない。自分の Zone 2 目標 HR を知っていても、週あたり何分達成できているか追跡できるシンプルなツールがない。

### Why Existing Solutions Fail

| 競合 | レビュー数 | 評価 | 失敗理由 |
|------|-----------|------|---------|
| Zones for Training | 18,871 | 4.79 | 全ゾーン対応で複雑すぎる。Zone 2 専用ではない。UI古い |
| Zone 2: Heart Rate Training | 226 | 4.65 | 基本計算のみ。進捗追跡なし。週間ダッシュボードなし |
| Zone 2 Buddy | 0 | — | 新規参入、機能不明 |
| Orange Zones Workout Companion | 1,049 | 4.45 | Orangetheory特化で汎用性なし |

### Gap in Market

> Zone 2 専用で、かつ「週間進捗トラッキング」と「目標達成率」を可視化するシンプルなアプリが存在しない。

---

## 3. Solution

### One-Liner

> マフェトン式で Zone 2 目標 HR を自動計算し、週150分達成を科学的にサポートするトレーニングコンパニオン

### How It Works

```
[年齢入力]
    ↓
[Zone 2 HR 自動計算 (180-age)]
    ↓
[ワークアウト記録 (タイマー + Zone 2 滞在時間入力)]
    ↓
[週間ダッシュボード (Zone 2 分数累計 / 目標150分)]
    ↓
[達成率 + ストリーク表示]
```

Source: [Maffetone Method — Phil Maffetone](https://philmaffetone.com/180-formula/) — 「The Maximum Aerobic Function (MAF) test: subtract your age from 180.」

### Key Differentiators

| 軸 | Zone2Daily | Zone 2: Heart Rate Training | Zones for Training |
|----|-----------|--------------------------|-------------------|
| Zone 2 専用設計 | ✅ Zone 2 のみ | ✅ Zone 2 中心 | ❌ 全ゾーン |
| 週間進捗追跡 | ✅ 150分/週目標 | ❌ なし | ⚠️ 限定的 |
| Maffetone 計算式 | ✅ 自動計算 | ⚠️ 手動設定 | ❌ なし |
| シンプルUX | ✅ 単一目的 | ⚠️ やや複雑 | ❌ 複雑 |
| 価格 | $4.99/月 Freemium | 無料 | 無料/買切り |

### Technology

| コンポーネント | 技術選択 | 理由 |
|-------------|---------|------|
| UI | SwiftUI | iOS 17+ ネイティブ、アニメーション自然 |
| データ永続化 | SwiftData | CoreData より軽量、iOS 17+ 標準 |
| 状態管理 | MVVM + @Observable | SwiftUI ベストプラクティス |
| 課金 | RevenueCat SDK | 業界標準、A/B テスト対応 |
| 通知 | UserNotifications | ワークアウトリマインダー |

---

## 4. Monetization

### Pricing Strategy

| Tier | 価格 | 内容 |
|------|------|------|
| Free | $0 | Zone 2 HR 計算のみ。直近7日間のログ3件まで |
| Monthly | **$4.99/月** | 無制限ログ + 週間ダッシュボード + 目標設定 + ストリーク |
| Annual | **$29.99/年** ($2.50/月) | Monthly の全機能。50% OFF 表示 |

### Pricing Justification

| ソース | データ | 適用 |
|--------|-------|------|
| [RevenueCat SOSA 2025 — H&F Median](https://www.revenuecat.com/state-of-subscription-apps-2025/) | H&F median: $7.73/月, $29.65/年 | $4.99/月は中央値の64%（許容範囲内） |
| [Jake Mor #17](https://www.revenuecat.com/blog/growth/how-to-price-your-app/) | Trial-less monthly + trialed annual at 50% apparent discount | Annual を Monthly × 12($59.88) の 50% OFF = $29.99 |
| [Jake Mor #15](https://www.revenuecat.com/blog/growth/how-to-price-your-app/) | Prices convert to clean weekly amounts | $29.99/年 = 週 $0.58 (コーヒー1/10杯) |
| 競合比較 | Zone 2: Heart Rate Training = 無料のみ | 有料機能で差別化可能 |

### Revenue Model

| シナリオ | 想定 | 月収 |
|---------|------|------|
| 保守的 (100 DL/月, 5% conversion) | 5 subscriptions × $4.99 | $25/月 |
| 中央値 (500 DL/月, 5% conversion) | 25 subscriptions × $4.99 | $125/月 |
| 楽観的 (2,000 DL/月, 8% conversion) | 160 subscriptions × $4.99 | $798/月 |

Source: [RevenueCat SOSA 2026](https://www.revenuecat.com/state-of-subscription-apps/) — 「5% trial-to-paid conversion is median for H&F apps.」

### RevenueCat Integration

| コンポーネント | 設定 |
|-------------|------|
| SDK | RevenueCat iOS SDK (SPM) |
| Offering ID | `default` |
| Entitlement ID | `premium` |
| Products | `zone2daily_monthly_499`, `zone2daily_annual_2999` |
| PaywallView | 自前 SwiftUI（RevenueCatUI 禁止 — Rule 20） |
| [Maybe Later] | オンボーディング最終画面でソフトペイウォール |

---

## 5. MVP Scope

### Must Have

| # | Feature | Description |
|---|---------|-------------|
| 1 | Zone 2 HR 計算 | 年齢入力 → Maffetone式（180−年齢）で Zone 2 HR 範囲を自動計算 |
| 2 | オンボーディング | 年齢入力 → Zone 2 HR 表示 → ソフトペイウォール（Maybe Later あり） |
| 3 | ワークアウト記録 | タイマー起動 → 終了時に「Zone 2 滞在時間」を手動入力 → 保存 |
| 4 | 週間ダッシュボード | 今週の Zone 2 分数累計 / 目標 150 分を進捗バーで表示 |
| 5 | ストリーク | 連続実施日数カウント（今日 Zone 2 実施 = +1） |
| 6 | 通知 | 毎朝「今日も Zone 2 をしよう」リマインダー（UNUserNotificationCenter） |
| 7 | 設定画面 | 年齢・目標変更 + Upgrade → PaywallView |

### Won't Have (v1.0)

| Feature | Reason |
|---------|--------|
| HealthKit リアルタイム HR 表示 | 権限管理が複雑、審査で追加説明必要（PROHIBITED Rule） |
| HealthKit WorkoutSession | 同上 |
| Live Activities / Dynamic Island | WidgetKit Extension 必要、Maestro E2E テスト困難（PROHIBITED Rule） |
| Apple Watch アプリ | WatchKit Extension 追加、テスト複雑（PROHIBITED Rule） |
| OpenAI / AI フィードバック | コスト発生（PROHIBITED Rule 23） |
| CloudKit 同期 | 複雑、デバッグ困難（PROHIBITED Rule） |
| Social sharing | スコープ外。v1.1 候補 |
| Karvonen / %HRmax 切替 | Maffetone 一本化でシンプルさ優先。v1.1 候補 |

### Technical Architecture

```
Zone2Daily/
├── App/
│   ├── Zone2DailyApp.swift        # @main, RevenueCat setup
│   └── AppState.swift              # @Observable global state
├── Models/
│   ├── WorkoutSession.swift        # SwiftData @Model
│   └── UserProfile.swift           # SwiftData @Model (age, weeklyGoal)
├── Services/
│   ├── SubscriptionServiceProtocol.swift
│   ├── SubscriptionService.swift   # RevenueCat DI
│   └── NotificationService.swift
├── ViewModels/
│   ├── OnboardingViewModel.swift
│   ├── WorkoutViewModel.swift
│   └── DashboardViewModel.swift
├── Views/
│   ├── Onboarding/
│   │   ├── OnboardingContainerView.swift
│   │   ├── AgeInputView.swift
│   │   ├── Zone2ExplainerView.swift
│   │   └── PaywallView.swift       # 自前 SwiftUI（RevenueCatUI禁止）
│   ├── Dashboard/
│   │   ├── DashboardView.swift
│   │   └── WeeklyProgressView.swift
│   ├── Workout/
│   │   ├── WorkoutTimerView.swift
│   │   └── WorkoutLogView.swift
│   └── Settings/
│       └── SettingsView.swift
├── DesignSystem/
│   ├── Colors.swift                # Brand tokens
│   ├── Typography.swift
│   └── Spacing.swift
├── Resources/
│   ├── Localizable.xcstrings      # en-US + ja
│   └── PrivacyInfo.xcprivacy
└── Tests/
    └── Zone2DailyTests/
```

### Localization

| Screen | en-US | ja |
|--------|-------|-----|
| App Name | Zone2Daily | Zone2Daily |
| Tagline | Train Smarter, Not Harder | 賢く鍛えよう |
| Onboarding CTA | Start Training | トレーニング開始 |
| Weekly Goal | 150 min/week goal | 週150分の目標 |
| Paywall title | Unlock All Features | 全機能を解放する |
| Maybe Later | Maybe Later | あとで |
| Settings | Settings | 設定 |

---

## 6. App Identity

### App Name

| 項目 | 値 |
|------|-----|
| App Name | **Zone2Daily** |
| App Title (Jake Mor format) | `Zone 2 Cardio - Zone2Daily` |
| Bundle ID | `com.aniccafactory.zone2daily` |
| Subtitle | Zone 2 Heart Rate Coach |
| Category | Health & Fitness |
| Age Rating | 4+ |

Source: [Jake Mor #53](https://www.revenuecat.com/blog/growth/how-to-price-your-app/) — App title format: `"Keyword - AppName"`

### iTunes Name Check

| 候補名 | 検索クエリ | 完全一致数 | 判定 |
|--------|---------|-----------|------|
| Zone2Daily | `zone2daily` | **0** | ✅ 採用 |
| Zone 2 Daily | `zone 2 daily` | **0** | ✅ (verified 2026-03-09) |

### ASO Keywords

| Priority | Keyword | Rationale |
|----------|---------|-----------|
| 1 | zone 2 cardio | TikTok 709K views #zone2cardio |
| 2 | zone 2 training | TikTok 713K views #zone2training |
| 3 | heart rate zone | 直接的な機能キーワード |
| 4 | maffetone method | 差別化計算式。競合が使っていない |
| 5 | aerobic training | 広義の有酸素トレーニング検索 |
| 6 | fat burning zone | Zone 2 の主要ベネフィット |
| 7 | cardio tracker | 競合キーワード |
| 8 | peter attia zone 2 | Attia/Huberman ファン層 |

---

## 7. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **HealthKit未使用で差別化困難** | High | Zone 2「専用」+ 週間進捗トラッキングに特化。v1.1 で HealthKit 追加 |
| **App Store Guideline 4.3 Spam** (同様アプリが多い) | Medium | Zone 2 Weekly Progress という独自 UI で差別化。スクショで可視化 |
| **HealthKit権限なしでのUX低下** | Medium | 手動入力でも十分なUX提供。タイマー機能で使いやすさを確保 |
| **低trial-to-paid (<5%)** | High | Maybe Later ソフトペイウォール。Free tier の制限（3件/7日）を明確に |
| **競合 "Zones for Training" のZone 2特化** | Low | 現在は全ゾーン対応。Zone 2 専用 UX での差別化は有効 |
| **Privacy Manifest 未申告 (ITMS-91053)** | High | PrivacyInfo.xcprivacy を必ず含める（US-005a で確認） |
| **App Completeness (Guideline 2.1)** | Medium | Maestro E2E でオンボーディング〜課金フロー完全テスト |

Source: [Twinr — App Store Rejection Reasons 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) — 「15% of submissions rejected. Over 40% of unresolved issues = Guideline 2.1.」
Source: [Full Scale — Risk Assessment](https://fullscale.io/blog/risk-assessment-for-startups/) — 「Companies with formal risk plans experience 30% fewer operational disruptions.」

---

## Sources Summary

| # | Source | What It Supports |
|---|--------|-----------------|
| 1 | [Grand View Research — Fitness App Market](https://www.grandviewresearch.com/industry-analysis/fitness-app-market) | Market size $14.7B, 17.6% CAGR |
| 2 | [Statista — Running App Users](https://www.statista.com/statistics/1222232/running-app-users-us/) | 88M+ US target audience |
| 3 | [Peter Attia MD — Zone 2](https://peterattiamd.com/zone2/) | Zone 2 as longevity protocol, target user validation |
| 4 | [Maffetone — 180 Formula](https://philmaffetone.com/180-formula/) | Core calculation formula |
| 5 | [Apify TikTok — #zone2cardio 709K](https://api.apify.com/v2/datasets/mVhGpSdPTa48eXLlC/items) | Trend validation |
| 6 | [iTunes API — Zone 2: Heart Rate Training (226 reviews)](https://itunes.apple.com/search?term=zone+2+heart+rate) | Competitive gap |
| 7 | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | H&F median pricing $7.73/mo |
| 8 | [RevenueCat SOSA 2026](https://www.revenuecat.com/state-of-subscription-apps/) | 5% trial-to-paid conversion |
| 9 | [Jake Mor #17 — Pricing Strategy](https://www.revenuecat.com/blog/growth/how-to-price-your-app/) | Annual = Monthly×12 at 50% off |
| 10 | [Jake Mor #53 — App Title](https://www.revenuecat.com/blog/growth/how-to-price-your-app/) | "Keyword - AppName" format |
| 11 | [Twinr — App Store Rejections 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) | Risk: 15% rejection rate |
| 12 | [Apple Developer — CFBundleIdentifier](https://developer.apple.com/documentation/bundleresources/information_property_list/cfbundleidentifier) | Bundle ID format rules |
