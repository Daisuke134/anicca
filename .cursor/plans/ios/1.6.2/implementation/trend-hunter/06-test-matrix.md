## テスト可能なコード境界（P0-1）

### アーキテクチャ原則

```
Pure Functions（決定論的・テスト容易）
    ↕ データだけやり取り
Mockable Interfaces（外部API・LLM呼び出し）
```

**純粋関数**: 同じ入力 → 常に同じ出力。副作用なし。ユニットテストのみで100%カバー。
**Mockableインターフェース**: 外部APIやLLMの呼び出し。テスト時はモックに差し替え。

### モジュール一覧

| モジュール | 種別 | 責務 | 入力 | 出力 |
|-----------|------|------|------|------|
| `queryBuilder` | Pure | ProblemType → 検索クエリ文字列を組み立て | `(problemType, contentType, lang)` | `string` |
| `rotationSelector` | Pure | 実行回数からローテーショングループを選択 | `(executionCount)` | `string[]`（ProblemType配列） |
| `twitterResponseParser` | Pure | TwitterAPI.io の生JSONを正規化 | `(rawJson, meta)` | `NormalizedTrend[]` |
| `redditResponseParser` | Pure | reddapi.dev の生JSONを正規化 | `(rawJson, meta)` | `NormalizedTrend[]` |
| `tiktokResponseParser` | Pure | Apify TikTok の生JSONを正規化 | `(rawJson)` | `NormalizedTrend[]` |
| `viralityFilter` | Pure | メトリクス閾値でフィルタ | `(trends[], thresholds)` | `NormalizedTrend[]` |
| `textSimilarity` | Pure | 2テキスト間の類似度計算（Jaccard） | `(text1, text2)` | `number`（0.0-1.0） |
| `slackFormatter` | Pure | 結果サマリーをSlackメッセージ文字列に変換 | `(results)` | `string` |
| `twitterApiClient` | Mockable | TwitterAPI.io への HTTP呼び出し | `(query, options)` | `Promise<RawTwitterResponse>` |
| `redditApiClient` | Mockable | reddapi.dev への HTTP呼び出し | `(query, options)` | `Promise<RawRedditResponse>` |
| `tiktokApiClient` | Mockable | Apify Actor 実行 + 結果取得 | `(region, options)` | `Promise<RawTikTokResponse>` |
| `llmClient` | Mockable | LLMフィルタ + hook生成 | `(prompt, data)` | `Promise<LlmResponse>` |
| `railwayApiClient` | Mockable | Railway API GET/POST hooks | `(method, data?)` | `Promise<ApiResponse>` |
| `orchestrator` | 統合 | 全モジュールを繋いで実行 | `(config: OrchestratorConfig)` | `Promise<ExecutionResult>` |

### 正規化データ型

```typescript
// 全ソース共通の正規化型
interface NormalizedTrend {
  id: string;                          // ソース固有ID
  source: 'x' | 'tiktok' | 'reddit' | 'github';
  problemType: string;                 // 検索時のProblemType
  contentType: 'empathy' | 'solution'; // 検索クエリの種別
  lang: 'ja' | 'en';
  text: string;                        // 本文 or ハッシュタグ名
  url: string | null;                  // 元投稿URL
  metrics: {
    engagement: number;                // ソースごとの主要指標（正規化済み）
    // X: likeCount, Reddit: upvotes, TikTok: viewCount
  };
  author: string | null;
  raw: Record<string, unknown>;        // パーサーが捨てなかった元データ
}

// LLMフィルタ出力型
interface FilteredTrend {
  trendId: string;
  relevanceScore: number;              // 0-10
  virality: 'high' | 'medium' | 'low';
  contentType: 'empathy' | 'solution';
  problemTypes: string[];
  angle: string;
  skipReason: string | null;
}

// hook候補型（trend-hunter が生成する中間型 → POST /api/agent/hooks で保存）
interface HookCandidate {
  text: string;                        // hookテキスト（max 500 chars）— DB: hook_candidates.text
  contentType: 'empathy' | 'solution';
  targetProblemTypes: string[];        // DB: hook_candidates.target_problem_types（配列）
  platform: 'x' | 'tiktok' | 'both';
  trendSource: {
    platform: string;
    url: string | null;
    hashtags: string[];
    metrics: Record<string, number>;
  };
  angle: string;
}

// Railway API GET /api/agent/hooks のレスポンス型
// closed-loop-ops DB の hook_candidates テーブルと一致
interface HookFromAPI {
  id: string;
  text: string;                        // hookテキスト（HookCandidate.text と同一）
  targetProblemTypes: string[];        // ProblemType 配列
  source: string;                      // 'trend-hunter'
  platform: string;
  xSampleSize: number;                 // X投稿回数（executeAnalyzeEngagement が更新）
  xEngagementRate: number;             // X エンゲージメント率（%）
  tiktokSampleSize: number;            // TikTok投稿回数
  tiktokLikeRate: number;              // TikTok いいね率（%）
  createdAt: string;
}

// --- ソース別バイラル閾値（P0 #7 解消）---
// 各ソースの engagement 指標が異なるため、ソース別に閾値を定義
const VIRALITY_THRESHOLDS: Record<NormalizedTrend['source'], number> = {
  x: 1000,        // likeCount >= 1000
  reddit: 100,    // upvotes >= 100
  tiktok: 10000,  // viewCount >= 10,000
  github: 50,     // stars >= 50（補助データ）
};
// viralityFilter はこの定数を使って判定する:
// trend.metrics.engagement >= VIRALITY_THRESHOLDS[trend.source]

// --- Orchestrator Config（P0 #8 解消）---
interface OrchestratorConfig {
  executionCount: number;           // 現在の実行回数（ローテーション決定用）
  targetTypes?: ProblemType[];      // 明示指定時はローテーションを上書き
  enabledSources: {
    x: boolean;                     // TwitterAPI.io
    tiktok: boolean;                // Apify
    reddit: boolean;                // reddapi
    github: boolean;                // GitHub Trending
  };
  llmChain: Array<{
    model: string;
    timeout: number;
  }>;
  dryRun?: boolean;                 // true: API保存をスキップ（テスト用）
  similarityThreshold?: number;     // デフォルト 0.7
}

interface ExecutionResult {
  scannedCount: number;             // 収集したトレンド総数
  filteredCount: number;            // LLMフィルタ通過数
  savedCount: number;               // Railway API に保存した hook 数
  skippedDuplicates: number;        // 重複スキップ数
  errors: Array<{
    source: string;
    error: string;
  }>;
  targetTypes: ProblemType[];       // 今回検索したProblemType
  duration: number;                 // 実行時間（ms）
}

// --- Railway API Client 詳細（P0 #9 解消）---
// Mockable Interfaces の railwayApiClient を詳細化
type SaveHookResult =
  | { status: 'created'; id: string; text: string; createdAt: string }
  | { status: 'duplicate'; existingId: string };

interface RailwayApiClient {
  getHooks(): Promise<{ hooks: Hook[] }>;
  saveHook(hook: HookSavePayload): Promise<SaveHookResult>;
  emitEvent(event: EventPayload): Promise<{ id: string }>;
}

interface HookSavePayload {
  text: string;                     // HookSaveSchema.text（max 500 chars）
  targetProblemTypes: ProblemType[]; // HookSaveSchema.targetProblemTypes（配列）
  source: 'trend-hunter';
  platform: 'x' | 'tiktok' | 'both'; // HookSaveSchema.platform
  contentType: 'empathy' | 'solution'; // HookSaveSchema.contentType
  idempotencyKey?: string;           // DLQリトライ時の重複防止キー（オプション）
  metadata?: {
    trendSource: HookCandidate['trendSource'];
    angle: string;
  };
}

interface Hook {
  id: string;
  text: string;                      // DB: hook_candidates.text
  targetProblemTypes: ProblemType[];  // DB: hook_candidates.target_problem_types
  source: string;
  platform: string;
  xSampleSize: number;
  xEngagementRate: number;
  tiktokSampleSize: number;
  tiktokLikeRate: number;
  createdAt: string;
}

interface EventPayload {
  source: string;
  kind: string;
  tags: string[];
  payload: Record<string, unknown>;
}
```

---

## テストマトリックス（P0-2）

### Pure Functions テスト

#### queryBuilder

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 1 | `test_queryBuilder_empathy_ja` | `('staying_up_late', 'empathy', 'ja')` | `'"また3時だ" OR "夜更かし やめられない"'` を含む文字列 | 日本語共感系 |
| 2 | `test_queryBuilder_solution_en` | `('staying_up_late', 'solution', 'en')` | `'"how to fix sleep schedule" OR "screen time before bed"'` を含む文字列 | 英語問題解決系 |
| 3 | `test_queryBuilder_all_problemTypes` | 13個のProblemType全て | 全てnon-emptyの文字列を返す（null/undefinedなし） | 辞書網羅 |
| 4 | `test_queryBuilder_unknown_type_throws` | `('invalid_type', 'empathy', 'ja')` | `Error` をthrow | 不正入力 |
| 5 | `test_queryBuilder_min_faves_appended` | `('anxiety', 'empathy', 'en')` に `{minFaves: 1000}` オプション | `'min_faves:1000'` が末尾に付与 | X検索オプション |

#### rotationSelector

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 6 | `test_rotation_group0` | `executionCount=0` | `['staying_up_late','cant_wake_up','self_loathing','rumination','procrastination']` | グループ0 |
| 7 | `test_rotation_group1` | `executionCount=1` | `['anxiety','lying','bad_mouthing','porn_addiction']` | グループ1 |
| 8 | `test_rotation_group2` | `executionCount=2` | `['alcohol_dependency','anger','obsessive','loneliness']` | グループ2 |
| 9 | `test_rotation_wraps` | `executionCount=3` | グループ0と同じ | 循環 |
| 10 | `test_rotation_large_number` | `executionCount=999` | グループ `999%3=0` | 大きい数 |

#### twitterResponseParser

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 11 | `test_parse_twitter_valid` | モックレスポンス（tweets配列2件） | `NormalizedTrend[]` 長さ2、source='x'、metrics.engagement=likeCount | 正常系 |
| 12 | `test_parse_twitter_empty` | `{"tweets":[],"has_next_page":false}` | 空配列 | 空レスポンス |
| 13 | `test_parse_twitter_missing_author` | author=null のtweet | `NormalizedTrend` でauthor=null、url=null | 欠損データ |
| 14 | `test_parse_twitter_malformed_json` | `"not json"` | `Error` をthrow | 不正JSON |

#### redditResponseParser

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 15 | `test_parse_reddit_valid` | モックレスポンス（results配列3件） | `NormalizedTrend[]` 長さ3、source='reddit'、metrics.engagement=upvotes | 正常系 |
| 16 | `test_parse_reddit_empty` | `{"success":true,"data":{"results":[]}}` | 空配列 | 空レスポンス |
| 17 | `test_parse_reddit_api_error` | `{"success":false,"error":"Rate limited"}` | `Error` をthrow | APIエラー |

#### tiktokResponseParser

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 18 | `test_parse_tiktok_valid` | モックレスポンス（ハッシュタグ配列2件） | `NormalizedTrend[]` 長さ2、source='tiktok'、metrics.engagement=viewCount | 正常系 |
| 19 | `test_parse_tiktok_filter_promoted` | `isPromoted: true` のハッシュタグ含む | promotedを除外 | プロモ除外 |
| 20 | `test_parse_tiktok_empty` | `[]` | 空配列 | 空レスポンス |

#### viralityFilter

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 21 | `test_filter_above_threshold` | engagement=5000, threshold=1000 | 通過（配列に含む） | 閾値以上 |
| 22 | `test_filter_below_threshold` | engagement=500, threshold=1000 | 除外（配列に含まない） | 閾値未満 |
| 23 | `test_filter_exact_threshold` | engagement=1000, threshold=1000 | 通過（>=で判定） | 境界値 |
| 24 | `test_filter_mixed` | 5件中2件が閾値以上 | 長さ2の配列 | 混在 |
| 25 | `test_filter_source_specific_thresholds` | X=1000, Reddit=100, TikTok=10000 のソース別閾値 | 各ソースの閾値で判定 | ソース別閾値 |

#### textSimilarity

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 26 | `test_similarity_identical` | `("hello world", "hello world")` | `1.0` | 完全一致 |
| 27 | `test_similarity_different` | `("hello world", "goodbye moon")` | `< 0.3` | 完全不一致 |
| 28 | `test_similarity_partial` | `("夜更かし やめたい", "夜更かし やめられない つらい")` | `0.3 < x < 0.8` | 部分一致 |
| 29 | `test_similarity_empty_string` | `("", "hello")` | `0.0` | 空文字列 |
| 30 | `test_similarity_threshold_check` | 類似度 > 0.8 のペア | `isDuplicate = true` | 重複判定閾値 |

#### slackFormatter

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 31 | `test_format_normal` | tiktok:3, reddit:5, x:10, saved:4 | ソース別件数 + 保存件数を含むメッセージ | 正常系 |
| 32 | `test_format_all_zero` | 全ソース0件 | 「トレンド0件」を含むメッセージ | 空結果 |
| 33 | `test_format_source_failure` | reddit: error | 「Reddit: エラー」を含むメッセージ | 部分失敗 |

### Mockable Interfaces テスト（統合テスト）

| # | テスト名 | モック設定 | 期待動作 | カバー |
|---|---------|----------|---------|--------|
| 34 | `test_orchestrator_happy_path` | 全API正常レスポンス + LLM正常出力 | hook候補がRailway APIに保存される | E2Eハッピーパス |
| 35 | `test_orchestrator_twitter_down` | twitterApiClient → Error | TikTok+Redditの結果のみで続行、Slackに警告 | X障害時 |
| 36 | `test_orchestrator_all_sources_down` | 全ApiClient → Error | Slack #alertsに通知、DLQに記録、hookは0件 | 全障害 |
| 37 | `test_orchestrator_llm_fallback` | llmClient gpt-4o → Error, gpt-4o-mini → 正常 | フォールバックで正常完了 | LLMフォールバック |
| 38 | `test_orchestrator_duplicate_skip` | railwayApiClient.getHooks → 既存hookと類似度0.9 | 保存スキップ、ログに記録 | 重複チェック |
| 39 | `test_orchestrator_railway_save_fail` | railwayApiClient.saveHook → Error | DLQに書き込み、次回リトライ | 保存失敗 |
| 40 | `test_orchestrator_rotation` | executionCount=0, 1, 2 を順に実行 | 各グループの ProblemType で検索される | ローテーション |
| 41 | `test_orchestrator_duplicate_server_response` | railwayApiClient.saveHook → `{ status: 'duplicate', existingId: 'xxx' }` | savedCount不変、skippedDuplicates+1、hook_savedイベント未発行 | サーバー側重複応答 |

---

