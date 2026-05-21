# Competitive Analysis: VagusReset

**Date:** 2026-03-09 | **Method:** iTunes Search API 実測 + レビュー分析

---

## 1. Competitive Landscape Overview

| カテゴリ | アプリ | レビュー数 | 特徴 |
|---------|--------|-----------|------|
| **直接競合** | NEUROFIT™ | 651 | 迷走神経特化、センサー依存 |
| **直接競合** | Settle: Nervous System Reset | 48 | 神経系リセット、瞑想+タッピング混在 |
| **直接競合** | Vagus Vibe: Heal by vibrations | 15 | 迷走神経特化、振動デバイス前提 |
| **直接競合** | Vagus Nerve Breathing - FlowMD | 35 | 迷走神経+呼吸、カメラ必須 |
| **直接競合** | Mindful Breathing — Vagus+ | 6 | 迷走神経+呼吸、汎用 |
| **間接競合** | Apollo Neuro | 1,735 | 自律神経、ウェアラブル前提 |
| **間接競合** | HeartMath | 4,112 | HRV biofeedback、専用センサー推奨 |
| **代替手段** | YouTube #vagusnerve | N/A | 無料動画コンテンツ |
| **代替手段** | TikTok #vagusnerve | 5M+ views | 無料ショート動画 |

Source: [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) / 実測: 2026-03-09

---

## 2. Competitor Profiles

### 直接競合

#### ### NEUROFIT™ (Vagus Nerve Reset)

| 項目 | 値 |
|------|-----|
| App ID | 1630278170 |
| Developer | Xama Technologies, Inc. |
| Rating | 4.79 / 5 |
| Reviews | 651件 |
| Price | Free（サブスク必須と推測） |
| 主要機能 | HRV計測（センサー依存）、神経系評価、エクササイズガイド |
| 最終更新 | 2024年（推定） |
| 1行サマリー | センサー依存の迷走神経アプリ。課金後コンテンツなしの★1レビュー多数。 |

Source: [iTunes API実測](https://itunes.apple.com/lookup?id=1630278170) / 2026-03-09

#### ### Settle: Nervous System Reset

| 項目 | 値 |
|------|-----|
| App ID | 6751709642 |
| Developer | Sola Studios, LLC |
| Rating | 4.58 / 5 |
| Reviews | 48件 |
| Price | Free |
| 主要機能 | 神経系リセット、瞑想、タッピング、ソマティック |
| 最終更新 | 2025年（推定） |
| 1行サマリー | 汎用神経系ツール。スキャムレビューあり、迷走神経特化でない。 |

Source: [iTunes API実測](https://itunes.apple.com/lookup?id=6751709642) / 2026-03-09

#### ### Vagus Vibe: Heal by vibrations

| 項目 | 値 |
|------|-----|
| App ID | 6748265558 |
| Developer | Lazy Loop AB |
| Rating | 4.53 / 5 |
| Reviews | 15件 |
| Price | Free |
| 主要機能 | 振動セラピー（デバイス前提）、ガイド付き迷走神経刺激 |
| 最終更新 | 2024年（推定） |
| 1行サマリー | 振動デバイスのコンパニオンアプリ。スマホ単体では機能不全。 |

Source: [iTunes API実測](https://itunes.apple.com/lookup?id=6748265558) / 2026-03-09

#### ### Vagus Nerve Breathing - FlowMD

| 項目 | 値 |
|------|-----|
| App ID | 6446627839 |
| Developer | Gal Harth |
| Rating | 4.66 / 5 |
| Reviews | 35件 |
| Price | Free |
| 主要機能 | カメラベース呼吸バイオフィードバック、呼吸エクササイズ |
| 最終更新 | 2026-01-06 |
| 1行サマリー | カメラ必須の呼吸特化アプリ。迷走神経エクササイズのバリエーション不足。 |

Source: [iTunes API実測](https://itunes.apple.com/lookup?id=6446627839) / 2026-03-09

#### ### Mindful Breathing — Vagus+

| 項目 | 値 |
|------|-----|
| App ID | 6747975890 |
| Developer | Alexandre Naud |
| Rating | 4.83 / 5 |
| Reviews | 6件 |
| Price | Free |
| 主要機能 | 迷走神経活性化呼吸、マインドフル呼吸 |
| 最終更新 | 2025年（推定） |
| 1行サマリー | 新規参入。レビュー極少で市場評価不明。 |

Source: [iTunes API実測](https://itunes.apple.com/lookup?id=6747975890) / 2026-03-09

### 間接競合

#### ### Apollo Neuro

| 項目 | 値 |
|------|-----|
| App ID | 1457385148 |
| Developer | Apollo Neuroscience, Inc. |
| Rating | 4.47 / 5 |
| Reviews | 1,735件 |
| Price | Free（デバイス購入必須） |
| 主要機能 | 音波振動で自律神経調整、ストレス・睡眠・集中サポート |
| 1行サマリー | ウェアラブルデバイス($349)前提。スマホ単体では機能しない。 |

Source: [iTunes API実測](https://itunes.apple.com/lookup?id=1457385148) / 2026-03-09

#### ### HeartMath

| 項目 | 値 |
|------|-----|
| App ID | 6446414998 |
| Developer | HeartMath LLC |
| Rating | 4.86 / 5 |
| Reviews | 4,112件 |
| Price | Free（センサー推奨） |
| 主要機能 | HRV biofeedback、心脳コヒーレンス計測、ストレス管理 |
| 1行サマリー | HRV専用センサー(Inner Balance ~$130)推奨。高評価だが高コスト参入障壁。 |

Source: [iTunes API実測](https://itunes.apple.com/lookup?id=6446414998) / 2026-03-09

---

## 3. Feature Comparison Matrix

| 機能 | VagusReset | NEUROFIT™ | Settle | Vagus Vibe | FlowMD | Apollo Neuro |
|------|-----------|----------|--------|-----------|--------|-------------|
| センサー不要 | ✅ | ❌ センサー必須 | ✅ | ❌ デバイス必須 | ⚠️ カメラ必須 | ❌ デバイス必須 |
| 迷走神経特化 | ✅ | ✅ | ❌ 汎用 | ✅ | ⚠️ 呼吸のみ | ⚠️ 自律神経全般 |
| 哼り(Humming) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| うがい(Gargling) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 冷水顔洗い | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| タイマー付きガイド | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| 無料体験5種以上 | ✅ | ❌ 3日トライアル | ✅ | ✅ | ✅ | ❌ |
| 20+エクササイズ | ✅ | ⚠️ 少ない | ⚠️ | ❌ | ❌ | ❌ |
| デイリーストリーク | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 通知リマインダー | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| $4.99/月以下 | ✅ | ❌ 高価格 | ✅ | ✅ | ✅ | ❌ デバイス$349 |
| 科学的根拠明記 | ✅ | ✅ | ⚠️ | ❌ | ✅ | ✅ |

---

## 4. Pricing Analysis

| アプリ | 月額 | 年額 | 初期費用 | 価格帯 |
|--------|------|------|---------|--------|
| **VagusReset** | **$4.99** | **$29.99** | $0 | LOW |
| NEUROFIT™ | 不明（$10+推定） | 不明 | $0 | HIGH |
| Settle | 不明 | 不明 | $0 | MID |
| Vagus Vibe | 不明 | 不明 | $0 | LOW |
| Apollo Neuro | 不明 | 不明 | デバイス$349 | VERY HIGH |
| HeartMath | 不明 | 不明 | センサー~$130 | HIGH |

**ポジショニングマップ（Price × Content Richness）:**

```
High Price
    │  HeartMath    Apollo Neuro
    │  NEUROFIT™
    │
    │
    │         VagusReset ← ここに配置
    │  Settle  Vagus Vibe  FlowMD
    │
Low Price ────────────────────────
         Low Content      High Content
```

Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — H&F median $7.73/月

---

## 5. SWOT Analysis

### NEUROFIT™ SWOT

| | Strengths | Weaknesses |
|--|-----------|-----------|
| | 651件レビュー（カテゴリ最多）; HRV計測機能; 確立ブランド | センサー依存（壊れると機能停止）; 課金後コンテンツ少ない |
| | **Opportunities** | **Threats** |
| | センサー不要版追加で差別化拡大可能 | VagusReset などセンサー不要の競合参入 |

### Settle SWOT

| | Strengths | Weaknesses |
|--|-----------|-----------|
| | 汎用神経系ツール | スキャム疑惑レビュー; 信頼性低い; 迷走神経特化でない |
| | **Opportunities** | **Threats** |
| | コンテンツ充実で評価向上可能 | 専門特化アプリに市場を奪われるリスク |

### VagusReset（自社）SWOT

| | Strengths | Weaknesses |
|--|-----------|-----------|
| | センサー不要; 低価格$4.99; 20+エクササイズ（哼り・うがい・冷水）; TikTokトレンド合致 | 新規参入で実績なし; ブランド認知ゼロ |
| | **Opportunities** | **Threats** |
| | 競合最大弱点（センサー依存・コンテンツ不足）を突く; 低競合カテゴリ | NEUROFITがセンサー不要版追加; App Store 4.3 Spam |

---

## 6. Feature Gap Analysis + Strategic Implications

### 競合が未対応のユーザーペイン TOP3

| # | ペイン（★1-2レビューより） | ソース競合 | VagusResetの対応 |
|---|--------------------------|-----------|----------------|
| 1 | **センサーが壊れて全機能停止** — 「Worked for 5 days then quit reading my phone」(Rating 1) | NEUROFIT | センサー完全不要。スマホのみで全機能動作 |
| 2 | **課金後コンテンツが解放されない** — 「subscribed and ZERO features unlocked」(Rating 1) | NEUROFIT | 無料5種体験可能。課金後即座に20+エクササイズ全解放 |
| 3 | **二値判定で個人差に対応しない** — 「all or nothing values... inaccurate」(Rating 2) | NEUROFIT | センサーなし→測定値なし→エクササイズ完了の主観的達成感を中心設計 |

**差別化戦略:** VagusResetは「センサー不要・コンテンツ充実・$4.99低価格」の三位一体で、NEUROFITの3大弱点を全て解決した迷走神経特化アプリとして市場に参入する。

Source: [Appbot: App Store Review Analysis](https://appbot.co/blog/app-store-review-analysis-complete-guide/) — 「reviews highlight the gap between app performance and what users truly want」

---

## Sources

| # | Source | URL | What It Supports |
|---|--------|-----|-----------------|
| 1 | iTunes Search API | https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/ | 全競合レビュー数・評価・価格の実測値 |
| 2 | NEUROFIT™ App Store | https://apps.apple.com/us/app/vagus-nerve-reset-neurofit/id1630278170 | 651件レビュー。★1-2レビュー「sensor stopped working」「ZERO content unlocked」 |
| 3 | Settle App Store | https://apps.apple.com/us/app/settle-nervous-system-reset/id6751709642 | 48件レビュー。★1「Scam app with fake reviews」 |
| 4 | Apollo Neuro App Store | https://apps.apple.com/us/app/apollo-neuro/id1457385148 | 1,735件。ウェアラブルデバイス$349前提 |
| 5 | HeartMath App Store | https://apps.apple.com/us/app/heartmath/id6446414998 | 4,112件。専用センサー推奨の高評価HRVアプリ |
| 6 | SplitMetrics ASO Research | https://splitmetrics.com/blog/aso-competitive-research-analysis-a-step-by-step-guide/ | 「Identifying keyword strategies should be the first step in competitive research」 |
| 7 | Appbot Review Analysis | https://appbot.co/blog/app-store-review-analysis-complete-guide/ | レビュー分類手法（Pain/Feature Request/Bug） |
| 8 | Slideworks Competitive Framework | https://slideworks.io/resources/competitive-analysis-framework-and-template | Assess→Benchmark→Strategize フレームワーク |
| 9 | Alpha Sense Competitor Profile | https://www.alpha-sense.com/blog/product/competitor-analysis-framework/ | 競合プロファイリング構造（6セクション） |
| 10 | AppRadar Competitor Analysis | https://appradar.com/blog/5-essential-factors-in-competitor-analysis-for-mobile-apps | 「top 10 apps in category as starting point」 |
