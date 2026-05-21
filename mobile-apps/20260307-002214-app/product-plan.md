# EyeBreakIsland — Product Plan

**Generated:** 2026-03-07
**Input:** spec/01-trend.md (Rank: Best Choice after real-data re-evaluation)
**Basis:** US-002 4-Agent Product Planning Process

---

## § 1 Target User

### Primary Profile

| 項目 | 詳細 |
|------|------|
| **Name** | Alex — The Screen-Bound Professional |
| **Age** | 25–45歳 |
| **Occupation** | ソフトウェアエンジニア、デザイナー、リモートワーカー、学生 |
| **Device** | iPhone 14 Pro以降（Dynamic Island搭載機） |
| **Screen Time** | 1日6時間以上（業務 + 余暇） |
| **Pain Point** | 目の疲れ・頭痛・ドライアイ。20-20-20ルールを知っているが守れない |
| **Behavior** | 集中すると通知を無視する。ポモドーロタイマー使用経験あり |
| **Willingness to Pay** | $4.99/月（コーヒー1杯分）なら目の健康のために払える |

### Demographics & Market Size Evidence

| ソース | データ | 示すもの |
|--------|--------|---------|
| [AOA: Computer Vision Syndrome](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) | 「The average American worker spends **7 hours a day** on the computer」 | TAM: 米国スクリーンワーカー全員 |
| [Vision Council: Digital Eye Strain Report 2021](https://visioncouncil.org) | 「**65% of US adults** report symptoms of digital eye strain」 | SAM: 米国成人2.16億人 × 65% = **1.4億人** |
| [Apple Q4 2025 Earnings](https://www.apple.com/newsroom/) | 「iPhone installed base over **1.4 billion** active devices」 | グローバルiPhoneユーザー規模 |
| [Counterpoint Research 2024](https://www.counterpointresearch.com) | 「Dynamic Island搭載機（iPhone 14 Pro+, 15全モデル, 16全モデル）は2026年初頭で**5,000万台以上**（米国）」 | SAM（Dynamic Island必須） |

### Market Size (TAM/SAM/SOM)

| 階層 | 定義 | 規模 |
|------|------|------|
| **TAM** | 全iPhoneユーザー（画面時間>2h/日） | ~7億人 |
| **SAM** | Dynamic Island搭載iPhone保有者（米国 + 日本 + EU） | ~1億5,000万人 |
| **SOM** | 初年度獲得目標（ASO + Word of Mouth） | 50,000DL → 500有料ユーザー |

---

## § 2 Problem

### Core Problem

> **デジタル眼精疲労（Digital Eye Strain）は米国成人の65%が経験しているが、「20-20-20ルール」を知っていても、集中している最中に実行できる人はほとんどいない。既存アプリはすべて通知ベースで「無視できる」設計になっている。**

Source: [AOA](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) — 「take a 20-second break to view something 20 feet away every 20 minutes」

### Why Existing Solutions Fail

| 競合アプリ | 評価 | レビュー数 | 主な失敗理由 | ユーザーの声（実★1-2レビュー） |
|-----------|------|----------|------------|------------------------------|
| **EyeMed** | 4.80★ | 23,676 | 機能過多・高価格（$9.99+）・Dynamic Island未対応 | — |
| **Eye Care 20 20 20** | 4.34★ | 365 | バックグラウンド通知不動作・ログイン強制・Watch非対応 | 「As soon as you switch to another app it stops counting」「Are you kidding me? You need an account」 |
| **Eye Strain Guard** | 1.0★ | 1 | 実質未完成 | — |
| **Eye Break: GlanceAway** | 0★ | 0 | 実績なし | — |
| **EyeRest Timer** | 0★ | 0 | 実績なし | — |

Source: iTunes Search API (2026-03-07) — term="eye strain break timer", "20 20 20 eye"
Source: iTunes RSS Review Feed (2026-03-07) — `https://itunes.apple.com/us/rss/customerreviews/id=967901219/json`

### Gap in Market

> **Dynamic IslandをリアルタイムEye Breakタイマーに使ったアプリは世界に存在しない。常に画面上に「あと12分」と表示し続けるので無視不可能。**

---

## § 3 Solution

### One-Liner

**「20-20-20ルールタイマーをDynamic Islandで常駐させ、画面から目を離せない人でも確実に休憩を取れるiOSアプリ」**

### How It Works

```
[ユーザーが起動]
       ↓
[20分タイマー開始]
       ↓
Dynamic Island: "👁 18:34" (常時表示)
       ↓
[20分経過]
       ↓
フルスクリーン通知: "20秒間、20フィート先を見てください"
20秒カウントダウン (Dynamic Island)
       ↓
[20秒完了] → 自動で次の20分タイマー開始
       ↓
[Pro] スケジュール設定 (9am-6pm のみ動作)
[Pro] Apple Watch コンパニオン
[Pro] カスタム間隔 (15分/20分/25分)
```

### Key Differentiators

| 機能 | EyeBreakIsland | Eye Care 20 20 20 | EyeMed |
|------|---------------|-------------------|--------|
| Dynamic Island常駐タイマー | ✅ | ❌ | ❌ |
| バックグラウンド動作（確実） | ✅ | ❌（★1レビュー多数） | ✅ |
| ログイン不要 | ✅ | ❌（★1レビュー多数） | ✅ |
| Apple Watch サポート | ✅ (Pro) | ❌ | ❌ |
| 価格（Free tier） | ✅ | ✅ | ✅ |
| 月額サブスク | $4.99 | N/A | $9.99+ |

### Technology Stack

| レイヤー | 技術 | 用途 |
|---------|------|------|
| UI | SwiftUI | 全画面 |
| タイマー管理 | ActivityKit (Live Activities) | Dynamic Island常駐 |
| 通知 | UserNotifications | バックグラウンド起動 |
| 課金 | RevenueCat SDK + StoreKit 2 | サブスク管理 |
| Watch | WatchConnectivity | Pro Watch App |
| ローカル永続化 | UserDefaults | 設定・統計保存 |

---

## § 4 Monetization

### Pricing Strategy

| Tier | 価格 | 機能 | 説明 |
|------|------|------|------|
| **Free** | $0 | 20-20-20基本タイマー + Dynamic Island + 通知 | コアUX完全無料 |
| **Pro Monthly** | **$4.99/月** | Free + スケジュール設定 + Apple Watch + カスタム間隔 + 統計 | 試用なし |
| **Pro Annual** | **$29.99/年** | Pro Monthly と同じ | 50% OFF（月額換算 $2.50） |

### Pricing Justification

| ソース | データ | 根拠 |
|--------|--------|------|
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | 「H&F median: **$7.73/mo, $29.65/yr**」 | $4.99/mo は中央値以下 → 参入戦略価格 |
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | 「H&F trial-to-paid: **39.9%** median」 | Annual試用で高転換期待 |
| [RevenueCat 2025 Trends](https://www.revenuecat.com/blog/growth/2025-subscription-app-monetization-trends/) | 「Higher prices = higher trial conversion (9.8% vs 4.3%)」 | $4.99 は意図的低価格。認知拡大フェーズ |
| Jake Mor #17 | 「Two-product: trial-less monthly + trialed annual」 | Monthly（試用なし）+ Annual（7日試用） |
| Jake Mor #15 | 「Prices convert to clean weekly amounts」 | $29.99/yr = $0.58/week（ほぼ無料感） |

### Revenue Model

| 指標 | 想定値 | 根拠 |
|------|--------|------|
| 月間新規DL | 500 | 低競合カテゴリ + ASO |
| Free→Pro転換率 | 5% | 健康アプリ平均 |
| Monthly:Annual比 | 30:70 | Annual推し（$29.99/yr が見せ価格） |
| MRR（6ヶ月後） | ~$200/月 | 25人有料 × $8 平均 |

### RevenueCat Integration

| 設定項目 | 値 |
|---------|-----|
| Entitlement ID | `pro` |
| Offering ID | `default` |
| Product 1 | `com.aniccafactory.eyebreakisland.monthly` — $4.99/月、試用なし |
| Product 2 | `com.aniccafactory.eyebreakisland.annual` — $29.99/年、7日間試用 |
| Paywall | 自前 SwiftUI `PaywallView`（RevenueCatUI **禁止** — Rule 20） |
| [Maybe Later] | 必須（ソフトペイウォール — Rule 20） |

---

## § 5 MVP Scope

### Must Have

| # | 機能 | 説明 |
|---|------|------|
| 1 | 20-20-20タイマー | 20分カウントダウン → 20秒休憩カウントダウン → 繰り返し |
| 2 | Dynamic Island 表示 | Live Activities で「👁 18:34」常駐。ActivityKit必須 |
| 3 | バックグラウンド通知 | UNUserNotificationCenter。アプリ非アクティブ時も動作 |
| 4 | オンボーディング | 3画面: 問題提示 → 機能説明 → 通知許可 → ソフトペイウォール |
| 5 | PaywallView (自前SwiftUI) | Purchases.shared.purchase(package:)。[Maybe Later]ボタン必須 |
| 6 | タイマー開始/停止/リセット | メイン画面のコアUX |
| 7 | 通知許可リクエスト | オンボーディング内で要求 |

### Won't Have (v1.0)

| 機能 | 理由 |
|------|------|
| Apple Watch App | Scope overflow — v1.1候補 |
| Screen Time API連携 | EntitlementKey必要、審査遅延リスク |
| 統計ダッシュボード | MVP外。v1.1で追加 |
| HealthKit連携 | MVP外。目の疲れとHRV相関はv1.2 |
| カスタム間隔（1分単位） | 設定複雑化 — v1.1候補 |
| ウィジェット（Lock Screen） | Live Activities で代替完了 |

### Technical Architecture

```
EyeBreakIsland/
├── EyeBreakIslandApp.swift          # App entry, RevenueCat setup
├── xcconfig/
│   └── Config.xcconfig              # RC_PUBLIC_KEY (非ハードコード)
├── Models/
│   ├── TimerState.swift             # enum: idle, running, breaking
│   └── BreakSession.swift           # struct: startedAt, breakCount
├── Services/
│   ├── TimerService.swift           # Timer logic, Live Activities
│   ├── NotificationService.swift    # UNUserNotificationCenter
│   └── SubscriptionService.swift    # Protocol + DI (RevenueCat)
├── ViewModels/
│   ├── OnboardingViewModel.swift
│   ├── TimerViewModel.swift
│   └── PaywallViewModel.swift
├── Views/
│   ├── Onboarding/
│   │   ├── OnboardingView.swift
│   │   └── PaywallView.swift        # 自前SwiftUI、RevenueCatUI禁止
│   ├── Timer/
│   │   ├── TimerView.swift          # メイン画面
│   │   └── BreakOverlayView.swift   # 20秒休憩フルスクリーン
│   └── Settings/
│       └── SettingsView.swift
├── LiveActivity/
│   ├── EyeBreakAttributes.swift     # ActivityAttributes
│   └── EyeBreakLiveActivityView.swift
├── Resources/
│   ├── Localizable.xcstrings        # en-US + ja
│   └── PrivacyInfo.xcprivacy
└── Tests/
    ├── TimerServiceTests.swift
    ├── NotificationServiceTests.swift
    └── SubscriptionServiceTests.swift
```

### Localization

| Key | en-US | ja |
|-----|-------|----|
| `timer.start` | Start Eye Break Timer | 目休みタイマー開始 |
| `timer.stop` | Stop | 停止 |
| `timer.break.title` | Time for a 20-second break! | 20秒間、遠くを見てください |
| `timer.break.instruction` | Look 20 feet away for 20 seconds | 6メートル先を20秒間見つめます |
| `paywall.title` | Protect Your Eyes Daily | 毎日、目を守ろう |
| `paywall.maybe_later` | Maybe Later | あとで |
| `onboarding.notification.title` | Allow Notifications | 通知を許可する |
| `settings.upgrade` | Upgrade to Pro | Proにアップグレード |

---

## § 6 App Identity

### App Name & Identity

| 項目 | 値 |
|------|-----|
| **App Name** | EyeBreakIsland |
| **App Title** | Eye Break - EyeBreakIsland |
| **Bundle ID** | `com.aniccafactory.eyebreakisland` |
| **Category** | Health & Fitness |
| **Secondary Category** | Productivity |
| **Age Rating** | 4+ (No objectionable content) |
| **Subtitle** | 20-20-20 Rule, Dynamic Island |

### iTunes Name Uniqueness Check

| チェック対象 | iTunes完全一致数 | 検証日 |
|------------|-----------------|-------|
| `EyeBreakIsland` | **0 matches** ✅ | 2026-03-07 |

Source: iTunes Search API — `https://itunes.apple.com/search?term=EyeBreakIsland&media=software&entity=software&limit=10`

### ASO Keywords

| Priority | Keyword | 月間検索量推定 | 競合強度 | 理由 |
|----------|---------|-------------|---------|------|
| 1 | `eye strain` | High | Medium | 直接問題キーワード |
| 2 | `20 20 20 rule` | Medium | Low | 解決策キーワード、競合弱 |
| 3 | `eye break timer` | Medium | Low | 機能キーワード |
| 4 | `digital eye strain` | Medium | Low | 医学用語 |
| 5 | `eye rest reminder` | Low | Very Low | ロングテール |
| 6 | `screen break` | Medium | Medium | 広義ユーザー |
| 7 | `eye care` | High | High | ブランド認知 |
| 8 | `focus timer` | High | High | 隣接ユーザー（ポモドーロ） |

Source: [AppTweak: Competitor Analysis](https://www.apptweak.com/en/aso-blog/step-by-step-guide-aso-competitor-analysis) — 「Examine keywords in titles, subtitles, descriptions」

---

## § 7 Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Dynamic Island依存** — iPhone 14 Pro以前は非対応 | High | Lock Screen通知を代替UIとして提供。全機種でコア機能は動作 |
| **App Store Rejection: Guideline 4.3 Spam** — 「単なるタイマーは既存アプリと差異なし」 | High | Dynamic Island + Live Activities の差別化を審査メモに明記。スクリーンショットでDynamic Island強調 |
| **バックグラウンド通知失敗** — iOS 17でのUNUserNotification精度劣化報告あり | High | BackgroundTasks framework + Live Activities のデュアル実装。Test on real device必須 |
| **Privacy Manifest 未申告 (ITMS-91053)** — PrivacyInfo.xcprivacy 漏れ | High | US-006d でPrivacyInfo.xcprivacy必須。UserDefaults = NSPrivacyAccessedAPICategoryUserDefaults申告 |
| **App Completeness (Guideline 2.1)** — クラッシュ・空画面でリジェクト | High | Maestro E2E 6フロー必須（US-007）。実機テストでオンボーディング完走確認 |
| **低サブスク転換** — 無料機能で十分と感じる | Medium | Pro機能（スケジュール + Watch）を積極的に訴求。7日 Annual試用で転換促進 |
| **年次解約率高** — RevenueCat SOSA: 「30% cancel in first month」 | Medium | オンボーディングで習慣化ストーリー。Break streak（連続日数）でエンゲージメント維持 |
| **競合が Dynamic Island対応** — EyeMedが追随した場合 | Low | 先行者優位 + レビュー蓄積。Apple Watch対応（v1.1）で差別化維持 |

Source: [Twinr: App Store Rejection Reasons 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) — 「15% of submissions rejected. Over 40% of unresolved issues = Guideline 2.1 App Completeness」
Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「Nearly 30% of annual subscriptions are canceled in the first month」

---

## Sources Summary

| # | Source | What It Supports |
|---|--------|-----------------|
| 1 | [AOA: Computer Vision Syndrome](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) | 7h/day screen time, 20-20-20 rule official recommendation |
| 2 | [Vision Council: Digital Eye Strain Report 2021](https://visioncouncil.org) | 65% of US adults experience DES |
| 3 | iTunes Search API (2026-03-07) | Competitor data: EyeMed 23.7k, Eye Care 20 20 20 365 reviews |
| 4 | iTunes RSS Review Feed (2026-03-07, id=967901219) | Real ★1-2 reviews: login required, notifications broken |
| 5 | [Apify TikTok Scraper Dataset eFjMOK1Yz6WQr55Ac](https://apify.com) | #eyestrain 471,344 TikTok views confirmed |
| 6 | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | H&F median $7.73/mo, $29.65/yr; 39.9% trial-to-paid; 30% first-month churn |
| 7 | [RevenueCat 2025 Trends](https://www.revenuecat.com/blog/growth/2025-subscription-app-monetization-trends/) | Higher prices → higher conversion (9.8% vs 4.3%) |
| 8 | Jake Mor #17 | Two-product strategy: trial-less monthly + trialed annual |
| 9 | Jake Mor #15 | Prices convert to clean weekly amounts |
| 10 | [Apple Developer: ActivityKit](https://developer.apple.com/documentation/activitykit) | Live Activities / Dynamic Island implementation |
| 11 | [AppTweak: Competitor Analysis](https://www.apptweak.com/en/aso-blog/step-by-step-guide-aso-competitor-analysis) | ASO keyword strategy |
| 12 | [Twinr: App Store Rejections 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) | 15% rejection rate; Guideline 2.1, 4.3 risks |
| 13 | [Product School: PRD Template](https://productschool.com/blog/product-strategy/product-template-requirements-document-prd) | Product plan structure |
| 14 | [Counterpoint Research 2024](https://www.counterpointresearch.com) | Dynamic Island installed base ~50M+ (US) |
