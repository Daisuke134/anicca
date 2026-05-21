/**
 * Grounding Variable Collectors for Commander Agent
 *
 * Each collector returns a formatted string for prompt injection.
 * Data window limits (spec L450-464):
 *   userState:        7 days, LIMIT 50
 *   hookPerformanceData: 7 days
 *   thompsonSamplingResult: all-time (α/β cumulative)
 *   typeStats:        latest daily aggregation
 *   crossPlatformData: 7 days, top 10
 *   flattenedSlotTable: today (pre-trimmed, max 32)
 *   behavioralScienceGuidelines: hardcoded, user-selected problems only
 */

import { buildFlattenedSlotTable, trimSlots, getScheduleMap } from './scheduleMap.js';

// ===== userState =====

/**
 * Build userState grounding: userId, problems, 7-day story, consecutive ignored days, per-problem tapRate.
 *
 * @param {Function} query - DB query function
 * @param {string} userId
 * @param {string[]} problems
 * @param {string} preferredLanguage
 * @returns {Promise<string>}
 */
export async function collectUserState(query, userId, problems, preferredLanguage) {
  // 7-day nudge history (LIMIT 50)
  const historyResult = await query(`
    SELECT
      ne.subtype as problem_type,
      ne.state->>'hook' as hook,
      ne.state->>'content' as content,
      ne.state->>'tone' as tone,
      ne.state->>'scheduledTime' as scheduled_time,
      ne.created_at,
      no.signals->>'hookFeedback' as hook_feedback,
      no.signals->>'contentFeedback' as content_feedback,
      no.reward
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '7 days'
    ORDER BY ne.created_at ASC
    LIMIT 50
  `, [userId]);

  // Per-problem tapRate
  const tapRateResult = await query(`
    SELECT
      ne.subtype as problem_type,
      COUNT(*) as total,
      SUM(CASE WHEN no.reward = 1 THEN 1 ELSE 0 END) as tapped
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '7 days'
      AND no.id IS NOT NULL
    GROUP BY ne.subtype
  `, [userId]);

  // Consecutive ignored days
  const ignoredResult = await query(`
    SELECT DATE(ne.created_at) as day,
      bool_and(no.reward = 0 OR no.reward IS NULL) as all_ignored
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '7 days'
    GROUP BY DATE(ne.created_at)
    ORDER BY day DESC
  `, [userId]);

  let consecutiveIgnored = 0;
  for (const row of ignoredResult.rows) {
    if (row.all_ignored) consecutiveIgnored++;
    else break;
  }

  // Format
  let output = `userId: ${userId}\n`;
  output += `言語: ${preferredLanguage}\n`;
  output += `選択問題: ${problems.join(', ')}\n`;
  output += `連続無視日数: ${consecutiveIgnored}日\n\n`;

  // Per-problem tapRate
  output += '### 問題別tapRate（過去7日）\n';
  for (const row of tapRateResult.rows) {
    const rate = row.total > 0 ? Math.round((row.tapped / row.total) * 100) : 0;
    output += `- ${row.problem_type}: ${rate}% (${row.tapped}/${row.total})\n`;
  }
  output += '\n';

  // 7-day story
  output += '### 過去7日のストーリー\n';
  if (historyResult.rows.length === 0) {
    output += '履歴なし（新規ユーザー）\n';
  } else {
    let currentDay = null;
    for (const row of historyResult.rows) {
      const day = row.created_at.toISOString().split('T')[0];
      if (day !== currentDay) {
        currentDay = day;
        output += `\n**${day}**\n`;
      }
      const time = row.scheduled_time || `${row.created_at.getHours()}:00`;
      const outcome = row.hook_feedback || (row.reward === 1 ? 'tapped' : row.reward === 0 ? 'ignored' : 'unknown');
      const feedback = row.content_feedback === 'thumbsUp' ? ' 👍' : row.content_feedback === 'thumbsDown' ? ' 👎' : '';
      output += `- ${time} ${row.problem_type}: (${row.tone}) → ${outcome}${feedback}\n`;
      output += `    Hook: "${row.hook || 'N/A'}"\n`;
      if (row.content && (row.content_feedback === 'thumbsUp' || row.content_feedback === 'thumbsDown')) {
        output += `    Content: "${row.content}"\n`;
      }
    }
  }

  return output;
}

// ===== thompsonSamplingResult =====

/**
 * Collect Thompson Sampling results.
 * Phase 3 will implement full Beta distribution. For now, returns per-problem tone stats.
 *
 * @param {Function} query
 * @param {string} userId
 * @param {string[]} problems
 * @returns {Promise<string>}
 */
export async function collectThompsonSampling(query, userId, problems) {
  // Use nudge_events + nudge_outcomes to compute α/β per (problem × tone)
  const result = await query(`
    SELECT
      ne.subtype as problem_type,
      ne.state->>'tone' as tone,
      COUNT(*) as total,
      SUM(CASE WHEN no.reward = 1 THEN 1 ELSE 0 END) as successes,
      SUM(CASE WHEN no.reward = 0 THEN 1 ELSE 0 END) as failures
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND no.id IS NOT NULL
    GROUP BY ne.subtype, ne.state->>'tone'
    ORDER BY ne.subtype, SUM(CASE WHEN no.reward = 1 THEN 1 ELSE 0 END) DESC
  `, [userId]);

  if (result.rows.length === 0) {
    return '統計データなし（新規ユーザー）。全アクションを均等に探索せよ。\n';
  }

  let output = '| 問題 | トーン | α (成功) | β (失敗) | 推定勝率 | サンプル |\n';
  output += '|------|--------|----------|----------|----------|----------|\n';

  for (const row of result.rows) {
    // Beta distribution: α = successes + 1, β = failures + 1 (prior = 1)
    const alpha = Number(row.successes) + 1;
    const beta = Number(row.failures) + 1;
    const winRate = Math.round((alpha / (alpha + beta)) * 100);
    output += `| ${row.problem_type} | ${row.tone || 'unknown'} | ${alpha} | ${beta} | ${winRate}% | ${row.total} |\n`;
  }

  return output;
}

// ===== hookPerformanceData =====

/**
 * Collect hook performance data (7-day window).
 * Reuses logic from nudgeHelpers.getHookContentPerformance.
 *
 * @param {Function} query
 * @param {string} userId
 * @param {string[]} problems
 * @returns {Promise<string>}
 */
export async function collectHookPerformance(query, userId, problems) {
  const result = await query(`
    SELECT
      ne.state->>'hook' as hook,
      ne.state->>'tone' as tone,
      ne.subtype as problem_type,
      COUNT(*) as total,
      SUM(CASE WHEN no.reward = 1 THEN 1 ELSE 0 END) as tapped
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '7 days'
      AND no.id IS NOT NULL
    GROUP BY ne.state->>'hook', ne.state->>'tone', ne.subtype
    ORDER BY SUM(CASE WHEN no.reward = 1 THEN 1 ELSE 0 END) DESC
  `, [userId]);

  if (result.rows.length === 0) {
    return '過去7日のhookデータなし。\n';
  }

  let output = '';
  for (const problem of problems) {
    const hooks = result.rows.filter(r => r.problem_type === problem);
    if (hooks.length === 0) continue;

    output += `### ${problem}\n`;
    for (const h of hooks.slice(0, 5)) {
      const tapRate = h.total > 0 ? Math.round((h.tapped / h.total) * 100) : 0;
      const emoji = tapRate >= 70 ? '✨' : tapRate <= 30 ? '❌' : '';
      output += `- "${h.hook}" (${h.tone}) → tap率${tapRate}% (${h.tapped}/${h.total}) ${emoji}\n`;
    }
    output += '\n';
  }

  return output;
}

// ===== typeStats =====

/**
 * Collect cross-user type_stats.
 *
 * @param {Function} query
 * @param {string} userId
 * @param {string[]} problems
 * @returns {Promise<string>}
 */
export async function collectTypeStats(query, userId, problems) {
  // Get user type first
  const typeResult = await query(
    `SELECT primary_type FROM user_type_estimates WHERE user_id = $1::uuid`,
    [userId]
  );
  const userType = typeResult.rows[0]?.primary_type;

  if (!userType) {
    return 'ユーザータイプ未分類。cross-userデータなし。\n';
  }

  const statsResult = await query(`
    SELECT type_id, tone, tap_rate, thumbs_up_rate, sample_size
    FROM type_stats
    WHERE type_id = $1 AND sample_size >= 10
    ORDER BY tap_rate DESC
  `, [userType]);

  if (statsResult.rows.length === 0) {
    return `ユーザータイプ: ${userType}。十分なcross-userデータなし。\n`;
  }

  let output = `ユーザータイプ: ${userType}\n\n`;
  output += '| トーン | tap率 | 👍率 | サンプル |\n';
  output += '|--------|-------|------|----------|\n';

  for (const row of statsResult.rows) {
    const tapRate = Math.round(Number(row.tap_rate) * 100);
    const thumbsRate = Math.round(Number(row.thumbs_up_rate) * 100);
    output += `| ${row.tone} | ${tapRate}% | ${thumbsRate}% | ${row.sample_size} |\n`;
  }

  return output;
}

// ===== crossPlatformData =====

/**
 * Collect cross-platform data (TikTok + X).
 * Phase 4 will populate these tables. Returns stub if empty.
 *
 * @param {Function} query
 * @returns {Promise<string>}
 */
export async function collectCrossPlatformData(query) {
  let output = '';

  // TikTok high performers (hook_candidates with tiktok scores)
  try {
    const tiktokResult = await query(`
      SELECT text, tone, tiktok_like_rate, tiktok_share_rate
      FROM hook_candidates
      WHERE tiktok_high_performer = true
      ORDER BY tiktok_like_rate DESC
      LIMIT 10
    `);

    if (tiktokResult.rows.length > 0) {
      output += '### TikTok High Performers\n';
      for (const row of tiktokResult.rows) {
        const likeRate = Math.round(Number(row.tiktok_like_rate || 0) * 100);
        const shareRate = Math.round(Number(row.tiktok_share_rate || 0) * 100);
        output += `- "${row.text}" (${row.tone}) like${likeRate}% share${shareRate}%\n`;
      }
      output += '\n';
    }
  } catch {
    // Table may not exist yet
  }

  // X posts performance
  try {
    const xResult = await query(`
      SELECT text, engagement_rate, impression_count
      FROM x_posts
      WHERE created_at >= NOW() - INTERVAL '7 days'
      ORDER BY engagement_rate DESC
      LIMIT 10
    `);

    if (xResult.rows.length > 0) {
      output += '### X/Twitter Recent Performance\n';
      for (const row of xResult.rows) {
        const engagement = Math.round(Number(row.engagement_rate || 0) * 100);
        output += `- "${(row.text || '').slice(0, 40)}..." engagement${engagement}% imp${row.impression_count}\n`;
      }
      output += '\n';
    }
  } catch {
    // Table may not exist yet
  }

  return output || 'クロスプラットフォームデータなし。\n';
}

// ===== flattenedSlotTable =====

/**
 * Build flattenedSlotTable as markdown for prompt injection.
 *
 * @param {string[]} problemTypes
 * @param {string} [appVersion] - Client app version for schedule map selection
 * @returns {{ table: string, slots: Array }}
 */
export function collectFlattenedSlotTable(problemTypes, appVersion = null) {
  const scheduleMap = getScheduleMap(appVersion);
  const allSlots = buildFlattenedSlotTable(problemTypes, scheduleMap);
  const trimmed = trimSlots(allSlots, problemTypes, 32);

  let table = '| slotIndex | Time  | Problem          |\n';
  table += '|-----------|-------|------------------|\n';
  for (const slot of trimmed) {
    table += `| ${slot.slotIndex} | ${slot.scheduledTime} | ${slot.problemType} |\n`;
  }

  return { table, slots: trimmed };
}

// ===== behavioralScienceGuidelines =====

const GUIDELINES = {
  staying_up_late: {
    doNot: '「明日仕事だろ」系の外的動機付けは効かない',
    works: 'マイクロアクション（スマホを2m離す）、ドーパミン科学、逃避パターンの自覚',
    science: '就寝90分前のブルーライト排除でメラトニン分泌58%向上（Harvard Medical School, 2015）',
  },
  cant_wake_up: {
    doNot: '「怠惰だ」と責めるな。睡眠慣性は生理現象',
    works: '光療法（起床直後の光曝露）、2分ルール（まず足を床につける）、前夜の準備',
    science: '起床後30分の10,000ルクス光曝露でサーカディアンリズム3日以内に前進（Sleep Medicine Reviews, 2019）',
  },
  self_loathing: {
    doNot: '「自分を好きになれ」は逆効果。自己肯定の強制は抵抗を生む',
    works: 'セルフコンパッション（自分を友人のように扱う）、小さな成功体験の積み上げ、比較の停止',
    science: 'セルフコンパッション介入はself-criticism を40%減少させる（Neff & Germer, 2013, Journal of Clinical Psychology）',
  },
  rumination: {
    doNot: '「考えすぎるな」は反芻を悪化させる',
    works: '行動活性化（体を動かす）、注意訓練（感覚に集中）、認知的距離化（思考を観察する）',
    science: '10分のウォーキングで反芻が40%減少（Bratman et al., 2015, PNAS）',
  },
  procrastination: {
    doNot: '「やればいいだけ」は完璧主義者を追い詰める',
    works: '2分ルール（2分だけやる）、実装意図（If-Then計画）、タスク分解（最小単位に）',
    science: 'Zeigarnik効果: 始めたタスクは完了欲求を生む。2分で十分（Zeigarnik, 1927）',
  },
  anxiety: {
    doNot: '「大丈夫」「心配しすぎ」は不安を無効化する。共感が先',
    works: '4-7-8呼吸法、エクスポージャー（段階的接触）、不確実性への耐性訓練',
    science: '4-7-8呼吸法は副交感神経を活性化し、不安を62%減少（Ma et al., 2017, Frontiers in Psychology）',
  },
  lying: {
    doNot: '「嘘つき」とラベリングするな。防衛機制を理解せよ',
    works: '心理的安全性の構築、小さな真実の練習、ありのままの自分の受容',
    science: '嘘の83%は「社会的受容への恐れ」が原因（DePaulo et al., 1996, Journal of Personality and Social Psychology）',
  },
  bad_mouthing: {
    doNot: '「悪口やめろ」は表面的。根底の不安を見よ',
    works: '感謝の実践、比較マインドセットの転換、自己価値の内在化',
    science: '感謝日記3週間で悪口頻度が35%減少、自尊心が25%向上（Emmons & McCullough, 2003）',
  },
  porn_addiction: {
    doNot: '「変態」「意志が弱い」は恥を強化し悪循環を作る',
    works: 'トリガー回避（環境設計）、代替行動（運動）、孤独感への対処、段階的削減',
    science: 'ポルノ使用の根底は68%が「孤独」「退屈」（Grubbs et al., 2019, Archives of Sexual Behavior）',
  },
  alcohol_dependency: {
    doNot: '「やめろ」は無力。段階的削減と代替を提案せよ',
    works: 'ハームリダクション、飲酒トリガーの特定、ソバーキュリアスアプローチ',
    science: 'ハームリダクション: 段階的削減は即時断酒より6ヶ月継続率が2倍（Marlatt et al., 2012）',
  },
  anger: {
    doNot: '「落ち着け」は怒りを増幅する。感情の正当性を認めよ',
    works: '6秒ルール（怒りのピークは6秒）、認知再評価、身体運動による発散',
    science: '怒りのピークは6秒。この間の反応を遅延させると攻撃行動が90%減少（Ekman, 2003）',
  },
  obsessive: {
    doNot: '「気にするな」は強迫を悪化させる',
    works: 'ERP（曝露反応妨害法）のセルフヘルプ版、不確実性への耐性訓練、マインドフルネス',
    science: 'ERP は強迫症状を60-80%減少させる（Foa & Kozak, 1986, Behavior Therapy）',
  },
  loneliness: {
    doNot: '「友達を作れ」は孤独な人にとって残酷',
    works: '小さな社会的接触（挨拶、雑談）、社会的認知の修正、共同体への段階的参加',
    science: '1日1回の「意味のある社会的接触」で孤独感が40%減少（Cacioppo et al., 2015）',
  },
};

/**
 * Build behavioral science guidelines for user's selected problems.
 *
 * @param {string[]} problemTypes
 * @returns {string}
 */
export function collectBehavioralScienceGuidelines(problemTypes) {
  let output = '';

  for (const pt of problemTypes) {
    const g = GUIDELINES[pt];
    if (!g) continue;

    output += `### ${pt}\n`;
    output += `- 🚫 絶対言うな: ${g.doNot}\n`;
    output += `- ✅ 効くこと: ${g.works}\n`;
    output += `- 📚 科学根拠: ${g.science}\n\n`;
  }

  return output || '行動科学ガイドラインなし。\n';
}

// ===== All-in-one collector =====

/**
 * Collect all grounding variables for Commander Agent.
 *
 * @param {Function} query - DB query function
 * @param {string} userId
 * @param {string[]} problems
 * @param {string} preferredLanguage
 * @param {string} [appVersion] - Client app version for schedule map selection (v1.6.0+)
 * @returns {Promise<{ grounding: object, slotTable: Array }>}
 */
export async function collectAllGrounding(query, userId, problems, preferredLanguage, appVersion = null) {
  // Parallel collection (independent queries)
  const [
    userState,
    thompsonSamplingResult,
    hookPerformanceData,
    typeStats,
    crossPlatformData,
  ] = await Promise.all([
    collectUserState(query, userId, problems, preferredLanguage),
    collectThompsonSampling(query, userId, problems),
    collectHookPerformance(query, userId, problems),
    collectTypeStats(query, userId, problems),
    collectCrossPlatformData(query),
  ]);

  // Sync collection (v1.6.0: pass appVersion for schedule map selection)
  const { table: flattenedSlotTable, slots: slotTable } = collectFlattenedSlotTable(problems, appVersion);
  const behavioralScienceGuidelines = collectBehavioralScienceGuidelines(problems);

  return {
    grounding: {
      userState,
      thompsonSamplingResult,
      hookPerformanceData,
      typeStats,
      crossPlatformData,
      flattenedSlotTable,
      behavioralScienceGuidelines,
    },
    slotTable,
  };
}
