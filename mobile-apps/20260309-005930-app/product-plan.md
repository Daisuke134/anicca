# LumaRed — Product Plan

Source: [Product School: PRD Template](https://productschool.com/blog/product-strategy/product-template-requirements-document-prd) — 「Essential sections: Overview, Success Metrics, Messaging, Timeline, Personas.」
Source: [Atlassian: PRD](https://www.atlassian.com/agile/product-management/requirements) — 「Include goals, assumptions, user stories, design, clear out-of-scope items.」

Date: 2026-03-09 | App: LumaRed | Status: Draft

---

## 1. Target User

### Primary Persona

| 項目 | 詳細 |
|------|------|
| Name | "Biohacker Kenji / Health-Conscious Sarah" |
| Age | 25–45歳 |
| Demographics | 健康意識が高い都市部在住者。デバイス所持者（赤色光パネル $200–$1,000 投資済み） |
| Pain Point | 高価な赤色光デバイスを「購入したが使い方がわからない」「プロトコルが複雑でどの部位に何分当てればいいか不明」 |
| Behavior | TikTok / Reddit / YouTube でセルフケア情報収集。Andrew Huberman / Ben Greenfield を視聴 |
| Willingness to Pay | 月 $5–15。既に健康サプリ・デバイスに月 $100+ 支出 |

### Market Size Evidence

| ソース | データ | 意味 |
|--------|-------|------|
| [Grand View Research: Red Light Therapy Market](https://www.grandviewresearch.com/industry-analysis/photobiomodulation-therapy-market-report) — 「The global photobiomodulation therapy market size was valued at USD 354.3 million in 2022 and is expected to expand at a CAGR of 5.6% from 2023 to 2030.」 | TAM $354M (2022)、2030年 $556M 予測 | 急成長市場 |
| [Mordor Intelligence: Red Light Therapy Device Market](https://www.mordorintelligence.com/industry-reports/red-light-therapy-device-market) — 「The Red Light Therapy Device Market is projected to grow from USD 0.55 billion in 2024 to USD 1.13 billion by 2029, at a CAGR of 15.47%.」 | デバイス市場 $550M（2024）、2029年 $1.13B | 15% CAGR = ユーザーベース急拡大 |
| iTunes Search API (実行: 2026-03-09) | "red light therapy" 検索: 専用アプリ上位でも 69 reviews 最大 | App Store での供給不足が明確 |

---

## 2. Problem

### Core Problem

赤色光デバイス（$200〜$1,000）を購入したユーザーの多くが、**部位別プロトコル・照射時間・距離・適切な波長の使い方がわからず、デバイスをほとんど使わないまま放置している。**

### Why Existing Solutions Fail

| 競合 | Reviews | 失敗理由 |
|------|---------|---------|
| Redd Light Therapy | 69 | 汎用ウェルネスアプリ。赤色光専用プロトコルなし。セッション管理機能なし |
| SUNI: Red Light Therapy | 2 | iPhoneスクリーン自体を赤色光として使用（デバイス非対応）。プロトコルガイドなし |
| Red Light For Your Eyes | 18 | 目専用のみ。部位別プロトコルなし |
| Vital Red Light | 1 | ほぼ機能なし。放置状態 |
| メーカー公式アプリ（例: MITO LIGHT） | 0–2 | デバイス制御のみ。プロトコルガイド・ログ機能なし |

Source: [iTunes Search API](https://itunes.apple.com/search) — 実行: 2026-03-09

### Gap in Market

「部位別エビデンスベースのプロトコルライブラリ × セッションタイマー × 効果ログ」を提供する赤色光療法専用コンパニオンアプリが存在しない。

---

## 3. Solution

### One-Liner

赤色光療法（フォトバイオモジュレーション）のエビデンスベース・プロトコルガイド＆セッショントラッカー。

### How It Works

```
ユーザーがアプリを起動
    ↓
部位を選択（顔 / 関節 / 傷 / 背中 / 全身）
    ↓
対応プロトコルが表示（波長 / 距離 / 時間 / 頻度）
    ↓
タイマー開始（BackgroundTasks 対応 — バックグラウンドでも動作）
    ↓
セッション終了 → ログ自動保存（日付 / 部位 / 時間 / 強度）
    ↓
ダッシュボードで連続日数・累計時間を可視化
```

### Key Differentiators

| 機能 | LumaRed | Redd Light Therapy | Red Light For Your Eyes |
|------|---------|---------------------|------------------------|
| 部位別プロトコル | ✅ 5部位 (顔・関節・傷・背中・全身) | ❌ なし | ❌ 目のみ |
| タイマー（BG対応） | ✅ BackgroundTasks | ❌ なし | ❌ なし |
| セッションログ | ✅ 無制限（Premium） | ❌ なし | ❌ なし |
| エビデンス引用 | ✅ 各プロトコルに研究引用 | ❌ なし | ⚠️ 1研究のみ |
| 価格 | Free + $4.99/月 | Free (機能なし) | $4.99 (一括) |

### Technology

Source: [Apple Developer: BackgroundTasks](https://developer.apple.com/documentation/backgroundtasks) — 「Use BGProcessingTaskRequest for deferrable processing and BGAppRefreshTaskRequest for keeping your content up to date.」
Source: [Apple Developer: SwiftUI Charts](https://developer.apple.com/documentation/charts) — 「Build charts in SwiftUI with Swift Charts framework.」

| フレームワーク | 用途 |
|-------------|------|
| SwiftUI | 全UI（iOS 17+ ネイティブ） |
| BackgroundTasks | バックグラウンドセッションタイマー |
| SwiftUI Charts | セッション履歴の可視化 |
| UserDefaults | セッションログ保存（シンプル・確実） |
| UserNotifications | セッション完了・リマインダー通知 |
| StoreKit 2 + RevenueCat | サブスクリプション管理 |

---

## 4. Monetization

### Pricing Strategy

Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「H&F median: $7.73/mo, $29.65/yr. Higher prices = higher trial conversion.」
Source: jake-mor.md #17 — 「Two-product strategy: trial-less monthly + trialed annual at 50% apparent discount.」

| Tier | Price | 内容 | 換算 |
|------|-------|------|------|
| Free | $0 | 3プロトコル（顔・関節・傷）+ 7日ログ | — |
| Monthly | **$4.99/月** | 全5プロトコル + 無制限ログ + 進捗ダッシュボード | ¥0.17/日 |
| Annual | **$29.99/年** | Monthly と同じ + 50%割引表示 | $2.50/月相当 |

### Pricing Justification

| ソース | 根拠 |
|--------|------|
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「H&F median: $7.73/mo」 | $4.99 = median の 65%（範囲内 ✅） |
| [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「H&F annual median: $29.65/yr」 | $29.99 = median ± 1% ✅ |
| jake-mor.md #15 — 「Prices aren't random — they convert to clean weekly/monthly amounts.」 | $29.99/年 = $0.58/週（クリーンな数字） |
| Red Light For Your Eyes — $4.99 一括 | 競合の一括価格 = 当社月額。サブスク優位性を訴求 |

### Revenue Model

| シナリオ | 月間ダウンロード | Paid 転換率 | Monthly:Annual | MRR |
|---------|----------------|------------|----------------|-----|
| Conservative | 500 | 3% | 70:30 | $150 |
| Base | 2,000 | 4% | 60:40 | $640 |
| Optimistic | 5,000 | 5% | 50:50 | $1,875 |

### RevenueCat Integration

| 項目 | 値 |
|------|-----|
| SDK | RevenueCat iOS SDK（SPM） |
| RevenueCatUI | **禁止（Rule 20）** |
| Paywall | 自前 SwiftUI PaywallView |
| [Maybe Later] ボタン | 必須（Rule 20 — ソフトペイウォール） |
| Entitlement | `premium` |
| Offering | `default` |
| Monthly Product | `lumaRed_monthly_499` |
| Annual Product | `lumaRed_annual_2999` |

---

## 5. MVP Scope

### Must Have

| # | Feature | Description |
|---|---------|-------------|
| 1 | 部位別プロトコルライブラリ | 5部位（顔・関節・傷・背中・全身）× 波長/距離/時間/頻度。静的コンテンツ |
| 2 | セッションタイマー | カウントダウン。BackgroundTasks対応（バックグラウンド動作） |
| 3 | セッションログ | 日付/部位/時間の自動保存。Free=7日、Premium=無制限 |
| 4 | ソフトペイウォール | オンボーディング最終画面。[Maybe Later] で閉じられる。自前 SwiftUI PaywallView |
| 5 | 通知リマインダー | セッション完了通知 + 翌日リマインダー |
| 6 | 連続日数 / 累計時間 | シンプルなダッシュボード（SwiftUI Charts） |

### Won't Have

| Feature | Reason |
|---------|--------|
| Live Activities / Dynamic Island | WidgetKit Extension 必要 → テスト困難（PROHIBITED） |
| HealthKit 連携 | 権限管理が複雑 → 審査リスク（PROHIBITED） |
| カメラ（写真比較） | プライバシー審査厳化 → v1.1候補（PROHIBITED） |
| LLM / AI 推奨 | APIコスト発生 → Rule 23 違反（PROHIBITED） |
| バックエンドサーバー | インフラコスト → PROHIBITED |
| CloudKit Sync | デバッグ困難 → UserDefaults で十分（PROHIBITED） |
| Sign in with Apple | Maestro E2E 自動化不可（PROHIBITED） |
| Apple Watch 連携 | watchOS Target 追加 → Scope overflow → v1.1候補 |

### Technical Architecture

```
LumaRed/
├── App/
│   ├── LumaRedApp.swift          # @main, RevenueCat init
│   └── ContentView.swift         # Tab navigation
├── Models/
│   ├── Protocol.swift            # 部位別プロトコルモデル
│   ├── Session.swift             # セッションログモデル
│   └── ProtocolLibrary.swift     # 静的プロトコルデータ
├── Services/
│   ├── SessionService.swift      # UserDefaults ログ管理
│   ├── SubscriptionService.swift # RevenueCat Protocol + DI
│   └── NotificationService.swift # UserNotifications
├── ViewModels/
│   ├── HomeViewModel.swift
│   ├── TimerViewModel.swift
│   └── DashboardViewModel.swift
├── Views/
│   ├── Onboarding/
│   │   ├── OnboardingView.swift
│   │   └── PaywallView.swift      # 自前 SwiftUI（RevenueCatUI 禁止）
│   ├── Home/
│   │   ├── HomeView.swift
│   │   └── ProtocolCardView.swift
│   ├── Timer/
│   │   └── TimerView.swift
│   ├── Dashboard/
│   │   └── DashboardView.swift
│   └── Settings/
│       └── SettingsView.swift
├── Resources/
│   ├── Localizable.xcstrings     # en-US + ja
│   └── PrivacyInfo.xcprivacy
└── Tests/
    └── LumaRedTests/
```

### Localization

| Key | en-US | ja |
|-----|-------|-----|
| `app.name` | LumaRed | LumaRed |
| `tab.home` | Protocols | プロトコル |
| `tab.timer` | Timer | タイマー |
| `tab.dashboard` | Dashboard | 記録 |
| `tab.settings` | Settings | 設定 |
| `paywall.title` | Start Your Glow Journey | 光療法を始めよう |
| `paywall.maybe_later` | Maybe Later | あとで |
| `paywall.monthly` | $4.99 / month | 月額 $4.99 |
| `paywall.annual` | $29.99 / year (Save 50%) | 年額 $29.99（50%お得） |
| `protocol.face` | Face & Skin | 顔・肌 |
| `protocol.joint` | Joint & Muscle | 関節・筋肉 |
| `protocol.wound` | Wound Healing | 傷の回復 |
| `protocol.back` | Back & Spine | 背中・脊椎 |
| `protocol.full` | Full Body | 全身 |

---

## 6. App Identity

### Name & Bundle ID

| 項目 | 値 |
|------|-----|
| App Name | LumaRed |
| Subtitle | Red Light Therapy Timer |
| App Title (ASO) | `Red Light Therapy - LumaRed` |
| Bundle ID | `com.aniccafactory.lumared` |
| Category | Health & Fitness |
| Secondary Category | — |
| Age Rating | 4+ |

### iTunes Name Check

| 候補 | 完全一致件数 | 判定 |
|------|------------|------|
| LumaRed | 0 | ✅ 採用（verified 2026-03-09） |

### ASO Keywords

Source: [AppTweak](https://www.apptweak.com/en/aso-blog/step-by-step-guide-aso-competitor-analysis) — 「Examine keywords in titles, subtitles, descriptions; check update frequency.」

| Priority | Keyword | Rationale |
|----------|---------|-----------|
| 1 | red light therapy | Core category keyword |
| 2 | photobiomodulation | Scientific term, less competition |
| 3 | RLT timer | Action-specific, biohacker slang |
| 4 | red light protocol | Protocol-seekers intent |
| 5 | biohacking | #biohacking 4.1M TikTok plays |
| 6 | infrared therapy | Adjacent wavelength category |
| 7 | wellness tracker | Broader health category |
| 8 | light therapy session | Session-specific query |

---

## 7. Risk Assessment

Source: [Full Scale: Risk Assessment](https://fullscale.io/blog/risk-assessment-for-startups/) — 「Companies with formal risk plans experience 30% fewer operational disruptions.」
Source: [Twinr: App Store Rejections 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) — 「Privacy violations = leading cause. 15% of submissions rejected. Over 40% of unresolved issues = Guideline 2.1 App Completeness.」

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **技術**: BackgroundTasks がiOS 17で動作しない | High | BGTaskScheduler.shared.register で事前テスト + Maestro E2E で検証 |
| **市場**: 競合が急成長してレビュー数が100倍になる | Medium | 低競合市場への先行投入。ASO で上位確保 |
| **App Store リジェクト**: Privacy Manifest 未申告 (ITMS-91053) | High | PrivacyInfo.xcprivacy を必ず追加。greenlight preflight でCRITICAL=0確認 |
| **App Store リジェクト**: Guideline 2.1 App Completeness | High | Maestro E2E でonboarding / timer / paywall フロー全通し検証 |
| **収益**: trial-to-paid 転換率が低い (<2%) | High | ソフトペイウォール + [Maybe Later] でUX損なわず + Annual 50%割引訴求 |
| **ユーザー**: 7日後チャーン急増 | Medium | 通知リマインダー（翌日 + 週次）+ 連続日数ゲーミフィケーション |
| **技術**: RevenueCat 初期設定ミスで購入できない | High | US-005b で事前検証。StoreKit テスト環境で必ず動作確認 |

---

## Sources Summary

| # | Source | What It Supports |
|---|--------|-----------------|
| 1 | [Grand View Research: RLT Market](https://www.grandviewresearch.com/industry-analysis/photobiomodulation-therapy-market-report) — 「$354.3M (2022), CAGR 5.6%」 | TAM |
| 2 | [Mordor Intelligence: RLT Device Market](https://www.mordorintelligence.com/industry-reports/red-light-therapy-device-market) — 「$0.55B (2024) → $1.13B (2029), CAGR 15.47%」 | TAM 成長率 |
| 3 | [iTunes Search API](https://itunes.apple.com/search) — 実行 2026-03-09 | 競合調査・名前チェック |
| 4 | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「H&F median: $7.73/mo, $29.65/yr」 | 価格設定根拠 |
| 5 | jake-mor.md #17 — 「Two-product strategy: trial-less monthly + trialed annual at 50% discount」 | 価格戦略 |
| 6 | jake-mor.md #53 — 「App title format: Keyword - AppName」 | ASO タイトル |
| 7 | [Apple Developer: BackgroundTasks](https://developer.apple.com/documentation/backgroundtasks) — 「BGProcessingTaskRequest for deferrable processing」 | タイマー技術選定 |
| 8 | [Apple Developer: SwiftUI Charts](https://developer.apple.com/documentation/charts) — 「Build charts in SwiftUI」 | ダッシュボード技術選定 |
| 9 | [AppTweak: ASO Competitor Analysis](https://www.apptweak.com/en/aso-blog/step-by-step-guide-aso-competitor-analysis) — 「Examine keywords in titles, subtitles, descriptions」 | ASO キーワード戦略 |
| 10 | [Twinr: App Store Rejections 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) — 「15% of submissions rejected. Guideline 2.1 over 40%」 | リスク評価 |
| 11 | [Full Scale: Risk Assessment](https://fullscale.io/blog/risk-assessment-for-startups/) — 「30% fewer operational disruptions with formal plans」 | リスク管理方針 |
| 12 | [Product School: PRD Template](https://productschool.com/blog/product-strategy/product-template-requirements-document-prd) | ドキュメント構造 |
| 13 | [ProductPlan: MoSCoW](https://www.productplan.com/glossary/moscow-prioritization/) — 「Must Have: Critical for current delivery」 | MVP 分類手法 |
