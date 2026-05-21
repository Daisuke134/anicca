# Product Requirements Document: LumaRed

Source: [Atlassian: PRD](https://www.atlassian.com/agile/product-management/requirements) — 「Include goals, assumptions, user stories, design, clear out-of-scope items.」
Source: [Product School: PRD Template](https://productschool.com/blog/product-strategy/product-template-requirements-document-prd) — 「Essential sections: Overview, Success Metrics, Messaging, Timeline, Personas.」

---

## 1. App Overview

| フィールド | 値 |
|-----------|-----|
| app_name | LumaRed |
| bundle_id | com.aniccafactory.lumared |
| one_liner | 赤色光療法（フォトバイオモジュレーション）のエビデンスベース・プロトコルガイド＆セッショントラッカー |
| subtitle | Red Light Therapy Timer |
| App Store Title | Red Light Therapy - LumaRed |
| platform | iOS 17+ |
| iOS minimum version | iOS 17.0 |
| Xcode version | Xcode 16+ |
| Swift version | Swift 5.10+ |
| Category | Health & Fitness |
| Age Rating | 4+ |

---

## 2. Target User

### Primary Persona: "Biohacker Kenji / Health-Conscious Sarah"

| 項目 | 詳細 |
|------|------|
| Age | 25–45歳 |
| Demographics | 健康意識が高い都市部在住者（US / JP）。赤色光デバイス所持（$200–$1,000投資済み） |
| Pain Point | 高価なデバイスを「購入したが使い方がわからない」「プロトコルが複雑でどの部位に何分当てればいいか不明」 |
| Behavior | TikTok / Reddit / YouTube でセルフケア情報収集。Andrew Huberman / Ben Greenfield を視聴 |
| Willingness to Pay | 月$5–15。既に健康サプリ・デバイスに月$100+支出 |
| Info Source | #redlighttherapy（698K TikTok plays）, #biohacking（4.1M plays） |

### Market Size Evidence

| ソース | データ |
|--------|-------|
| [Grand View Research: Photobiomodulation Market](https://www.grandviewresearch.com/industry-analysis/photobiomodulation-therapy-market-report) — 「$354.3M (2022), CAGR 5.6%」 | TAM $354M（2022）→ $556M（2030） |
| [Mordor Intelligence: RLT Device Market](https://www.mordorintelligence.com/industry-reports/red-light-therapy-device-market) — 「$0.55B (2024) → $1.13B (2029), CAGR 15.47%」 | デバイス市場が急拡大 = ユーザーベース急増 |

---

## 3. Problem Statement

赤色光デバイス（$200〜$1,000）を購入したユーザーの多くが、**部位別プロトコル・照射時間・距離・適切な波長の使い方がわからず、デバイスをほとんど使わないまま放置している。**

### Why Existing Solutions Fail

| 競合 | Reviews | 失敗理由 |
|------|---------|---------|
| Redd Light Therapy | 69 | 汎用ウェルネスアプリ。赤色光専用プロトコルなし。セッション管理機能なし |
| Red Light For Your Eyes | 18 | 目専用のみ。部位別プロトコルなし |
| SUNI | 2 | iPhoneスクリーン自体を赤色光として使用（デバイス非対応） |
| Vital Red Light | 1 | ほぼ機能なし |

Source: [iTunes Search API](https://itunes.apple.com/search) — 実行: 2026-03-09

### Gap

「部位別エビデンスベースのプロトコルライブラリ × セッションタイマー × 効果ログ」を提供する赤色光療法専用コンパニオンアプリが存在しない。

---

## 4. Goals & Success Metrics

| KPI | Target (Month 3) | Measurement |
|-----|-----------------|-------------|
| Monthly Downloads | 2,000 | App Store Connect |
| Trial-to-Paid Conversion | 4% | RevenueCat dashboard |
| MRR | $640 | RevenueCat |
| Day 7 Retention | 35% | UserDefaults session count |
| App Store Rating | ≥ 4.5 | App Store Connect |
| Crash Rate | < 0.1% | Xcode Organizer |

---

## 5. Solution Overview

LumaRed は、赤色光デバイス所持者向けの完全自己完結型コンパニオンアプリ。部位別エビデンスベースプロトコル（静的コンテンツ）+ BackgroundTasks対応タイマー + セッションログで、ユーザーが赤色光療法を継続できるよう支援する。外部API・AI不使用でコストゼロ。

---

## 6. MVP Features

| Feature ID | Feature | Priority | Description |
|-----------|---------|----------|-------------|
| F-001 | 部位別プロトコルライブラリ | Must | 5部位（顔・関節・傷・背中・全身）× 波長/距離/時間/頻度。静的コンテンツ |
| F-002 | セッションタイマー | Must | カウントダウン。BackgroundTasks対応（バックグラウンド動作）。完了通知 |
| F-003 | セッションログ | Must | 日付/部位/時間の自動保存。Free=7日、Premium=無制限 |
| F-004 | ソフトペイウォール | Must | オンボーディング最終画面。[Maybe Later] で閉じられる。自前SwiftUI PaywallView（RC-UI-library禁止 — Rule 20） |
| F-005 | 通知リマインダー | Must | セッション完了通知 + 翌日リマインダー |
| F-006 | 連続日数 / 累計時間ダッシュボード | Must | SwiftUI Charts を使ったシンプルな可視化 |

---

## 7. User Stories

| ID | As a | I want to | So that |
|----|------|-----------|---------|
| US-A | 赤色光デバイス所持者 | 部位別プロトコルを素早く確認したい | 正しい方法で療法を実施できる |
| US-B | 赤色光ユーザー | タイマーをバックグラウンドで動かしたい | 照射中にスマホを使える |
| US-C | 継続ユーザー | セッション記録を振り返りたい | 習慣化できているか確認できる |
| US-D | 新規ユーザー | ペイウォールを強制されずに試したい | まず価値を感じてから課金できる |
| US-E | Premiumユーザー | 全5部位のプロトコルにアクセスしたい | より全体的なケアができる |

---

## 8. Monetization

### Subscription Pricing

| Tier | Price | 内容 |
|------|-------|------|
| Free | $0 | 3プロトコル（顔・関節・傷）+ 7日ログ |
| Monthly | **$4.99/月** | 全5プロトコル + 無制限ログ + ダッシュボード |
| Annual | **$29.99/年** | Monthly と同じ + 50%割引表示（$2.50/月相当） |

| trial_days | free_tier_limit |
|-----------|-----------------|
| 7日間（Annualのみ） | 3プロトコル / 7日ログ |

### Product IDs (RevenueCat)

| Product | ID | Type |
|---------|-----|------|
| Monthly | `lumaRed_monthly_499` | Auto-renewable subscription |
| Annual | `lumaRed_annual_2999` | Auto-renewable subscription |
| Entitlement | `premium` | — |
| Offering | `default` | — |

### Paywall Design Best Practices

Source: [Adapty: iOS Paywall Design](https://adapty.io/blog/how-to-design-ios-paywall/) — 「3 products vs 2: +44% conversion; Animation: 2.9x higher conversion.」
Source: [Funnelfox: Effective Paywall Designs](https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/) — 「Benefit-driven CTAs outperform generic ones. Message consistency across onboarding increases conversions.」
Source: [Appagent: Paywall Optimization](https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/) — 「Paywall immediately after onboarding: up to +234%. Long-form: up to 12x revenue.」

| Element | Requirement |
|---------|------------|
| Headline | 価値訴求（"Start Your Glow Journey"） |
| Benefits | 3-5箇条の具体的アウトカム |
| Pricing Grid | Monthly / Annual（Annual = "Best Value"バッジ + "Save 50%"） |
| CTA | "Start Free Trial" / "Unlock Full Access" |
| FAQ | 請求・キャンセルポリシー |
| Social Proof | App Storeレーティング表示 |
| Maybe Later | ソフトペイウォール必須（Rule 20） |
| Privacy Links | Privacy Policy + Terms of Service |

---

## 9. Market Context

TAM $83M（フォトバイオモジュレーション療法市場のApp Store相当部分）/ SAM $676K（US+JP iOS）/ SOM Year1 $2,399 ARR。競合最大手でも69 reviews — 市場空白。

Source: [competitive-analysis.md]() — 直接競合5社、最大でも69 reviews

---

## 10. Privacy & Compliance

| 項目 | 値 |
|------|-----|
| データ収集 | None（個人情報収集なし） |
| ATT | **No — Rule 20b（AppTrackingTransparency不使用）** |
| PrivacyInfo.xcprivacy | NSPrivacyAccessedAPICategoryUserDefaults CA92.1（セッションログ保存のみ） |
| データ保存先 | UserDefaults（デバイス内のみ） |
| サーバー送信 | なし |

---

## 11. Localization

| 言語 | コード | 対応スコープ |
|------|-------|------------|
| English (US) | en-US | 全画面・メタデータ・Paywall |
| Japanese | ja | 全画面・メタデータ・Paywall |

---

## 12. Technical Constraints

| Rule | 制約 | 根拠 |
|------|------|------|
| **Rule 17** | tracking-SDK / tracking-SDK 禁止。一切のアナリティクスSDK不可 | Greenlight が tracking SDK 検出 = CRITICAL |
| **Rule 20** | 自前 SwiftUI PaywallView 必須。`Purchases.shared.purchase(package:)` 使用。RC-UI-library 禁止 | App Store ガイドライン |
| **Rule 20b** | AppTrackingTransparency 不使用。NSUserTrackingUsageDescription 禁止 | ATT ダイアログ = スクショ汚染 |
| **Rule 21** | AI API / 外部APIコスト禁止（third-party-AI-API, third-party-AI, Gemini, Apple on-device-AI-framework一切不可）。完全自己完結 | 月収$29 vs APIコスト$300+ |

---

## 13. Out of Scope (v1.0)

| Feature | Reason |
|---------|--------|
| Live Activities / Dynamic Island | WidgetKit Extension 必要 → テスト困難 |
| HealthKit 連携 | 権限管理複雑 → v1.1候補 |
| カメラ（写真比較） | プライバシー審査厳化 → v1.1候補 |
| LLM / AI 推奨 | Rule 21 違反 |
| バックエンドサーバー | インフラコスト |
| CloudKit Sync | デバッグ困難。UserDefaults で十分 |
| Sign in with Apple | Maestro E2E 自動化不可 |
| Apple Watch 連携 | watchOS Target追加 → Scope overflow |

---

## 14. App Store Metadata

### en-US

| フィールド | 値 |
|-----------|-----|
| App Name | LumaRed |
| Subtitle | Red Light Therapy Timer |
| Keywords | red light therapy,photobiomodulation,RLT timer,biohacking,infrared therapy,wellness tracker,light therapy session,red light protocol |
| Description | **LumaRed — Your Red Light Therapy Companion**\n\nOwn a red light therapy device but not sure how to use it? LumaRed gives you science-backed protocols for every body part, a background-compatible timer, and session tracking to build a lasting habit.\n\n**Science-Backed Protocols**\nEvidence-based guidelines for Face & Skin, Joints & Muscles, Wound Healing, Back & Spine, and Full Body — with optimal wavelength, distance, duration, and frequency for each.\n\n**Background Timer**\nStart a session and put your phone down. LumaRed's timer keeps running in the background, completing your session without interruption.\n\n**Session Tracking & Streaks**\nLog every session automatically. Track your streak, cumulative time, and progress over time.\n\n**Free to Start**\n3 protocols and 7-day log history — no credit card required. Upgrade to Premium for all protocols and unlimited history.\n\nNo AI. No backend. No data collection. Everything runs on your device. |
| Promotional Text | Master your red light therapy routine. |

### ja

| フィールド | 値 |
|-----------|-----|
| App Name | LumaRed |
| Subtitle | 赤色光療法タイマー |
| Keywords | 赤色光療法,フォトバイオモジュレーション,RLTタイマー,バイオハッキング,赤外線療法,ウェルネス,光療法,赤色光プロトコル |
| Description | **LumaRed — 赤色光療法コンパニオン**\n\n赤色光デバイスを持っているけど、使い方がわからない？LumaRedはエビデンスに基づく部位別プロトコル、バックグラウンド対応タイマー、セッション記録で習慣化をサポートします。\n\n**科学的根拠のあるプロトコル**\n顔・肌、関節・筋肉、傷の回復、背中・脊椎、全身の5部位について、最適な波長・距離・時間・頻度を提供。\n\n**バックグラウンドタイマー**\nセッション開始後はスマホを置いていても大丈夫。バックグラウンドでタイマーが動き続けます。\n\n**セッション記録 & 連続日数**\nすべてのセッションを自動記録。連続日数・累計時間で進捗を可視化。\n\n**まずは無料で試せる**\n3プロトコル・7日分のログは無料。プレミアムにアップグレードすると全プロトコル・無制限ログが使えます。\n\nAI不使用。バックエンド不要。個人情報収集なし。すべてデバイス内で完結。 |
| Promotional Text | 赤色光療法を習慣に。 |
