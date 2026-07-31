# US-002: Product Planning

Source: rshankras product-agent
URL: https://github.com/rshankras/claude-code-apple-skills/blob/main/skills/product/WORKFLOW.md

## Source Skills (参考のみ — 読み込み不要。コマンドは下記に全てインライン)
元ネタ: prd-generator, app-store-scraper

## Input
`spec/01-trend.md`（Rank 1 のアイデア）— 以下のフィールドを product-plan.md にマッピング:

| 01-trend.md フィールド | → product-plan.md セクション |
|----------------------|---------------------------|
| `target_user` | §1 Target User → Primary |
| `problem_statement` | §2 Problem → Core Problem |
| `one_liner` | §3 Solution → One-Liner |
| `monetization_model` | §4 Monetization → Pricing Strategy |
| `mvp_scope` | §5 MVP Scope → Must Have |
| `competition_notes` | §2 Problem → Why Existing Solutions Fail |
| `feasibility` | §7 Risk Assessment |

---

## Process: 4 Agents（ステップバイステップ）

Source: [arXiv: Deep Research Survey](https://arxiv.org/html/2508.12752v1) — 「The agent performs a search, generates an answer, then reflects on its quality. Based on reflection, initiates further planning and search, iterating until satisfactory.」

### Agent 1: Problem Discovery Agent

**入力:** 01-trend.md の `problem_statement` + `target_user`
**出力:** §1 Target User + §2 Problem

| Step | アクション | 検索クエリテンプレート |
|------|-----------|---------------------|
| 1 | 01-trend.md を読み、痛みの核心を1文で定義 | — |
| 2 | ターゲットユーザーの痛み統計を検索（3クエリ以上） | `"{problem} statistics {year}"`, `"{target_user} pain points survey"`, `「{問題} 統計 {年}」` |
| 3 | 市場規模（TAM/SAM/SOM に使える数字）を検索 | `"{problem} market size TAM"`, `"{category} market size forecast"` |
| 4 | 既存解決策が失敗する理由を3つ以上列挙 | `"{category} app review site:apps.apple.com"` + app-store-scraper で競合取得 |
| 5 | Gap in Market を1文で定義 | — |

**検索ルール:**
- 各セクション最低3クエリ、英語+日本語
- 見つからない → キーワード一般化 → 隣接分野
- Source: [arXiv: LLM Deep Search Survey](https://arxiv.org/html/2508.05668v3) — 「Decomposition-based approaches break into smaller sub-queries executed in parallel.」

### Agent 2: MVP Scoping Agent

**入力:** Problem セクション + 01-trend.md の `mvp_scope`
**出力:** §5 MVP Scope

| Step | アクション |
|------|-----------|
| 1 | 01-trend.md の `mvp_scope` を機能候補リストとして取得 |
| 2 | MoSCoW 法で4分類 |
| 3 | Must-Have に「1日で実装可能か？」フィルタ適用 |
| 4 | Won't Have に理由を付ける（`Scope overflow — v1.1 候補` 等） |
| 5 | Technical Architecture（ディレクトリ構造）を生成 |
| 6 | Localization テーブル（en-US + ja）を追加 |

**PROHIBITED FEATURES（MVPファクトリーでは使用禁止 — Fix #10）:**

Source: RevenueCat SOSA 2026 — https://www.revenuecat.com/state-of-subscription-apps/
核心の引用: 「Despite a 7× surge in new app launches since 2022, apps launched before 2020 still account for nearly 70 cents of every dollar generated. Apps launched in 2025 or later (aka, the vibe coding era) account for just 3%.」
→ シンプルでも確実にApp Store通過するほうが量が稼げる。複雑さは敵。

Source: Uptech MVP Guide — https://www.uptech.team/blog/build-an-mvp
核心の引用: 「Solve one core problem. Focus on what matters most to your users, not every possible feature. Keep it simple but solid.」

| 🚫 PROHIBITED（Must Never Have） | 理由 |
|----------------------------------|------|
| Dynamic Island / Live Activities | WidgetKit Extension 必要、Maestro E2E テスト困難 |
| Widgets (WidgetKit) | Extension Target 追加、テスト困難、レビュー複雑化 |
| LLM API 呼び出し（OpenAI/Anthropic/Gemini/FoundationModels） | コスト発生、APIキー管理必要、ユーザーにAPIキー入力させるのはUX最悪 |
| バックエンドサーバー必須の機能 | インフラコスト、メンテ、障害リスク |
| HealthKit / ScreenTime API | 権限管理が複雑、審査で追加説明必要 |
| カメラ / マイク | プライバシー審査が厳しくなる、NSUsageDescription 必要 |
| Sign in with Apple（認証フロー） | テスト困難、Maestro E2E で自動化不可 |
| CoreData / CloudKit sync | 複雑、デバッグ困難。SwiftData or UserDefaults で十分 |

PROHIBITEDに該当しない全てのSwiftUI標準テクノロジーは使用可能。CCはPRDのトレンドリサーチとMVPスコープに基づき自由に技術選定してよい。

**Agent 2 は Must Have 判定時に PROHIBITED リストを必ず参照し、PROHIBITED に該当する機能は自動的に Won't Have に分類すること。**

**MoSCoW 判定フロー:**
Source: [ProductPlan: MoSCoW](https://www.productplan.com/glossary/moscow-prioritization/) — 「Must Have: Critical for current delivery. Won't Have: Agreed as out of scope.」

```
機能候補リスト
    ↓
Q1: コアの痛みを直接解決するか？ → No → Won't Have
    ↓ Yes
Q2: 1日で実装可能か？ → No → Won't Have（v1.1候補）
    ↓ Yes
Q3: サブスクなしで動くか？ → Yes → Free tier
                             → No → Premium tier
    ↓
Must Have テーブルに追加
```

### Agent 3: Positioning Agent

**入力:** MVP Scope + 01-trend.md の `competition_notes`
**出力:** §3 Solution + §4 Monetization

| Step | アクション |
|------|-----------|
| 1 | app-store-scraper で競合5個の詳細を取得（下記手順） |
| 2 | 機能/価格/レーティング比較テーブル生成 |
| 3 | 差別化ポイント1つ決定 + Key Differentiators テーブル |
| 4 | 価格設定（下記ルール準拠） |
| 5 | RevenueCat Integration テーブル生成 |

**競合分析手順:**
Source: [AppTweak](https://www.apptweak.com/en/aso-blog/step-by-step-guide-aso-competitor-analysis) — 「Examine keywords in titles, subtitles, descriptions; check update frequency.」
Source: [Appark.ai](https://appark.ai/en/blog/mobile-app-competitor-analysis) — 「Create spreadsheet with app name, type, rank, downloads, monetization model, feature notes.」

```bash
# Step 1: カテゴリ検索（5キーワード）
for KEYWORD in "keyword1" "keyword2" "keyword3" "keyword4" "keyword5"; do
  curl -s "https://itunes.apple.com/search?term=${KEYWORD}&media=software&entity=software&limit=10" | \
    jq '.results[] | {name: .trackName, rating: .averageUserRating, reviews: .userRatingCount, price: .formattedPrice}'
  sleep 2
done

# Step 2: 上位5個を比較テーブルに整理
# 分析項目: trackName, price, averageUserRating, userRatingCount, description（先頭200文字）
# ダウンロード数推定 = レビュー数 × 50-100（業界目安）
```

**価格設定ルール:**
Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「H&F median: $7.73/mo, $29.65/yr. Higher prices = higher trial conversion.」
Source: jake-mor.md #15 — 「Prices aren't random — they convert to clean weekly/monthly amounts.」
Source: jake-mor.md #17 — 「Two-product strategy: trial-less monthly + trialed annual at 50% apparent discount.」
Source: [RevenueCat 2025 Trends](https://www.revenuecat.com/blog/growth/2025-subscription-app-monetization-trends/) — 「Premium pricing is the new norm. Middle ground is shrinking.」

| ルール | 根拠 |
|--------|------|
| Monthly = H&F median ($7.73) の 50-130% 範囲内 | RevenueCat SOSA 2025 |
| Annual = Monthly × 12 の 50-65% off に見える価格 | Jake Mor #17 |
| Annual 実額 = H&F median ($29.65) ± 15% | RevenueCat SOSA 2025 |
| 価格はクリーンな週額に変換可能 | Jake Mor #15 |
| RevenueCat Integration テーブル必須 | SDK, Offering, Entitlement, Paywall 方式 |
| **RevenueCatUI 禁止 — 自前 SwiftUI PaywallView** | Rule 20 |
| **[Maybe Later] ボタン必須** | Rule 20（ソフトペイウォール） |

### Agent 4: ASO Optimization Agent

**入力:** Solution セクション + 競合分析
**出力:** §6 App Identity

| Step | アクション |
|------|-----------|
| 1 | アプリ名一意性チェック（下記手順） |
| 2 | App Title = Jake Mor フォーマット適用 |
| 3 | ASO キーワード8個選定 |
| 4 | Bundle ID 決定 |

**アプリ名一意性チェック手順:**
Source: [Apple iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/)

```bash
# Step 1: 第一候補を検索
curl -s "https://itunes.apple.com/search?term=APP_NAME&media=software&entity=software&limit=10" | \
  jq '[.results[] | select(.trackName | ascii_downcase | contains("app_name_lower"))] | length'

# Step 2: 完全一致あり → 代替名を5個生成
# 命名パターン: {Verb}{Noun}, {Adj}{Noun}, {Noun}{Tool}
# 全候補を同手順でチェック

# Step 3: 0 matches の名前を採用 → product-plan.md に記録
# 記録内容: 「✅ 0 exact matches (verified YYYY-MM-DD)」
```

**App Title フォーマット:**
Source: jake-mor.md #53 — App title format: `"Keyword - AppName"`
例: `"Desk Stretching - DeskStretch"`, `"Personal Trainer - FitnessAI"`

**Bundle ID ルール:**
Source: [Apple Developer: CFBundleIdentifier](https://developer.apple.com/documentation/bundleresources/information_property_list/cfbundleidentifier) — 「Use reverse-DNS format. Each component: alphanumeric, period, hyphen only. Cannot change after submission.」

フォーマット: `com.aniccafactory.{appname}` — appname は小文字英数字のみ、ハイフン可

---

## Output Template

`product-plan.md` — 以下の7セクション構成（この順序で出力）:

Source: [Product School: PRD Template](https://productschool.com/blog/product-strategy/product-template-requirements-document-prd) — 「Essential sections: Overview, Success Metrics, Messaging, Timeline, Personas.」
Source: [Atlassian: PRD](https://www.atlassian.com/agile/product-management/requirements) — 「Include goals, assumptions, user stories, design, clear out-of-scope items.」

### 必須セクション

| # | セクション | 必須コンテンツ |
|---|-----------|--------------|
| 1 | **Target User** | Primary, Demographics, Pain Point, Behavior, Willingness to Pay テーブル + Market Size Evidence テーブル（2+ ソース） |
| 2 | **Problem** | Core Problem（日本語1文）+ Why Existing Solutions Fail テーブル（3+ 競合）+ Gap in Market（1文） |
| 3 | **Solution** | One-Liner + How It Works（ASCII フロー図）+ Key Differentiators テーブル（3列: 自社 vs 競合A vs 競合B）+ Technology テーブル |
| 4 | **Monetization** | Pricing Strategy テーブル（Free/Monthly/Annual 3行）+ Pricing Justification テーブル（3+ ソース）+ Revenue Model テーブル + RevenueCat Integration テーブル |
| 5 | **MVP Scope** | Must Have テーブル（# / Feature / Description）+ Won't Have テーブル（Feature / Reason）+ Technical Architecture（ディレクトリ構造コードブロック）+ Localization テーブル |
| 6 | **App Identity** | App Name, Bundle ID, Subtitle, Category, Age Rating, iTunes Name Check テーブル + ASO Keywords テーブル（Priority / Keyword / Rationale） |
| 7 | **Risk Assessment** | Risk / Impact / Mitigation テーブル（5+ 行） |

### 末尾必須
**Sources Summary** テーブル（# / Source / What It Supports）— 10+ ソース

---

## Source Citation Rules

Source: [Anthropic: Reduce Hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations) — 「Citation-based responses significantly reduce hallucination rates.」

| ルール | 詳細 |
|--------|------|
| 合計 10+ ソース | 全体で最低10個の外部ソース |
| Target User | 2+ ソース（学術論文、業界統計） |
| Problem | 2+ ソース（医療/産業統計） |
| Solution | 1+ ソース（Apple Developer Docs 等） |
| Monetization | 3+ ソース（RevenueCat, jake-mor.md, 競合価格） |
| Risk Assessment | 2+ ソース（App Store リジェクト統計、市場データ） |
| フォーマット | `[Source Name](URL) — 「原文引用」` |

---

## Risk Assessment Instructions

Source: [Full Scale: Risk Assessment](https://fullscale.io/blog/risk-assessment-for-startups/) — 「Companies with formal risk plans experience 30% fewer operational disruptions.」
Source: [Twinr: App Store Rejections 2025](https://twinr.dev/blogs/apple-app-store-rejection-reasons-2025/) — 「Privacy violations = leading cause. 15% of submissions rejected. Over 40% of unresolved issues = Guideline 2.1 App Completeness.」

**必須リスクカテゴリ（5つ以上）:**

| カテゴリ | 含めるべきリスク例 |
|---------|------------------|
| **技術リスク** | iOS バージョン制限、Foundation Models 依存、API 制限 |
| **市場リスク** | 低コンバージョン、競合のAI追加、市場飽和 |
| **App Store リジェクト** | Privacy Manifest 未申告（ITMS-91053）、App Completeness（Guideline 2.1）、4.3 Spam |
| **ユーザーリスク** | チャーン、ノベルティ消失、低 trial-to-paid |
| **収益リスク** | 価格が低すぎ/高すぎ、Annual 比率低迷 |

**テンプレート:** `| Risk | Impact | Mitigation |`

---

## US-002 vs US-004 の境界

| US-002 (product-plan.md) | US-004 (docs/PRD.md + 6ドキュメント) |
|--------------------------|-------------------------------------|
| ビジネス・市場計画 | 技術仕様書 |
| ターゲットユーザー、問題、解決策 | ARCHITECTURE.md, UX_SPEC.md |
| 価格設定、マネタイズ | IMPLEMENTATION_GUIDE.md |
| MVP スコープ（機能一覧） | TEST_SPEC.md, RELEASE_SPEC.md |
| **What & Why を定義** | **How を定義** |

US-002 は「何を作るか、なぜ作るか、誰に売るか」。
US-004 は「どう作るか、どうテストするか、どうリリースするか」。
重複を避ける: 技術仕様は US-002 に書かない。

---

## Acceptance Criteria

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | product-plan.md exists | `ls product-plan.md` |
| 2 | Contains: target user, problem, solution, monetization, MVP scope | `grep -c "## [1-7]" product-plan.md` ≥ 7 |
| 3 | monetization specifies subscription prices (monthly + annual) | `grep -c "\\$/mo\|\\$/yr" product-plan.md` ≥ 2 |
| 4 | All claims cite external sources | `grep -c "http" product-plan.md` ≥ 10 |
| 5 | curl itunes.apple.com/search for APP_NAME returns 0 exact name matches | iTunes API 検証済み記録あり |
| 6 | Typecheck passes | N/A（ドキュメントのみ） |
