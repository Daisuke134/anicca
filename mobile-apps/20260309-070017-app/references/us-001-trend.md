# US-001: Trend Research + Idea Selection

## トレンドリサーチ制限（トークン節約 — MUST）
Source: ghuntley.com/ralph — "use as little context as possible"

| ルール | 値 | 根拠 |
|--------|-----|------|
| アイデア生成 | 最大 5 個 | 時間節約: 1 Lens 1 アイデアで十分 |
| 深掘り | トップ 1 のみ | 選定アプリ 1 つに集中 |
| 競合分析 | 3 社まで | 最小限で十分 |
| Web 検索 | 1 Lens あたり最大 2 クエリ | 検索は高コスト（1回 ~100K tokens） |
| 合計検索回数 | 最大 8 回/US-001 | 4 Lens × 2（Lens 1 検索不要） |

Source: rshankras idea-generator SKILL.md
URL: https://github.com/rshankras/claude-code-apple-skills/blob/main/skills/product/idea-generator/SKILL.md

## Source Skills (参考のみ — 読み込み不要。コマンドは下記に全てインライン)
元ネタ: idea-generator, apify-ultimate-scraper, app-store-scraper

## Environment

```bash
source ~/.config/mobileapp-builder/.env
# APIFY_TOKEN が必要（TikTok ハッシュタグスクレイピング用）
# 前提: npm install -g @apify/mcpc（未インストール時のみ）
```

## Process

**このファイルが US-001 の唯一の正本。** idea-generator SKILL.md は実行前に必ず読むこと。

---

### 0. Pre-check: 既存アプリ重複排除

**Apple Guideline 4.3 (Spam) 対策。同カテゴリのアプリを同一デベロッパーアカウントから出すとリジェクトされる。**

#### 手順:
1. `ls mobile-apps/` を実行して既存アプリ一覧を取得
2. 各アプリの `mobile-apps/<app>/spec/01-trend.md` を読む（存在する場合）
3. 各アプリのカテゴリ・問題領域を抽出して「除外カテゴリリスト」を動的に構築
4. 除外カテゴリリストを Step 3 Feasibility Filtering に渡す

```bash
ls mobile-apps/
# 各ディレクトリの spec/01-trend.md からカテゴリを抽出
```

**判定基準:** 既存アプリと「同じ App Store サブカテゴリ」または「同じコア問題」を解決するアイデアは除外。

例（2026-03-05 時点。この表はあくまで例 — `ls` の動的出力が正本）:

| 既存アプリ | 除外カテゴリ |
|-----------|-------------|
| breath-calm, breatheai | 呼吸法・瞑想 |
| sleep-ritual | 睡眠 |
| dailydhamma | マインドフルネス・仏教 |
| calmcortisol | ストレス管理 |
| rork-thankful-gratitude-app | 感謝日記 |
| stretch-flow | デスクストレッチ・姿勢改善 |

---

### 1. Developer Profile（固定）

| 項目 | 値 |
|------|-----|
| Platform | iOS 17+ (Swift/SwiftUI) |
| Scope | 4-8 weeks（Claude Code が実装するため実質数十分） |
| Dev Type | Solo dev |
| Monetization | Subscription ($4.99/月, $29.99/年 が基準。カテゴリによって調整可） |
| 目的 | 人々の苦しみを減らすアプリ（ヘルス・ウェルネス・生産性・自己改善） |
| AI / 外部 API | **禁止（Rule 21）** — 完全自己完結。ローカル・静的コンテンツのみ。バックエンド不要 |
| AI API 制約 | **AI API / AI モデル / 外部 AI サービス完全禁止**（Rule 21）。月額収益 $29 vs API コスト $300+。Apple FoundationModels も iOS 26+ のみでユーザーベース皆無。AI 機能が必要なアイデアはオンデバイスロジック or 静的キュレーションコンテンツで代替すること |

**このプロファイルは全 Lens に共通。変更しない。**

---

### 検索ルール

| ルール | 値 |
|--------|-----|
| WebSearch 最低回数 | **5回**（Lens 2-5 × 1-2回） |
| Apify TikTok | Lens 5 で必須（定量データ取得） |
| iTunes Search API | Lens 4 で必須（競合分析 + ★1-2 レビュー） |
| キーワード多様性 | 英語 + 日本語、一般化・隣接分野含む |
| `{YEAR}` プレースホルダー | 実行時の西暦に置換（例: 2026） |

---

### 2. Five Brainstorming Lenses

**各 Lens で1個のベストアイデアを生成する。量より質を優先。**

合計: 5 Lens × 1個 = **最低5個の raw ideas** → Filtering → Scoring → Top 3

---

#### Lens 1: Skills & Interests（内部知識）

**問い:** Apple の独自フレームワーク（HealthKit, CoreMotion, Foundation Models, ARKit, SiriKit 等）を活かして何が作れるか？

生成方法:
1. Apple が {YEAR} に推してるフレームワークを列挙（WWDC セッション、Apple developer news を参照）
2. 各フレームワークを「人の苦しみを減らす」用途にマッピング
3. 最低5個のアイデアを生成

検索は不要。Apple の公式ドキュメントと内部知識で生成する。

---

#### Lens 2: Problem-First（WebSearch）

**問い:** 日常で30秒かかることが5秒で終わるなら？身体的・精神的な苦しみで「まだ良い解決策がない」ものは？

検索クエリ例（最低2回実行）:
```
"iOS app idea {YEAR} underserved niche health wellness"
"日常の不便 アプリで解決 {YEAR}"
"reddit what app do you wish existed {YEAR}"
```

生成方法:
1. 検索結果から具体的なペインポイントを抽出
2. 各ペインポイントに対して「iOS アプリでどう解決するか」を1文で書く
3. 最低5個のアイデアを生成

---

#### Lens 3: Technology-First（WebSearch）

**問い:** Apple が最近リリースしたフレームワークで、まだインディーアプリが少ないものは？

検索クエリ例（最低2回実行）:
```
"Apple Foundation Models on-device AI indie app {YEAR}"
"iOS 18 new framework underused {YEAR}"
"HealthKit sleep CoreMotion indie app opportunity"
```

生成方法:
1. 検索結果から「フレームワーク名 + それを使ったインディーアプリが少ない」組み合わせを抽出
2. 各フレームワークを「人の苦しみを減らす」用途にマッピング
3. 最低5個のアイデアを生成

---

#### Lens 4: Market Gap（App Store データ）

**問い:** App Store で競合が弱い（レビュー少 + 評価低）カテゴリはどこか？ユーザーの不満は何か？

##### 手順:

**Step 4a:** Lens 1-3 で出たアイデアのカテゴリキーワードを3-5個抽出する。
例: Lens 2 で「デスクワーカーの腰痛」が出た → キーワード = `"back pain relief"`

**Step 4b:** 各キーワードで iTunes Search API を実行:
```bash
# KEYWORD を Step 4a のキーワードに置換（最低3キーワード実行）
curl -s "https://itunes.apple.com/search?term=KEYWORD&media=software&entity=software&limit=10" | \
  jq '.results[] | {name: .trackName, rating: .averageUserRating, reviews: .userRatingCount, price: .formattedPrice}'
```

**Step 4c:** 結果を分析:
- レビュー数 < 1,000 かつ 評価 < 3.5 = **競合が弱い穴**（チャンス大）
- レビュー数 > 50,000 = **参入障壁が高い**（避ける）

**Step 4d:** 上位3アプリの★1-2レビューを取得（ペインポイント発掘）:
```bash
# APP_ID を Step 4b の結果から取得（trackId フィールド）
curl -s "https://itunes.apple.com/us/rss/customerreviews/page=1/id=APP_ID/sortby=mostrecent/json" | \
  jq '.feed.entry[] | select((.["im:rating"].label | tonumber) <= 2) | {title: .title.label, rating: .["im:rating"].label, review: .content.label}'
```

**Step 4e:** ★1-2レビューの不満パターンから新アイデアを5個以上生成。
例: 「ストレッチが9種類しかない」→「AI が毎日違うルーティンを生成するアプリ」

---

#### Lens 5: Trend-Based（TikTok + WebSearch）

**問い:** TikTok で実際にバズってるヘルス・ウェルネス系トピックは何か？

##### 手順:

**Step 5a:** WebSearch でトレンドの候補を取得:
```
"TikTok wellness trend {YEAR}"
"TikTok health viral {YEAR}"
"trending health topics social media {YEAR}"
```

**Step 5b:** 検索結果からハッシュタグ候補を3-5個抽出する。
例: WebSearch で「デスクストレッチがバズってる」→ ハッシュタグ = `deskstretching`, `officestretching`

**Step 5c:** TikTok ハッシュタグスクレイパーで定量検証:
```bash
source ~/.config/mobileapp-builder/.env
curl -s "https://api.apify.com/v2/acts/clockworks~tiktok-hashtag-scraper/run-sync-get-dataset-items?token=$APIFY_TOKEN" \
  -X POST -H "Content-Type: application/json" \
  -d '{"hashtags": ["HASHTAG1", "HASHTAG2", "HASHTAG3"], "resultsPerPage": 5}'

# ⛔ mcpc / MCP 経由の Apify アクセスは絶対禁止（stdin hang の原因）
```

**Step 5d:** ビュー数で判定:

| ビュー数 | 判定 |
|---------|------|
| 50,000+ | ✅ トレンド確認済み → アイデア化 |
| 10,000 - 49,999 | ⚠️ 追加 WebSearch で検証が必要 |
| < 10,000 | ❌ トレンド未確認 → スキップ |

**Step 5e:** トレンド確認済みのトピックからアイデアを5個以上生成。

---

### 3. Feasibility Filtering

各アイデアを以下5基準で **1-10 スコアリング**し、**いずれか1つでも 4以下ならば除外**する。

| 基準 | 略称 | 4以下で除外する理由 |
|------|------|-------------------|
| Solo Dev Scope | S | 1人 × 4-8週間で作れないスコープは Factory の前提を壊す |
| Platform API Fit | P | Apple API がないと App Store での差別化ができない |
| Monetization Viability | M | サブスク($4.99/月)で課金する価値がないアプリは収益化不可 |
| Competition Density | C | 上位5アプリの平均レビュー数 > 50,000 なら参入障壁が高すぎる |
| Technical Fit | T | Swift/SwiftUI + 既存ライブラリで実装できない場合は除外 |

**追加除外ルール:**
- Step 0 の除外カテゴリに該当するアイデアは無条件で除外
- アダルト・ギャンブル・暴力系は除外（人の苦しみを減らすアプリのみ）
- **🔴 AI API / 外部 API コストが必要なアイデアは除外（Rule 21）** — OpenAI, Anthropic, Gemini, Apple FoundationModels（iOS 26+ = ユーザー基盤小）一切禁止。アプリは完全自己完結。ローカル・静的コンテンツのみ。バックエンド不要。理由: 月収 $29 vs API コスト $300+
- **AI API / 外部 AI サービスが必須のアイデアは除外**（Rule 21: 月額収益 $29 vs API コスト $300+）。オンデバイスロジック or 静的キュレーションコンテンツで代替できる場合のみ PASS

---

### 4. Scoring and Ranking

#### 計算式:

```
overall_score = (S×1.5 + P×1.0 + M×1.0 + C×1.0 + T×1.5) / 6.0
```

| 略称 | 次元 | 重み |
|------|------|------|
| S | Solo Dev Scope | 1.5x |
| P | Platform API Fit | 1.0x |
| M | Monetization Viability | 1.0x |
| C | Competition（低競合 = 高スコア） | 1.0x |
| T | Technical Fit | 1.5x |

#### 計算例:
S=8, P=7, M=9, C=6, T=8
→ (8×1.5 + 7 + 9 + 6 + 8×1.5) / 6.0 = (12+7+9+6+12) / 6.0 = **7.67**

**Filtering 通過アイデアを overall_score 降順でソートし、Top 3 を Shortlist にする。**

---

### 5. Shortlist Output (Top 3)

各アイデアに以下のフィールドを必ず含める:

| フィールド | 内容 |
|-----------|------|
| rank | 1-5 |
| idea | アプリ名（英語、キャメルケース） |
| one_liner | 1文で何をするアプリか |
| lens | どの Lens から生まれたか（Lens 1-5） |
| platform | iOS 17+ |
| problem_statement | 解決する問題（2-3文） |
| target_user | ターゲットユーザー（年齢、状況、ペイン） |
| feasibility | S:X P:X M:X C:X T:X（各 1-10） |
| overall_score | 計算式の結果（小数点1桁） |
| monetization_model | Freemium + Subscription ($X.XX/月, $XX.XX/年) |
| competition_notes | 主要競合アプリ名、レビュー数、弱点 |
| mvp_scope | MVP に含める機能（3-5個） |
| next_step | 「US-002 で product-plan.md を作成」 |

---

## Output

### ディレクトリ作成（Shortlist 確定後・Rank 1 決定後に実行）

```bash
# APP_NAME = Rank 1 のアプリ名を kebab-case に変換
# 例: StretchFlow → stretch-flow, EyeRest → eye-rest
APP_NAME="<kebab-case-app-name>"
mkdir -p mobile-apps/${APP_NAME}/spec
```

### ファイル出力

`mobile-apps/${APP_NAME}/spec/01-trend.md` に以下のテンプレートで出力:

```markdown
# Trend Research: [App Name]

## Developer Profile

| 項目 | 値 |
|------|-----|
| Platform | iOS 17+ (Swift/SwiftUI) |
| Scope | 4-8 weeks (solo dev) |
| Monetization | Subscription ($X.XX/月, $XX.XX/年) |

## Lenses Applied

### Lens 1: Skills & Interests
（5+ アイデア + 根拠）

### Lens 2: Problem-First
（5+ アイデア + 検索クエリ + ソース）

### Lens 3: Technology-First
（5+ アイデア + 検索クエリ + ソース）

### Lens 4: Market Gap
（5+ アイデア + iTunes API 結果 + ★1-2 レビューからの洞察）

### Lens 5: Trend-Based
（5+ アイデア + TikTok ビュー数 + WebSearch ソース）

## Feasibility Filtering

| アイデア | S | P | M | C | T | 結果 |
|---------|---|---|---|---|---|------|
| ... | X | X | X | X | X | PASS / FAIL（理由） |

## Shortlist (Top 3)

### Rank 1: [App Name]

| Field | Value |
|-------|-------|
| one_liner | ... |
| lens | Lens X |
| platform | iOS 17+ |
| problem_statement | ... |
| target_user | ... |
| feasibility | S:X P:X M:X C:X T:X |
| overall_score | X.X |
| monetization_model | ... |
| competition_notes | ... |
| mvp_scope | ... |
| next_step | US-002 で product-plan.md を作成 |

### Rank 2: [App Name]
（同じテーブル形式）

...

### Rank 5: [App Name]
（同じテーブル形式）

## Ideas Filtered Out

| アイデア | 除外理由 |
|---------|---------|
| ... | S=3（Solo Dev Scope 不足） |
| ... | Step 0 除外カテゴリ（呼吸法） |

## Recommendation

**選定アプリ:** [Rank 1 のアプリ名]
**理由:** （3-5文。スコア、競合の弱さ、トレンドの強さを引用）
**ソース:** （判断の根拠となった URL を列挙）
```

---

## Acceptance Criteria

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | `mobile-apps/<app>/spec/01-trend.md` が存在する | `test -f mobile-apps/<app>/spec/01-trend.md` |
| 2 | Raw ideas が最低5個（5 Lens × 1個）生成されている | 01-trend.md の各 Lens セクションにアイデア1個以上 |
| 3 | Feasibility Filtering テーブルが存在する | PASS/FAIL + 理由が全アイデアに付いている |
| 4 | Top 3 Shortlist が存在し、全フィールドが埋まっている | 13フィールド × 3アイデア |
| 5 | overall_score が計算式通りに算出されている | 手動検算で一致 |
| 6 | 各トレンドにソース（URL）が引用されている | grep で URL が 3件以上 |
| 7 | Step 0 の除外カテゴリが動的に生成されている | `ls mobile-apps/` の結果と一致 |
| 8 | TikTok ビュー数データが含まれている（Lens 5） | ビュー数の数値が記載 |
| 9 | ★1-2 App Store レビューが引用されている（Lens 4） | レビュー本文が記載 |
