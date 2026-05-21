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
