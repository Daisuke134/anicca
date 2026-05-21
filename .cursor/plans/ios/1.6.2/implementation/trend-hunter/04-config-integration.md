## Required Tools

| ツール | 用途 |
|--------|------|
| `exec` | TwitterAPI.io呼び出し、reddapi API呼び出し、Apify API呼び出し、Railway API呼び出し |
| `web_search` | 補助検索（Brave API経由） |
| `slack` | 結果サマリー投稿 |
| `read` | 設定ファイル、既存hook一覧 |
| `write` | DLQ書き込み |

## Error Handling

| エラー | 対応 |
|--------|------|
| TwitterAPI.io 失敗/停止 | TikTok + Reddit の結果のみで続行。Slack #alerts に通知 |
| Apify TikTok Scraper 失敗 | X + Reddit の結果のみで続行 |
| reddapi API失敗 | X + TikTok の結果のみで続行 |
| LLMフィルタ/生成失敗 | Fallback Chain（下記詳細参照） |
| Railway API保存失敗 | DLQ に書き込み、次回実行時にリトライ |
| 全ソース失敗 | Slack #alerts に通知、DLQに記録 |

### LLM Fallback Chain 詳細契約

OpenClawエージェントのLLM呼び出し（`exec` 内のプロンプト処理）に対するフォールバック戦略。

| 順位 | モデル | タイムアウト | リトライ | 用途 |
|------|--------|------------|---------|------|
| 1 | gpt-4o | 30秒 | 1回 | 高品質フィルタ + hook生成 |
| 2 | gpt-4o-mini | 20秒 | 1回 | コスト効率の高いフォールバック |
| 3 | claude-3-5-haiku | 20秒 | 1回 | プロバイダ多様性（OpenAI障害対策） |
| 4 | — | — | — | DLQに記録してスキップ |

**フォールバック発火条件:**

| エラー種別 | 判定方法 | アクション |
|-----------|---------|-----------|
| タイムアウト | レスポンスなし（上記秒数超過） | 次のモデルにフォールバック |
| 不正JSON | `JSON.parse()` 失敗 | 同じモデルで1回リトライ（プロンプト末尾に `必ず有効なJSONで返してください` 追加）|
| スキーマ不適合 | JSON Schema バリデーション失敗 | 同じモデルで1回リトライ（エラー箇所をフィードバック） |
| トークン超過 | 入力が長すぎるエラー | 入力を50%に truncate して同じモデルでリトライ |
| 全モデル失敗 | 順位4到達 | 当該バッチをDLQに記録、Slack #alertsに通知 |

**スキーマバリデーション:**
フィルタ出力 → `07-mock-data-validation.md` の「フィルタ出力スキーマ」で検証。
hook生成出力 → `07-mock-data-validation.md` の「hook生成出力スキーマ」で検証。

```javascript
// LLM呼び出し + バリデーション疑似コード
async function callLLMWithFallback(prompt, schema, models = LLM_CHAIN) {
  for (const model of models) {
    for (let retry = 0; retry < 2; retry++) {
      try {
        const raw = await callLLM(model, prompt, { timeout: model.timeout });
        const parsed = JSON.parse(raw);
        validateSchema(parsed, schema); // throws on failure
        return parsed;
      } catch (err) {
        if (err.type === 'schema_validation' && retry === 0) {
          prompt += `\n\n前回の出力でスキーマエラー: ${err.message}\n修正して再出力してください。`;
          continue; // 同じモデルでリトライ
        }
        break; // 次のモデルへ
      }
    }
  }
  throw new LLMExhaustedError('All models failed');
}
```

---

## Cron設定

```yaml
trend-hunter:
  skill: trend-hunter
  cron: "0 */4 * * *"   # 4時間ごと（1日6回）
  session: isolated
  delivery:
    mode: "none"
  prompt: |
    trend-hunter スキルを実行してください。

    1. 今回のローテーショングループを決定（実行回数 % 3）
    2. 対象ProblemTypeに対して、TikTok / Reddit / X から並列でトレンド収集
    3. Aniccaフィルタ（LLM）で関連度・バイラル度を判定
    4. 通過したトレンドからhook候補を生成（共感系 + 問題解決系、最大5件/回）
    5. 重複チェック後、Railway DBに保存
    6. Slack #trends に結果サマリーを投稿

    exec, browser, web_search, slack ツールを使用してください。
```

## 必要な環境変数

| 変数 | 用途 | コスト | 取得方法 | ステータス |
|------|------|--------|---------|-----------|
| `TWITTERAPI_KEY` | TwitterAPI.io（X検索+メトリクス） | $0.15/1k件（月~$9） | twitterapi.io でGoogle登録 | **ユーザーGUI作業必要** |
| `REDDAPI_API_KEY` | reddapi.dev セマンティック検索 | $9.90/月（Liteプラン） | reddapi.dev でGoogle/GitHub登録 | **ユーザーGUI作業必要** |
| `APIFY_API_TOKEN` | Apify TikTok Trends Scraper | 既存Apify枠内（$5/月） | **既にGitHub Secretsに登録済み** | **VPSの.envにもあるか要確認** |
| `ANICCA_AGENT_TOKEN` | Railway API 認証 | なし | 既存（VPSの.envにある） | 済 |
| `BRAVE_API_KEY` | web_search（補助検索） | 既存 | VPSの.envにある | 済 |

### 月間コスト見積もり

| 項目 | 計算 | 月額 |
|------|------|------|
| TwitterAPI.io | 1,920ツイート/日 × 30日 ÷ 1,000 × $0.15 | ~$9 |
| reddapi.dev Lite | 500 API calls/月（固定） | $9.90 |
| Apify TikTok Trends | 既存無料枠（$5/月クレジット）内で~540 runs | $0 |
| LLM（フィルタ+hook生成） | 12回/日 × 30日、gpt-4o-mini推定 | ~$3 |
| **合計** | | **~$22/月** |

## trend-watcher（ClawHub）からの流用

| 流用するもの | 内容 |
|------------|------|
| **スキル構造** | SKILL.md のみ（`index.js` / `_meta.json` はカスタムツール実装時のみ必要、今回不要） |
| **HTTPリクエスト関数** | `httpRequest()` — タイムアウト付き、Node.js標準のみ |
| **HTMLパーサーパターン** | `parseTrendingHTML()` — GitHub Trending用。TikTok Creative Center にも応用 |
| **カテゴリフィルタ方式** | キーワード辞書 → 13 ProblemType辞書に置き換え |
| **キャッシュデータ方式** | API失敗時のフォールバック用ローカルキャッシュ |

## reddapi（ClawHub）からの流用

| 流用するもの | 内容 |
|------------|------|
| **セマンティック検索パターン** | `"I wish there was an app that"` 系のクエリ設計 |
| **トレンドAPI** | `growth_rate` によるトレンド急成長検出 |
| **curlベースの実装** | OpenClaw exec ツールとの親和性が高い |

## イベント接続仕様（trend-hunter → closed-loop-ops）

> **C2/C3解消**: trend-hunter が closed-loop-ops の Reaction Matrix に接続するためのイベント契約

### イベント種別（Event Vocabulary）

| イベント kind | source | tags | いつ発行 | Reaction Matrix の反応 |
|-------------|--------|------|---------|---------------------|
| `hook_saved` | `trend-hunter` | `['hook_candidate', 'found']` | hook 1件保存ごとに発行（個別イベント） | x-poster に `evaluate_hook` 提案（probability: 0.5） |
| `scan_completed` | `trend-hunter` | `['scan', 'completed']` | 実行完了時（hook 0件でも） | 監視ログ用（Reaction不要） |
| `scan_failed` | `trend-hunter` | `['scan', 'failed', 'alert']` | 全ソース障害時 | Slack #alerts に通知提案 |

> **タグ命名の根拠**: closed-loop-ops の `02-data-layer.md` seed data と完全一致させる。
> `['hook_candidate', 'found']` = Reaction Matrix の `ops_reaction_matrix` パターンと正確にマッチ。

### イベント発行経路（2つのコンテキスト）

> **重要**: hook ごとに個別イベントを発行する（配列ではない）。
> evaluate_hook は hook_saved イベントの `eventId` を起点に評価する。イベント payload 内の `hookId` を参照してhookを取得する。

| 呼び出しコンテキスト | イベント発行経路 | 理由 |
|---------------------|-----------------|------|
| **Step executor**（closed-loop-ops の run_trend_scan ステップ） | `PATCH /api/ops/step/:id/complete` の `body.events` | 正規経路。Step完了とイベント発行をアトミックに処理 |
| **Standalone cron**（Phase C: 4h間隔の独立スキャン） | 直接 `POST /api/ops/events` | Step コンテキストが存在しないため |

> **設計判断**: body.events が正規経路。standalone cron は closed-loop-ops 導入前の移行経路。
> Phase C 以降、trend-hunter は全て closed-loop-ops の Proposal → run_trend_scan Step として実行される。

#### イベントペイロード（共通）

```json
{
  "source": "trend-hunter",
  "kind": "hook_saved",
  "tags": ["hook_candidate", "found"],
  "payload": {
    "hookId": "hook_123",
    "hookType": "empathy",
    "targetTypes": ["staying_up_late", "cant_wake_up"]
  }
}
```

#### Step executor 経路（正規 — 03-processing-flow.md 参照）

```javascript
// VPS SKILL.md 内でイベントを配列に収集
const collectedEvents = [];
for (const hook of savedHooks) {
  collectedEvents.push({
    source: 'trend-hunter', kind: 'hook_saved',
    tags: ['hook_candidate', 'found'],
    payload: { hookId: hook.id, hookType: hook.contentType, targetTypes: hook.targetProblemTypes }
  });
}
collectedEvents.push({
  source: 'trend-hunter', kind: 'scan_completed',
  tags: ['scan', 'completed'],
  payload: { savedCount: savedHooks.length, empathyCount, solutionCount }
});
// → VPS Worker が PATCH /api/ops/step/:id/complete の body.events として送信
```

### Reaction Matrix パターン（closed-loop-ops 側で定義）

```json
{
  "source": "trend-hunter",
  "tags": ["hook_candidate", "found"],
  "target": "x-poster",
  "type": "evaluate_hook",
  "probability": 0.5,
  "cooldown": 240,
  "payload_template": {
    "eventId": "{{id}}"
  }
}
```

**cooldown: 240** = 240分（4時間）。trend-hunterの実行間隔と同じ。

---

## x-poster との連携（データフロー）

```
trend-hunter (4h間隔)
    ↓ ProblemType別にバイラルコンテンツ検出
    ↓ 共感系 + 問題解決系の hook候補を生成
    ↓ POST /api/agent/hooks
    ↓
Railway DB (Hook テーブル)
    ↓ Thompson Sampling で選択
    ↓ contentType (empathy/solution) も考慮
    ↓
x-poster (09:00/21:00 JST)
    ↓ 朝=問題解決系（行動促進）、夜=共感系（寄り添い）
    ↓ content-verifier で検証
    ↓ X API で投稿
    ↓
投稿結果 → Hook統計更新 → Thompson Sampling の学習
    ↓
trend-hunter が学習結果を参照
    ↓ 高スコアProblemType → 検索頻度UP
    ↓ 低スコアProblemType → 検索頻度DOWN
```

