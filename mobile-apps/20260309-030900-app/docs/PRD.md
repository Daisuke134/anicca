# Product Requirements Document: VagusReset

Source: SpecKit SDD — 「Constitution phase: core values, technical principles, decision framework」
Source: [Perforce SRS Guide](https://www.perforce.com/blog/alm/how-write-software-requirements-specification-srs-document) — 「Each requirement should be traceable」

---

## 1. App Overview

| 項目 | 値 |
|------|-----|
| app_name | **VagusReset** |
| bundle_id | `com.aniccafactory.vagusreset` |
| app_title_aso | **Vagus Nerve Reset - VagusReset** |
| subtitle | Calm Your Nervous System Daily |
| one_liner | 毎日2分の迷走神経リセット — 哼り・うがい・冷水で自律神経バランスを整えるルーティンアプリ |
| platform | iOS 17+ (Swift/SwiftUI) |
| ios_minimum | iOS 17.0 |
| category | Health & Fitness |
| age_rating | 4+ |
| localization | en-US, ja |

---

## 2. Target User

### ICP（Ideal Customer Profile）
25–45歳のデスクワーカー・子育て世代で、慢性的なストレス・疲労・不安感を抱えつつ、センサー不要でスマホだけで今すぐ試せる自律神経ケアを求めている層。

### Demographics

| 属性 | 値 | ソース |
|------|-----|--------|
| Age | 25–45歳 | product-plan.md §1 |
| Gender | 60% 女性 / 40% 男性 | Business of Apps H&F 2024 |
| Location | US 65% / CA+AU 20% / 日本 15% | product-plan.md §1 |
| Device | iPhone（iOS 17+）、Apple Watch なし想定 | product-plan.md §1 |
| App habit | Calm/Headspace などサブスク経験あり、月$5–10の課金耐性あり | product-plan.md §1 |

---

## 3. Problem Statement

デジタル過多・慢性ストレスで自律神経が乱れた現代人に、**センサー不要でスマホのみで今すぐ実践できる迷走神経リセット法が存在しない**。

| 統計 | 数値 | ソース |
|------|------|--------|
| 世界の不安障害罹患者 | 3億人超（世界人口の4%） | [WHO Mental Health Fact Sheet 2022](https://www.who.int/news/item/02-03-2022-covid-19-pandemic-triggers-25-increase-in-prevalence-of-anxiety-and-depression-worldwide) |
| COVID-19後の不安・うつ増加率 | +25%（2020–2021） | [WHO COVID-19 Mental Health Brief 2022](https://www.who.int/news/item/02-03-2022-covid-19-pandemic-triggers-25-increase-in-prevalence-of-anxiety-and-depression-worldwide) |

### Why Existing Solutions Fail

| 競合 | レビュー数 | 失敗理由 |
|------|----------|---------|
| NEUROFIT™ | 651件 | センサー依存、課金後コンテンツ不足、二値判定 |
| Settle | 48件 | 迷走神経特化でない（汎用ツール） |
| Vagus Vibe | 15件 | 振動デバイス前提、スマホ単体非対応 |

---

## 4. Goals & Success Metrics

| Metric | Year 1 Target | Measurement |
|--------|--------------|-------------|
| DAU | 2,000 | UserDefaults 起動日付 |
| Day-7 retention | 40%+ | streak ≥ 7 のユーザー比率 |
| Free→Trial conversion | 15% | RevenueCat dashboard |
| Trial→Paid conversion | 30% | RevenueCat dashboard |
| MRR (Year 1 end) | $2,732/月 | RevenueCat metrics |
| App Store rating | 4.5+ | ASC Reviews |
| Crash-free rate | 99.5%+ | Xcode Organizer |

---

## 5. Solution Overview

VagusReset は、科学的に実証された迷走神経活性化エクササイズ（哼り・うがい・冷水・横隔膜・笑い）を、センサー不要・スマホのみで毎日2分のルーティンとして提供する。静的コンテンツ（JSON）のみ使用し、AI API や外部 API コストをゼロに抑える。

Source: [PMC5859128 — Vagus Nerve as Modulator of the Brain-Gut Axis (Front. Psychiatry, 2018)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5859128/) — 「哼り・冷水・深呼吸は vagal tone を高める非侵襲的刺激法」

---

## 6. MVP Features

| Feature ID | Feature | Priority | Description |
|-----------|---------|---------|-------------|
| F-001 | エクササイズライブラリ | MUST | 20+エクササイズ（哼り・うがい・冷水・横隔膜呼吸・笑い等）静的 JSON |
| F-002 | タイマー付きセッション | MUST | エクササイズごとのガイド + カウントダウンタイマー（バックグラウンド対応） |
| F-003 | ホーム画面（今日のルーティン） | MUST | 3–5エクササイズのデイリーセット。無料は5種のみ表示 |
| F-004 | ソフトペイウォール | MUST | オンボーディング最終画面。[Maybe Later] で閉じれる（Rule 20） |
| F-005 | デイリーストリーク | MUST | UserDefaults で連続日数管理 |
| F-006 | 通知権限リクエスト | MUST | オンボーディング内でリマインダー設定（UserNotifications） |
| F-007 | 設定画面 | MUST | サブスク管理 + 通知時間設定 + Upgrade→Paywall 遷移 |
| F-008 | オンボーディング（3画面） | MUST | 問題提示 → 解決策 → ソフトペイウォール |
| F-009 | 進捗カレンダー | SHOULD | 月次チェックイン履歴（有料機能） |
| F-010 | 完了アニメーション | SHOULD | セッション完了時の達成感 UI |

---

## 7. User Stories

| ID | As a | I want to | So that |
|----|------|-----------|---------|
| US-A1 | 新規ユーザー | オンボーディングで迷走神経リセットの価値を理解したい | 課金するかどうか判断できる |
| US-A2 | 無料ユーザー | 5種のエクササイズを毎日実践したい | センサー不要で自律神経ケアを試せる |
| US-A3 | 有料ユーザー | 20+エクササイズから今日の気分に合わせて選びたい | 飽きずに継続できる |
| US-A4 | 有料ユーザー | タイマー付きガイドに従ってエクササイズしたい | 正しい時間で実践できる |
| US-A5 | 全ユーザー | デイリーストリークで連続達成日数を確認したい | モチベーションを維持できる |
| US-A6 | 全ユーザー | 毎日リマインダーを受け取りたい | 習慣化できる |
| US-A7 | 有料ユーザー | 過去の実践カレンダーを見たい | 継続の証跡を確認できる |

---

## 8. Monetization

### Subscription Pricing

| Tier | 価格 | 内容 | free_tier_limit |
|------|------|------|----------------|
| Free | $0 | エクササイズ5種のみ。7日ストリーク上限 | 5 exercises/day |
| Monthly | **$4.99/mo** | 全20+エクササイズ + 詳細ガイド + 通知カスタム + ストリーク無制限 | — |
| Annual | **$29.99/yr** | Monthly の全機能 + 50%割引（$59.88比） | — |
| trial_days | 7日間 | 全機能お試し | — |

Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「H&F apps median monthly $7.73, annual $29.65」
Source: [Jake Mor #17 Two-product strategy](https://www.revenuecat.com/blog/) — 「annual apparent 50% discount 購買意欲増」

### Paywall Design Requirements

Source: [Adapty iOS Paywall Guide](https://adapty.io/blog/how-to-design-ios-paywall/)
Source: [Funnelfox Effective Paywall Designs](https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/)
Source: [Appagent Paywall Optimization](https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/)

| Element | Requirement | Conversion Impact |
|---------|------------|-------------------|
| Pricing Plans | Monthly + Annual 2プラン | Jake Mor two-product strategy |
| Discount Badge | "Save 50%" バッジ + 取り消し線価格 | +20–30% |
| CTA Copy | 「Start My Reset」（ベネフィット訴求） | 汎用「Subscribe」より高コンバージョン |
| Paywall Placement | オンボーディング直後 | 100%視認率 |
| Social Proof | レビュー数 + 星評価表示 | 信頼性向上 |
| [Maybe Later] | 閉じられる（Rule 20必須） | ソフトペイウォール |
| Privacy Policy + Terms | フッターリンク | App Review必須 |

### RevenueCat Integration

| 項目 | 設定 |
|------|------|
| SDK | `RevenueCat` via SPM（RC-UI-package 禁止 — Rule 20） |
| Entitlement | `premium` |
| Offering | `default` |
| Packages | `$rc_monthly`（$4.99）+ `$rc_annual`（$29.99） |
| Paywall | 自前 SwiftUI `PaywallView`。`Purchases.shared.purchase(package:)` |

---

## 9. Market Context

TAM $6.7B（H&F全体）/ SAM ~$43.5M（自律神経・ストレス管理）/ SOM Year1 ~$4,350（0.01%）。競合 NEUROFIT™ 651件レビューで低競合カテゴリ確認済み。センサー不要・コンテンツ充実で差別化。

Source: [Business of Apps H&F Report 2025](https://www.businessofapps.com/data/health-fitness-app-market/)
Source: [Grand View Research Mental Wellness App Market](https://www.grandviewresearch.com/industry-analysis/mental-wellness-market) — 「CAGR 17.8%（2022→2028）」

---

## 10. Privacy & Compliance

| 項目 | 値 |
|------|-----|
| データ収集 | なし（UserDefaults ローカルのみ） |
| ATT | 不使用（Rule 20b） |
| PrivacyInfo.xcprivacy | NSPrivacyAccessedAPICategoryUserDefaults CA92.1 |
| NSPrivacyTracking | false |
| NSUserTrackingUsageDescription | 不要（ATT 禁止） |
| tracking SDK | 禁止（Rule 17: data collection SDK 一切不可） |

---

## 11. Localization

| 言語 | App Name | Subtitle | Description キーワード |
|------|---------|---------|---------------------|
| en-US | VagusReset | Calm Your Nervous System Daily | vagus nerve, nervous system reset, stress relief, anxiety |
| ja | VagusReset | 迷走神経デイリーリセット | 迷走神経, 自律神経, ストレス解消, リラックス |

---

## 12. Technical Constraints

| Rule | 制約 | 理由 |
|------|------|------|
| **Rule 17** | tracking / data-collection SDK 完全禁止 | Greenlight CRITICAL = リジェクト |
| **Rule 20** | 自前 SwiftUI PaywallView + `Purchases.shared.purchase(package:)`。RC-UI-package 禁止 | App Review ガイドライン対応 |
| **Rule 20b** | ATT（AppTrackingTransparency）禁止 | スクショに ATT ダイアログが写り込む |
| **Rule 21** | AI API / 外部 AI サービス完全禁止（外部 LLM・AI モデル API 全般（Rule 21）） | 月収 $29 vs API コスト $300+ |
| Static content | エクササイズデータは JSON ファイル（バックエンド不要） | コスト・シンプル性 |
| No HealthKit | 審査で追加説明必要 | MVP スコープ外 |
| No WidgetKit | Extension Target = Maestro E2E テスト困難 | MVP スコープ外 |

---

## 13. Out of Scope

| 機能 | 理由 |
|------|------|
| WidgetKit / Dynamic Island | Extension 必要、Maestro テスト困難 |
| HealthKit | 審査で追加説明必要 |
| カメラ・マイク | プライバシー審査厳格化 |
| Sign in with Apple | Maestro E2E 自動化不可 |
| CoreData / CloudKit | UserDefaults で十分 |
| AI / LLM | コスト発生（Rule 21）|
| Apple Watch | HealthKit 不使用で価値なし |
| Social features | MVP スコープ外 |
| 呼吸法エクササイズ（直接） | 既存アプリとの重複カテゴリ |

---

## 14. App Store Metadata

### en-US

| 項目 | 内容 |
|------|------|
| Name | Vagus Nerve Reset - VagusReset |
| Subtitle | Calm Your Nervous System Daily |
| Keywords | vagus nerve,nervous system reset,vagal tone,stress relief,anxiety relief,parasympathetic,autonomic nervous,daily routine |
| Promotional Text | Science-backed vagus nerve exercises. No sensors needed — just 2 minutes a day. |
| Description | Reset your nervous system in 2 minutes. VagusReset guides you through scientifically-backed vagus nerve exercises — humming, gargling, cold water, and more — to calm anxiety and reduce stress. No sensors required. Start free with 5 exercises, or unlock 20+ with Premium. Build your daily streak and feel the difference in a week. |

### ja

| 項目 | 内容 |
|------|------|
| Name | Vagus Nerve Reset - VagusReset |
| Subtitle | 迷走神経デイリーリセット |
| Keywords | 迷走神経,自律神経,ストレス解消,リラックス,不安解消,副交感神経,毎日ルーティン,セルフケア |
| Promotional Text | 科学的根拠のある迷走神経エクササイズ。センサー不要、毎日2分で自律神経を整える。 |
| Description | 迷走神経をリセットして、毎日2分でストレスを手放そう。VagusResetは科学的に実証された迷走神経活性化エクササイズ（哼り・うがい・冷水など）をガイドし、不安を和らげ自律神経バランスを整えます。センサー不要。まず5種のエクササイズを無料で体験、Premiumで20種以上にアクセス。デイリーストリークで習慣化をサポートします。 |
