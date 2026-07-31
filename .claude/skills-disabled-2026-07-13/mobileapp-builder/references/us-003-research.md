# US-003: Market Research

Source: rshankras competitive-analysis + market-research
URL: https://github.com/rshankras/claude-code-apple-skills/tree/main/skills/product

## Source Skills (参考のみ — 読み込み不要。コマンドは下記に全てインライン)
元ネタ: competitive-analysis, market-research

## Input → Output マッピング

| Input ファイル | 抽出フィールド | → Output セクション |
|---------------|--------------|-------------------|
| `spec/01-trend.md` | `problem_statement` | competitive-analysis.md §1 検索キーワードのシード |
| `spec/01-trend.md` | `target_user` | market-research.md §2 ICP 定義 |
| `spec/01-trend.md` | `competition_notes` | competitive-analysis.md §2 初期競合リスト |
| `spec/01-trend.md` | `monetization_model` | market-research.md §4 ARPU 計算 |
| `spec/01-trend.md` | `mvp_scope` | competitive-analysis.md §3 Feature Gap キーワード |
| `product-plan.md` | §4 Monetization | competitive-analysis.md §4 価格ポジショニング比較 |
| `product-plan.md` | §1 Target User | market-research.md §2 TAM セグメント定義 |
| `product-plan.md` | §2 Problem | market-research.md §3 Problem Size 統計 |

---

## Process: 3 Steps（ステップバイステップ）

**このファイルが US-003 の唯一の正本。** SKILL.md は実行前に必ず読むこと。

Source: [Slideworks](https://slideworks.io/resources/competitive-analysis-framework-and-template) — 「Assess (identify competitors) → Benchmark (analyze each rival) → Strategize (translate insights into strategic implications)」

---

### Step 1: 競合特定 + プロファイリング

**入力:** 01-trend.md の `problem_statement` + `competition_notes` + `mvp_scope`
**出力:** competitive-analysis.md

#### 1a. キーワード導出

01-trend.md から以下を抽出してキーワード5個を生成:

```
problem_statement → 名詞キーワード 3個
mvp_scope         → 機能キーワード 2個
合計: 5キーワード（英語。日本語版も1-2個追加可）
```

Source: [SplitMetrics](https://splitmetrics.com/blog/aso-competitive-research-analysis-a-step-by-step-guide/) — 「Identifying keyword strategies should be the first step in your competitive research deep dive.」

#### 1b. iTunes Search API で競合収集

```bash
# 各キーワードで実行（最低5キーワード）
for KEYWORD in "keyword1" "keyword2" "keyword3" "keyword4" "keyword5"; do
  curl -s "https://itunes.apple.com/search?term=${KEYWORD}&media=software&entity=software&limit=10" | \
    jq '.results[] | {name: .trackName, id: .trackId, rating: .averageUserRating, reviews: .userRatingCount, price: .formattedPrice, developer: .sellerName, description: .description[0:200]}'
  sleep 2
done
```

Source: [AppRadar](https://appradar.com/blog/5-essential-factors-in-competitor-analysis-for-mobile-apps) — 「Find your app's category and make note of the top 10 free apps as well as the top 10 paid apps in that category.」

#### 1c. 競合分類

全検索結果を以下3カテゴリに分類し、**合計5社以上**を選定:

| カテゴリ | 定義 | 最低数 |
|---------|------|--------|
| **直接競合** | 同じ問題を同じ方法で解決 | 3社 |
| **間接競合** | 同じ問題を別の方法で解決 | 2社 |
| **代替手段** | 非アプリの解決策（YouTube, 本等） | 記載のみ（分析対象外） |

#### 1d. 各競合の詳細取得

選定した5社以上について、以下を収集:

```bash
# 各競合の詳細（trackId を Step 1b から取得）
curl -s "https://itunes.apple.com/lookup?id={TRACK_ID}" | \
  jq '.results[0] | {name: .trackName, rating: .averageUserRating, reviews: .userRatingCount, price: .formattedPrice, description: .description, version: .version, updated: .currentVersionReleaseDate, size: .fileSizeBytes, developer: .sellerName, url: .trackViewUrl}'
```

#### 1e. ★1-2 レビュー分析（直接競合のみ）

```bash
# 直接競合 Top 3 の低評価レビューを取得
curl -s "https://itunes.apple.com/us/rss/customerreviews/page=1/id={TRACK_ID}/sortby=mostrecent/json" | \
  jq '.feed.entry[] | select((.["im:rating"].label | tonumber) <= 2) | {title: .title.label, rating: .["im:rating"].label, review: .content.label}'
```

レビューを3カテゴリで分類:

| カテゴリ | 内容 |
|---------|------|
| **ペイン** | ユーザーが不満に感じている機能・体験 |
| **要望** | ユーザーが欲しいと言っている機能 |
| **バグ** | 技術的な不具合の報告 |

Source: [Appbot](https://appbot.co/blog/app-store-review-analysis-complete-guide/) — 「App store reviews highlight the gap between your app's performance and what users truly want.」

---

### Step 2: 市場規模（TAM/SAM/SOM）

**入力:** product-plan.md の §1 Target User + §4 Monetization
**出力:** market-research.md

#### 2a. 市場定義（スコープ確定）

| 項目 | 値 |
|------|-----|
| カテゴリ | product-plan.md から取得 |
| 地域 | iOS: US + JP（product-plan.md の Localization から） |
| ICP | product-plan.md §1 Target User を1文で要約 |

#### 2b. TAM 計算（トップダウン + ボトムアップ クロスチェック）

Source: [Antler](https://www.antler.co/blog/tam-sam-som) — 「The bottom-up approach is often more credible to investors, as it is grounded in specific, realistic assumptions.」
Source: [GoingVC](https://www.goingvc.com/post/how-investors-use-tam-sam-som-to-evaluate-startups) — 「Investors look at SOM to understand whether you've done a grounded, bottom-up forecast.」

**トップダウン:**
```
WebSearch: "{CATEGORY} market size {YEAR}"
WebSearch: "{CATEGORY} app market CAGR forecast"
WebSearch: 「{カテゴリ} 市場規模 {年}」

TAM = 市場レポートの数字（ソース必須）
```

**ボトムアップ:**
```
TAM = 対象カテゴリの推定ユーザー数 × ARPU
ARPU = product-plan.md §4 の Annual Price × Paid率

推定ユーザー数の算出:
  - 競合上位5アプリのレビュー数合計 × 50-100（業界目安）= 推定インストール数
  - 対象地域のスマートフォンユーザー × カテゴリ利用率
```

**クロスチェック:** トップダウン vs ボトムアップの乖離が **3倍以上** → 仮定を見直す。

#### 2c. SAM 計算

```
SAM = TAM × iOS率 × ターゲット地域率 × セグメント率

iOS率: 27%（グローバル）or 57%（US）or 68%（JP）
ターゲット地域率: product-plan.md の対象市場から算出
セグメント率: ICP に合致する人口比率（ソース必須）
```

Source: [WaveUp](https://waveup.com/blog/tam-sam-som/) — 「Use primary data to estimate the potential market size for each target market segment.」

#### 2d. SOM 計算

```
SOM = SAM × 市場シェア率

インディーデベロッパーの現実的シェア:
  Year 1: SAM × 0.01%（新規参入）
  Year 2: SAM × 0.05%（トラクション獲得後）
  Year 3: SAM × 0.2%（口コミ + ASO 最適化後）
```

**禁止:** SOM を SAM の 1% 以上にする（HubSpot/Salesforce と競合しない限り）。

Source: [GoingVC](https://www.goingvc.com/post/how-investors-use-tam-sam-som-to-evaluate-startups) — 「A startup calculated their SOM as 15% of SAM while competing against HubSpot—realistic SOM was closer to 0.5%.」

#### 2e. Problem Size（需要の根拠）

```
WebSearch: "{PROBLEM} statistics prevalence"
WebSearch: "{PROBLEM} economic cost annually"
WebSearch: 「{問題} 統計 有病率」

最低3つの統計データで需要を数字で証明する。
```

---

### Step 3: POEM スコアリング（Market Opportunity Score）

Source: [Mind the Product](https://www.mindtheproduct.com/poem-framework/) — 「Identify strengths and weaknesses in a market opportunity based on five key forces: Customer, Product, Timing, Competition, and Finance.」

| 軸 | 評価内容 | 1-5 基準 |
|----|---------|---------|
| **Customer** | ペインの深刻度 + WTP（支払い意欲） | 5=深刻+高WTP, 1=軽微+低WTP |
| **Product** | 技術的実現性 + 差別化の強さ | 5=容易+強差別化, 1=困難+なし |
| **Timing** | トレンド合致 + 規制環境 | 5=上昇トレンド, 1=下降 |
| **Competition** | 競合密度 + 参入障壁の高さ | 5=低競合+低障壁, 1=高競合+高障壁 |
| **Finance** | SOM規模 + 想定LTV:CAC | 5=SOM>$500K+LTV:CAC>3, 1=SOM<$10K |

**判定:**

| 合計スコア | 判定 |
|-----------|------|
| 20-25 | 🟢 Strong Opportunity |
| 15-19 | 🟡 Moderate Opportunity |
| 10-14 | 🟠 Weak — 差別化戦略の見直し必要 |
| 5-9 | 🔴 参入見送り推奨 |

**必須:** ネガティブシグナルを最低1つ列挙する（確証バイアス防止）。

Source: [Charisol](https://charisol.io/12-common-market-research-mistakes-and-how-to-avoid-them/) — 「It's easy to let personal opinions influence how you interpret data. Sometimes, teams cherry-pick findings that support what they already believe.」

---

## Output Templates

### competitive-analysis.md（6セクション構成）

Source: [Alpha Sense](https://www.alpha-sense.com/blog/product/competitor-analysis-framework/) — 「Competitor Profile → Market Research Data → Product Analysis → Marketing Analysis → SWOT Analysis.」

```markdown
# Competitive Analysis: {APP_NAME}

## 1. Competitive Landscape Overview
（直接競合 / 間接競合 / 代替手段の3分類テーブル）

## 2. Competitor Profiles
（各競合: 名前, 価格, 評価, レビュー数, 主要機能, 最終更新日, 1行サマリー）

## 3. Feature Comparison Matrix
（機能 × 競合 のテーブル。✅/❌/⚠️ で表記）

## 4. Pricing Analysis
（価格帯テーブル + ポジショニングマップ: Price × Complexity の2軸）

## 5. SWOT Analysis
（直接競合 Top 3 + 自社 の SWOT テーブル）

## 6. Feature Gap Analysis + Strategic Implications
（競合が未対応のユーザーペイン TOP3 + 自社の差別化戦略1文）

## Sources
（# / Source / URL / What It Supports テーブル — 5+ ソース）
```

### market-research.md（5セクション構成）

Source: [AppTweak](https://www.apptweak.com/en/aso-blog/app-market-research) — 「Key research areas include market insights, competitors, target audience, budget, monetization, and financial forecasts.」

```markdown
# Market Research: {APP_NAME}

## 1. Market Definition
（カテゴリ, 地域, ICP, App Store サブカテゴリ）

## 2. Market Sizing (TAM/SAM/SOM)
（トップダウン + ボトムアップ クロスチェック テーブル）
（Year 1 / Year 2 / Year 3 の SOM テーブル）

## 3. Problem Size & Demand Validation
（統計データ3+ で需要を数字で証明）

## 4. Growth Analysis
（CAGR, Growth Drivers テーブル, Headwinds テーブル）

## 5. POEM Market Opportunity Score
（5軸スコアリングテーブル + 合計 + 判定 + ネガティブシグナル1つ）

## Sources
（# / Source / URL / What It Supports テーブル — 5+ ソース）
```

---

## Source Citation Rules

Source: [Anthropic: Reduce Hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations) — 「Citation-based responses significantly reduce hallucination rates.」

| ルール | 詳細 |
|--------|------|
| 合計 10+ ソース | competitive-analysis.md に 5+、market-research.md に 5+ |
| TAM/SAM/SOM | 各値に最低1ソース（市場レポート or 推計根拠） |
| 競合データ | iTunes Search API の結果を証拠として記載 |
| フォーマット | `[Source Name](URL) — 「原文引用」` |

---

## Acceptance Criteria

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | competitive-analysis.md が存在する | `test -f competitive-analysis.md` |
| 2 | 5社以上の競合が分析されている | `grep -c "^### " competitive-analysis.md` ≥ 5（§2 内） |
| 3 | Feature Comparison Matrix が存在する | `grep -c "✅\|❌\|⚠️" competitive-analysis.md` ≥ 10 |
| 4 | market-research.md が存在する | `test -f market-research.md` |
| 5 | TAM/SAM/SOM が全て数値で記載されている | `grep -cE "\\\$[0-9]" market-research.md` ≥ 3 |
| 6 | POEM スコアが算出されている | `grep -c "POEM\|Market Opportunity Score" market-research.md` ≥ 1 |
| 7 | 合計10+ソースが引用されている | `grep -c "http" competitive-analysis.md market-research.md` ≥ 10 |
| 8 | ネガティブシグナルが記載されている | §5 POEM 内にリスク/ネガティブ要素の記述あり |
