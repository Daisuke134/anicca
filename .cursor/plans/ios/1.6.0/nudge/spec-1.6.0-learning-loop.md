# Spec: 1.6.0 Learning Loop — X Metrics + Cross-Platform Pipeline + Schedule Unification

## 開発環境

| 項目 | 値 |
|------|-----|
| **ワークツリーパス** | `/Users/cbns03/Downloads/anicca-1.6.0-one-buddha` |
| **ブランチ** | `feature/1.6.0-one-buddha` |
| **ベースブランチ** | `dev` |
| **作業状態** | Spec作成中 |

---

## 1. 概要（What & Why）

### What

1.6.0 One Buddha の Phase 5（Cross-Platform Learning）が未完成。以下を完成させる:

1. **X API メトリクス取得** — X API v2 Free Tier で自分の投稿の `public_metrics` を取得
2. **Cross-Platform Learning Pipeline 配線** — 定義済みの4関数を `generateNudges.js` 冒頭で実行
3. **TikTok/X スケジュール統一** — 両方とも 9:00 JST + 21:00 JST の2投稿に統一
4. **Commander Agent スキーマ変更** — tiktokPost(単数) → tiktokPosts(複数, morning/evening)

### Why

現状、Commander Agent は App nudge + TikTok + X の全チャネルを決定するが:
- X に投稿した後、**メトリクスを回収するコードがない** → 何が効いたか分からない
- `refreshBaselines()`, `syncXMetricsToHookCandidates()`, `identifyPromotions()`, `executePromotions()` が**どのcronからも呼ばれていない** → 学習ループが回っていない
- TikTok は曜日別自律スケジュール、X は 9am+9pm。統一されていない
- Commander Agent の `tiktokPost` が単数 → 9am/9pm の2投稿に対応できない

### 完成後のフロー（1日のタイムライン）

```
05:00 JST  Commander Agent 実行（Railway Cron）
           ├── App Nudges: 問題×タイムスロット（既存通り）
           ├── TikTok: morning (9am) + evening (9pm) の2投稿を決定
           └── X: morning (9am) + evening (9pm) の2投稿を決定
           → notification_schedules に保存

08:50 JST  TikTok Agent (GHA) — morning スロット投稿
08:50 JST  X Agent (GHA) — morning スロット投稿

09:00 JST  TikTok/X 朝の投稿がタイムラインに出現

10:00 JST  TikTok メトリクス取得 (GHA, 既存) — 昨日の投稿
10:00 JST  X メトリクス取得 (GHA, 新規) — 昨日の投稿

20:50 JST  TikTok Agent (GHA) — evening スロット投稿
20:50 JST  X Agent (GHA) — evening スロット投稿

21:00 JST  TikTok/X 夜の投稿がタイムラインに出現

翌 05:00 JST  Commander Agent 再実行（generateNudges.js）
              1. Cross-Platform Learning（generateNudges 内で最初に実行）
                 a. refreshBaselines() — Z-Score 基準値更新
                 b. syncXMetricsToHookCandidates() — X メトリクス → HookCandidate
                 c. identifyPromotions() — X→TikTok, TikTok→App 候補抽出
                 d. executePromotions() — プロモーション実行
              2. Commander Agent が最新の crossPlatformData で判断
              → 学習ループが回る
```

---

## 2. 受け入れ条件

| # | 条件 | テスト可能な形式 |
|---|------|-----------------|
| AC-1 | X API v2 で `xPostId` を使って `public_metrics` を取得できる（取得できた投稿・フィールドのみ部分更新。欠落フィールドは既存値維持） | `fetch_x_metrics.py` 実行 → `x_posts` テーブルの取得できたフィールド（`impression_count`, `like_count`, `retweet_count`, `reply_count`）が更新される。欠落フィールドは null 上書きしない。`xPostId` が null のレコードはスキップ |
| AC-2 | X メトリクス取得 GHA が毎日 10:00 JST に実行される | `.github/workflows/fetch-x-metrics.yml` の cron が `0 1 * * *` |
| AC-3 | Cross-Platform Learning の4関数が日次で実行される | `generateNudges.js` 内の冒頭で `runCrossPlatformSync()` が呼ばれ、4関数が順番に実行される |
| AC-4 | `refreshBaselines()` が x_posts の30日データから X_MEAN/X_STDDEV を更新する（メトリクス取得は直近7日） | テスト: 10件のx_postsデータ投入後、baselines が更新される |
| AC-5 | `syncXMetricsToHookCandidates()` が HookCandidate の X フィールドを更新する | テスト: x_posts にメトリクスあり → hook_candidates.x_engagement_rate が非null |
| AC-6 | Commander Agent の出力スキーマが `tiktokPosts: [{slot: "morning"}, {slot: "evening"}]` に変更される | Zod schema validation テスト |
| AC-7 | TikTok Agent が morning/evening スロットを区別して投稿する | GHA 8:50 JST 実行 → morning 投稿。20:50 JST 実行 → evening 投稿 |
| AC-8 | X Agent が morning/evening スロットを区別して投稿する | 同上 |
| AC-9 | Commander Agent のプロンプトが「TikTok: 2投稿 (9am/9pm)」に更新される | プロンプト内のテキストを確認 |
| AC-10（前提） | GitHub Secrets に `X_BEARER_TOKEN`, `X_API_KEY`, `X_API_KEY_SECRET` が設定済み | `gh secret list` で確認 |
| AC-11 | Commander Agent の出力スキーマが `xPosts: [{slot: "morning"}, {slot: "evening"}]` の2件必須に変更される | Zod schema validation テスト（length(2) + slot enum 検証） |

---

## 3. As-Is / To-Be

### 3.1 X メトリクス取得（新規）

**As-Is**: なし。X に投稿した後、メトリクスを回収するコードが存在しない。

**To-Be**: 2段階の設計。

#### 3.1.1 xPostId 検証（X Agent 投稿時）

X Agent (`anicca_x_agent.py`) が Blotato API で投稿した後、Blotato の返す `id` / `postId` を `xPostId` として DB に保存している（既存動作）。しかし Blotato ID が X の投稿IDと同じかは不確定。

**対策**: X Agent 投稿後に、`GET /2/tweets/search/recent?query=from:anicca_self` は Free Tier 不可のため、以下の方式で X 投稿ID を検証する:

1. **Phase A-1（即時対応）**: Blotato API の返す `id` が X 投稿ID だと仮定して `GET /2/tweets?ids={blotato_id}` を試す
2. 成功した場合 → `xPostId` はそのまま X 投稿IDとして使える
3. 失敗（404）した場合 → `xPostId` は**そのまま残し**、当該IDは**スキップ**してログに残す（Free Tier ではタイムライン取得不可のためテキストマッチングは行わない）
4. **実装時に Blotato の返す ID を検証**: 最初の1回は手動で `curl -H "Authorization: Bearer $X_BEARER_TOKEN" "https://api.x.com/2/tweets?ids={blotato_id}"` を実行して確認

**結論**: テキストマッチング設計は廃止。xPostId ベースの `GET /2/tweets?ids=...` のみで完結させる。

#### 3.1.2 メトリクス取得スクリプト

`scripts/x-agent/fetch_x_metrics.py` を新規作成。

```python
# fetch_x_metrics.py のシグネチャ

def fetch_metrics_by_ids(bearer_token: str, tweet_ids: list[str]) -> dict[str, dict]:
    """X API v2 GET /2/tweets?ids={id1},{id2},...&tweet.fields=public_metrics,created_at

    Free Tier 制限: 月間読み取り上限あり（最新のX開発者ポータルに準拠） / レート制限は x-rate-limit-* ヘッダーで確認
    バッチ: 最大100 IDs/リクエスト

    Returns: { tweet_id: { impression_count, like_count, retweet_count, reply_count } }
    tweet_id が見つからない場合はスキップ（Blotato ID ≠ X 投稿ID の可能性）
    429 の場合は処理を中断し、次回の cron に回す
    """

def update_metrics(api_base_url: str, auth_token: str, db_record_id: str, metrics: dict) -> None:
    """PUT /api/admin/x/posts/:id/metrics を呼ぶ

    ※ :id は DB レコードの主キー（x_posts.id）。xPostId（X投稿ID）ではない。
    ※ このエンドポイントは**新規作成**（xposts.js に追加）
    ※ 認証: requireInternalAuth（既存 router で自動適用）
    ※ ペイロード: { impression_count?, like_count?, retweet_count?, reply_count? }
       → 送信されたフィールドのみ DB 更新（部分更新）。未送信フィールドは既存値維持
    """

def main():
    """メインフロー:
    1. GET /api/admin/x/recent-posts?days=7 で DB の x_posts 取得（xPostId 付き / 直近7日固定）
       ※ 既存エンドポイント: apps/api/src/routes/admin/xposts.js L130-145
       ※ 認証: requireInternalAuth（既存 router で自動適用済み）
       ※ 変更不要（既存のまま利用）
    2. xPostId が非null のレコードのみ抽出
    3. GET /2/tweets?ids={xPostId1},{xPostId2},...&tweet.fields=public_metrics,created_at でメトリクス取得
    4. マッチした投稿の update_metrics(db_record_id, metrics) を呼ぶ
       ※ /recent-posts レスポンスの各レコードは { id (DB主キー), xPostId (X投稿ID), ... } を含む
       ※ X API 応答は xPostId をキーに返すので、xPostId → db_record_id のマッピングで更新
    5. マッチしなかった xPostId はログに warn 出力（Blotato ID ≠ X 投稿ID の証拠）
    6. 429 の場合は以降を中断し、次回の cron に回す
    """
```

**X API v2 Free Tier の制限（重要）**:

| 制限 | 値 |
|------|-----|
| 月間ツイート読み取り | Free Tier 上限（最新のX開発者ポータルに準拠） |
| レート制限 | x-rate-limit-* ヘッダーで確認 |
| 利用可能エンドポイント | `GET /2/tweets?ids=...`, `GET /2/users/me` |
| 取得可能フィールド | `public_metrics` (impression_count, like_count, retweet_count, reply_count) |
| **使えないエンドポイント** | `GET /2/users/:id/tweets`（Basic $100/mo 以上）、`GET /2/tweets/search/recent`（Basic 以上） |

**設計の前提**: X 投稿ID は xPostId（Blotato 返却値）を直接使う。タイムライン取得やテキストマッチングは行わない。取得失敗はログに残し、次回 cron で再試行する。

**メトリクス欠落時の更新ポリシー**: X API v2 が返す `public_metrics` 内のフィールドが欠落している場合（例: `impression_count` が null/undefined）:
- 欠落フィールドは**更新しない**（既存値を維持）。`null` で上書きしない
- `update_metrics()` は存在するフィールドのみ DB に書き込む（部分更新）
- 全フィールドが欠落している場合はログに warn を出し、次回 cron で再試行

**ファイル**: `scripts/x-agent/fetch_x_metrics.py`（新規）
**依存**: `scripts/x-agent/config.py`（既存、X_BEARER_TOKEN 追加）
**GHA**: `.github/workflows/fetch-x-metrics.yml`（新規）

### 3.2 X メトリクス取得 GHA ワークフロー（新規）

**As-Is**: なし。

**To-Be**: `.github/workflows/fetch-x-metrics.yml`

```yaml
name: Fetch X Metrics
on:
  schedule:
    - cron: '0 1 * * *'  # 10:00 JST
  workflow_dispatch: {}
concurrency:
  group: fetch-x-metrics
  cancel-in-progress: false
jobs:
  fetch:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install requests
      - run: python scripts/x-agent/fetch_x_metrics.py
        env:
          X_BEARER_TOKEN: ${{ secrets.X_BEARER_TOKEN }}
          API_BASE_URL: ${{ secrets.API_BASE_URL }}
          API_AUTH_TOKEN: ${{ secrets.API_AUTH_TOKEN }}
```

**GitHub Secrets（登録済み）**:

| Secret | 用途 | 登録状態 |
|--------|------|---------|
| `X_BEARER_TOKEN` | X API v2 Bearer Token | ✅ 登録済み（本Spec作成時に登録） |
| `X_API_KEY` | X API Consumer Key | ✅ 登録済み |
| `X_API_KEY_SECRET` | X API Consumer Key Secret | ✅ 登録済み |
| `API_BASE_URL` | Railway Production URL (`anicca-proxy-production.up.railway.app`) | ✅ 既存 |
| `API_AUTH_TOKEN` | Railway INTERNAL_API_TOKEN | ✅ 既存 |

### 3.3 Cross-Platform Learning Pipeline 配線（generateNudges.js 統合）

**As-Is**: 4関数が `crossPlatformLearning.js` に定義済みだが、どのジョブからも呼ばれていない。

**To-Be**: `apps/api/src/jobs/syncCrossPlatform.js` を新規作成。

```javascript
// syncCrossPlatform.js のシグネチャ

import {
  refreshBaselines,
  syncXMetricsToHookCandidates,
  identifyPromotions,
  executePromotions,
} from '../agents/crossPlatformLearning.js';

/**
 * Cross-Platform Learning Pipeline（generateNudges 起動時 / 05:00 JST）
 *
 * 実行順序（依存関係あり、並列化不可）:
 * 1. refreshBaselines() — Z-Score 基準値を DB から更新
 * 2. syncXMetricsToHookCandidates() — x_posts → hook_candidates の X フィールド
 * 3. identifyPromotions() — X→TikTok (Z≥1.0), TikTok→App (score≥1.5) 候補抽出
 * 4. executePromotions() — 候補の hook_candidates.promoted = true に更新
 *
 * @param {object} query - Prisma query interface
 */
export async function runCrossPlatformSync(query) { ... }
```

**実行方式**: `generateNudges.js` の**冒頭**で `runCrossPlatformSync()` を呼び出す。

**理由**:
- 新 Railway サービス不要（コスト節約、railway.toml 変更不要）
- Commander Agent が最新の crossPlatformData を使えるよう、**先に**学習パイプラインを実行
- 実行順序: `runCrossPlatformSync()` → Commander Agent（各ユーザー）

**コード（`generateNudges.js` 冒頭に追加）**:

```javascript
import { runCrossPlatformSync } from './syncCrossPlatform.js';

// Step 0: Cross-Platform Learning — 前日のメトリクスを処理（失敗しても Commander は続行）
try {
  logger.info('Running cross-platform learning pipeline...');
  await runCrossPlatformSync(prisma);
  logger.info('Cross-platform learning complete.');
} catch (error) {
  logger.error('Cross-platform learning failed, continuing with Commander:', error.message);
  // 学習パイプライン失敗は日次 Nudge 生成を止めない（graceful degradation）
}

// Step 1: Commander Agent for each user（既存コード）
```

**失敗時ポリシー**: `runCrossPlatformSync()` は graceful degradation。失敗しても Commander Agent は古い crossPlatformData で実行を続行する。Nudge 生成が止まることはユーザー体験に直接影響するため、学習パイプラインの失敗でブロックしない。

### 3.4 Commander Agent スキーマ変更

**As-Is**:

```javascript
const AgentRawOutputSchema = z.object({
  rootCauseHypothesis: z.string(),
  overallStrategy: z.string(),
  frequencyReasoning: z.string(),
  appNudges: z.array(AppNudgeSchema),
  tiktokPost: TiktokPostSchema.optional(),          // 単数
  xPosts: z.array(XPostSchema).optional(),           // 件数不定
});
```

**To-Be**:

```javascript
const TiktokPostSlot = z.enum(['morning', 'evening']);
const XPostSlot = z.enum(['morning', 'evening']);

const TiktokPostSchema = z.object({
  slot: TiktokPostSlot,
  caption: z.string().max(2200),  // TikTok caption limit
  hashtags: z.array(z.string()).max(5).optional(),
  tone: z.string(),
  reasoning: z.string(),
});

const XPostSchema = z.object({
  slot: XPostSlot,
  text: z.string().max(280),  // X character limit
  reasoning: z.string(),
});

const AgentRawOutputSchema = z.object({
  rootCauseHypothesis: z.string(),
  overallStrategy: z.string(),
  frequencyReasoning: z.string(),
  appNudges: z.array(AppNudgeSchema),
  tiktokPosts: z.array(TiktokPostSchema).length(2),  // 必ず morning + evening
  xPosts: z.array(XPostSchema).length(2),             // 必ず morning + evening
}).superRefine((data, ctx) => {
  // slot 一意性保証: morning + evening が各1件ずつであること
  for (const [field, arr] of [['tiktokPosts', data.tiktokPosts], ['xPosts', data.xPosts]]) {
    const slots = arr.map(p => p.slot);
    if (!slots.includes('morning') || !slots.includes('evening')) {
      ctx.addIssue({ code: 'custom', message: `${field} must have exactly one morning and one evening slot` });
    }
  }
});
```

**ファイル**: `apps/api/src/agents/commander.js`

**影響範囲**:
- `commander.js` — スキーマ定義 + プロンプト内 TikTok/X セクション
- `commander.test.js` — テストフィクスチャ更新
- `generateNudges.js` — `notification_schedules` への保存ロジック（agentRawOutput に新形式）
- `xposts.js` — `/api/admin/x/pending` の読み取りロジック（slot フィルタリング追加）

#### 後方互換設計（重要）

デプロイ直後、DB に旧形式の `notification_schedules`（`tiktokPost` 単数、`xPosts` に `slot` なし）が残っている。`/api/admin/x/pending` と `/api/admin/tiktok/pending` はこれを安全に処理する必要がある。

**互換パース関数** (`normalizeScheduleOutput`):

```javascript
/**
 * 旧形式の notification_schedules を新形式に正規化。
 *
 * 旧: { tiktokPost: {...}, xPosts: [{text, reasoning}] }
 * 新: { tiktokPosts: [{slot, ...}, {slot, ...}], xPosts: [{slot, ...}, {slot, ...}] }
 */
function normalizeScheduleOutput(raw) {
  // tiktokPost（単数）→ tiktokPosts（複数）
  let tiktokPosts = raw.tiktokPosts;
  if (!tiktokPosts && raw.tiktokPost) {
    // 旧形式: 単数を morning スロットに割り当て
    tiktokPosts = [{ ...raw.tiktokPost, slot: 'morning' }];
  }

  // tiktokPosts に slot がない場合のフォールバック（件数は増やさない）
  if (tiktokPosts) {
    tiktokPosts = tiktokPosts.map((post, i) => ({
      ...post,
      slot: post.slot || (i === 0 ? 'morning' : 'evening'),
    }));
  }

  // xPosts に slot がない場合のフォールバック（件数は増やさない）
  let xPosts = raw.xPosts || [];
  xPosts = xPosts.map((post, i) => ({
    ...post,
    slot: post.slot || (i === 0 ? 'morning' : 'evening'),
  }));

  return { tiktokPosts: tiktokPosts || [], xPosts };
}
```

**適用箇所**: `xposts.js` の `GET /pending` と `tiktok.js` の `GET /pending` で、notification_schedules から読み取った後に `normalizeScheduleOutput()` を適用。

**スロット欠損時の挙動（重要）**: 旧形式データでは tiktokPost が1件、xPosts が slot なしの1-2件となる。`normalizeScheduleOutput()` は**件数を増やさない**（旧1件なら morning のみ）。GHA が evening スロットで `/pending?slot=evening` を呼んだ時に該当投稿がない場合:
- API は空配列を返す（200 OK + `{ xPosts: [] }` / `{ tiktokPosts: [] }` ）
- GHA Agent は「投稿なし」としてログ出力 + 正常終了（exit 0）
- これは移行期間中（1日以内）の想定動作。翌日の Commander Agent は新スキーマで2件生成するため、以降は発生しない

**テスト**:
- `test_pending_backward_compat_single_tiktokPost()` — 旧形式データでも slot=morning として返ること
- `test_pending_evening_slot_empty_returns_200()` — 旧形式データで evening を問い合わせた時に空配列 + 200 OK を返すこと

### 3.5 Commander Agent プロンプト変更

**As-Is** (`commander.js` 内の SYSTEM_PROMPT + buildCommanderPrompt):

```
### TikTok / X（固定スケジュール）
- TikTok: 1投稿（09:00 JST に即時投稿）
- X: 2投稿（09:00 JST 即時 + 21:00 JST 予約）
```

**To-Be**:

```
### TikTok / X（固定スケジュール: 9:00 + 21:00 JST）

TikTok と X、それぞれ2投稿を生成せよ:

| プラットフォーム | スロット | 投稿時刻 | 目的 |
|----------------|---------|---------|------|
| TikTok | morning | 09:00 JST | 朝の通勤・準備時間帯。啓発・問題提起系 |
| TikTok | evening | 21:00 JST | 夜のリラックス時間帯。内省・共感系 |
| X | morning | 09:00 JST | 朝のタイムライン。知識・洞察系 |
| X | evening | 21:00 JST | 夜のタイムライン。共感・物語系 |

ルール:
- App で効いた洞察を TikTok/X にも展開せよ
- TikTok/X で効いた洞察を App にフィードバックせよ
- morning と evening は異なる切り口にせよ（同じ内容を繰り返すな）
- TikTok caption は 2200文字以内、ハッシュタグ最大5つ
- X text は 280文字以内
```

**ファイル**: `apps/api/src/agents/commander.js` 内の `buildCommanderPrompt()`

### 3.6 TikTok Agent スケジュール変更

**As-Is**: GHA が 9:00 JST に1回トリガー。TikTok Agent が曜日別に自律的にスケジュール決定。

**To-Be**: GHA が 8:50 JST + 20:50 JST に2回トリガー。TikTok Agent は `notification_schedules` から該当スロット（morning/evening）を取得して投稿。`POST_SLOT` を GHA から明示的に渡す。

**ファイル変更**:

1. `.github/workflows/anicca-daily-post.yml` — cron を2つに:
   ```yaml
   on:
     schedule:
       - cron: '50 23 * * *'  # 08:50 JST (23:50 UTC前日)
       - cron: '50 11 * * *'  # 20:50 JST
     workflow_dispatch:
       inputs:
         slot:
           description: 'Slot to post (morning/evening)'
           required: false
           default: 'morning'
   env:
     POST_SLOT: ${{ inputs.slot || (github.event.schedule == '50 23 * * *' && 'morning' || 'evening') }}
   ```

2. `scripts/anicca-agent/anicca_tiktok_agent.py` — 自律スケジュール削除、slot パラメータ追加:
   - 環境変数 `POST_SLOT` (morning/evening) を受け取る
   - `GET /api/admin/tiktok/pending` に `?slot=morning` を付けて該当投稿を取得
   - Blotato API で即時投稿（スケジュール済みのため即時でOK）

3. TikTok pending エンドポイント追加（`apps/api/src/routes/admin/tiktok.js` に追加）:
   - `GET /api/admin/tiktok/pending?slot=morning` — notification_schedules から tiktokPosts の該当スロットを返す
   - **認証**: `requireInternalAuth` ミドルウェア必須（既存の tiktok.js router に設定済み）
   - 旧形式データ（`tiktokPost` 単数）に対しても `normalizeScheduleOutput()` で互換処理

### 3.7 X Agent スケジュール変更

**As-Is**: GHA が 9:00 JST に1回トリガー。X Agent 内で LLM が morning/evening を選択。

**To-Be**: GHA が 8:50 JST + 20:50 JST に2回トリガー。X Agent は `notification_schedules` から該当スロット取得。`POST_SLOT` を GHA から明示的に渡す。

**ファイル変更**:

1. `.github/workflows/anicca-x-post.yml` — cron を2つに（`POST_SLOT` を schedule から設定）
   ```yaml
   env:
     POST_SLOT: ${{ inputs.slot || (github.event.schedule == '50 23 * * *' && 'morning' || 'evening') }}
   ```
2. `scripts/x-agent/anicca_x_agent.py` — LLM セレクター削除（Commander が既に決定済み）。slot パラメータで該当投稿を取得して投稿するだけ
3. `scripts/x-agent/config.py` — `X_BEARER_TOKEN` 追加

### 3.8 `/api/admin/x/pending` の slot フィルタリング

**As-Is**: 全 xPosts を返す。

**To-Be**: `?slot=morning` クエリパラメータ対応。該当が無い場合は空配列を返す（200）。

```javascript
// GET /api/admin/x/pending?slot=morning
router.get('/pending', async (req, res) => {
  const { slot } = req.query;  // 'morning' or 'evening'
  // ... notification_schedules から agentRawOutput.xPosts を取得
  // slot が指定されていれば、該当スロットのみフィルタ
  const filtered = slot
    ? xPosts.filter(p => p.slot === slot)
    : xPosts;
  res.json({ xPosts: filtered });
});
```

**ファイル**: `apps/api/src/routes/admin/xposts.js`

---

## 4. テストマトリックス

| # | To-Be | テスト名 | ファイル | カバー |
|---|-------|----------|---------|--------|
| 1 | X メトリクス取得（xPostId ベース） | `test_fetch_metrics_by_ids_success()` | `scripts/x-agent/test_fetch_x_metrics.py` | ✅ |
| 2 | X メトリクス取得（ID不一致時） | `test_fetch_metrics_by_ids_missing_id()` | 同上 | ✅ |
| 3 | X メトリクス取得（xPostId null スキップ） | `test_main_skips_null_xPostId()` | 同上 | ✅ |
| 4 | Cross-Platform sync ジョブ | `test_runCrossPlatformSync_calls_all_four()` | `apps/api/src/jobs/__tests__/syncCrossPlatform.test.js` | ✅ |
| 5 | Cross-Platform sync ジョブ | `test_runCrossPlatformSync_handles_empty_data()` | 同上 | ✅ |
| 6 | Commander schema 変更 | `test_schema_requires_two_tiktokPosts()` | `apps/api/src/agents/__tests__/commander.test.js` | ✅ |
| 7 | Commander schema 変更 | `test_schema_requires_morning_evening_slots()` | 同上 | ✅ |
| 8 | Commander schema 変更 | `test_schema_rejects_single_tiktokPost()` | 同上 | ✅ |
| 9 | X pending slot フィルタ | `test_pending_filters_by_slot()` | `apps/api/src/routes/admin/__tests__/xposts.test.js` | ✅ |
| 10 | X pending 後方互換 | `test_pending_backward_compat_no_slot()` | 同上 | ✅ |
| 11 | TikTok pending slot フィルタ | `test_tiktok_pending_filters_by_slot()` | `apps/api/src/routes/admin/__tests__/tiktok.test.js` | ✅ |
| 12 | TikTok pending 後方互換 | `test_tiktok_pending_backward_compat_single()` | 同上 | ✅ |
| 13 | normalizeToDecision 新形式 | `test_normalizeToDecision_preserves_tiktokPosts()` | `apps/api/src/agents/__tests__/commander.test.js` | ✅ |
| 14 | normalizeScheduleOutput 互換 | `test_normalizeScheduleOutput_single_to_array()` | `apps/api/src/routes/admin/__tests__/xposts.test.js` | ✅ |
| 15 | refreshBaselines 動作 | `test_refreshBaselines_updates_from_db()` | `apps/api/src/agents/__tests__/crossPlatformLearning.test.js`（既存） | ✅ |
| 16 | generateNudges + syncCrossPlatform 統合 | `test_generateNudges_calls_syncCrossPlatform()` | `apps/api/src/jobs/__tests__/generateNudges.test.js` | ✅ |
| 17 | GHA cron スケジュール 2回化 | 手動実行検証: `gh workflow run` with `slot=morning` / `slot=evening` | GHA 手動検証 | ✅ |
| 18 | Commander プロンプト更新 | `test_prompt_includes_morning_evening_table()` | `apps/api/src/agents/__tests__/commander.test.js` | ✅ |
| 19 | Commander schema xPosts length(2) | `test_schema_requires_two_xPosts()` | `apps/api/src/agents/__tests__/commander.test.js` | ✅ |
| 20 | Commander schema xPosts slot必須 | `test_schema_requires_xPosts_morning_evening_slots()` | 同上 | ✅ |
| 21 | X pending evening スロット欠損 | `test_pending_evening_slot_empty_returns_200()` | `apps/api/src/routes/admin/__tests__/xposts.test.js` | ✅ |
| 22 | TikTok pending evening スロット欠損 | `test_tiktok_pending_evening_slot_empty_returns_200()` | `apps/api/src/routes/admin/__tests__/tiktok.test.js` | ✅ |
| 23 | Commander schema slot重複拒否 | `test_schema_rejects_duplicate_slots()` | `apps/api/src/agents/__tests__/commander.test.js` | ✅ |
| 24 | syncCrossPlatform 失敗時 graceful degradation | `test_generateNudges_continues_on_sync_failure()` | `apps/api/src/jobs/__tests__/generateNudges.test.js` | ✅ |
| 25 | X メトリクス部分欠落時 | `test_fetch_metrics_partial_fields_no_overwrite()` | `scripts/x-agent/test_fetch_x_metrics.py` | ✅ |
| 26 | tiktokPosts slot欠損フォールバック | `test_normalize_tiktokPosts_slot_fallback()` | `apps/api/src/routes/admin/__tests__/tiktok.test.js` | ✅ |
| 27 | PUT /x/posts/:id/metrics 部分更新 | `test_put_metrics_partial_update()` | `apps/api/src/routes/admin/__tests__/xposts.test.js` | ✅ |
| 28 | PUT /x/posts/:id/metrics 認証必須 | `test_put_metrics_requires_auth()` | 同上 | ✅ |

---

## 5. 境界

### 触るファイル

| ファイル | 操作 |
|---------|------|
| `scripts/x-agent/fetch_x_metrics.py` | **新規作成** |
| `scripts/x-agent/test_fetch_x_metrics.py` | **新規作成**（テスト） |
| `scripts/x-agent/config.py` | 修正（X_BEARER_TOKEN 追加） |
| `.github/workflows/fetch-x-metrics.yml` | **新規作成** |
| `.github/workflows/anicca-x-post.yml` | 修正（cron 2回化 + slot パラメータ） |
| `.github/workflows/anicca-daily-post.yml` | 修正（cron 2回化 + slot パラメータ） |
| `apps/api/src/agents/commander.js` | 修正（スキーマ + プロンプト） |
| `apps/api/src/agents/__tests__/commander.test.js` | 修正（新スキーマテスト + プロンプトテスト） |
| `apps/api/src/jobs/generateNudges.js` | 修正（syncCrossPlatform 呼び出し追加） |
| `apps/api/src/jobs/__tests__/generateNudges.test.js` | 修正（syncCrossPlatform 統合テスト追加） |
| `apps/api/src/jobs/syncCrossPlatform.js` | **新規作成** |
| `apps/api/src/jobs/__tests__/syncCrossPlatform.test.js` | **新規作成** |
| `apps/api/src/routes/admin/xposts.js` | 修正（slot フィルタ + 後方互換パース + `PUT /:id/metrics` 新規追加 + `requireInternalAuth` 既存適用済み） |
| `apps/api/src/routes/admin/__tests__/xposts.test.js` | **新規作成**（slot フィルタ + 後方互換テスト） |
| `apps/api/src/routes/admin/tiktok.js` | 修正（`/pending` エンドポイント追加 + `requireInternalAuth` 既存 router で自動適用） |
| `apps/api/src/routes/admin/__tests__/tiktok.test.js` | **新規作成**（pending テスト） |
| `scripts/x-agent/anicca_x_agent.py` | 修正（LLM セレクター削除、slot ベース） |
| `scripts/anicca-agent/anicca_tiktok_agent.py` | 修正（自律スケジュール削除、slot ベース） |

### 触らないファイル

| ファイル | 理由 |
|---------|------|
| `apps/api/prisma/schema.prisma` | DB スキーマ変更なし（既存フィールドで対応可能） |
| `aniccaios/**` | iOS 変更なし |
| `apps/api/src/agents/crossPlatformLearning.js` | 既存の4関数をそのまま使う。変更不要 |
| `apps/api/src/agents/scheduleMap.js` | 変更なし |
| `apps/api/src/agents/groundingCollectors.js` | 変更なし |

---

## 6. 実行手順

### Phase A: X メトリクス取得（#1, #2, #3）

```bash
# テスト
cd /Users/cbns03/Downloads/anicca-1.6.0-one-buddha
python scripts/x-agent/fetch_x_metrics.py  # ローカル実行（要: X_BEARER_TOKEN env）

# GHA テスト
gh workflow run "Fetch X Metrics" --ref feature/1.6.0-one-buddha --repo Daisuke134/anicca.ai
gh run list --workflow "Fetch X Metrics" -L 3
```

### Phase B: Commander スキーマ + プロンプト変更（#4, #5, #6）

```bash
cd /Users/cbns03/Downloads/anicca-1.6.0-one-buddha/apps/api
npx vitest run src/agents/__tests__/commander.test.js
```

### Phase C: GHA スケジュール統一（#7, #8）

```bash
# GHA テスト（手動実行）
gh workflow run "Anicca X Post" --ref feature/1.6.0-one-buddha -f slot=morning
gh workflow run "Anicca Daily TikTok Post" --ref feature/1.6.0-one-buddha -f slot=morning
```

### Phase D: Cross-Platform Learning 配線（#9, #10）

```bash
cd /Users/cbns03/Downloads/anicca-1.6.0-one-buddha/apps/api
npx vitest run src/jobs/__tests__/syncCrossPlatform.test.js
npx vitest run  # 全テスト
```

### 全テスト

```bash
cd /Users/cbns03/Downloads/anicca-1.6.0-one-buddha/apps/api
npx vitest run  # 全テスト PASS を確認
```

---

## 7. リスク・注意事項

| リスク | 対策 |
|--------|------|
| Blotato ID ≠ X 投稿ID の場合 | 初回デプロイ後に手動で `GET /2/tweets?ids={blotato_id}` を検証。不一致なら該当IDはスキップしログに残す（テキストマッチングは行わない） |
| X API Free Tier で `GET /2/users/:id/tweets` が使えない | **設計で排除済み**: `GET /2/tweets?ids=...` のみ使用 |
| Commander Agent が新スキーマに従わない場合 | Zod validation でエラー → リトライ（既存の maxRetries=2 で対応） |
| Cross-Platform Learning で DB が空の場合 | `refreshBaselines()` はデータ0件時にデフォルト値を維持（既存実装で対応済み） |
| デプロイ直後の旧形式データ | `normalizeScheduleOutput()` で旧形式（tiktokPost 単数、slot なし）を新形式に自動変換 |
| TikTok pending エンドポイントの認証 | 既存の `tiktok.js` router は `requireInternalAuth` 設定済み。新 `/pending` にも自動適用 |
| Railway Cron サービス追加 | 不要。`generateNudges.js` の冒頭で `runCrossPlatformSync()` を実行 |
| Cross-Platform Learning 失敗時 | try/catch で graceful degradation。Commander Agent は古い crossPlatformData で続行。Nudge 生成は止めない |
| X API impression_count 欠落 | 欠落フィールドは更新しない（既存値維持）。全欠落時は warn ログ + 次回 cron で再試行 |
| Commander が重複スロット出力 | superRefine で morning+evening の一意性を Zod で検証。重複は reject → リトライ |
