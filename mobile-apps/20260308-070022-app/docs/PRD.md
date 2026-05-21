# Product Requirements Document: LymphaFlow

Source: [Product School PRD Template](https://productschool.com/blog/product-strategy/product-template-requirements-document-prd) — 「Essential sections: Overview, Success Metrics, Messaging, Timeline, Personas.」
Source: [Atlassian PRD Guide](https://www.atlassian.com/agile/product-management/requirements) — 「Include goals, assumptions, user stories, design, clear out-of-scope items.」

---

## 1. App Overview

| 項目 | 値 |
|------|-----|
| app_name | **LymphaFlow** |
| bundle_id | `com.aniccafactory.lymphaflow` |
| one_liner | TikTok55億回再生の#lymphaticdrainage トレンドに特化した、デバイス不要のセルフリンパマッサージガイドアプリ |
| platform | iOS 17+ (Swift/SwiftUI) |
| iOS minimum | 17.0 |
| category | Health & Fitness |
| age_rating | 4+ |
| app_title_aso | Lymphatic Massage - LymphaFlow |
| subtitle | Self Lymph Drainage Guide |

---

## 2. Target User

**ICP:** 25-45歳女性。むくみ・疲労感に悩む在宅勤務者・術後患者・美容意識の高い層。TikTokでリンパマッサージ動画を見て実践したいが、正確な手順を覚えられない。

Source: [Apify TikTok Hashtag Scraper](https://apify.com/clockworks/tiktok-hashtag-scraper) — Run ID: 1O5ifI6T5EAz2i7iY — 「#lymphaticdrainage: 5,500,000,000 total views（2026-03-08）」

| 属性 | 値 |
|------|-----|
| 年齢 | 25-45歳 |
| 性別 | 女性 (推定70%) |
| 地域 | 米国・日本・カナダ・英国 |
| デバイス | iPhone (iOS 17+) |
| ライフスタイル | 在宅勤務 / 産後・術後リカバリー中 |
| 支払い意欲 | $4.99-$9.99/月（美容・ウェルネスカテゴリ） |

---

## 3. Problem Statement

リンパドレナージュはむくみ・免疫改善・術後リカバリーに有効として急速に普及しているが、一般消費者が毎日正確に実践できるデジタルガイドアプリが事実上存在しない。

Source: [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) — 2026-03-08実行結果

| 競合アプリ | 評価 | レビュー数 | 問題点 |
|-----------|------|---------|--------|
| Lymphia: Lymphatic Exercises | ★5.0 | 2 | 機能最小限。継続性なし |
| Kylee Lymphedema Assistant | ★4.8 | 914 | Bluetoothデバイス専用。一般消費者不可 |
| LymphaTrack | ★4.0 | 3 | ユーザビリティ問題 |
| Body Roll Studio | ★5.0 | 45 | フォームローラー器具前提 |

**Gap:** 道具なし・デバイスなし・知識なしで毎日実践できる一般消費者向けガイドが2026年3月現在存在しない。

---

## 4. Goals & Success Metrics

| Metric | Target (Month 6) | Measurement |
|--------|-----------------|-------------|
| DAU | 500 | App Store Connect |
| Trial-to-Paid Conversion | 8% | RevenueCat dashboard |
| Day-7 Retention | 30% | UserDefaults streak data |
| MRR | $2,000 | RevenueCat dashboard |
| App Store Rating | ≥4.5 ★ | App Store Connect |
| 1-Star Review Rate | <2% | App Store Connect |

---

## 5. Solution Overview

LymphaFlowはスマートフォンだけで完結するセルフリンパマッサージガイドアプリ。部位別ステップ表示・タイマー・ストリーク記録の組み合わせで、TikTokで見たリンパマッサージを毎日正確に実践できる習慣を形成する。AI/外部APIを一切使わず、静的キュレーションコンテンツのみで動作する（Rule 21準拠）。

---

## 6. MVP Features

| Feature ID | Feature | Priority | Description |
|-----------|---------|----------|-------------|
| F-001 | ルーティン選択画面 | MUST | 顔・首・鎖骨の3ルーティン（Free）、全12部位（Pro）|
| F-002 | ステップバイステップガイド | MUST | イラスト + テキスト説明。各ステップのタイマー（30-60秒）|
| F-003 | Morning/Evening プログラム | MUST | 朝5分・夜10分の2プリセットプログラム |
| F-004 | セッション記録 + ストリーク | MUST | UserDefaultsで毎日の記録、連続日数表示 |
| F-005 | PaywallView（ソフトペイウォール） | MUST | 自前SwiftUI + [Maybe Later]ボタン。全身12部位アンロック |
| F-006 | オンボーディング | MUST | 3スクリーン説明 → 通知許可 → PaywallView |
| F-007 | 毎日リマインダー | MUST | UserNotificationsで朝/夜の通知 |
| F-008 | 設定画面 | MUST | サブスク管理、通知設定、Upgrade → PaywallView |

Feature IDは IMPLEMENTATION_GUIDE.md Phase Breakdown と1:1対応。

---

## 7. User Stories

| ID | As a | I want to | So that |
|----|------|-----------|---------|
| US-A | 無料ユーザー | 顔・首のリンパマッサージ手順を毎日確認したい | 正しい手技で継続実践できる |
| US-B | 無料ユーザー | ステップごとのタイマーを使いたい | 各部位に適切な時間をかけられる |
| US-C | 無料ユーザー | 連続記録（ストリーク）を見たい | モチベーションを維持できる |
| US-D | 有料ユーザー | 全12部位のルーティンにアクセスしたい | 全身のリンパケアができる |
| US-E | 有料ユーザー | Morning/Eveningプログラムを使いたい | 目的に合わせたルーティンを実行できる |
| US-F | 全ユーザー | 毎日リマインダーを受け取りたい | 習慣化を促進できる |

---

## 8. Monetization

### Subscription Pricing

Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「H&F median: $7.73/mo, $29.65/yr.」
Source: [Jake Mor #17](https://jakemor.com) — 「Two-product strategy: trial-less monthly + trialed annual.」

| Plan | Price | Trial | Content |
|------|-------|-------|---------|
| Free | $0 | — | 顔・首・鎖骨の基本ルーティン3種（毎日利用可）|
| Monthly | **$4.99/月** | なし | 全12部位 + 目的別プログラム + 進捗ログ |
| Annual | **$29.99/年** | **7-day** | Monthlyと同内容（週換算$0.58、50%OFF表示）|

| 変数 | 値 |
|------|-----|
| monthly_price | $4.99 |
| annual_price | $29.99 |
| trial_days | 7（Annual のみ）|
| free_tier_limit | 3 routines/day（顔・首・鎖骨のみ）|

### Paywall Design Best Practices

Source: [Adapty iOS Paywall Guide](https://adapty.io/blog/how-to-design-ios-paywall/) — 「3 products vs 2: +44% conversion. Discount badge: +20% to +30%.」
Source: [Funnelfox Paywall Screen Designs](https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/) — 「Message consistency: Ad → Onboarding → Paywall must use same tone.」
Source: [Appagent Paywall Optimization](https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/) — 「Paywall immediately after onboarding: up to +234%.」

| Element | Requirement |
|---------|------------|
| Headline | 価値訴求型（"Unlock Your Full Body Lymph Journey"）|
| Benefits | 5箇条（具体的な成果: むくみ軽減、免疫サポート等）|
| Pricing Grid | Monthly + Annual（Annual に "Best Value" バッジ）|
| Discount Badge | "Save 50%" + 月額換算 $2.49/月 |
| CTA | "Start 7-Day Free Trial" / "Subscribe Monthly" |
| Maybe Later | 必須（Rule 20: ソフトペイウォール）|
| Social Proof | レビュー数 + 平均評価 |
| FAQ | 課金詳細・解約手順 |
| Privacy Links | Privacy Policy + Terms |

### RevenueCat Configuration

| コンポーネント | 設定値 |
|-------------|-------|
| SDK | RevenueCat (Swift Package Manager) |
| RC公式UIライブラリ | **禁止（Rule 20）** |
| Entitlement | `pro` |
| Offering | `default` |
| Monthly Package | `$rc_monthly` — $4.99/month |
| Annual Package | `$rc_annual` — $29.99/year (7-day trial) |

---

## 9. Market Context

Source: [Grand View Research: Lymphedema Treatment Market](https://www.grandviewresearch.com/industry-analysis/lymphedema-treatment-market) — 「$1.18B (2023), CAGR 6.1% through 2030.」

| 指標 | 値 |
|------|-----|
| TAM | $6.0B（ウェルネスアプリ全体）|
| SAM | $825K（リンパ・マッサージ特化iOS App）|
| SOM Year 1 | $996 |
| 競合優位 | Lymphia: 2 reviews（事実上ブルーオーシャン）|
| TikTokシグナル | #lymphaticdrainage 5.5B views（最大級トレンド）|

---

## 10. Privacy & Compliance

Source: [Apple Developer PrivacyInfo](https://developer.apple.com/documentation/bundleresources/privacy_manifest_files) — 「Required for apps using UserDefaults or other privacy-impacting APIs.」

| 項目 | 値 |
|------|-----|
| データ収集 | なし（ユーザーデータをサーバーに送信しない）|
| ATT（App Tracking Transparency） | **使用しない（Rule 20b）** |
| PrivacyInfo.xcprivacy | 必須。NSPrivacyAccessedAPICategoryUserDefaults: CA92.1 |
| ITSAppUsesNonExemptEncryption | false（Info.plist）|

---

## 11. Localization

| 言語 | ロケール | 対象市場 |
|------|--------|---------|
| English (US) | en-US | 米国・英国・カナダ（主要市場）|
| Japanese | ja | 日本市場 |

---

## 12. Technical Constraints

Source: [CLAUDE.md CRITICAL Rules] — mobileapp-builder ルールセット

| Rule | 制約内容 |
|------|---------|
| **Rule 17** | 分析・トラッキング系SDK 一切禁止（grep検出 = CRITICAL）|
| **Rule 20** | 自前SwiftUI PaywallView必須。RC公式UIライブラリ禁止。[Maybe Later]ボタン必須 |
| **Rule 20b** | AppTrackingTransparency / NSUserTrackingUsageDescription 使用禁止 |
| **Rule 21** | 外部AI API / AIモデル / 外部AIサービス 一切禁止。静的コンテンツのみ |
| **Rule 23** | バックエンド不要。完全自己完結アプリ |

---

## 13. Out of Scope

| Feature | Reason |
|---------|--------|
| HealthKit統合 | 権限管理複雑化。v1.1候補 |
| 動画コンテンツ | アプリサイズ肥大・審査リスク |
| ソーシャル共有 | バックエンド必須 → Rule 23違反 |
| AI個別化推薦 | Rule 21（AI API禁止）|
| WidgetKit / Dynamic Island | Extension Target複雑化 |
| Sign in with Apple | Maestro E2E自動化不可 |
| CloudKit同期 | デバッグ困難 |
| カメラ・マイク | プライバシー審査リスク |

---

## 14. App Store Metadata

### English (en-US)

| 項目 | 内容 |
|------|------|
| app_name | LymphaFlow |
| title | Lymphatic Massage - LymphaFlow |
| subtitle | Self Lymph Drainage Guide |
| keywords | lymphatic massage,lymph drainage,lymphatic drainage,self massage guide,body massage routine,lymph flow,wellness routine,massage timer |
| promotional_text | New routines added! Full-body lymph drainage in 5-10 minutes a day. |
| description | **Feel lighter, less puffy, and more energized every day.**\n\nLymphaFlow guides you through proven self-lymphatic drainage routines — step by step, with built-in timers. No devices, no equipment, no expertise needed.\n\n**HOW IT WORKS**\nChoose a routine (Face, Neck, Full Body), follow the illustrated steps, and let the timer guide each movement. Complete your session and track your streak.\n\n**FREE FEATURES**\n• Face, neck & collarbone routines\n• Step-by-step illustrated guides\n• Built-in timers for each step\n• Daily streak tracking\n\n**PRO FEATURES (Subscription)**\n• All 12 body areas unlocked\n• Morning & Evening programs\n• Goal-based programs (Detox, Immunity, Post-Op Recovery)\n• Full progress dashboard\n\nSubscriptions: $4.99/month or $29.99/year (7-day free trial). Cancel anytime in Settings > Apple ID. This app is for wellness purposes only and is not a medical device or treatment.\n\nPrivacy Policy: https://aniccaai.com/privacy |

### Japanese (ja)

| 項目 | 内容 |
|------|------|
| app_name | LymphaFlow |
| title | リンパマッサージ - LymphaFlow |
| subtitle | セルフリンパドレナージュガイド |
| keywords | リンパマッサージ,リンパドレナージュ,むくみ解消,セルフマッサージ,リンパ流し,ウェルネス,マッサージタイマー |
| promotional_text | 毎日5〜10分。全身リンパケアの新ルーティン追加！ |
| description | **むくみを流して、軽い体へ。毎日続けるリンパドレナージュ。**\n\nLymphaFlowは、イラスト＋タイマー付きのステップガイドで、セルフリンパマッサージを正確に実践できます。器具不要、専門知識不要。\n\n**使い方**\nルーティンを選んで（顔・首・全身）、ステップに従って動かすだけ。タイマーが自動で次のステップへ案内します。\n\n**無料機能**\n• 顔・首・鎖骨のルーティン\n• イラスト付きステップガイド\n• ステップごとのタイマー\n• 毎日の継続記録（ストリーク）\n\n**Proプラン（サブスクリプション）**\n• 全12部位のルーティン解放\n• Morning / Evening プログラム\n• 目的別プログラム（むくみ解消、免疫サポート、術後ケア）\n• 進捗ダッシュボード\n\nサブスクリプション: 月額$4.99 または 年額$29.99（7日間無料トライアル）。設定 > Apple IDでいつでもキャンセル可能。本アプリはウェルネス目的のガイドアプリです。医療機器・医療行為ではありません。\n\nプライバシーポリシー: https://aniccaai.com/privacy |
