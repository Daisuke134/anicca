# Cross-User Learning 集計ジョブ実装 TODO

**作成日**: 2026-02-02
**優先度**: 中
**ステータス**: 未実装

---

## 概要

Cross-User Learning システムの統計集計ジョブが未実装のため、`type_stats` テーブルが空のまま。
このジョブを実装しないと、Cross-User Learning が機能しない。

---

## 現状

| コンポーネント | 状態 | 説明 |
|---------------|------|------|
| ユーザー分類 | ✅ 動作中 | `userTypeService.js` でタイプを計算・保存 |
| 反応記録 | ✅ 動作中 | `generateNudges.js` で `nudge_events.state.user_type` に保存 |
| **統計集計** | ❌ **未実装** | `aggregateTypeStats.js` が存在しない |
| 統計活用 | ⚠️ 準備のみ | `groundingCollectors.js` がデータを読む準備はある |

---

## やるべきこと

### 1. `aggregateTypeStats.js` を作成

**場所**: `apps/api/src/jobs/aggregateTypeStats.js`

**機能**:
- `nudge_events` テーブルから過去60日間のイベントを集計
- タイプ × トーン ごとにタップ率・👍率を計算
- `type_stats` テーブルを更新

**参考SQL**:
```sql
WITH event_counts AS (
  SELECT
    ne.state->>'user_type' as type_id,
    ne.state->>'tone' as tone,
    COUNT(*) as total_events,
    COUNT(CASE WHEN no.signals->>'outcome' = 'tapped' THEN 1 END) as tapped,
    COUNT(CASE WHEN no.signals->>'thumbsUp' = 'true' THEN 1 END) as thumbs_up,
    COUNT(CASE WHEN no.signals->>'thumbsUp' = 'false' THEN 1 END) as thumbs_down
  FROM nudge_events ne
  LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
  WHERE ne.domain = 'problem_nudge'
    AND ne.created_at >= NOW() - INTERVAL '60 days'
    AND ne.state->>'user_type' IS NOT NULL
  GROUP BY type_id, tone
)
INSERT INTO type_stats (type_id, tone, tapped_count, ignored_count, thumbs_up_count, thumbs_down_count, sample_size, updated_at)
SELECT
  type_id, tone, tapped, total_events - tapped, thumbs_up, thumbs_down, total_events, NOW()
FROM event_counts
ON CONFLICT (type_id, tone) DO UPDATE SET
  tapped_count = EXCLUDED.tapped_count,
  ignored_count = EXCLUDED.ignored_count,
  thumbs_up_count = EXCLUDED.thumbs_up_count,
  thumbs_down_count = EXCLUDED.thumbs_down_count,
  sample_size = EXCLUDED.sample_size,
  updated_at = EXCLUDED.updated_at;
```

### 2. Railway Cron設定

- **サービス名**: `aggregate-stats-cron`
- **環境変数**: `CRON_MODE=aggregate_type_stats`
- **スケジュール**: `0 21 * * *` (毎日6:00 JST)

---

## なぜ重要か

Cross-User Learning は「似たユーザーには似たNudgeが効く」という機能。

- **今の状態**: データは溜まっているが集計されていない → 機能していない
- **実装後**: 日々のデータが集計され、新規ユーザーへのNudge精度が向上

---

## 確認方法

実装後、以下で確認:

```sql
SELECT * FROM type_stats ORDER BY sample_size DESC;
```

データが入っていれば成功。

---

## 関連ファイル

- `apps/api/src/services/userTypeService.js` - ユーザー分類ロジック
- `apps/api/src/jobs/generateNudges.js` - Nudge生成（タイプ保存）
- `apps/api/src/agents/groundingCollectors.js` - 統計読み取り
- `apps/api/prisma/schema.prisma` - type_stats, user_type_estimates テーブル定義
