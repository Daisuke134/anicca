## DLQリトライロジック

> リサーチ結果（2026-02-08）: Bull Queue + async-retry + AWS SQS のベストプラクティスを統合。
> ファイルベースDLQ（JSON Lines形式）で実装。DBアクセス不要。

### DLQ構造

**形式**: JSON Lines（`.jsonl`） — 1行 = 1エントリ。追記専用でロック不要。

**パス**: `~/.openclaw/dlq/trend-hunter-hooks.jsonl`

```typescript
interface DLQEntry {
  jobId: string;           // 一意識別子（`hook-${timestamp}-${random}`）
  data: {                  // リトライ時に再実行するペイロード
    hook: HookCandidate;   // 保存するhook候補
    endpoint: string;      // Railway API URL
  };
  attemptsMade: number;    // 現在の試行回数
  maxAttempts: number;     // 最大リトライ回数（5）
  timestamp: number;       // 初回失敗時刻（Unix ms）
  nextRetry: number;       // 次回リトライ時刻（Unix ms）
  error: {                 // 最後のエラー情報
    message: string;
    code: string | null;   // HTTP status or error code
  };
  state: 'pending' | 'retrying' | 'exhausted' | 'resolved';
}
```

### リトライ戦略

**採用: 指数バックオフ + ジッター**

| パラメータ | 値 | 理由 |
|-----------|-----|------|
| **factor** | 2 | 業界標準（AWS, Bull Queue共通） |
| **minTimeout** | 60,000 ms (1分) | Railway APIの一時障害を吸収 |
| **maxTimeout** | 3,600,000 ms (1時間) | 長時間障害でも上限あり |
| **maxAttempts** | 5 | 外部API呼び出しの推奨値 |
| **jitter** | ±30秒ランダム | Thundering Herd 回避 |

**待機時間の計算:**

| 試行 | 計算 | 待機時間 |
|------|------|---------|
| 1回目 | 60s × 2^0 + random(-30s, +30s) | 30秒〜1.5分 |
| 2回目 | 60s × 2^1 + random(-30s, +30s) | 1.5分〜2.5分 |
| 3回目 | 60s × 2^2 + random(-30s, +30s) | 3.5分〜4.5分 |
| 4回目 | 60s × 2^3 + random(-30s, +30s) | 7.5分〜8.5分 |
| 5回目 | 60s × 2^4 + random(-30s, +30s) | 15.5分〜16.5分 |
| **合計最大** | | **約33分** |

### 実装

```javascript
const DLQ_PATH = '/home/anicca/.openclaw/dlq/trend-hunter-hooks.jsonl';
const MAX_ATTEMPTS = 5;
const BASE_DELAY_MS = 60000; // 1分
const JITTER_MS = 30000;     // ±30秒

// DLQに書き込み
function writeToDLQ(hook, endpoint, error, attemptsMade = 0) {
  const entry = {
    jobId: `hook-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    data: { hook, endpoint },
    attemptsMade: attemptsMade + 1,
    maxAttempts: MAX_ATTEMPTS,
    timestamp: Date.now(),
    nextRetry: Date.now() + calcDelay(attemptsMade + 1),
    error: { message: error.message, code: error.code || null },
    state: attemptsMade + 1 >= MAX_ATTEMPTS ? 'exhausted' : 'pending',
  };

  // exec でファイル追記（heredoc でシェルエスケープ問題を回避 — P0 #18 解消）
  // 注: echo + 単一引用符だと JSON 内の ' でシェルが壊れる
  const jsonLine = JSON.stringify(entry);
  exec(`cat <<'DLQEOF' >> ${DLQ_PATH}\n${jsonLine}\nDLQEOF`);

  return entry;
}

// 指数バックオフ + ジッター
function calcDelay(attempt) {
  const base = BASE_DELAY_MS * Math.pow(2, attempt - 1);
  const jitter = (Math.random() * 2 - 1) * JITTER_MS; // ±30秒
  return Math.min(base + jitter, 3600000); // 上限1時間
}

// DLQエントリの状態更新（JSONL全体を読み→フィルタ→書き戻し）
// P0 #17 解消: retryDLQ() から呼ばれる未定義関数
function updateDLQEntry(jobId, newState) {
  const raw = exec(`cat ${DLQ_PATH} 2>/dev/null || echo ""`);
  if (!raw.trim()) return;

  const entries = raw.trim().split('\n').map(line => JSON.parse(line));
  const updated = entries.map(entry => {
    if (entry.jobId === jobId) {
      return { ...entry, state: newState, resolvedAt: newState === 'resolved' ? Date.now() : undefined };
    }
    return entry;
  });

  // 書き戻し（heredoc でシェルエスケープ問題を回避 — P0 #18 パターン適用）
  const content = updated.map(e => JSON.stringify(e)).join('\n');
  exec(`cat <<'DLQEOF' > ${DLQ_PATH}\n${content}\nDLQEOF`);
}

// DLQ読み込み + リトライ対象抽出
function readRetryable() {
  const raw = exec(`cat ${DLQ_PATH} 2>/dev/null || echo ""`);
  if (!raw.trim()) return [];

  return raw.trim().split('\n')
    .map(line => JSON.parse(line))
    .filter(entry =>
      entry.state === 'pending' &&
      entry.attemptsMade < entry.maxAttempts &&
      Date.now() >= entry.nextRetry
    );
}

// リトライ実行（trend-hunterのStep 4冒頭で呼ぶ）
async function retryDLQ() {
  const retryable = readRetryable();
  let resolved = 0;

  for (const entry of retryable) {
    try {
      // P0 #18 解消: heredoc でペイロードのシェルエスケープ問題を回避
      const payload = JSON.stringify({
        ...entry.data.hook,
        idempotencyKey: entry.jobId  // DLQリトライ時の重複防止
      });
      await exec(`curl -s -X POST \
        -H "Authorization: Bearer ${ANICCA_AGENT_TOKEN}" \
        -H "Content-Type: application/json" \
        "${entry.data.endpoint}" \
        -d @- <<'CURLEOF'\n${payload}\nCURLEOF`);

      // 成功 → resolved に更新
      updateDLQEntry(entry.jobId, 'resolved');
      resolved++;
    } catch (retryError) {
      // 再失敗 → 既存エントリを更新（新規作成ではない）
      const nextAttempt = entry.attemptsMade + 1;
      if (nextAttempt >= MAX_RETRIES) {
        updateDLQEntry(entry.jobId, 'exhausted');
      } else {
        // attemptsMade と nextRetry を更新（既存エントリの上書き）
        const raw = exec(`cat ${DLQ_PATH} 2>/dev/null || echo ""`);
        const entries = raw.trim().split('\n').map(line => JSON.parse(line));
        const updated = entries.map(e => {
          if (e.jobId === entry.jobId) {
            return { ...e, attemptsMade: nextAttempt, nextRetry: Date.now() + backoff(nextAttempt), lastError: String(retryError) };
          }
          return e;
        });
        const content = updated.map(e => JSON.stringify(e)).join('\n');
        exec(`cat <<'DLQEOF' > ${DLQ_PATH}\n${content}\nDLQEOF`);
      }
    }
  }

  return { total: retryable.length, resolved };
}
```

### DLQクリーンアップ

| ルール | 値 | タイミング |
|--------|-----|---------|
| resolved エントリ | 24時間後に削除 | 各実行の末尾 |
| exhausted エントリ | 7日後に削除 | 各実行の末尾 |
| pending エントリ | 削除しない（リトライ対象） | - |

```javascript
// クリーンアップ（7日以上前のexhausted + 24時間以上前のresolved）
function cleanupDLQ() {
  const raw = exec(`cat ${DLQ_PATH} 2>/dev/null || echo ""`);
  if (!raw.trim()) return;

  const entries = raw.trim().split('\n').map(line => JSON.parse(line));
  const now = Date.now();
  const DAY_MS = 86400000;

  const kept = entries.filter(entry => {
    if (entry.state === 'resolved' && now - entry.timestamp > DAY_MS) return false;
    if (entry.state === 'exhausted' && now - entry.timestamp > 7 * DAY_MS) return false;
    return true;
  });

  // 全体を書き直し（heredoc でシェルエスケープ問題を回避 — P0 #18 解消）
  const content = kept.map(e => JSON.stringify(e)).join('\n');
  exec(`cat <<'DLQEOF' > ${DLQ_PATH}\n${content}\nDLQEOF`);
}
```

### べき等性（重複保存防止）

| 対策 | 実装 |
|------|------|
| **hookのjobIdを送信** | Railway API POSTリクエストに `idempotencyKey: jobId` を含める |
| **Railway API側で重複チェック** | 同じ `idempotencyKey` の2回目以降はスキップ |
| **DLQ側でresolved確認** | リトライ前に既にresolvedでないか確認 |

### DLQ テストケース（追加分）

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 50 | `test_writeToDLQ_creates_entry` | hook + error | DLQファイルに1行追記、state='pending' | 書き込み |
| 51 | `test_writeToDLQ_exhausted_on_max` | attemptsMade=4 (5回目) | state='exhausted' | 上限到達 |
| 52 | `test_calcDelay_exponential` | attempt=1,2,3 | 60s, 120s, 240s（±jitter） | 指数バックオフ |
| 53 | `test_calcDelay_max_cap` | attempt=20 | <= 3,600,000ms（1時間） | 上限キャップ |
| 54 | `test_readRetryable_filters` | pending×2 + exhausted×1 + resolved×1 | 長さ2（pendingのみ） | フィルタ |
| 55 | `test_readRetryable_respects_nextRetry` | nextRetry=未来 | 空配列（まだ早い） | 時刻判定 |
| 56 | `test_retryDLQ_success` | Railway APIモック成功 | resolved=1 | リトライ成功 |
| 57 | `test_retryDLQ_fail_again` | Railway APIモック再失敗 | 新DLQエントリ（attempt+1） | リトライ再失敗 |
| 58 | `test_cleanupDLQ_removes_old` | 8日前のexhausted | 削除される | クリーンアップ |
| 59 | `test_cleanupDLQ_keeps_pending` | 8日前のpending | 保持される | pending保護 |
| 60 | `test_updateDLQEntry_resolves` | jobId存在 + 'resolved' | 対象エントリのstate='resolved'、他エントリは不変 | P0 #17 updateDLQEntry |
| 61 | `test_updateDLQEntry_missing_jobId` | 存在しないjobId | 全エントリ不変（エラーなし） | 不在jobId |
| 62 | `test_shellEscape_singleQuote` | hook.content に `it's` を含むhook | DLQファイルに正しく書き込み | P0 #18 シェルエスケープ |
| 63 | `test_shellEscape_jsonSpecialChars` | hook.content に `{"key":"val"}` を含むhook | curl -d で正しく送信 | P0 #18 JSON in JSON |

---

## Spec完了チェックリスト

| # | セクション | 状態 | テスト数 |
|---|-----------|------|---------|
| 1 | 概要（What & Why） | ✅ | - |
| 2 | 受け入れ条件 | ✅ | AC-1〜AC-10 |
| 3 | As-Is / To-Be | ✅ | - |
| 4 | テストマトリックス | ✅ | 59テスト |
| 5 | 境界（やらないこと） | ✅ | B-1〜B-10 |
| 6 | 実行手順 | ✅ | デプロイ6ステップ + テスト5種 |
| 7 | E2E判定 | ✅ | 不要（バックエンドのみ） |
| 8 | ファイル構成 | ✅ | SKILL.mdのみ |
| 9 | DLQリトライロジック | ✅ | 14テスト (#50-63) |
| 10 | Thompson Sampling v2 | ✅ | 9テスト (#41-49) |
| 11 | モックAPIレスポンス | ✅ | 5ソース分 |
| 12 | LLM出力バリデーション | ✅ | JSON Schema 2種 |
| 13 | 重複判定アルゴリズム | ✅ | Jaccard bi-gram |
| **合計テスト数** | | | **63** |
