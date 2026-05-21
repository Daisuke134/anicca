# Product Requirements Document: Zone2Daily

Source: [SpecKit SDD](https://github.com/feiskyer/claude-code-settings/blob/main/skills/speckit/SKILL.md) — 「PRD is the SSOT for all design and implementation decisions.」
Source: [Anthropic Skills Guide](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — 「Be specific and actionable.」

---

## 1. App Overview

| フィールド | 値 |
|-----------|-----|
| app_name | **Zone2Daily** |
| bundle_id | `com.aniccafactory.zone2daily` |
| one_liner | マフェトン式で Zone 2 目標 HR を自動計算し、週150分達成を科学的にサポートするトレーニングコンパニオン |
| platform | iOS 17+ (Swift/SwiftUI) |
| iOS minimum | iOS 17.0 |
| Xcode | 16.0+ |
| App Title (ASO) | `Zone 2 Cardio - Zone2Daily` |
| Subtitle | Zone 2 Heart Rate Coach |
| Category | Health & Fitness |
| Age Rating | 4+ |

Source: [Jake Mor #53 — App Title Format](https://www.revenuecat.com/blog/growth/how-to-price-your-app/) — 「Keyword - AppName format maximizes search visibility.」

---

## 2. Target User

### ICP サマリー

> 30-50代の Huberman/Attia プロトコル実践者で、Zone 3-4 で走りすぎていることに気づき、科学的な Zone 2 トレーニングに移行したいランナー・サイクリスト。

### Demographics テーブル

| 属性 | 内容 |
|------|------|
| 年齢 | 30-50代 |
| 性別 | 男女問わず |
| デバイス | iPhone (iOS 17+) |
| 行動 | 毎週3-5回の有酸素運動 |
| Pain Point | Zone 2 目標 HR がわからない。週間進捗が見えない |
| Willingness to Pay | $4.99/月（ジム1回分以下）で即決 |

Source: [Statista — Running App Users US 2024](https://www.statista.com/statistics/1222232/running-app-users-us/) — 「88M+ US running app users.」

---

## 3. Problem Statement

> ほとんどのランナーが Zone 3-4 で走り、Zone 2 の脂肪燃焼・長寿効果を得られていない。マフェトン法（180−年齢）は Peter Attia や Andrew Huberman が推奨する科学的手法だが、リアルタイムで自分の HR がゾーン内かを確認し、週間進捗を追跡できるシンプルなアプリが存在しない。

### 統計データ

| データ | ソース |
|--------|--------|
| #zone2cardio TikTok 709K views | [Apify TikTok Scraper Dataset mVhGpSdPTa48eXLlC](https://api.apify.com/v2/datasets/mVhGpSdPTa48eXLlC/items) |
| Zone 2: Heart Rate Training — 226 reviews only | [iTunes Search API 2026-03-09](https://itunes.apple.com/search?term=zone+2+heart+rate) |
| Zone 2 = "most discussed longevity protocol 2024-2025" | [Peter Attia MD — Zone 2](https://peterattiamd.com/zone2/) |

---

## 4. Goals & Success Metrics

| Metric | Target (Month 3) | Measurement Method |
|--------|-----------------|-------------------|
| Monthly Downloads | 500+ | App Store Connect |
| Trial-to-Paid Conversion | 5%+ | RevenueCat |
| MRR | $125+ | RevenueCat |
| DAU/MAU | 30%+ | SwiftData session logs |
| App Store Rating | 4.5+ | App Store Connect |
| Week-1 Retention | 40%+ | SwiftData session |

Source: [RevenueCat SOSA 2026](https://www.revenuecat.com/state-of-subscription-apps/) — 「5% trial-to-paid conversion is median for H&F apps.」

---

## 5. Solution Overview

Zone2Daily は年齢入力だけで Maffetone 式（180−年齢）の Zone 2 目標 HR を即座に計算し、手動ワークアウト記録と週間ダッシュボードで「今週 Zone 2 を何分達成したか」を可視化する。AI API・HealthKit・外部サービス一切不要の完全ローカル動作。

Source: [Maffetone — 180 Formula](https://philmaffetone.com/180-formula/) — 「Subtract your age from 180 to find your Maximum Aerobic Function heart rate.」

---

## 6. MVP Features

| Feature ID | Feature | Priority | Description |
|------------|---------|----------|-------------|
| F-001 | Zone 2 HR 計算 | P0 | 年齢入力 → 180−年齢 = Zone 2 上限 HR 自動表示 |
| F-002 | オンボーディング | P0 | 年齢入力 → Zone 2 説明 → 通知許可 → ソフトペイウォール（Maybe Later） |
| F-003 | ワークアウト記録 | P0 | タイマー起動 → 終了時 Zone 2 滞在時間入力 → SwiftData 保存 |
| F-004 | 週間ダッシュボード | P0 | 今週 Zone 2 分数 / 150分目標 進捗バー表示 |
| F-005 | ストリーク | P1 | 連続実施日数カウント（今日 Zone 2 実施 = +1） |
| F-006 | 通知 | P1 | 毎朝リマインダー（UNUserNotificationCenter） |
| F-007 | 設定画面 | P1 | 年齢・目標変更 + Upgrade → PaywallView |
| F-008 | Paywall | P0 | 自前 SwiftUI PaywallView + Purchases.shared.purchase(package:) — Rule 20 |

Source: [Apple HIG — SwiftUI](https://developer.apple.com/design/human-interface-guidelines/) — 「Use clear, scannable feature lists.」

---

## 7. User Stories

| ID | As a | I want to | So that |
|----|------|-----------|---------|
| US-F001 | 新規ユーザー | 年齢を入力するだけで Zone 2 HR を知りたい | Maffetone 式を自分で計算しなくていい |
| US-F002 | ランナー | ワークアウト後に Zone 2 滞在時間を記録したい | 今週の進捗を把握できる |
| US-F003 | ランナー | 週間ダッシュボードで 150分/週 の達成率を見たい | Zone 2 トレーニングの科学的推奨を満たしているか確認できる |
| US-F004 | 無料ユーザー | ペイウォールで「あとで」を選べるようにしたい | 圧力なく試してから決断できる |
| US-F005 | 有料ユーザー | 過去の全ワークアウト履歴を見たい | 長期的な進歩を確認できる |
| US-F006 | ユーザー | 毎朝通知を受け取りたい | Zone 2 トレーニングを忘れないようにできる |

---

## 8. Monetization

### Subscription Tiers

| Tier | monthly_price | Description |
|------|--------------|-------------|
| Free | $0 | Zone 2 HR 計算 + 直近7日間のログ3件まで |
| **Monthly** | **$4.99/月** | 無制限ログ + 週間ダッシュボード + 目標設定 + ストリーク |
| **Annual** | **$29.99/年** ($2.50/月) | Monthly の全機能 + Save 50% バッジ |

- trial_days: 0（トライアルなし）
- free_tier_limit: 3 workouts per 7 days
- annual_price: $29.99

### Paywall Design Best Practices

Source: [Adapty iOS Paywall Guide](https://adapty.io/blog/how-to-design-ios-paywall/) — 「3 products vs 2: +44% conversion.」
Source: [Funnelfox Paywall Guide](https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/) — 「Benefit-driven CTA outperforms generic.」
Source: [Appagent Paywall Optimization](https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/) — 「Paywall after onboarding: up to +234%.」

| Element | Requirement | Conversion Impact |
|---------|-------------|------------------|
| Headline | Value-focused ("Unlock Your Zone 2 Potential") | — |
| Benefits | 4-5 bullet points (tangible outcomes) | — |
| Pricing Grid | Annual highlighted as "Best Value" + "Save 50%" badge | +44% |
| CTA | "Start Training" (NOT "Subscribe") | Outperforms generic |
| Maybe Later | Visible soft-paywall dismiss button — **Rule 20 MANDATORY** | Reduces friction |
| FAQ | Billing + cancellation info | Trust building |
| Privacy | Privacy Policy + Terms links | App Review compliance |

### RevenueCat Setup

| コンポーネント | 設定値 |
|-------------|-------|
| SDK | RevenueCat iOS (SPM) — **RC-UI-extension 禁止 Rule 20** |
| Offering ID | `default` |
| Entitlement ID | `premium` |
| Monthly Product ID | `zone2daily_monthly_499` |
| Annual Product ID | `zone2daily_annual_2999` |

Source: [RevenueCat iOS SDK Docs](https://docs.revenuecat.com/docs/ios) — 「Purchases.shared.purchase(package:) is the standard purchase flow.」

---

## 9. Market Context

- **TAM**: $88M (Zone 2 / Cardio Training app niche of $14.7B H&F market)
- **SAM**: $9.8M (iOS-first, English/Japanese, subscription-willing users)
- **SOM Year 3**: $19.6K (2% SAM capture)
- **競合差別化**: Zone 2 専用 + Maffetone 計算 + 週間進捗追跡の3点セット。最近接競合「Zone 2: Heart Rate Training」は226 reviewsのみで大きな市場ギャップ。

Source: [Grand View Research — Fitness App Market 2024](https://www.grandviewresearch.com/industry-analysis/fitness-app-market) — 「$14.7B market, 17.6% CAGR.」

---

## 10. Privacy & Compliance

| 項目 | 値 |
|------|-----|
| データ収集 | なし（ローカル SwiftData のみ） |
| ATT | 不使用 — **Rule 20b**: AppTrackingTransparency 禁止 |
| PrivacyInfo.xcprivacy | 必須: NSPrivacyAccessedAPICategoryUserDefaults CA92.1 |
| サードパーティ tracking SDK | 禁止 — **Rule 17**: tracking / event SDK 一切不可 |
| AI API | 禁止 — **Rule 21**: AI API / AI モデル一切不可 |

Source: [Apple Privacy Manifest](https://developer.apple.com/documentation/bundleresources/privacy_manifest_files) — 「Apps must include PrivacyInfo.xcprivacy for required reason API usage.」

---

## 11. Localization

| 言語 | ロケール | 対応範囲 |
|------|---------|---------|
| English | en-US | 全画面 + App Store メタデータ |
| Japanese | ja | 全画面 + App Store メタデータ |

---

## 12. Technical Constraints

| # | Rule | 制約内容 |
|---|------|---------|
| Rule 17 | tracking SDK 禁止 | tracking SDK 一切使用不可。Greenlight CRITICAL = 即ブロック |
| Rule 20 | 自前 PaywallView | RC UI extension 禁止。`Purchases.shared.purchase(package:)` のみ |
| Rule 20b | ATT 禁止 | `AppTrackingTransparency` 使用不可 |
| Rule 21 | AI API 禁止 | AI completion API / on-device LLM (iOS 26+) 完全禁止。理由: 月収 $29 vs API コスト $300+ |
| — | HealthKit 禁止 | 権限管理複雑・審査リスク。手動入力 + SwiftData で代替 |
| — | Live Activities 禁止 | WidgetKit Extension → Maestro E2E テスト困難 |
| — | CloudKit 禁止 | デバッグ困難。ローカル SwiftData のみ |

---

## 13. Out of Scope (v1.0)

| Feature | 理由 |
|---------|------|
| HealthKit リアルタイム HR | 権限管理複雑・審査リスク（v1.1候補） |
| Apple Watch アプリ | WatchKit Extension → スコープ外 |
| Karvonen / %HRmax 切替 | Maffetone 一本化でシンプルさ優先 |
| Social sharing | v1.1 候補 |
| CloudKit 同期 | デバッグ困難 |
| AI completion API フィードバック | Rule 21 禁止 |

---

## 14. App Store Metadata

### en-US

| フィールド | 内容 |
|-----------|------|
| App Name | Zone2Daily |
| Subtitle | Zone 2 Heart Rate Coach |
| Keywords | zone 2 cardio,heart rate zone,maffetone method,aerobic training,fat burning zone,cardio tracker,peter attia zone 2,zone 2 training |
| Promotional Text | Train in the fat-burning zone. Maffetone formula calculates your exact Zone 2 heart rate. Track weekly minutes, build streaks. |
| Description | Zone2Daily is the simplest way to train smarter using Zone 2 cardio — the proven protocol recommended by Peter Attia and Andrew Huberman for fat burning, longevity, and endurance.\n\n**What is Zone 2?**\nZone 2 is the aerobic training zone where your heart rate stays between 60-70% of your maximum. The Maffetone formula (180 minus your age) gives you your exact upper limit. Most people train too hard — Zone2Daily keeps you on track.\n\n**Features:**\n• Instant Zone 2 HR calculation (just enter your age)\n• Workout timer with Zone 2 time tracking\n• Weekly dashboard: track progress toward 150 min/week goal\n• Daily streak counter\n• Morning reminder notifications\n\n**Why Zone2Daily?**\nUnlike complex multi-zone apps, Zone2Daily focuses entirely on Zone 2 — the single most important zone for metabolic health. No complicated setup, no subscriptions required to see your target HR.\n\nPremium unlocks unlimited workout history and the full weekly analytics dashboard.\n\nPrivacy: No data leaves your device. No account required. |

### ja

| フィールド | 内容 |
|-----------|------|
| App Name | Zone2Daily |
| Subtitle | ゾーン2 心拍数コーチ |
| Keywords | ゾーン2,有酸素運動,心拍数ゾーン,マフェトン法,脂肪燃焼,カーディオ,トレーニング追跡,ピーターアティア |
| Promotional Text | 脂肪燃焼ゾーンでトレーニング。マフェトン式であなたのゾーン2目標心拍数を自動計算。週間分数を追跡してストリークを積み上げよう。 |
| Description | Zone2Daily は、Peter Attia と Andrew Huberman が推奨するゾーン2カーディオで賢くトレーニングするための最もシンプルなアプリです。\n\n**ゾーン2とは？**\nゾーン2は、心拍数が最大心拍数の60〜70%に保たれた有酸素トレーニングゾーンです。マフェトン式（180マイナス年齢）があなたの正確な上限値を計算します。多くの人が運動しすぎています — Zone2Daily があなたを正しいゾーンに保ちます。\n\n**機能:**\n• 瞬時のゾーン2心拍数計算（年齢を入力するだけ）\n• ゾーン2時間追跡付きワークアウトタイマー\n• 週間ダッシュボード：週150分目標への進捗を追跡\n• 毎日のストリークカウンター\n• 朝のリマインダー通知\n\nプレミアムで無制限のワークアウト履歴と週間分析ダッシュボードが解放されます。\n\nプライバシー：データはデバイスから出ません。アカウント不要。 |
