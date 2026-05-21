import express from 'express';
import prisma from '../../lib/prisma.js';
import requireInternalAuth from '../../middleware/requireInternalAuth.js';
import baseLogger from '../../utils/logger.js';

const router = express.Router();
const logger = baseLogger.withContext('AdminTiktok');

router.use(requireInternalAuth);

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function normalizeScheduleOutput(raw) {
  // tiktokPost（単数）→ tiktokPosts（複数）
  let tiktokPosts = raw?.tiktokPosts;
  if (!tiktokPosts && raw?.tiktokPost) {
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
  let xPosts = Array.isArray(raw?.xPosts) ? raw.xPosts : [];
  xPosts = xPosts.map((post, i) => ({
    ...post,
    slot: post.slot || (i === 0 ? 'morning' : 'evening'),
  }));

  return { tiktokPosts: tiktokPosts || [], xPosts };
}

// =============================================================================
// EP-0: GET /api/admin/tiktok/pending
// Fetch today's Commander-generated tiktokPosts from notification_schedules
// Used by: TikTok Agent GHA to get content to post
// =============================================================================
router.get('/pending', async (req, res) => {
  try {
    const { slot } = req.query;

    const schedules = await prisma.notificationSchedule.findMany({
      where: {
        createdAt: { gte: new Date(Date.now() - 24 * 60 * 60 * 1000) },
      },
      orderBy: { createdAt: 'desc' },
      take: 5,
    });

    const tiktokPosts = [];
    for (const s of schedules) {
      const raw = s.agentRawOutput;
      const normalized = normalizeScheduleOutput(raw || {});
      const candidates = normalized.tiktokPosts || [];
      for (const tp of candidates) {
        if (slot && tp.slot !== slot) continue;
        // Filter out enabled=false (fallback posts); undefined=true for legacy data
        if (tp.enabled === false) continue;
        tiktokPosts.push({
          caption: tp.caption,
          hashtags: tp.hashtags || [],
          tone: tp.tone,
          reasoning: tp.reasoning,
          slot: tp.slot,
          sourceUserId: s.userId,
          scheduleId: s.id,
        });
      }
    }

    // Deduplicate by caption + slot
    const seen = new Set();
    const unique = tiktokPosts.filter((p) => {
      const key = `${p.slot || 'any'}::${p.caption}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    res.json({ tiktokPosts: unique.slice(0, 10) });
  } catch (error) {
    logger.error('Failed to fetch pending tiktok posts', error);
    res.status(500).json({ error: 'Failed to fetch pending tiktok posts' });
  }
});

// =============================================================================
// EP-1: GET /api/admin/tiktok/recent-posts
// Agent tool: get_yesterday_performance
// =============================================================================
router.get('/recent-posts', async (req, res) => {
  try {
    const days = Math.min(Math.max(parseInt(req.query.days) || 1, 1), 30);

    const posts = await prisma.tiktokPost.findMany({
      where: {
        postedAt: { gte: new Date(Date.now() - days * 24 * 60 * 60 * 1000) },
      },
      orderBy: { postedAt: 'desc' },
      include: { hookCandidate: { select: { text: true, tone: true } } },
    });

    const result = posts.map((p) => {
      const viewCount = Number(p.viewCount ?? 0);
      const likeCount = Number(p.likeCount ?? 0);
      const shareCount = Number(p.shareCount ?? 0);
      return {
        id: p.id,
        caption: p.caption,
        posted_at: p.postedAt,
        view_count: viewCount,
        like_count: likeCount,
        share_count: shareCount,
        comment_count: Number(p.commentCount ?? 0),
        like_rate: viewCount > 0 ? likeCount / viewCount : 0,
        share_rate: viewCount > 0 ? shareCount / viewCount : 0,
        agent_reasoning: p.agentReasoning,
        scheduled_at: p.scheduledAt,
        hook: p.hookCandidate
          ? { text: p.hookCandidate.text, tone: p.hookCandidate.tone }
          : null,
      };
    });

    res.json({ posts: result });
  } catch (error) {
    logger.error('Failed to fetch recent posts', error);
    res.status(500).json({ error: 'Failed to fetch recent posts' });
  }
});

// =============================================================================
// EP-3: POST /api/admin/tiktok/posts
// Agent tool: save_post_record
// Duplicate guard: 409 if already posted today
// =============================================================================
router.post('/posts', async (req, res) => {
  try {
    const { hook_candidate_id, blotato_post_id, caption, agent_reasoning, scheduled_time, slot } = req.body;

    if (!blotato_post_id || typeof blotato_post_id !== 'string') {
      return res.status(400).json({ error: 'blotato_post_id is required' });
    }
    if (!caption || typeof caption !== 'string') {
      return res.status(400).json({ error: 'caption is required' });
    }
    // B2: conservative limit to avoid provider-side counting mismatch
    if (caption.length > 2000) {
      return res.status(400).json({ error: 'caption exceeds 2000 characters' });
    }
    if (blotato_post_id.length > 100) {
      return res.status(400).json({ error: 'blotato_post_id exceeds 100 characters' });
    }
    if (agent_reasoning && agent_reasoning.length > 10000) {
      return res.status(400).json({ error: 'agent_reasoning exceeds 10000 characters' });
    }
    if (hook_candidate_id && !UUID_RE.test(hook_candidate_id)) {
      return res.status(400).json({ error: 'hook_candidate_id must be a valid UUID' });
    }
    if (slot && !['morning', 'evening'].includes(slot)) {
      return res.status(400).json({ error: 'slot must be "morning" or "evening"' });
    }
    if (scheduled_time) {
      const parsed = new Date(scheduled_time);
      if (isNaN(parsed.getTime())) {
        return res.status(400).json({ error: 'scheduled_time must be a valid ISO 8601 datetime' });
      }
      const now = Date.now();
      if (parsed.getTime() < now - 5 * 60 * 1000) {
        return res.status(400).json({ error: 'scheduled_time must be in the future' });
      }
      if (parsed.getTime() > now + 30 * 24 * 60 * 60 * 1000) {
        return res.status(400).json({ error: 'scheduled_time must be within 30 days' });
      }
    }

    // Duplicate guard: same blotato_post_id only (allow 2 posts/day for morning+evening slots)
    if (blotato_post_id) {
      const existing = await prisma.tiktokPost.findFirst({
        where: { blotatoPostId: blotato_post_id },
      });
      if (existing) {
        return res.status(409).json({
          error: 'Duplicate blotato_post_id',
          existing_post_id: existing.id,
        });
      }
    }

    const post = await prisma.tiktokPost.create({
      data: {
        hookCandidateId: hook_candidate_id || null,
        blotatoPostId: blotato_post_id,
        caption,
        agentReasoning: agent_reasoning || null,
        slot: slot || null,
        scheduledAt: scheduled_time ? new Date(scheduled_time) : null,
        postedAt: new Date(),
      },
    });

    logger.info(`TikTok post saved: ${post.id}`);
    res.json({ success: true, record_id: post.id });
  } catch (error) {
    // P2002 = unique constraint violation
    if (error.code === 'P2002') {
      return res.status(409).json({ error: 'Duplicate post (DB constraint)' });
    }
    logger.error('Failed to save post record', error);
    res.status(500).json({ error: 'Failed to save post record' });
  }
});

// =============================================================================
// EP-4: PUT /api/admin/tiktok/posts/:id/metrics
// Used by: fetch_metrics.py
// =============================================================================
router.put('/posts/:id/metrics', async (req, res) => {
  try {
    const { id } = req.params;
    if (!UUID_RE.test(id)) {
      return res.status(400).json({ error: 'id must be a valid UUID' });
    }
    const { tiktok_video_id, view_count, like_count, share_count, comment_count } = req.body;

    const MAX_METRIC = 1_000_000_000;
    const metrics = { view_count, like_count, share_count, comment_count };
    for (const [key, val] of Object.entries(metrics)) {
      if (val === undefined || val === null) continue;
      if (typeof val !== 'number' || !Number.isInteger(val) || val < 0 || val > MAX_METRIC) {
        return res.status(400).json({ error: `${key} must be integer 0-${MAX_METRIC}` });
      }
    }
    if (tiktok_video_id && tiktok_video_id.length > 100) {
      return res.status(400).json({ error: 'tiktok_video_id exceeds 100 characters' });
    }

    const updateData = { metricsFetchedAt: new Date() };
    if (tiktok_video_id) updateData.tiktokVideoId = tiktok_video_id;
    if (view_count !== undefined) updateData.viewCount = BigInt(view_count);
    if (like_count !== undefined) updateData.likeCount = BigInt(like_count);
    if (share_count !== undefined) updateData.shareCount = BigInt(share_count);
    if (comment_count !== undefined) updateData.commentCount = BigInt(comment_count);

    await prisma.tiktokPost.update({
      where: { id },
      data: updateData,
    });

    logger.info(`Metrics updated for post: ${id}`);
    res.json({ success: true });
  } catch (error) {
    if (error.code === 'P2025') {
      return res.status(404).json({ error: 'Post not found' });
    }
    logger.error('Failed to update metrics', error);
    res.status(500).json({ error: 'Failed to update metrics' });
  }
});

// =============================================================================
// EP-5: GET /api/admin/tiktok/posts?metrics_pending=true
// Used by: fetch_metrics.py
// =============================================================================
router.get('/posts', async (req, res) => {
  try {
    if (req.query.metrics_pending === 'true') {
      const twentyHoursAgo = new Date(Date.now() - 20 * 60 * 60 * 1000);
      const posts = await prisma.tiktokPost.findMany({
        where: {
          metricsFetchedAt: null,
          postedAt: { lt: twentyHoursAgo },
        },
        orderBy: { postedAt: 'desc' },
      });

      return res.json({
        posts: posts.map((p) => ({
          id: p.id,
          caption: p.caption,
          posted_at: p.postedAt,
          tiktok_video_id: p.tiktokVideoId,
          blotato_post_id: p.blotatoPostId,
        })),
      });
    }

    const posts = await prisma.tiktokPost.findMany({
      orderBy: { postedAt: 'desc' },
      take: 30,
    });
    res.json({
      posts: posts.map((p) => ({
        id: p.id,
        caption: p.caption,
        posted_at: p.postedAt,
        view_count: Number(p.viewCount ?? 0),
        like_count: Number(p.likeCount ?? 0),
        share_count: Number(p.shareCount ?? 0),
        comment_count: Number(p.commentCount ?? 0),
        tiktok_video_id: p.tiktokVideoId,
      })),
    });
  } catch (error) {
    logger.error('Failed to fetch posts', error);
    res.status(500).json({ error: 'Failed to fetch posts' });
  }
});

export default router;
