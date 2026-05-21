# Competitive Analysis: Zone2Daily

**Date:** 2026-03-09
**Status:** COMPLETED (US-003)
**Method:** iTunes Search API × 5 keywords + RSS review scraping

---

## 1. Competitive Landscape Overview

| カテゴリ | アプリ | 判定 |
|---------|-------|------|
| **直接競合** | Zone 2: Heart Rate Training | Zone 2 専用。226 reviews のみ |
| **直接競合** | Zone 2 Plus: Cardio Fitness | Zone 2 専用。有料$1.99、レビュー 0 |
| **直接競合** | Aerobic Pro - HR Zone Training | 有酸素ゾーン専用。3 reviews のみ |
| **間接競合** | Zones for Training | 全ゾーン対応。Zone 2 専用ではない |
| **間接競合** | Orange Zones Workout Companion | Orangetheory 専用。汎用性なし |
| **間接競合** | Myzone | 専用デバイス必須。一般ユーザー向けでない |
| **代替手段** | Apple Fitness+ | 全ゾーン。Zone 2 特化なし |
| **代替手段** | Garmin Connect / Strava | 高機能すぎる。Zone 2 専用 UX なし |
| **代替手段** | YouTube / ポッドキャスト（Attia/Huberman） | 情報のみ。追跡なし |

Source: [iTunes Search API](https://itunes.apple.com/search?term=zone+2+cardio) — Evidence: 2026-03-09 実行結果

---

## 2. Competitor Profiles

### 直接競合

#### ### Zone 2: Heart Rate Training

| 属性 | 値 |
|------|-----|
| Developer | Shannon Bolick（個人開発） |
| Price | Free（課金モデル不明） |
| Rating | 4.65 |
| Reviews | 226 |
| Version | 4.0.6 |
| Last Updated | 2026-02-03 |
| App Store URL | https://apps.apple.com/us/app/zone-2-heart-rate-training/id6444690892 |
| 1行サマリー | Zone 2 特化の先発アプリだが Apple Watch 必須で、手動ログ不可 |

**主要機能:** Zone 2 時間トラッキング、週間 150 分目標、HR モニター接続

**ユーザーペイン（低評価レビューから抽出）:**

| ペイン | 原文 | 評価 |
|-------|------|------|
| HR 計算方式がユーザーと合わない | "the calculation does zones based on HRR, not percentage of max HR" | ★2 |
| Apple Watch disconnects | "Watch disconnects constantly while working out" | ★1 |
| クラッシュ | "App just crashes on iPhone 11pro running iOS 17.4.1" | ★1 |
| HR モニター接続不安定 | "Constantly disconnects from Polar HR monitor" | ★1 |

Source: [iTunes RSS — Zone 2: Heart Rate Training](https://itunes.apple.com/us/rss/customerreviews/page=1/id=6444690892/sortby=mostrecent/json)

---

#### ### Zone 2 Plus: Cardio Fitness

| 属性 | 値 |
|------|-----|
| Developer | Andrey Gudilov |
| Price | $1.99（買切り） |
| Rating | 0（レビューなし） |
| Reviews | 0 |
| App Store URL | https://apps.apple.com/us/app/zone-2-plus-cardio-fitness/id6472242919 |
| 1行サマリー | 有料買切り。レビューなしで実績不明 |

---

#### ### Aerobic Pro - HR Zone Training

| 属性 | 値 |
|------|-----|
| Developer | 不明 |
| Price | Free |
| Rating | 3.33 |
| Reviews | 3 |
| 1行サマリー | 有酸素ゾーン対応。低評価で実質存在感なし |

---

### 間接競合

#### ### Zones for Training

| 属性 | 値 |
|------|-----|
| Developer | Flask LLP |
| Price | Free（サブスクあり: $7.99/月） |
| Rating | 4.79 |
| Reviews | 18,871 |
| Version | 9.0.0 |
| Last Updated | 2025-12-04 |
| App Store URL | https://apps.apple.com/us/app/zones-for-training/id1139688415 |
| 1行サマリー | 70+種類のワークアウト対応の全ゾーンアプリ。Zone 2 専用ではない |

**ユーザーペイン（低評価レビューから）:**

| ペイン | 原文 | 評価 |
|-------|------|------|
| Zone 2 計算が間違い | "can't get the intensity minutes to calculate HR zone 2,3 for moderate correctly" | ★2 |
| Apple Fitness からインポートできない | "assumed after upgrading that my Apple fitness workouts would get imported — it does not" | ★1 |
| HealthKit write 権限が必須で操作できない | "app requires both read and write for all records. This app was purchased and I should be able to determine the priorities" | ★2 |
| 課金後に削除→再課金 | "deleted my zones app and it charged me $7.99 for a subscription instead" | ★2 |
| Zone 2 のみカウントしない | "usually what most apps should do is only count zone two and above — this app counts all zones as exercise" | ★1 |

Source: [iTunes RSS — Zones for Training](https://itunes.apple.com/us/rss/customerreviews/page=1/id=1139688415/sortby=mostrecent/json)

---

#### ### Orange Zones Workout Companion

| 属性 | 値 |
|------|-----|
| Developer | Bred Ventures Inc |
| Price | Free |
| Rating | 4.45 |
| Reviews | 1,049 |
| Version | 1.57.1 |
| Last Updated | 2025-12-05 |
| App Store URL | https://apps.apple.com/us/app/orange-zones-workout-companion/id1482990976 |
| 1行サマリー | Orangetheory 会員向け専用。Zone 2 汎用ではない |

---

#### ### Myzone

| 属性 | 値 |
|------|-----|
| Developer | MYZONE INC |
| Price | Free（専用ハードウェア必須: $120+） |
| Rating | 4.75 |
| Reviews | 22,421 |
| 1行サマリー | Myzone ベルト必須。一般 Apple Watch ユーザー対象外 |

---

## 3. Feature Comparison Matrix

| 機能 | Zone2Daily（自社） | Zone 2: HR Training | Zones for Training | Orange Zones | Myzone |
|------|:---:|:---:|:---:|:---:|:---:|
| Zone 2 専用設計 | ✅ | ✅ | ❌ | ❌ | ❌ |
| Maffetone 式（180-年齢） | ✅ | ❌ | ❌ | ❌ | ❌ |
| 手動ワークアウトログ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Apple Watch 不要 | ✅ | ❌ | ❌ | ❌ | ❌（専用デバイス必要） |
| 週間 150 分目標追跡 | ✅ | ✅ | ⚠️ 部分的 | ❌ | ❌ |
| 週間ダッシュボード | ✅ | ⚠️ 限定的 | ✅ | ❌ | ✅ |
| リアルタイム HR ゾーン | ❌（v1.0） | ✅ | ✅ | ✅ | ✅ |
| ストリーク追跡 | ✅ | ❌ | ❌ | ❌ | ❌ |
| オフライン完全動作 | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ |
| Freemium モデル | ✅ | ✅ | ✅ | ✅ | ❌ |
| サブスク（月額） | ✅ $4.99 | ❌（無料のみ） | ✅ $7.99 | ⚠️ 不明 | ❌ |
| iOS 17+ ネイティブ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 日本語ローカライズ | ✅ | ❌ | ❌ | ❌ | ✅ |

---

## 4. Pricing Analysis

| アプリ | 無料 | 月額 | 年額 | 買切り | 収益構造 |
|-------|------|------|------|--------|---------|
| Zone2Daily | ✅ 3件/7日 | $4.99 | $29.99 | ❌ | Freemium Subscription |
| Zone 2: HR Training | ✅ フル無料 | ❌ | ❌ | ❌ | 広告のみ？ |
| Zones for Training | ✅ 制限付き | $7.99 | 不明 | ❌ | Freemium Subscription |
| Orange Zones | ✅ | ❌ | ❌ | ❌ | 広告のみ |
| Zone 2 Plus | ❌ | ❌ | ❌ | $1.99 | 買切り |
| Myzone | ❌（デバイス必須） | - | - | $120+ | ハードウェア |

**ポジショニングマップ（Price × Zone 2 特化度）:**

```
高価格
    │
$7.99│  [Zones for Training]
     │
$4.99│         [Zone2Daily ★] ← Zone 2特化 + 適正価格
     │
$1.99│ [Zone 2 Plus]
     │
Free │ [Zone 2: HR Training]  [Orange Zones]
     │─────────────────────────────────────→
      汎用/全ゾーン       Zone 2 専用特化
```

**戦略:** Zone 2 専用 × $4.99/月 は Zones for Training ($7.99) より安く、無料競合より価値が高い。適正な Sweet Spot。

---

## 5. SWOT Analysis

### 直接競合 Top: Zone 2: Heart Rate Training

| | Strengths | Weaknesses |
|--|-----------|-----------|
| **機会** | Zone 2 専用、大量ポジティブレビュー | Apple Watch 必須、クラッシュ多発、手動ログ不可 |
| **脅威** | 開発者のレスポンスが速い（競争力） | 収益化なし（広告/課金なし）= 開発継続性リスク |

### 間接競合 Top: Zones for Training

| | Strengths | Weaknesses |
|--|-----------|-----------|
| **機会** | 18,871 reviews = ブランド認知度 | Zone 2 計算が不正確（★1-2 レビュー多数） |
| **脅威** | $7.99/月 = 高価格 → スイッチコスト | 複雑すぎる UI、HealthKit 書き込み問題 |

### 自社: Zone2Daily

| | Strengths | Weaknesses |
|--|-----------|-----------|
| **機会** | Maffetone 専用計算、手動ログで Apple Watch 不要、シンプル UX | リアルタイム HR なし（v1.0）、ブランド認知度ゼロ |
| **脅威** | 新参者バイアス（0 reviews = 信頼不足） | HealthKit なし → "本格的でない" 印象リスク |

---

## 6. Feature Gap Analysis + Strategic Implications

### 競合が未対応のユーザーペイン TOP3

| ランク | ペイン | 証拠 | Zone2Daily の解決策 |
|--------|-------|------|-------------------|
| 1 | Apple Watch なし / HR モニターなしでは使えない | 複数の ★1-2 レビュー: "disconnects constantly" | **手動入力** でデバイス不要。Maffetone 計算で自分の Zone 2 HR を把握し、後から滞在時間を記録 |
| 2 | Zone 2 計算方式がユーザーの期待と合わない | "based on HRR, not percentage of max HR" | **Maffetone (180-age)** を デフォルト採用 — Peter Attia/Huberman ファンが求める計算式 |
| 3 | 週間 Zone 2 進捗が一目で見えない | "all zones counted as exercise including gentle stroll" | **週間ダッシュボード** に Zone 2 分数 / 150 分目標のみ表示。他ゾーン不要 |

### 差別化戦略

> **Zone2Daily は「Apple Watch を持っていない Huberman/Attia プロトコル実践者のための Zone 2 ファーストアプリ」** — デバイス依存ゼロ、Maffetone 式デフォルト、週間 150 分ゴールトラッキングの三点で既存競合が解決できていない問題を解決する。

---

## Sources

| # | Source | URL | What It Supports |
|---|--------|-----|-----------------|
| 1 | iTunes Search API — zone 2 cardio | https://itunes.apple.com/search?term=zone+2+cardio&media=software&entity=software | 競合リスト取得（2026-03-09 実行） |
| 2 | iTunes Lookup — Zones for Training | https://itunes.apple.com/lookup?id=1139688415 | 競合詳細データ（18,871 reviews, $7.99/月） |
| 3 | iTunes Lookup — Zone 2: HR Training | https://itunes.apple.com/lookup?id=6444690892 | 最大直接競合（226 reviews, 無料） |
| 4 | iTunes RSS Reviews — Zones for Training | https://itunes.apple.com/us/rss/customerreviews/page=1/id=1139688415/sortby=mostrecent/json | Zone 計算不正確・HealthKit 問題（★1-2） |
| 5 | iTunes RSS Reviews — Zone 2: HR Training | https://itunes.apple.com/us/rss/customerreviews/page=1/id=6444690892/sortby=mostrecent/json | Apple Watch 接続問題・クラッシュ（★1-2） |
| 6 | SplitMetrics — ASO Competitive Research | https://splitmetrics.com/blog/aso-competitive-research-analysis-a-step-by-step-guide/ | 「Identifying keyword strategies should be the first step in competitive research.」 |
| 7 | Slideworks — Competitive Analysis Framework | https://slideworks.io/resources/competitive-analysis-framework-and-template | 「Assess → Benchmark → Strategize framework」 |
| 8 | AppRadar — Competitor Analysis Factors | https://appradar.com/blog/5-essential-factors-in-competitor-analysis-for-mobile-apps | 「Find your category and note top 10 free + paid apps.」 |
| 9 | Appbot — App Store Review Analysis | https://appbot.co/blog/app-store-review-analysis-complete-guide/ | 「App store reviews highlight the gap between performance and what users truly want.」 |
| 10 | Alpha Sense — Competitor Analysis Framework | https://www.alpha-sense.com/blog/product/competitor-analysis-framework/ | 「Competitor Profile → Market Research → Product Analysis → SWOT」 |
