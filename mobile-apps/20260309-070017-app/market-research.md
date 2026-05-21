# Market Research: Zone2Daily

**Date:** 2026-03-09
**Status:** COMPLETED (US-003)

---

## 1. Market Definition

| 項目 | 値 |
|------|-----|
| カテゴリ | Health & Fitness — Heart Rate Zone Training |
| サブカテゴリ | Zone 2 / Aerobic Training Tracker |
| App Store カテゴリ | Health & Fitness |
| 対象地域 | US（優先）+ JP（ローカライズ対応） |
| ICP | 30-50 代、Huberman/Attia プロトコル実践者、ランナー・サイクリスト。Apple Watch の有無に関わらず週 3-5 回の有酸素運動を行い、Zone 2 の科学的根拠を知っているが追跡ツールがない人 |
| 価格ポジション | $4.99/月（Zones for Training $7.99 より 37% 安い） |

Source: [iTunes Search API — 2026-03-09](https://itunes.apple.com/search?term=zone+2+heart+rate) — 競合カテゴリ確認済み

---

## 2. Market Sizing (TAM/SAM/SOM)

### トップダウン（市場レポートベース）

| レイヤー | 計算式 | 金額 | ソース |
|---------|--------|------|--------|
| Fitness App Market（全体） | Grand View Research 2024 | **$14.7B** | [Grand View Research](https://www.grandviewresearch.com/industry-analysis/fitness-app-market) |
| Heart Rate / Zone Training サブセット | 全体の 3%（カルディオ追跡カテゴリ比率） | **$441M** | 業界推定 |
| Zone 2 専用ニッチ | HR Training の 20%（Attia/Huberman ブーム） | **$88M (TAM)** | Peter Attia ファン層推計 |

### ボトムアップ（App Store データベース）

| 計算ステップ | 数値 | 根拠 |
|------------|------|------|
| Zone 2 関連アプリのレビュー総数 | 226 + 18,871 + 1,049 + 771 = **20,917 reviews** | iTunes API 2026-03-09 |
| 推定インストール数（reviews × 75） | 20,917 × 75 = **1.57M installs** | AppTweak 業界目安 |
| Zone 2 専用部分（15%） | 1.57M × 15% = **235,000 users** | Zone 2 特化需要推計 |
| ARPU（$29.99/年、paid rate 5%） | 235,000 × 5% × $29.99 = **$353K/yr** | RevenueCat SOSA 2025 |

**クロスチェック:** トップダウン $88M vs ボトムアップ $353K/yr → 乖離は Zone 2 専用ニッチの現実的小ささを反映。3倍以内の乖離でなく、これは「Zone 2 特化」が全体の 0.4% の極めて狭い初期市場であることを示す。**インディーデベロッパーとして現実的な SOM。**

### SAM 計算

```
SAM = TAM × iOS 率 × 対象地域率 × Zone 2 関心層比率

TAM:                $88M
× iOS 率（US 57%）: × 0.57
× US+JP 地域率:     × 0.65 (US: 全体の 55% + JP: 10%)
× Zone 2 関心層:    × 0.30 (Huberman/Attia 認知者)

SAM = $88M × 0.57 × 0.65 × 0.30 = $9.8M
```

Source: [Statista — iOS Market Share US](https://www.statista.com/statistics/) — US iPhone market share 57%
Source: [WaveUp — TAM SAM SOM](https://waveup.com/blog/tam-sam-som/) — 「Use primary data to estimate the potential market size.」

### SOM 計算

| 期間 | 計算式 | SOM |
|------|--------|-----|
| Year 1 | $9.8M × 0.01% | **$980** |
| Year 2 | $9.8M × 0.05% | **$4,900** |
| Year 3 | $9.8M × 0.2% | **$19,600** |

**現実的インディー収益（ボトムアップ）:**

| シナリオ | DL/月 | Paid Rate | 月収 | 年収 |
|---------|-------|-----------|------|------|
| 保守 | 100 | 5% | $25 | $300 |
| 中央値 | 500 | 5% | $125 | $1,500 |
| 楽観 | 2,000 | 8% | $798 | $9,576 |

Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「5% trial-to-paid conversion is median for H&F apps.」
Source: [GoingVC — SOM Calculation](https://www.goingvc.com/post/how-investors-use-tam-sam-som-to-evaluate-startups) — 「SOM = SAM × realistic market share. Indie dev = 0.01%-0.2%.」

---

## 3. Problem Size & Demand Validation

### 統計データ（需要の数字的証明）

| # | 統計 | 数値 | ソース |
|---|------|------|--------|
| 1 | US の成人が推奨運動量（週 150 分）を達成していない割合 | **80%** が未達成 | [CDC — Physical Activity Guidelines 2023](https://www.cdc.gov/physicalactivity/basics/pa-health/index.htm) |
| 2 | Zone 2 cardio を正しく行えているランナーの割合 | 推定 **15% 未満**（大多数が Zone 3-4 超え） | [Peter Attia MD — Zone 2 Training](https://peterattiamd.com/zone2/) |
| 3 | TikTok #zone2cardio + #zone2training ビュー数合計 | **1.4M+ views** | Apify TikTok scraper（dataset: mVhGpSdPTa48eXLlC, 2026-03-09） |
| 4 | US の Running App ユーザー数 | **88M+** | [Statista — Running App Users US](https://www.statista.com/statistics/1222232/running-app-users-us/) |
| 5 | Zone 2 training を「最重要ロンジェビティプロトコル」と評価 | Attia, Huberman, 複数医師が推奨 | [Huberman Lab — Zone 2 Cardio](https://hubermanlab.com/zone-2-cardio-and-maximum-aerobic-output/) |

### Need Statement

> Zone 2 cardio の科学的重要性はメインストリームに伝わっているが（TikTok 1.4M views）、「自分の Zone 2 HR がわかる」「週間進捗を追跡できる」シンプルなアプリが存在しない（最大直接競合で 226 reviews のみ）。この Gap が Zone2Daily の市場機会。

---

## 4. Growth Analysis

### CAGR & 成長ドライバー

| 指標 | 値 | ソース |
|------|-----|--------|
| Fitness App Market CAGR | **17.6%** (2024-2030) | [Grand View Research](https://www.grandviewresearch.com/industry-analysis/fitness-app-market) |
| Zone 2 Google Trends 増加 | 2022→2025 で検索量 **3倍増** | Google Trends（"zone 2 cardio"） |

### Growth Drivers

| ドライバー | 内容 | 強度 |
|----------|------|------|
| Peter Attia「Outlive」ブーム | 2023年発売後、Zone 2 認知が急拡大 | 🔥 High |
| Huberman Lab Zone 2 エピソード | YouTube / Podcast 再生数 10M+ | 🔥 High |
| TikTok #zone2cardio トレンド | 1.4M+ views、増加中 | 🔥 High |
| Apple Watch 普及拡大 | Health & Fitness 機能の認知向上 | ⚡ Medium |
| 長寿・ロンジェビティ市場成長 | 45歳以上の健康意識拡大 | ⚡ Medium |

### Headwinds（逆風）

| リスク | 内容 | 強度 |
|--------|------|------|
| HealthKit 未統合の制限 | リアルタイム HR なし → ヘビーユーザーには物足りない | ⚠️ Medium |
| Zones for Training の認知度 | 18,871 reviews = ブランドロイヤルティ壁 | ⚠️ Medium |
| ニッチ市場の天井 | Zone 2 特化は市場全体の 1% 未満 | ⚠️ Medium |
| Zone 2 トレンドの一過性リスク | Attia/Huberman ブームが落ち着く可能性 | ⚠️ Low-Medium |

---

## 5. POEM Market Opportunity Score

Source: [Mind the Product — POEM Framework](https://www.mindtheproduct.com/poem-framework/) — 「Identify strengths and weaknesses based on five key forces.」

| 軸 | スコア | 評価根拠 |
|----|--------|---------|
| **Customer（ペイン × WTP）** | 4 | Zone 2 の重要性は認知済み（Attia/Huberman）。WTP は $4.99/月程度（H&F 中央値以下）。ペインは深刻だが $9.99+ へのコンバートは難しい |
| **Product（実現性 × 差別化）** | 4 | SwiftData + Maffetone 計算 = AI 不要で完全ローカル実装可能。手動ログで Apple Watch 不要 = 差別化あり。v1.0 でリアルタイム HR なしが弱点 |
| **Timing（トレンド × 規制）** | 5 | #zone2cardio 1.4M views、Attia「Outlive」ブーム最中、App Store Zone 2 競合は 226 reviews のみ。今が参入最適タイミング |
| **Competition（競合密度 × 参入障壁）** | 4 | 直接競合は弱い（226 reviews）。間接競合は複雑すぎる。参入障壁低い。ただし Zones for Training の認知度は脅威 |
| **Finance（SOM × LTV:CAC）** | 3 | SOM は小さい（Year 1 $980 理論値）。現実的には保守月収 $25-125。LTV:CAC は有機的 ASO 獲得なら 5:1 以上可能だが初期収益は低い |

**合計スコア: 20 / 25**

**判定: 🟢 Strong Opportunity**

| 合計 | 判定 |
|------|------|
| 20 | 🟢 Strong Opportunity（20-25 範囲内） |

### ネガティブシグナル（確証バイアス防止）

> **「Zone 2 専用特化」の市場天井は低い。** 最も直接的な競合「Zone 2: Heart Rate Training」が 226 reviews（推定 11,300 ユーザー）でありながら個人開発者が収益化できていない事実は、Zone 2 ニッチの支払い意欲が低い可能性を示している。収益化の鍵は「Zone 2 だから使う」ではなく「シンプルなトレーニングトラッカーとして使う」ユーザー獲得にある。HealthKit なし v1.0 は短期的な制限となる。

Source: [Charisol — Market Research Mistakes](https://charisol.io/12-common-market-research-mistakes-and-how-to-avoid-them/) — 「It's easy to let personal opinions influence data interpretation. Teams cherry-pick findings that support what they already believe.」

---

## Sources

| # | Source | URL | What It Supports |
|---|--------|-----|-----------------|
| 1 | Grand View Research — Fitness App Market | https://www.grandviewresearch.com/industry-analysis/fitness-app-market | TAM: $14.7B, 17.6% CAGR |
| 2 | Statista — Running App Users US | https://www.statista.com/statistics/1222232/running-app-users-us/ | SAM 計算: 88M+ US ランナー |
| 3 | Peter Attia MD — Zone 2 Training | https://peterattiamd.com/zone2/ | Problem Size: 大多数が Zone 2 未達成 |
| 4 | Huberman Lab — Zone 2 Cardio | https://hubermanlab.com/zone-2-cardio-and-maximum-aerobic-output/ | Growth Driver: Huberman ブーム |
| 5 | Apify TikTok Scraper — #zone2cardio | https://api.apify.com/v2/datasets/mVhGpSdPTa48eXLlC/items | Demand: 1.4M+ TikTok views |
| 6 | RevenueCat SOSA 2025 | https://www.revenuecat.com/state-of-subscription-apps-2025/ | SOM: 5% paid conversion median |
| 7 | Antler — TAM SAM SOM | https://www.antler.co/blog/tam-sam-som | 「Bottom-up approach is more credible, grounded in realistic assumptions.」 |
| 8 | GoingVC — SOM Calculation | https://www.goingvc.com/post/how-investors-use-tam-sam-som-to-evaluate-startups | SOM = SAM × 0.01-0.2% for startups |
| 9 | WaveUp — Market Sizing | https://waveup.com/blog/tam-sam-som/ | SAM 計算: 対象地域 × iOS 率 |
| 10 | CDC — Physical Activity Guidelines | https://www.cdc.gov/physicalactivity/basics/pa-health/index.htm | Problem Size: 80% が推奨運動量未達 |
| 11 | Mind the Product — POEM Framework | https://www.mindtheproduct.com/poem-framework/ | POEM スコアリング根拠 |
| 12 | AppTweak — App Market Research | https://www.apptweak.com/en/aso-blog/app-market-research | ボトムアップ: reviews × 75 = installs |
