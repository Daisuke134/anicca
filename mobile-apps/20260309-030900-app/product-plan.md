# VagusReset — Product Plan

**Version:** 1.0 | **Date:** 2026-03-09 | **App:** VagusReset（迷走神経デイリーリセット）

---

## 1. Target User

### Primary

| 項目 | 内容 |
|------|------|
| Age | 25–45歳 |
| Occupation | デスクワーカー・子育て世代・フリーランサー |
| Pain Point | 慢性疲労・不安感・消化不良。病院に行くほどではないが毎日のストレスが体に出ている |
| Behavior | TikTok で「迷走神経」コンテンツを見て興味を持ち、センサー不要でスマホだけで試したい |
| Willingness to Pay | $4.99/月（Calm/Headspace の半額以下）なら試す意欲あり |

### Demographics

| 属性 | 値 |
|------|-----|
| Gender | 60% 女性 / 40% 男性（wellness app 業界比率。Source: Business of Apps H&F 2024） |
| Location | US（65%）/ CA, AU（20%）/ 日本（15%） |
| Device | iPhone（iOS 17+）。Apple Watch なし想定（センサー不要） |
| App habit | Calm, Headspace などサブスク経験あり。月$5-10の課金耐性あり |

### Market Size Evidence

| 指標 | 数値 | ソース |
|------|------|--------|
| 世界の不安障害罹患者 | 3億人超（世界人口の4%） | [WHO Mental Health Fact Sheet 2022](https://www.who.int/news/item/02-03-2022-covid-19-pandemic-triggers-25-increase-in-prevalence-of-anxiety-and-depression-worldwide) |
| COVID-19後の不安・うつ増加率 | **+25%**（2020-2021） | [WHO COVID-19 Mental Health Brief 2022](https://www.who.int/news/item/02-03-2022-covid-19-pandemic-triggers-25-increase-in-prevalence-of-anxiety-and-depression-worldwide) |
| Global H&F app revenue (2024) | $6.7B | [Business of Apps H&F Report 2025](https://www.businessofapps.com/data/health-fitness-app-market/) |
| Mental wellness app market CAGR | 17.8%（2022→2028） | [Grand View Research Mental Wellness App Market](https://www.grandviewresearch.com/industry-analysis/mental-wellness-market) |

**TAM/SAM/SOM 推定:**

| 市場区分 | 規模 | 根拠 |
|---------|------|------|
| TAM（全 H&F アプリ市場） | $6.7B/年 | Business of Apps 2024 |
| SAM（自律神経・ストレス管理アプリ） | ~$500M/年（TAMの~7%） | 業界推定 |
| SOM（年1%獲得目標） | $5M/年 | 保守的3年目標 |

---

## 2. Problem

### Core Problem

デジタル過多・慢性ストレスで自律神経が乱れた現代人に、センサー不要でスマホのみで今すぐ実践できる迷走神経リセット法が存在しない。

### Why Existing Solutions Fail

| 競合 | レビュー数 | 失敗理由 | ソース |
|------|----------|---------|--------|
| **NEUROFIT™** | 651件 | センサー依存（壊れると全機能停止）、課金後コンテンツ解放なし、二値判定で細かさがない | iTunes API実測 / App Store ★1-2レビュー（2026-03-09） |
| **Settle: Nervous System Reset** | 48件 | 汎用ツール（瞑想・タッピング等）で迷走神経特化でない | iTunes API実測（2026-03-09） |
| **Vagus Vibe** | 15件 | 振動デバイス前提。スマホ単体では機能しない | iTunes API実測（2026-03-09） |
| **Vagal Tones** | 0件 | ハードウェア（tVNS刺激装置）のコンパニオンアプリ。スタンドアローン不可 | iTunes API実測（2026-03-09） |

### Gap in Market

NEUROFIT が支配するカテゴリで唯一の「センサー不要・コンテンツ充実・無料で5エクササイズ体験可能」な迷走神経専用デイリーエクササイズアプリが存在しない。

---

## 3. Solution

### One-Liner

毎日2分の迷走神経リセット — 哼り・うがい・冷水で自律神経バランスを整えるルーティンアプリ。

### How It Works

```
ユーザー起動
    │
    ▼
オンボーディング（3画面）
    │ ← 何が解決するか説明
    ▼
ソフトペイウォール（[Maybe Later] で閉じれる）
    │ ← 無料: 5エクササイズ | 有料: 全20+
    ▼
ホーム画面（今日のルーティン）
    │
    ▼
エクササイズ選択 → タイマー付きガイド → 完了チェック
    │
    ▼
デイリーストリーク更新
    │
    ▼
翌日通知（リマインダー）
```

### Key Differentiators

| 特徴 | VagusReset | NEUROFIT™ | Settle |
|------|-----------|----------|-------|
| センサー要否 | **不要（スマホのみ）** | 必須（壊れると機能停止） | 不要 |
| 専門性 | **迷走神経特化** | 自律神経全般 | 神経系全般 |
| 無料体験 | **5エクササイズ体験** | 3日トライアルのみ | あり |
| コンテンツ量 | **20+エクササイズ** | 課金後コンテンツ少ない（★1レビュー指摘） | 瞑想・タッピング等混在 |
| 価格 | **$4.99/月** | 不明（$10+推定） | 不明 |

### Technology

| 技術 | 用途 | ルール |
|------|------|--------|
| SwiftUI | 全UI | iOS 17+ |
| UserDefaults | ストリーク・設定保存 | CoreData/CloudKit禁止（Rule） |
| RevenueCat SDK | サブスク管理 | RevenueCatUI禁止（Rule 20） |
| AVFoundation（再生音なし） | タイマー音 | カメラ・マイク禁止 |
| UserNotifications | デイリーリマインダー | — |

**Science Backing:** 迷走神経刺激は治療抵抗性うつ病・PTSD・炎症性腸疾患の有望な治療法として査読済み研究で実証済み。哼り・冷水・深呼吸は vagal tone を高める非侵襲的刺激法として確認されている。
[Source: PMC5859128 — Vagus Nerve as Modulator of the Brain-Gut Axis (Front. Psychiatry, 2018)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5859128/)

---

## 4. Monetization

### Pricing Strategy

| Tier | 価格 | 内容 |
|------|------|------|
| Free | $0 | エクササイズ5種（哼り・うがい・冷水・横隔膜・笑い）+ 7日ストリーク |
| Monthly | **$4.99/mo** ($4.99/月) | 全20+エクササイズ + 詳細ガイド + 通知カスタム + ストリーク無制限 |
| Annual | **$29.99/yr** ($29.99/年) | Monthly の全機能 + **50%割引（$4.99/mo × 12=$59.88 比）** |

### Pricing Justification

| 根拠 | 数値 | ソース |
|------|------|--------|
| H&F apps median monthly price | $7.73/月 | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) |
| H&F apps median annual price | $29.65/年 | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) |
| VagusReset monthly ($4.99) vs median | median の65%（範囲内: $3.87–$10.05） | Jake Mor Rule #15 |
| VagusReset annual ($29.99) vs median | 中央値+1.1%（範囲内: $25.20–$34.10） | RevenueCat SOSA 2025 |
| Annual apparent discount | 50%（$4.99×12=59.88 比）→ 購買意欲増 | [Jake Mor #17 Two-product strategy](https://www.revenuecat.com/blog/) |

**週換算:** Monthly $4.99/4.3週 = **$1.16/週**（コーヒー1杯以下）

### Revenue Model

| 指標 | 数値 | 根拠 |
|------|------|------|
| Year 1 install 目標 | 10,000 | TikTok SEO + ASO（低競合カテゴリ） |
| Free→Trial conversion | 15% | RevenueCat H&F median 15.8% |
| Trial→Paid conversion | 30% | RevenueCat H&F median 30.7% |
| Monthly users | 450 × $4.99 = **$2,245/月** | 保守的推定 |
| Annual users (30%) | 195 × $29.99/12 = **$487/月** | 保守的推定 |
| **Year 1 MRR target** | **~$2,732/月** | — |

### RevenueCat Integration

| 項目 | 設定 |
|------|------|
| SDK | `RevenueCat` via SPM（RevenueCatUI は禁止 — Rule 20） |
| Entitlement | `premium` |
| Offering | `default` |
| Packages | `$rc_monthly`（$4.99）+ `$rc_annual`（$29.99） |
| Paywall | 自前 SwiftUI `PaywallView`。`Purchases.shared.purchase(package:)` |
| Soft paywall | `[Maybe Later]` ボタンで閉じれる（Rule 20） |

---

## 5. MVP Scope

### Must Have

| # | 機能 | 説明 |
|---|------|------|
| M1 | エクササイズライブラリ | 20+エクササイズ（哼り・うがい・冷水・横隔膜呼吸・笑い等）静的 JSON |
| M2 | タイマー付きセッション | エクササイズごとのガイド + カウントダウンタイマー |
| M3 | ホーム画面（今日のルーティン） | 3-5エクササイズのデイリーセット。無料は5種のみ表示 |
| M4 | ソフトペイウォール | オンボーディング最終画面。[Maybe Later] で閉じれる。RevenueCatUI禁止 |
| M5 | デイリーストリーク | UserDefaults で連続日数管理 |
| M6 | 通知権限リクエスト | オンボーディング内でリマインダー設定（UserNotifications） |
| M7 | 設定画面 | サブスク管理 + 通知時間設定 + Upgrade→Paywall遷移 |
| M8 | オンボーディング（3画面） | 問題提示 → 解決策 → ソフトペイウォール |

### Should Have

| 機能 | 説明 |
|------|------|
| 完了アニメーション | セッション完了時の達成感 UI |
| 進捗カレンダー | 月次チェックイン履歴（有料機能） |

### Won't Have（理由付き）

| 機能 | 理由 |
|------|------|
| WidgetKit ウィジェット | Extension Target 追加、Maestro E2E テスト困難（PROHIBITED — Reference Fix #10） |
| Dynamic Island / Live Activities | Extension 必要、テスト困難（PROHIBITED） |
| HealthKit 連携 | 審査で追加説明必要（PROHIBITED） |
| カメラ・マイク | プライバシー審査厳格化（PROHIBITED） |
| Sign in with Apple | Maestro E2E 自動化不可（PROHIBITED） |
| CoreData / CloudKit sync | UserDefaults で十分（PROHIBITED） |
| AI / LLM 機能 | コスト発生 + iOS 26+ 限定（Rule 23） |
| Apple Watch 対応 | HealthKit 不使用でWatch の価値なし |

### Technical Architecture

```
VagusReset/
├── App/
│   ├── VagusResetApp.swift        # @main, RevenueCat configure
│   └── ContentView.swift          # RootView, onboarding state
├── Config/
│   └── VagusReset.xcconfig        # RC_PUBLIC_KEY (not hardcoded)
├── Models/
│   ├── Exercise.swift             # Codable struct
│   └── ExerciseData.json          # 20+ exercises static content
├── ViewModels/
│   ├── OnboardingViewModel.swift
│   ├── HomeViewModel.swift
│   ├── SessionViewModel.swift     # Timer logic
│   └── SettingsViewModel.swift
├── Views/
│   ├── Onboarding/
│   │   ├── OnboardingView.swift
│   │   └── PaywallView.swift      # Custom SwiftUI (RevenueCatUI禁止)
│   ├── Home/
│   │   ├── HomeView.swift
│   │   └── ExerciseCardView.swift
│   ├── Session/
│   │   ├── SessionView.swift
│   │   └── TimerView.swift
│   └── Settings/
│       └── SettingsView.swift
├── Services/
│   ├── SubscriptionService.swift  # Protocol + DI (testable)
│   └── StreakService.swift        # UserDefaults wrapper
└── Tests/
    └── VagusResetTests/
        ├── SubscriptionServiceTests.swift
        ├── StreakServiceTests.swift
        └── SessionViewModelTests.swift
```

### Localization

| 言語 | App Name | Subtitle | Description キーワード |
|------|---------|---------|---------------------|
| en-US | VagusReset | Vagus Nerve Daily Reset | vagus nerve, nervous system, stress relief, anxiety |
| ja | VagusReset | 迷走神経デイリーリセット | 迷走神経, 自律神経, ストレス解消, リラックス |

---

## 6. App Identity

### App Details

| 項目 | 値 |
|------|-----|
| App Name | **VagusReset** |
| Bundle ID | `com.aniccafactory.vagusreset` |
| App Title（ASO） | **Vagus Nerve Reset - VagusReset** |
| Subtitle | Calm Your Nervous System Daily |
| Category | Health & Fitness |
| Age Rating | 4+ |
| iTunes Name Check | ✅ 0 exact matches（"VagusReset" 検索 — verified 2026-03-09） |
| ✅ iTunes Name Check 2 | ✅ 0 exact matches（"Vagus Reset" 検索 — verified 2026-03-09） |

**App Title フォーマット根拠:**
[Source: Jake Mor #53 — App title format: "Keyword - AppName"](https://www.revenuecat.com/blog/)
例: `"Vagus Nerve Reset - VagusReset"` ← 検索キーワード + ブランド名

### ASO Keywords

| Priority | Keyword（en-US） | 根拠 |
|---------|----------------|------|
| 1 | vagus nerve | #vagusnerve TikTok 1.5M+ views; NEUROFIT 651 reviews = 低競合 |
| 2 | nervous system reset | Settle 48件 = 低競合、高検索意図 |
| 3 | vagal tone | 専門キーワード、低競合 |
| 4 | stress relief | H&F の汎用高検索ワード |
| 5 | anxiety relief | 300M+ 罹患者（WHO） |
| 6 | parasympathetic | 専門性を示す差別化ワード |
| 7 | daily routine | habit forming コンテキスト |
| 8 | autonomic nervous | 日英共通で上位表示狙い |

---

## 7. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **App Store リジェクト: Guideline 2.1（App Completeness）** | HIGH — 提出遅延 | Maestro E2E 6+フロー。全画面テスト済み。fastlane test PASS 確認必須 |
| **App Store リジェクト: ITMS-91053（Privacy Manifest）** | HIGH — 即拒否 | PrivacyInfo.xcprivacy 必須。NSPrivacyTracking=false。SDK 依存 privacy manifest 確認 |
| **競合が機能コピー（NEUROFITがセンサー不要版追加）** | MEDIUM — 差別化消失 | コンテンツ量（20+）とUX品質で先行。価格優位性維持 |
| **低 trial→paid conversion（<10%）** | HIGH — 収益未達 | ソフトペイウォール + 価値提示強化。onboarding A/Bテスト（v1.1） |
| **TikTokトレンド終息（vagus nerve バズが下火）** | MEDIUM — UA停滞 | ASO（App Store自然検索）をメイン獲得チャネルに。TikTok依存しない |
| **RevenueCat SDK 審査引っかかり** | LOW — まれ | Real SDK 使用（Mock禁止）。sandbox でテスト済み確認 |
| **App Store 4.3 Spam リジェクト** | MEDIUM — シリーズ全体リスク | アプリ名・説明・UI を十分に差別化。テンプレ感排除 |
| **ユーザーリテンション低下（1週間で離脱）** | HIGH — LTV低下 | デイリーストリーク + 通知リマインダー。7日以内に通知許可取得 |

---

## Sources Summary

| # | Source | What It Supports |
|---|--------|-----------------|
| 1 | [WHO COVID-19 Mental Health Brief 2022](https://www.who.int/news/item/02-03-2022-covid-19-pandemic-triggers-25-increase-in-prevalence-of-anxiety-and-depression-worldwide) | +25% anxiety/depression. 市場需要の根拠 |
| 2 | [PMC5859128 — Vagus Nerve as Modulator (Front. Psychiatry, 2018)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5859128/) | 迷走神経刺激の科学的有効性。うつ・PTSDへの有望治療 |
| 3 | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | H&F median $7.73/月, $29.65/年。価格設定根拠 |
| 4 | [RevenueCat SOSA 2026](https://www.revenuecat.com/state-of-subscription-apps/) | 「vibe coding era apps account for just 3%」— シンプル設計の価値 |
| 5 | [Jake Mor — Revenue Cat Blog](https://www.revenuecat.com/blog/) | #15 クリーン週額変換。#17 Two-product strategy。#53 App title format |
| 6 | [Apple iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) | 競合レビュー数実測。名前一意性確認 |
| 7 | iTunes API 実測（2026-03-09） | NEUROFIT 651件, Settle 48件, Vagus Vibe 15件, Vagal Tones 0件 |
| 8 | [Apify TikTok Hashtag Scraper 実測（2026-03-09）](https://apify.com/clockworks/tiktok-hashtag-scraper) | #vagusnerve 1.5M+ views。トレンド実証 |
| 9 | [Grand View Research Mental Wellness App Market](https://www.grandviewresearch.com/industry-analysis/mental-wellness-market) | Market CAGR 17.8%（2022→2028）。TAM根拠 |
| 10 | [Business of Apps H&F Report 2025](https://www.businessofapps.com/data/health-fitness-app-market/) | Global H&F app revenue $6.7B（2024）。市場規模 |
| 11 | [Twinr: App Store Rejections 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) | 15%の申請が却下。Guideline 2.1 = 40%以上。リスク根拠 |
| 12 | [Apple CFBundleIdentifier Docs](https://developer.apple.com/documentation/bundleresources/information_property_list/cfbundleidentifier) | Bundle ID フォーマット: com.aniccafactory.vagusreset |
| 13 | [ProductPlan: MoSCoW](https://www.productplan.com/glossary/moscow-prioritization/) | MVP スコープの MoSCoW 分類根拠 |
