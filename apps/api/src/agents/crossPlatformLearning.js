/**
 * Cross-Platform Learning Module (Phase 5 + 1.6.1 Extension)
 *
 * Z-Score normalization across 5 platforms: App, TikTok, X, Moltbook, Slack.
 * Promotion pipeline: X → TikTok → App Nudge + Agent → HookCandidates.
 */

// ── Z-Score Constants ───────────────────────────────────────────────────────
// Initial baselines (updated daily from actual data via refreshBaselines)
let APP_MEAN = 0.25;   // avg app tap rate
let APP_STDDEV = 0.15;
let TIK_MEAN = 0.05;   // avg TikTok like rate
let TIK_STDDEV = 0.03;
let X_MEAN = 0.02;     // avg X engagement rate
let X_STDDEV = 0.015;

// 1.6.1: Moltbook and Slack baselines
let MOLTBOOK_VIEWS_MEAN = 0.05;   // upvotes / views
let MOLTBOOK_VIEWS_STDDEV = 0.03;
let MOLTBOOK_UPVOTES_MEAN = 3.0;  // absolute upvotes (for views=null)
let MOLTBOOK_UPVOTES_STDDEV = 2.0;
let SLACK_MEAN = 0.10;  // reactions / messages
let SLACK_STDDEV = 0.05;

// Minimum sample sizes for statistical significance
const MIN_APP_SAMPLES = 5;
const MIN_TIKTOK_SAMPLES = 3;
const MIN_X_SAMPLES = 10;
const MIN_MOLTBOOK_SAMPLES = 10;
const MIN_MOLTBOOK_VIEWS = 10;  // minimum views to use views-based calculation
const MIN_SLACK_SAMPLES = 5;

// 1.6.1: 5-channel weights (spec: App=0.40, TikTok=0.20, X=0.15, Moltbook=0.15, Slack=0.10)
const W_APP = 0.40;
const W_TIK = 0.20;
const W_X = 0.15;
const W_MOLT = 0.15;
const W_SLACK = 0.10;

// Promotion thresholds
const X_TO_TIKTOK_THRESHOLD = 1.0;
const TIKTOK_TO_APP_THRESHOLD = 1.5;
const AGENT_PROMOTION_UPVOTES = 5;
const AGENT_PROMOTION_UNIFIED_SCORE = 0.5;

// ── Z-Score Calculation ─────────────────────────────────────────────────────

/**
 * Calculate unified Z-Score for a hook candidate (5 channels).
 *
 * @param {object} hook
 * @param {number} hook.appTapRate - App tap rate (0-1)
 * @param {number} hook.appSampleSize - Number of app nudge sends
 * @param {number} hook.tiktokLikeRate - TikTok like rate (0-1)
 * @param {number} hook.tiktokSampleSize - Number of TikTok posts
 * @param {number} hook.xEngagementRate - X engagement rate (0-1)
 * @param {number} hook.xSampleSize - Number of X posts
 * @param {number} [hook.moltbookUpvotes] - Moltbook upvotes
 * @param {number} [hook.moltbookViews] - Moltbook views
 * @param {number} [hook.moltbookSampleSize] - Number of Moltbook posts
 * @param {number} [hook.slackReactions] - Slack total reactions
 * @param {number} [hook.slackSampleSize] - Number of Slack messages
 * @returns {number} Unified Z-Score
 */
export function unifiedScore(hook) {
  const appZ = hook.appSampleSize >= MIN_APP_SAMPLES
    ? (hook.appTapRate - APP_MEAN) / (APP_STDDEV || 1) : 0;
  const tikZ = hook.tiktokSampleSize >= MIN_TIKTOK_SAMPLES
    ? (hook.tiktokLikeRate - TIK_MEAN) / (TIK_STDDEV || 1) : 0;
  const xZ = hook.xSampleSize >= MIN_X_SAMPLES
    ? (hook.xEngagementRate - X_MEAN) / (X_STDDEV || 1) : 0;

  // 1.6.1: Moltbook Z-Score
  let moltZ = 0;
  if (hook.moltbookSampleSize >= MIN_MOLTBOOK_SAMPLES) {
    if (hook.moltbookViews != null && hook.moltbookViews >= MIN_MOLTBOOK_VIEWS) {
      // Use upvotes/views ratio
      const rate = hook.moltbookUpvotes / hook.moltbookViews;
      moltZ = (rate - MOLTBOOK_VIEWS_MEAN) / (MOLTBOOK_VIEWS_STDDEV || 1);
    } else if (hook.moltbookViews === null || hook.moltbookViews === undefined) {
      // Fallback: use absolute upvotes with separate baseline
      moltZ = (hook.moltbookUpvotes - MOLTBOOK_UPVOTES_MEAN) / (MOLTBOOK_UPVOTES_STDDEV || 1);
    }
    // If views === 0, exclude from calculation (moltZ stays 0)
  }

  // 1.6.1: Slack Z-Score
  let slackZ = 0;
  if (hook.slackSampleSize >= MIN_SLACK_SAMPLES && hook.slackReactions != null) {
    const rate = hook.slackReactions / hook.slackSampleSize;
    slackZ = (rate - SLACK_MEAN) / (SLACK_STDDEV || 1);
  }

  return W_APP * appZ + W_TIK * tikZ + W_X * xZ + W_MOLT * moltZ + W_SLACK * slackZ;
}

/**
 * Calculate individual platform Z-Score.
 * @param {number} value
 * @param {number} mean
 * @param {number} stddev
 * @returns {number}
 */
export function zScore(value, mean, stddev) {
  if (!stddev || stddev === 0) return 0;
  return (value - mean) / stddev;
}

// ── Baseline Refresh ────────────────────────────────────────────────────────

/**
 * Refresh Z-Score baselines from actual DB data.
 * Called during daily cron job.
 *
 * @param {Function} query - DB query function
 */
export async function refreshBaselines(query) {
  // App baselines: from nudge_outcomes
  const appResult = await query(`
    SELECT
      AVG(CASE WHEN no.reward = 1 THEN 1.0 ELSE 0.0 END) as mean_tap_rate,
      STDDEV_POP(CASE WHEN no.reward = 1 THEN 1.0 ELSE 0.0 END) as stddev_tap_rate
    FROM nudge_events ne
    JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '30 days'
  `);

  if (appResult.rows[0]?.mean_tap_rate != null) {
    APP_MEAN = Number(appResult.rows[0].mean_tap_rate);
    APP_STDDEV = Math.max(Number(appResult.rows[0].stddev_tap_rate) || 0.15, 0.01);
  }

  // TikTok baselines: from hook_candidates tiktok metrics
  const tikResult = await query(`
    SELECT
      AVG(tiktok_like_rate) as mean_like_rate,
      STDDEV_POP(tiktok_like_rate) as stddev_like_rate
    FROM hook_candidates
    WHERE tiktok_like_rate > 0
  `);

  if (tikResult.rows[0]?.mean_like_rate != null) {
    TIK_MEAN = Number(tikResult.rows[0].mean_like_rate);
    TIK_STDDEV = Math.max(Number(tikResult.rows[0].stddev_like_rate) || 0.03, 0.001);
  }

  // X baselines: from x_posts
  try {
    const xResult = await query(`
      SELECT
        AVG(engagement_rate) as mean_engagement,
        STDDEV_POP(engagement_rate) as stddev_engagement
      FROM x_posts
      WHERE engagement_rate > 0
    `);

    if (xResult.rows[0]?.mean_engagement != null) {
      X_MEAN = Number(xResult.rows[0].mean_engagement);
      X_STDDEV = Math.max(Number(xResult.rows[0].stddev_engagement) || 0.015, 0.001);
    }
  } catch {
    // x_posts table may not exist yet
  }

  // 1.6.1: Moltbook baselines (views-based)
  try {
    const moltViewsResult = await query(`
      SELECT
        AVG(upvotes::float / NULLIF(views, 0)) as mean_rate,
        STDDEV_POP(upvotes::float / NULLIF(views, 0)) as stddev_rate
      FROM agent_posts
      WHERE platform = 'moltbook'
        AND views IS NOT NULL
        AND views >= $1
        AND created_at >= NOW() - INTERVAL '30 days'
    `, [MIN_MOLTBOOK_VIEWS]);

    if (moltViewsResult.rows[0]?.mean_rate != null) {
      MOLTBOOK_VIEWS_MEAN = Number(moltViewsResult.rows[0].mean_rate);
      MOLTBOOK_VIEWS_STDDEV = Math.max(Number(moltViewsResult.rows[0].stddev_rate) || 0.03, 0.001);
    }
  } catch {
    // agent_posts may not exist yet
  }

  // 1.6.1: Moltbook baselines (upvotes-only, for views=null)
  try {
    const moltUpvotesResult = await query(`
      SELECT
        AVG(upvotes) as mean_upvotes,
        STDDEV_POP(upvotes) as stddev_upvotes
      FROM agent_posts
      WHERE platform = 'moltbook'
        AND views IS NULL
        AND created_at >= NOW() - INTERVAL '30 days'
    `);

    if (moltUpvotesResult.rows[0]?.mean_upvotes != null) {
      MOLTBOOK_UPVOTES_MEAN = Number(moltUpvotesResult.rows[0].mean_upvotes);
      MOLTBOOK_UPVOTES_STDDEV = Math.max(Number(moltUpvotesResult.rows[0].stddev_upvotes) || 2.0, 0.1);
    }
  } catch {
    // agent_posts may not exist yet
  }

  // 1.6.1: Slack baselines (COALESCE all reaction types to handle NULL)
  try {
    const slackResult = await query(`
      SELECT
        AVG(
          COALESCE((reactions->>'👍')::int, 0) + 
          COALESCE((reactions->>'❤️')::int, 0) + 
          COALESCE((reactions->>'🙏')::int, 0) +
          COALESCE((reactions->>'🔥')::int, 0)
        ) as mean_reactions,
        STDDEV_POP(
          COALESCE((reactions->>'👍')::int, 0) + 
          COALESCE((reactions->>'❤️')::int, 0) + 
          COALESCE((reactions->>'🙏')::int, 0) +
          COALESCE((reactions->>'🔥')::int, 0)
        ) as stddev_reactions
      FROM agent_posts
      WHERE platform = 'slack'
        AND reactions != '{}'
        AND created_at >= NOW() - INTERVAL '30 days'
    `);

    if (slackResult.rows[0]?.mean_reactions != null) {
      SLACK_MEAN = Number(slackResult.rows[0].mean_reactions);
      SLACK_STDDEV = Math.max(Number(slackResult.rows[0].stddev_reactions) || 0.05, 0.01);
    }
  } catch {
    // agent_posts may not exist yet
  }
}

// ── Promotion Pipeline ──────────────────────────────────────────────────────

/**
 * Identify hook candidates eligible for promotion.
 *
 * @param {Function} query - DB query function
 * @returns {Promise<{ xToTiktok: Array, tiktokToApp: Array }>}
 */
export async function identifyPromotions(query) {
  // X → TikTok promotion candidates
  const xCandidates = await query(`
    SELECT
      hc.id, hc.text, hc.tone,
      hc.x_engagement_rate, hc.x_sample_size,
      hc.tiktok_like_rate, hc.tiktok_share_rate,
      hc.promoted
    FROM hook_candidates hc
    WHERE hc.x_sample_size >= $1
      AND hc.x_high_performer = true
      AND hc.promoted = false
    ORDER BY hc.x_engagement_rate DESC
    LIMIT 20
  `, [MIN_X_SAMPLES]);

  const xToTiktok = xCandidates.rows.filter((hc) => {
    const xZ = zScore(Number(hc.x_engagement_rate), X_MEAN, X_STDDEV);
    return xZ >= X_TO_TIKTOK_THRESHOLD;
  });

  // TikTok → App promotion candidates
  let tiktokToApp = [];
  try {
    const tikCandidates = await query(`
      SELECT
        hc.id, hc.text, hc.tone,
        hc.tiktok_like_rate, hc.tiktok_share_rate,
        hc.x_engagement_rate, hc.x_sample_size
      FROM hook_candidates hc
      WHERE hc.tiktok_high_performer = true
        AND hc.source != 'manual'
      ORDER BY hc.tiktok_like_rate DESC
      LIMIT 20
    `);

    tiktokToApp = tikCandidates.rows.filter((hc) => {
      const score = unifiedScore({
        appTapRate: 0, appSampleSize: 0,  // not yet in app
        tiktokLikeRate: Number(hc.tiktok_like_rate || 0),
        tiktokSampleSize: MIN_TIKTOK_SAMPLES,  // already filtered
        xEngagementRate: Number(hc.x_engagement_rate || 0),
        xSampleSize: Number(hc.x_sample_size || 0),
      });
      return score >= TIKTOK_TO_APP_THRESHOLD;
    });
  } catch {
    // columns may not exist yet
  }

  return { xToTiktok, tiktokToApp };
}

/**
 * Execute promotions: mark hook_candidates as promoted and update source.
 *
 * @param {Function} query - DB query function
 * @param {Array} hookIds - IDs of hooks to promote
 * @param {string} newSource - Source label for promoted hooks
 */
export async function executePromotions(query, hookIds, newSource) {
  if (!hookIds.length) return;

  await query(
    `UPDATE hook_candidates SET promoted = true, source = $1 WHERE id = ANY($2::uuid[])`,
    [newSource, hookIds]
  );
}

/**
 * Update X metrics on hook_candidates from x_posts data.
 * Called by daily cron to sync cross-platform metrics.
 *
 * @param {Function} query - DB query function
 */
export async function syncXMetricsToHookCandidates(query) {
  try {
    await query(`
      UPDATE hook_candidates hc SET
        x_engagement_rate = sub.avg_engagement,
        x_sample_size = sub.post_count,
        x_high_performer = (sub.avg_engagement > $1)
      FROM (
        SELECT
          xp.hook_candidate_id,
          AVG(xp.engagement_rate) as avg_engagement,
          COUNT(*) as post_count
        FROM x_posts xp
        WHERE xp.hook_candidate_id IS NOT NULL
          AND xp.metrics_fetched_at IS NOT NULL
        GROUP BY xp.hook_candidate_id
      ) sub
      WHERE hc.id = sub.hook_candidate_id
    `, [X_MEAN + X_STDDEV]);  // high performer = above 1σ
  } catch {
    // x_posts may not exist yet
  }
}

// ── Exports for testing ─────────────────────────────────────────────────────

export function _getBaselines() {
  return { 
    APP_MEAN, APP_STDDEV, 
    TIK_MEAN, TIK_STDDEV, 
    X_MEAN, X_STDDEV,
    MOLTBOOK_VIEWS_MEAN, MOLTBOOK_VIEWS_STDDEV,
    MOLTBOOK_UPVOTES_MEAN, MOLTBOOK_UPVOTES_STDDEV,
    SLACK_MEAN, SLACK_STDDEV,
  };
}

export function _setBaselines({ 
  appMean, appStddev, tikMean, tikStddev, xMean, xStddev,
  moltViewsMean, moltViewsStddev, moltUpvotesMean, moltUpvotesStddev,
  slackMean, slackStddev,
}) {
  if (appMean != null) APP_MEAN = appMean;
  if (appStddev != null) APP_STDDEV = appStddev;
  if (tikMean != null) TIK_MEAN = tikMean;
  if (tikStddev != null) TIK_STDDEV = tikStddev;
  if (xMean != null) X_MEAN = xMean;
  if (xStddev != null) X_STDDEV = xStddev;
  if (moltViewsMean != null) MOLTBOOK_VIEWS_MEAN = moltViewsMean;
  if (moltViewsStddev != null) MOLTBOOK_VIEWS_STDDEV = moltViewsStddev;
  if (moltUpvotesMean != null) MOLTBOOK_UPVOTES_MEAN = moltUpvotesMean;
  if (moltUpvotesStddev != null) MOLTBOOK_UPVOTES_STDDEV = moltUpvotesStddev;
  if (slackMean != null) SLACK_MEAN = slackMean;
  if (slackStddev != null) SLACK_STDDEV = slackStddev;
}

export {
  X_TO_TIKTOK_THRESHOLD,
  TIKTOK_TO_APP_THRESHOLD,
  AGENT_PROMOTION_UPVOTES,
  AGENT_PROMOTION_UNIFIED_SCORE,
  MIN_APP_SAMPLES,
  MIN_TIKTOK_SAMPLES,
  MIN_X_SAMPLES,
  MIN_MOLTBOOK_SAMPLES,
  MIN_MOLTBOOK_VIEWS,
  MIN_SLACK_SAMPLES,
  W_APP,
  W_TIK,
  W_X,
  W_MOLT,
  W_SLACK,
};
