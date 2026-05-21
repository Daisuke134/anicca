# LymphaFlow — Product Plan

Source: [Product School: PRD Template](https://productschool.com/blog/product-strategy/product-template-requirements-document-prd) — 「Essential sections: Overview, Success Metrics, Messaging, Timeline, Personas.」
Source: [Atlassian: PRD](https://www.atlassian.com/agile/product-management/requirements) — 「Include goals, assumptions, user stories, design, clear out-of-scope items.」

---

## 1. Target User

### Primary

| 項目 | 値 |
|------|-----|
| セグメント | 25-45歳女性、在宅勤務者・術後患者・美容意識の高い層 |
| 痛みポイント | むくみ・疲労感・術後浮腫。リンパマッサージを試したいが正確な手順を覚えられない |
| 行動特性 | TikTokでリンパマッサージ動画を見て実践を試みる。#lymphaticdrainage で5.5B回再生確認済み |
| 支払い意欲 | 月$4.99-$9.99 (美容・ウェルネスカテゴリ平均と比較して低リスク価格帯) |

### Demographics

| 属性 | 値 |
|------|-----|
| 年齢 | 25-45歳 |
| 性別 | 女性 (推定70%) |
| 地域 | 米国・日本・カナダ・英国（英語・日本語ローカライズ） |
| デバイス | iPhone (iOS 17+) |
| ライフスタイル | 在宅勤務または産後・術後リカバリー中 |

### Market Size Evidence

Source: [Grand View Research: Lymphedema Treatment Market](https://www.grandviewresearch.com/industry-analysis/lymphedema-treatment-market) — 「The global lymphedema treatment market size was valued at USD 1.18 billion in 2023 and is projected to grow at a CAGR of 6.1% from 2024 to 2030.」

Source: [Apify TikTok Hashtag Scraper](https://apify.com/clockworks/tiktok-hashtag-scraper) — Run ID: 1O5ifI6T5EAz2i7iY — 「#lymphaticdrainage: 5,500,000,000 total views（2026-03-08実行）」

| 指標 | 値 | ソース |
|------|-----|-------|
| #lymphaticdrainage TikTok views | 5.5B（55億） | Apify TikTok Scraper 2026-03-08 |
| 世界リンパ浮腫治療市場 | $1.18B (2023) + CAGR 6.1% | Grand View Research |
| 米国ウェルネスアプリ市場 | $4.2B (2025推定) | Statista Mobile Health |
| TAM（全ウェルネスアプリユーザー） | $4.2B | Statista |
| SAM（リンパ・マッサージ特化） | $42M（TAMの1%） | 独自推計 |
| SOM（初年度目標） | $420K（SAMの1%） | 独自推計 |

---

## 2. Problem

### Core Problem

リンパドレナージュはむくみ・免疫改善・術後リカバリーに有効として急速に普及しているが、一般消費者が毎日正確に実践できるデジタルガイドアプリが事実上存在しない。

### Why Existing Solutions Fail

Source: [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) — 2026-03-08実行結果

| 競合アプリ | 評価 | レビュー数 | 問題点 |
|-----------|------|---------|--------|
| Lymphia: Lymphatic Exercises | ★5.0 | 2 | アプリが空白同然。機能が最小限で継続性なし |
| Kylee Lymphedema Assistant | ★4.8 | 914 | Bluetoothデバイス専用。一般消費者が使えない |
| LymphaTrack | ★4.0 | 3 | 機能不明確。ユーザーレビューから「使いにくい」 |
| Body Roll Studio | ★5.0 | 45 | フォームローラー道具前提。手技マッサージ非対応 |
| Thoracic Lymph Node Map | ★4.8 | 25 | 医療専門家向け解剖図。セルフケア手順なし |

### Gap in Market

一般消費者が道具なし・デバイスなし・知識なしで、TikTokで見たリンパマッサージを毎日正確に実践できるガイドアプリが、2026年3月時点で存在しない。

---

## 3. Solution

### One-Liner

TikTok5.5B回再生の#lymphaticdrainage トレンドに特化した、デバイス不要・手順通りに進めるだけのセルフリンパマッサージガイドアプリ。

### How It Works

```
ユーザー起動
    ↓
ルーティン選択（顔 / 首・鎖骨 / 腕 / 腹部 / 脚）
    ↓
ステップ表示（イラスト + 解説テキスト）
    ↓
タイマーカウント（部位ごと30-60秒）
    ↓
次ステップへ（自動遷移）
    ↓
セッション完了 → ストリーク更新 + 記録保存
    ↓
[有料] 全12部位へのアクセス解放
```

### Key Differentiators

| 機能 | LymphaFlow（自社） | Kylee（競合A） | Lymphia（競合B） |
|------|-----------------|--------------|---------------|
| 道具不要 | ✅ | ❌（Bluetooth必須） | ✅ |
| ステップバイステップガイド | ✅ | ❌ | ⚠️ 最小限 |
| タイマー統合 | ✅ | ❌ | ❌ |
| ストリーク追跡 | ✅ | ❌ | ❌ |
| 一般消費者向けデザイン | ✅ | ❌（医療用途） | ⚠️ |
| 価格 | $4.99/月 | 無料(デバイス購入要) | 無料 |

### Technology

Source: [Apple Developer: SwiftUI](https://developer.apple.com/xcode/swiftui/) — 「Build beautiful apps with a declarative Swift syntax.」

| 技術 | 用途 |
|------|------|
| SwiftUI | 全UI（iOS 17+） |
| UserDefaults | セッション記録・ストリーク |
| UserNotifications | 毎日リマインダー |
| RevenueCat SDK | サブスクリプション管理 |
| Core Animation | ステップ遷移アニメーション |

---

## 4. Monetization

### Pricing Strategy

Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「H&F median: $7.73/mo, $29.65/yr. Higher prices = higher trial conversion.」
Source: [jake-mor.md #17](https://jakemor.com) — 「Two-product strategy: trial-less monthly + trialed annual at 50% apparent discount.」
Source: [jake-mor.md #15](https://jakemor.com) — 「Prices aren't random — they convert to clean weekly/monthly amounts.」

| プラン | 価格 | 内容 |
|--------|------|------|
| Free | $0 | 顔・首の基本ルーティン3種（毎日利用可） |
| Monthly | **$4.99/月** | 全12部位 + 目的別プログラム（むくみ/免疫/術後） + 進捗ログ |
| Annual | **$29.99/年** | Monthlyと同内容。週換算 $0.58/週。Monthlyの50%OFF表示 |

### Pricing Justification

| 根拠 | 値 | ソース |
|------|-----|-------|
| H&F カテゴリ中央値 (月額) | $7.73 | RevenueCat SOSA 2025 |
| $4.99 = H&F中央値の65% | 50-130%範囲内 ✅ | RevenueCat |
| H&F カテゴリ中央値 (年額) | $29.65 | RevenueCat SOSA 2025 |
| $29.99 vs $29.65 | 差異+1.2%（±15%内） ✅ | RevenueCat |
| Annual apparent discount | $4.99×12=$59.88 → $29.99 = 50.0% off ✅ | Jake Mor #17 |
| 週換算 | $29.99÷52 = $0.58/週（クリーン） ✅ | Jake Mor #15 |

### Revenue Model

| シナリオ | MRR（6ヶ月後） | 前提 |
|---------|--------------|------|
| 保守 | $500/月 | 100 DAU × 5% conversion |
| 標準 | $2,000/月 | 500 DAU × 8% conversion |
| 楽観 | $5,000/月 | 1,500 DAU × 10% conversion |

### RevenueCat Integration

Source: [RevenueCat SDK Docs](https://www.revenuecat.com/docs/getting-started/installation/ios) — 「Add RevenueCat as a Swift Package Manager dependency.」

| コンポーネント | 設定値 |
|-------------|-------|
| SDK | RevenueCat (Swift Package Manager) |
| Entitlement | `pro` |
| Offering | `default` |
| Monthly Package | `$rc_monthly` — $4.99/month (no trial) |
| Annual Package | `$rc_annual` — $29.99/year (7-day trial) |
| Paywall方式 | 自前SwiftUI PaywallView（RevenueCatUI禁止 — Rule 20）|
| ソフトペイウォール | [Maybe Later] ボタン必須（Rule 20）|

---

## 5. MVP Scope

Source: [ProductPlan: MoSCoW](https://www.productplan.com/glossary/moscow-prioritization/) — 「Must Have: Critical for current delivery. Won't Have: Agreed as out of scope.」
Source: [Uptech MVP Guide](https://www.uptech.team/blog/build-an-mvp) — 「Solve one core problem. Focus on what matters most to your users.」

### Must Have

| # | Feature | Description |
|---|---------|-------------|
| 1 | ルーティン選択画面 | 顔・首・鎖骨の3ルーティン（Free）、全12部位（Pro） |
| 2 | ステップバイステップガイド | イラスト + テキスト説明、各ステップのタイマー（30-60秒） |
| 3 | Morning/Evening プログラム | 朝5分・夜10分の2プリセットプログラム |
| 4 | セッション記録 + ストリーク | UserDefaultsで毎日の記録、連続日数表示 |
| 5 | PaywallView（ソフトペイウォール） | 自前SwiftUI + [Maybe Later]ボタン。全身12部位アンロック |
| 6 | オンボーディング | アプリ説明3スクリーン → 通知許可 → PaywallView |
| 7 | 毎日リマインダー | UserNotificationsで朝/夜の通知 |
| 8 | 設定画面 | サブスク管理、通知設定、Upgrade → PaywallView |

### Won't Have

| Feature | Reason |
|---------|--------|
| HealthKit統合 | 権限管理複雑化。MVP範囲外（Scope overflow — v1.1候補） |
| 動画コンテンツ | アプリサイズ肥大・審査リスク増加 |
| ソーシャル共有機能 | バックエンド必須 → Rule 23違反 |
| AI個別化推薦 | Rule 23（AI API禁止）。コスト発生 |
| WidgetKit拡張 | Extension Target複雑化（PROHIBITED） |
| Dynamic Island | WidgetKit Extension必須（PROHIBITED） |
| Sign in with Apple | Maestro E2E自動化不可（PROHIBITED） |
| CloudKit同期 | 複雑、デバッグ困難（PROHIBITED） |
| カメラ・マイク | プライバシー審査厳格化リスク |

### Technical Architecture

```
LymphaFlow/
├── App/
│   ├── LymphaFlowApp.swift          # @main, RevenueCat.configure()
│   └── ContentView.swift            # NavigationStack root
├── Models/
│   ├── Routine.swift                # struct Routine: Identifiable
│   ├── Step.swift                   # struct Step（name, duration, illustration）
│   └── SessionRecord.swift          # struct SessionRecord（date, routineId）
├── Services/
│   ├── SubscriptionServiceProtocol.swift
│   ├── SubscriptionService.swift    # RevenueCat実装
│   ├── SessionStore.swift           # UserDefaults CRUD
│   └── NotificationService.swift   # UNUserNotificationCenter
├── ViewModels/
│   ├── OnboardingViewModel.swift
│   ├── HomeViewModel.swift
│   ├── TimerViewModel.swift
│   └── SettingsViewModel.swift
├── Views/
│   ├── Onboarding/
│   │   ├── OnboardingView.swift
│   │   ├── OnboardingPageView.swift
│   │   └── NotificationPermissionView.swift
│   ├── Home/
│   │   ├── HomeView.swift
│   │   └── RoutineCardView.swift
│   ├── Session/
│   │   ├── SessionView.swift
│   │   └── StepView.swift
│   ├── Progress/
│   │   └── ProgressView.swift
│   ├── Settings/
│   │   └── SettingsView.swift
│   └── Paywall/
│       └── PaywallView.swift        # 自前SwiftUI（RevenueCatUI禁止）
├── Resources/
│   ├── Assets.xcassets/
│   ├── Localizable.xcstrings        # en-US + ja
│   ├── PrivacyInfo.xcprivacy
│   └── Data/
│       └── routines.json            # 静的コンテンツ（AI不使用）
└── Tests/
    └── LymphaFlowTests/
```

### Localization

| 言語 | ロケール | 対象 |
|------|--------|------|
| English (US) | en-US | App Store 主要市場 |
| Japanese | ja | App Store 日本市場 |

---

## 6. App Identity

### App Name

Source: [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) — 2026-03-08実行

| 項目 | 値 |
|------|-----|
| App Name | **LymphaFlow** |
| iTunes Name Check | ✅ 0 exact matches（`LymphaFlow` 完全一致 = 0件, 2026-03-08確認） |
| App Title (ASO) | **Lymphatic Massage - LymphaFlow** |
| Subtitle | Self Lymph Drainage Guide |
| Bundle ID | `com.aniccafactory.lymphaflow` |
| Category | Health & Fitness |
| Age Rating | 4+ |

Source: [jake-mor.md #53](https://jakemor.com) — App title format: `"Keyword - AppName"` 例: 「Desk Stretching - DeskStretch」
Source: [Apple Developer: CFBundleIdentifier](https://developer.apple.com/documentation/bundleresources/information_property_list/cfbundleidentifier) — 「Use reverse-DNS format. Cannot change after submission.」

### ASO Keywords

Source: [AppTweak ASO Guide](https://www.apptweak.com/en/aso-blog/step-by-step-guide-aso-competitor-analysis) — 「Examine keywords in titles, subtitles, descriptions; check update frequency.」

| Priority | Keyword | Rationale |
|---------|---------|-----------|
| 1 | lymphatic massage | カテゴリ核心キーワード |
| 2 | lymph drainage | #lymphaticdrainage TikTok 5.5B views |
| 3 | lymphatic drainage | 同上、完全形 |
| 4 | self massage guide | デバイス不要の差別化 |
| 5 | body massage routine | 広義の検索流入 |
| 6 | lymph flow | ブランド連想キーワード |
| 7 | wellness routine | ウェルネス汎用キーワード |
| 8 | massage timer | タイマー機能の差別化 |

---

## 7. Risk Assessment

Source: [Full Scale: Risk Assessment](https://fullscale.io/blog/risk-assessment-for-startups/) — 「Companies with formal risk plans experience 30% fewer operational disruptions.」
Source: [Twinr: App Store Rejections 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) — 「Privacy violations = leading cause. 15% of submissions rejected. Over 40% of unresolved issues = Guideline 2.1 App Completeness.」

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **技術リスク**: iOS 17+ 限定でユーザー基盤限定 | 中 | iOS 17 シェア >85%（2026年時点）。許容範囲内 |
| **App Store リジェクト**: Privacy Manifest 未申告（ITMS-91053） | 高 | PrivacyInfo.xcprivacy必須。Greenlight preflight で事前チェック |
| **App Store リジェクト**: Guideline 2.1 App Completeness | 高 | Maestro E2E 6フロー完備。ReviewDetails に明確なデモ手順 |
| **市場リスク**: 競合（Kylee）がUI改善・デバイス不要版リリース | 中 | 先行者優位+ストリーク機能でロック。一般消費者UXに集中 |
| **収益リスク**: trial-to-paid 転換率が3%未満 | 高 | Annual 7日trial + Monthly trial-less の2プロダクト戦略（Jake Mor #17）|
| **ユーザーリスク**: ノベルティ消失・チャーン急増 | 中 | ストリーク + 毎日通知 + 新ルーティン追加（v1.1）でリテンション維持 |
| **コンテンツリスク**: 医療的効能の誇大表示でリジェクト | 高 | 「wellness guide」ポジショニング。医療効果の断言禁止。免責事項必須 |

---

## Sources Summary

Source: [Product School: PRD](https://productschool.com/blog/product-strategy/product-template-requirements-document-prd) — 「PRD is the blueprint for product development.」

| # | Source | What It Supports |
|---|--------|-----------------|
| 1 | [Apify TikTok Hashtag Scraper](https://apify.com/clockworks/tiktok-hashtag-scraper) | #lymphaticdrainage 5.5B views（Target User, Problem）|
| 2 | [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) | 競合分析 + 名前一意性確認（Problem, App Identity）|
| 3 | [Grand View Research: Lymphedema Market](https://www.grandviewresearch.com/industry-analysis/lymphedema-treatment-market) | TAM/SAM/SOM（Target User）|
| 4 | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | 価格設定根拠（Monetization）|
| 5 | [jake-mor.md #17](https://jakemor.com) | 2プロダクト戦略（Monetization）|
| 6 | [jake-mor.md #15](https://jakemor.com) | クリーン週額価格（Monetization）|
| 7 | [jake-mor.md #53](https://jakemor.com) | App Title フォーマット（App Identity）|
| 8 | [RevenueCat SDK Docs](https://www.revenuecat.com/docs/getting-started/installation/ios) | SPM統合手順（Solution, Monetization）|
| 9 | [ProductPlan: MoSCoW](https://www.productplan.com/glossary/moscow-prioritization/) | MVP Scope 判断フレームワーク |
| 10 | [Twinr: App Store Rejections 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) | リジェクトリスク（Risk Assessment）|
| 11 | [Full Scale: Risk Assessment](https://fullscale.io/blog/risk-assessment-for-startups/) | リスク管理フレームワーク（Risk Assessment）|
| 12 | [Apple Developer: CFBundleIdentifier](https://developer.apple.com/documentation/bundleresources/information_property_list/cfbundleidentifier) | Bundle ID ルール（App Identity）|
| 13 | [AppTweak ASO Guide](https://www.apptweak.com/en/aso-blog/step-by-step-guide-aso-competitor-analysis) | ASO キーワード選定（App Identity）|
| 14 | [Uptech MVP Guide](https://www.uptech.team/blog/build-an-mvp) | MVPスコーピング原則（MVP Scope）|
