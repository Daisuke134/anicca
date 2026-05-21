# Spec: aggregateTypeStats を nudge-cron に統合

## 概要

`aggregateTypeStats.js` を別のRailwayサービスとして動かすのではなく、既存の `nudge-cron` ジョブに統合する。

## 背景

- 現状: `aggregateTypeStats.js` は `CRON_MODE=aggregate_type_stats` で別サービスとして動く設計
- 問題: ユーザー数が少ない段階で別サービスを作るのはoverkill
- 解決: `generateNudges.js` の最初で呼び出し、同一ジョブ内で実行

## 実行順序

```
nudge-cron (20:00 UTC / 5:00 JST)
  ├─ Step 0a: runAggregateTypeStats(query) ← 統計集計（non-fatal）
  ├─ Step 0b: runCrossPlatformSync(query) ← 既存のcross-platform learning
  └─ Step 1-N: runGenerateNudges() の既存処理
```

---

## パッチ 1: aggregateTypeStats.js をリファクタリング（Pool削除、query注入）

**ファイル:** `apps/api/src/jobs/aggregateTypeStats.js`

**問題:** モジュールレベルでPoolを作成すると、generateNudges.jsから呼ばれた時にコネクションリークが発生する。

**解決:** syncCrossPlatform.js と同じパターンで、query関数を引数として受け取る。

**変更後の全体:**

```javascript
/**
 * Cross-User Learning 統計集計ジョブ
 *
 * generateNudges.js から呼び出される。
 * nudge_events から過去60日間のデータを集計し、type_stats を更新。
 */

/**
 * type_stats テーブルを集計・更新
 * @param {Function} query - DB query function (injected from caller)
 */
export async function runAggregateTypeStats(query) {
  console.log('✅ [AggregateTypeStats] Starting type_stats aggregation');

  try {
    // 過去60日間の nudge_events を集計
    const result = await query(`
      WITH event_counts AS (
        SELECT
          ne.state->>'user_type' as type_id,
          -- tone正規化: 許可リスト外はデフォルト'logical'にフォールバック
          CASE WHEN ne.state->>'tone' IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')
               THEN ne.state->>'tone'
               ELSE 'logical'
          END as tone,
          COUNT(*) as total_events,
          COUNT(CASE WHEN no.signals->>'outcome' = 'tapped' THEN 1 END) as tapped,
          COUNT(CASE WHEN no.signals->>'outcome' = 'tapped' AND no.signals->>'thumbsUp' = 'true' THEN 1 END) as thumbs_up,
          COUNT(CASE WHEN no.signals->>'outcome' = 'tapped' AND no.signals->>'thumbsUp' = 'false' THEN 1 END) as thumbs_down
        FROM nudge_events ne
        LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
        WHERE ne.domain = 'problem_nudge'
          AND ne.created_at >= NOW() - INTERVAL '60 days'
          AND ne.state->>'user_type' IS NOT NULL
          AND ne.state->>'user_type' IN ('T1', 'T2', 'T3', 'T4')
        GROUP BY ne.state->>'user_type',
                 CASE WHEN ne.state->>'tone' IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')
                      THEN ne.state->>'tone'
                      ELSE 'logical'
                 END
      )
      INSERT INTO type_stats (type_id, tone, tapped_count, ignored_count, thumbs_up_count, thumbs_down_count, sample_size, updated_at)
      SELECT
        type_id,
        tone,
        tapped::BIGINT as tapped_count,
        (total_events - tapped)::BIGINT as ignored_count,
        thumbs_up::BIGINT as thumbs_up_count,
        thumbs_down::BIGINT as thumbs_down_count,
        total_events::BIGINT as sample_size,
        NOW() as updated_at
      FROM event_counts
      ON CONFLICT (type_id, tone) DO UPDATE SET
        tapped_count = EXCLUDED.tapped_count,
        ignored_count = EXCLUDED.ignored_count,
        thumbs_up_count = EXCLUDED.thumbs_up_count,
        thumbs_down_count = EXCLUDED.thumbs_down_count,
        sample_size = EXCLUDED.sample_size,
        updated_at = EXCLUDED.updated_at
    `);

    console.log(`✅ [AggregateTypeStats] Updated ${result.rowCount} type_stats rows`);

    // 集計結果を確認
    const statsResult = await query(`
      SELECT type_id, tone, sample_size, tap_rate, thumbs_up_rate
      FROM type_stats
      ORDER BY sample_size DESC
      LIMIT 10
    `);

    console.log('📊 [AggregateTypeStats] Top 10 stats:');
    for (const row of statsResult.rows) {
      const tapRate = Math.round(Number(row.tap_rate) * 100);
      const thumbsRate = Math.round(Number(row.thumbs_up_rate) * 100);
      console.log(`  ${row.type_id}/${row.tone}: sample=${row.sample_size}, tap=${tapRate}%, 👍=${thumbsRate}%`);
    }

    return { success: true, rowCount: result.rowCount };
  } catch (error) {
    console.error('❌ [AggregateTypeStats] Failed:', error.message);
    throw error;
  }
}
```

---

## パッチ 2: generateNudges.js にインポート追加

**ファイル:** `apps/api/src/jobs/generateNudges.js`

**場所:** 19行目付近（既存のインポートの後）

```diff
 import { runCrossPlatformSync } from './syncCrossPlatform.js';
+import { runAggregateTypeStats } from './aggregateTypeStats.js';
 import { collectAllGrounding } from '../agents/groundingCollectors.js';
```

---

## パッチ 3: generateNudges.js の runGenerateNudges 関数に呼び出し追加

**ファイル:** `apps/api/src/jobs/generateNudges.js`

**場所:** `runGenerateNudges` 関数内、既存の Step 0 の前（約295行目付近）

**現在のコード:**
```javascript
export async function runGenerateNudges() {
  console.log('✅ [GenerateNudges] Starting Phase 7+8 nudge generation cron job');

  // Step 0: Cross-Platform Learning — 前日のメトリクスを処理
  try {
    console.log('🔁 [GenerateNudges] Running cross-platform learning pipeline...');
    await runCrossPlatformSync(query);
```

**変更後:**
```javascript
export async function runGenerateNudges() {
  console.log('✅ [GenerateNudges] Starting Phase 7+8 nudge generation cron job');

  // Step 0a: Cross-user learning stats aggregation (optional, non-fatal)
  try {
    await runAggregateTypeStats(query);
    console.log('✅ [GenerateNudges] type_stats aggregation completed');
  } catch (err) {
    console.warn(`⚠️ [GenerateNudges] type_stats aggregation failed (non-fatal): ${err.message}`);
  }

  // Step 0b: Cross-Platform Learning — 前日のメトリクスを処理
  try {
    console.log('🔁 [GenerateNudges] Running cross-platform learning pipeline...');
    await runCrossPlatformSync(query);
```

---

## パッチ 4: aggregateTypeStats.test.js を更新（query注入パターン対応）

**ファイル:** `apps/api/src/jobs/__tests__/aggregateTypeStats.test.js`

**変更後の全体:**

```javascript
/**
 * AggregateTypeStats ジョブのテスト
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { runAggregateTypeStats } from '../aggregateTypeStats.js';

describe('aggregateTypeStats', () => {
  let mockQuery;

  beforeEach(() => {
    mockQuery = vi.fn();
  });

  it('should aggregate type_stats from nudge_events', async () => {
    // Mock INSERT result
    mockQuery.mockResolvedValueOnce({ rowCount: 8 });

    // Mock SELECT result for logging
    mockQuery.mockResolvedValueOnce({
      rows: [
        { type_id: 'T1', tone: 'gentle', sample_size: 100, tap_rate: 0.45, thumbs_up_rate: 0.80 },
        { type_id: 'T2', tone: 'logical', sample_size: 80, tap_rate: 0.38, thumbs_up_rate: 0.75 },
      ],
    });

    const result = await runAggregateTypeStats(mockQuery);

    expect(result.success).toBe(true);
    expect(result.rowCount).toBe(8);

    // Verify INSERT query was called
    expect(mockQuery).toHaveBeenCalledTimes(2);
    const insertCall = mockQuery.mock.calls[0][0];
    expect(insertCall).toContain('INSERT INTO type_stats');
    expect(insertCall).toContain('ON CONFLICT (type_id, tone) DO UPDATE');
  });

  it('should handle empty results gracefully', async () => {
    mockQuery.mockResolvedValueOnce({ rowCount: 0 });
    mockQuery.mockResolvedValueOnce({ rows: [] });

    const result = await runAggregateTypeStats(mockQuery);

    expect(result.success).toBe(true);
    expect(result.rowCount).toBe(0);
  });

  it('should throw on database error', async () => {
    mockQuery.mockRejectedValueOnce(new Error('Connection failed'));

    await expect(runAggregateTypeStats(mockQuery)).rejects.toThrow('Connection failed');
  });

  it('should filter only valid user types (T1-T4)', async () => {
    mockQuery.mockResolvedValueOnce({ rowCount: 4 });
    mockQuery.mockResolvedValueOnce({ rows: [] });

    await runAggregateTypeStats(mockQuery);

    const insertCall = mockQuery.mock.calls[0][0];
    expect(insertCall).toContain("IN ('T1', 'T2', 'T3', 'T4')");
  });

  it('should normalize invalid tones to logical', async () => {
    mockQuery.mockResolvedValueOnce({ rowCount: 4 });
    mockQuery.mockResolvedValueOnce({ rows: [] });

    await runAggregateTypeStats(mockQuery);

    const insertCall = mockQuery.mock.calls[0][0];
    expect(insertCall).toContain("ELSE 'logical'");
  });
});
```

---

## パッチ 5: generateNudges.test.js に統合テスト追加

**ファイル:** `apps/api/src/jobs/__tests__/generateNudges.test.js`

**追加するテスト:**

```javascript
it('imports and calls runAggregateTypeStats', () => {
  expect(generaTeNudgesSource).toContain(
    "import { runAggregateTypeStats } from './aggregateTypeStats.js'"
  );
  expect(generaTeNudgesSource).toContain('await runAggregateTypeStats(query)');
});

it('wraps runAggregateTypeStats in try/catch for graceful degradation', () => {
  const syncCallIndex = generaTeNudgesSource.indexOf('await runAggregateTypeStats(query)');
  expect(syncCallIndex).toBeGreaterThan(0);

  const beforeSync = generaTeNudgesSource.substring(0, syncCallIndex);
  const lastTry = beforeSync.lastIndexOf('try {');
  expect(lastTry).toBeGreaterThan(0);

  const afterSync = generaTeNudgesSource.substring(syncCallIndex);
  const catchBlock = afterSync.substring(0, 200);
  expect(catchBlock).toContain('warn');
});
```

---

## テスト要件

| テスト | 期待結果 |
|--------|---------|
| `npm test -- --run src/jobs/__tests__/generateNudges.test.js` | Pass |
| `npm test -- --run src/jobs/__tests__/aggregateTypeStats.test.js` | Pass |
| 統合テスト: `runGenerateNudges()` を呼ぶと `runAggregateTypeStats(query)` も実行される | Pass |
| `runAggregateTypeStats(query)` が失敗しても `runGenerateNudges()` は続行する | Pass |

---

## Railway 設定変更

**変更なし。** 新しいサービスは不要。既存の `nudge-cron` がそのまま動く。

---

## 完了条件

- [ ] パッチ 1: aggregateTypeStats.js をリファクタリング（Pool削除、query注入）
- [ ] パッチ 2: generateNudges.js にインポート追加
- [ ] パッチ 3: generateNudges.js に呼び出し追加（Step 0a）
- [ ] パッチ 4: aggregateTypeStats.test.js を更新
- [ ] パッチ 5: generateNudges.test.js に統合テスト追加
- [ ] 全テスト Pass
- [ ] Lint エラーなし
