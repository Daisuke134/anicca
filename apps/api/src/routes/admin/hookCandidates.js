import express from 'express';
import prisma from '../../lib/prisma.js';
import requireInternalAuth from '../../middleware/requireInternalAuth.js';
import baseLogger from '../../utils/logger.js';
import { selectHook } from '../../services/hookSelector.js';
import { extractWisdom } from '../../services/wisdomExtractor.js';

const router = express.Router();
const logger = baseLogger.withContext('AdminHookCandidates');

router.use(requireInternalAuth);

// =============================================================================
// EP-2: GET /api/admin/hook-candidates
// Agent tool: get_hook_candidates
// =============================================================================
router.get('/', async (req, res) => {
  try {
    const strategy = req.query.strategy;

    // Thompson Sampling mode: select ONE hook via algorithm
    if (strategy === 'thompson') {
      const allCandidates = await prisma.hookCandidate.findMany();
      const result = selectHook(allCandidates);
      if (!result) {
        return res.json({ selected: null, strategy: 'thompson', meta: { totalCandidates: 0 } });
      }
      const c = result.hook;
      return res.json({
        selected: {
          id: c.id,
          text: c.text,
          tone: c.tone,
          target_problem_types: c.targetProblemTypes,
          target_user_types: c.targetUserTypes,
          app_tap_rate: Number(c.appTapRate),
          app_thumbs_up_rate: Number(c.appThumbsUpRate),
          app_sample_size: c.appSampleSize,
          tiktok_like_rate: Number(c.tiktokLikeRate),
          tiktok_share_rate: Number(c.tiktokShareRate),
          tiktok_sample_size: c.tiktokSampleSize,
          tiktok_high_performer: c.tiktokHighPerformer,
          is_wisdom: c.isWisdom,
          exploration_weight: Number(c.explorationWeight),
        },
        strategy: result.strategy,
        score: result.score,
        meta: { totalCandidates: allCandidates.length },
      });
    }

    // Default: list mode
    const limit = Math.min(Math.max(parseInt(req.query.limit) || 20, 1), 100);
    const sortBy = req.query.sort_by || 'app_tap_rate';

    const orderByMap = {
      app_tap_rate: { appTapRate: 'desc' },
      tiktok_like_rate: { tiktokLikeRate: 'desc' },
      exploration_weight: { explorationWeight: 'desc' },
    };
    const orderBy = orderByMap[sortBy] || { appTapRate: 'desc' };

    const candidates = await prisma.hookCandidate.findMany({
      take: limit,
      orderBy,
    });

    // Phase detection
    const withMetrics = await prisma.tiktokPost.count({
      where: { metricsFetchedAt: { not: null } },
    });
    const highSampleCount = await prisma.hookCandidate.count({
      where: { tiktokSampleSize: { gte: 3 } },
    });
    const totalCandidates = await prisma.hookCandidate.count();

    let currentPhase = 1;
    if (withMetrics >= 30 && highSampleCount >= 5) {
      currentPhase = 3;
    } else if (withMetrics >= 10) {
      currentPhase = 2;
    }

    res.json({
      candidates: candidates.map((c) => ({
        id: c.id,
        text: c.text,
        tone: c.tone,
        target_problem_types: c.targetProblemTypes,
        target_user_types: c.targetUserTypes,
        app_tap_rate: Number(c.appTapRate),
        app_thumbs_up_rate: Number(c.appThumbsUpRate),
        app_sample_size: c.appSampleSize,
        tiktok_like_rate: Number(c.tiktokLikeRate),
        tiktok_share_rate: Number(c.tiktokShareRate),
        tiktok_sample_size: c.tiktokSampleSize,
        tiktok_high_performer: c.tiktokHighPerformer,
        is_wisdom: c.isWisdom,
        exploration_weight: Number(c.explorationWeight),
      })),
      meta: {
        currentPhase,
        totalCandidates,
      },
    });
  } catch (error) {
    logger.error('Failed to fetch hook candidates', error);
    res.status(500).json({ error: 'Failed to fetch hook candidates' });
  }
});

// =============================================================================
// EP-6: POST /api/admin/hook-candidates/refresh-tiktok-stats
// Called by: fetch_metrics.py after updating individual post metrics
// Recalculates aggregate TikTok metrics for all hook_candidates
// =============================================================================
router.post('/refresh-tiktok-stats', async (req, res) => {
  try {
    // Aggregate TikTok metrics per hook_candidate using raw SQL
    // This is idempotent: safe to call multiple times
    const updated = await prisma.$executeRaw`
      UPDATE hook_candidates hc SET
        tiktok_like_rate = COALESCE(agg.like_rate, 0),
        tiktok_share_rate = COALESCE(agg.share_rate, 0),
        tiktok_sample_size = COALESCE(agg.sample_size, 0),
        tiktok_high_performer = (
          COALESCE(agg.like_rate, 0) > 0.10
          AND COALESCE(agg.share_rate, 0) > 0.05
          AND COALESCE(agg.sample_size, 0) >= 5
        ),
        is_wisdom = (
          hc.app_tap_rate > 0.50
          AND hc.app_thumbs_up_rate > 0.60
          AND COALESCE(agg.like_rate, 0) > 0.10
          AND COALESCE(agg.share_rate, 0) > 0.05
          AND COALESCE(agg.sample_size, 0) >= 5
        ),
        updated_at = NOW()
      FROM (
        SELECT
          hook_candidate_id,
          CASE WHEN SUM(view_count) > 0
            THEN SUM(like_count)::numeric / SUM(view_count)::numeric
            ELSE 0 END AS like_rate,
          CASE WHEN SUM(view_count) > 0
            THEN SUM(share_count)::numeric / SUM(view_count)::numeric
            ELSE 0 END AS share_rate,
          COUNT(*)::int AS sample_size
        FROM tiktok_posts
        WHERE hook_candidate_id IS NOT NULL
          AND metrics_fetched_at IS NOT NULL
        GROUP BY hook_candidate_id
      ) agg
      WHERE hc.id = agg.hook_candidate_id
    `;

    // After refreshing TikTok stats, run wisdom extraction
    const wisdom = await extractWisdom(prisma);

    logger.info(`Refreshed TikTok stats for hook candidates (${updated} rows), wisdom: ${wisdom.total}`);
    res.json({ success: true, updated, wisdom });
  } catch (error) {
    logger.error('Failed to refresh TikTok stats', error);
    res.status(500).json({ error: 'Failed to refresh TikTok stats' });
  }
});

export default router;
