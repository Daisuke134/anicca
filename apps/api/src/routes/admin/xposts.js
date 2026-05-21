import express from 'express';
import prisma from '../../lib/prisma.js';
import requireInternalAuth from '../../middleware/requireInternalAuth.js';
import baseLogger from '../../utils/logger.js';

const router = express.Router();
const logger = baseLogger.withContext('AdminXPosts');

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
// GET /api/admin/x/pending
// Fetch today's Commander-generated xPosts from notification_schedules
// Used by: X Agent GHA to get content to post
// =============================================================================
router.get('/pending', async (req, res) => {
  try {
    const { slot } = req.query;

    // Get most recent notification_schedule with xPosts
    const schedules = await prisma.notificationSchedule.findMany({
      where: {
        createdAt: { gte: new Date(Date.now() - 24 * 60 * 60 * 1000) },
      },
      orderBy: { createdAt: 'desc' },
      take: 5,
    });

    const xPosts = [];
    for (const s of schedules) {
      const raw = s.agentRawOutput;
      const normalized = normalizeScheduleOutput(raw || {});
      const candidates = normalized.xPosts || [];
      for (const xp of candidates) {
        if (slot && xp.slot !== slot) continue;
        // Filter out enabled=false (fallback posts); undefined=true for legacy data
        if (xp.enabled === false) continue;
        xPosts.push({
          text: xp.text,
          reasoning: xp.reasoning,
          slot: xp.slot,
          sourceUserId: s.userId,
          scheduleId: s.id,
        });
      }
    }

    // Deduplicate by text
    const seen = new Set();
    const unique = xPosts.filter((p) => {
      const key = `${p.slot || 'any'}::${p.text}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    res.json({ xPosts: unique.slice(0, 10) });
  } catch (error) {
    logger.error('Failed to fetch pending x posts', error);
    res.status(500).json({ error: 'Failed to fetch pending x posts' });
  }
});

// =============================================================================
// POST /api/admin/x/posts
// Save a posted X/Twitter record
// Used by: X Agent GHA after posting via Blotato
// =============================================================================
router.post('/posts', async (req, res) => {
  try {
    const { hook_candidate_id, x_post_id, blotato_post_id, text, agent_reasoning, posted_at, slot } = req.body;

    if (!text || typeof text !== 'string') {
      return res.status(400).json({ error: 'text is required' });
    }
    // B2: conservative limit to avoid provider-side counting mismatch
    if (text.length > 260) {
      return res.status(400).json({ error: 'text exceeds 260 characters' });
    }
    if (hook_candidate_id && !UUID_RE.test(hook_candidate_id)) {
      return res.status(400).json({ error: 'hook_candidate_id must be a valid UUID' });
    }
    if (slot && !['morning', 'evening'].includes(slot)) {
      return res.status(400).json({ error: 'slot must be "morning" or "evening"' });
    }

    // Duplicate guard: check x_post_id or blotato_post_id
    if (x_post_id) {
      const existing = await prisma.xPost.findUnique({ where: { xPostId: x_post_id } });
      if (existing) {
        return res.status(409).json({ error: 'X post already recorded', existing_id: existing.id });
      }
    }
    if (blotato_post_id) {
      const existing = await prisma.xPost.findFirst({ where: { blotatoPostId: blotato_post_id } });
      if (existing) {
        return res.status(409).json({ error: 'Duplicate blotato_post_id', existing_id: existing.id });
      }
    }

    const post = await prisma.xPost.create({
      data: {
        hookCandidateId: hook_candidate_id || null,
        xPostId: x_post_id || null,
        blotatoPostId: blotato_post_id || null,
        text,
        slot: slot || null,
        agentReasoning: agent_reasoning || null,
        postedAt: posted_at ? new Date(posted_at) : new Date(),
      },
    });

    logger.info(`X post saved: ${post.id}`);
    res.json({ success: true, record_id: post.id });
  } catch (error) {
    if (error.code === 'P2002') {
      return res.status(409).json({ error: 'Duplicate X post (DB constraint)' });
    }
    logger.error('Failed to save x post record', error);
    res.status(500).json({ error: 'Failed to save x post record' });
  }
});

// =============================================================================
// GET /api/admin/x/recent-posts
// Fetch recent X posts with metrics
// Used by: X Agent for performance review
// =============================================================================
router.get('/recent-posts', async (req, res) => {
  try {
    const days = Math.min(Math.max(parseInt(req.query.days) || 7, 1), 30);

    const posts = await prisma.xPost.findMany({
      where: {
        postedAt: { gte: new Date(Date.now() - days * 24 * 60 * 60 * 1000) },
      },
      orderBy: { postedAt: 'desc' },
      include: { hookCandidate: { select: { text: true, tone: true } } },
    });

    const result = posts.map((p) => ({
      id: p.id,
      text: p.text,
      x_post_id: p.xPostId,
      blotato_post_id: p.blotatoPostId,
      posted_at: p.postedAt,
      impression_count: Number(p.impressionCount ?? 0),
      like_count: Number(p.likeCount ?? 0),
      retweet_count: Number(p.retweetCount ?? 0),
      reply_count: Number(p.replyCount ?? 0),
      engagement_rate: Number(p.engagementRate ?? 0),
      agent_reasoning: p.agentReasoning,
      hook: p.hookCandidate
        ? { text: p.hookCandidate.text, tone: p.hookCandidate.tone }
        : null,
    }));

    res.json({ posts: result });
  } catch (error) {
    logger.error('Failed to fetch recent x posts', error);
    res.status(500).json({ error: 'Failed to fetch recent x posts' });
  }
});

// =============================================================================
// PUT /api/admin/x/posts/:id/metrics
// Update X post metrics
// Used by: metrics fetcher script
// =============================================================================
router.put('/posts/:id/metrics', async (req, res) => {
  try {
    const { id } = req.params;
    if (!UUID_RE.test(id)) {
      return res.status(400).json({ error: 'id must be a valid UUID' });
    }

    const { x_post_id, impression_count, like_count, retweet_count, reply_count } = req.body;

    const MAX_METRIC = 1_000_000_000;
    const metrics = { impression_count, like_count, retweet_count, reply_count };
    for (const [key, val] of Object.entries(metrics)) {
      if (val === undefined || val === null) continue;
      if (typeof val !== 'number' || !Number.isInteger(val) || val < 0 || val > MAX_METRIC) {
        return res.status(400).json({ error: `${key} must be integer 0-${MAX_METRIC}` });
      }
    }

    // 部分更新: 送信されたフィールドのみ更新（欠落フィールドは既存値維持）
    const updateData = { metricsFetchedAt: new Date() };
    if (x_post_id && typeof x_post_id === 'string' && x_post_id.length <= 100) {
      updateData.xPostId = x_post_id;
    }
    if (impression_count !== undefined && impression_count !== null) {
      updateData.impressionCount = BigInt(impression_count);
    }
    if (like_count !== undefined && like_count !== null) {
      updateData.likeCount = BigInt(like_count);
    }
    if (retweet_count !== undefined && retweet_count !== null) {
      updateData.retweetCount = BigInt(retweet_count);
    }
    if (reply_count !== undefined && reply_count !== null) {
      updateData.replyCount = BigInt(reply_count);
    }

    // engagementRate は全フィールド揃った時のみ再計算
    if (impression_count != null && like_count != null && retweet_count != null && reply_count != null) {
      const totalEngagements = like_count + retweet_count + reply_count;
      updateData.engagementRate = impression_count > 0 ? totalEngagements / impression_count : 0;
    }

    await prisma.xPost.update({
      where: { id },
      data: updateData,
    });

    logger.info(`X post metrics updated: ${id}`);
    res.json({ success: true });
  } catch (error) {
    if (error.code === 'P2025') {
      return res.status(404).json({ error: 'X post not found' });
    }
    if (error.code === 'P2002') {
      return res.status(409).json({ error: 'Duplicate x_post_id (DB constraint)' });
    }
    logger.error('Failed to update x post metrics', error);
    res.status(500).json({ error: 'Failed to update x post metrics' });
  }
});

export default router;
