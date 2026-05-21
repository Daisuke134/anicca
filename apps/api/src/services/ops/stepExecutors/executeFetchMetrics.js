import { prisma } from '../../../lib/prisma.js';
import { logger } from '../../../lib/logger.js';

const BLOTATO_BASE_URL = 'https://backend.blotato.com/v2';
const X_API_BASE = 'https://api.x.com/2';

/**
 * 投稿のエンゲージメントデータを実APIから取得
 *
 * Flow:
 * 1. イベントから postId を取得 → XPost/TiktokPost 検索
 * 2. xPostId が null なら Blotato API で実 tweet ID 解決
 * 3. X API v2 で public_metrics 取得
 * 4. DB 更新（impression_count, like_count, etc.）
 * 5. metrics を返す → analyze_engagement step へ
 *
 * Input: { triggeredBy: string, eventId: string }
 * Output: { metrics: Object, postId: string, platform: string }
 */
export async function executeFetchMetrics({ input, proposalPayload }) {
  const eventId = input.eventId || proposalPayload?.eventId;
  const event = await prisma.opsEvent.findUnique({
    where: { id: eventId }
  });

  if (!event) {
    throw new Error(`Event not found: ${eventId}`);
  }

  const postId = event.payload?.postId;
  const platform = event.kind.includes('tweet') ? 'x' : 'tiktok';

  if (!postId) {
    throw new Error(`Event ${eventId} has no postId in payload`);
  }

  let metrics;
  if (platform === 'x') {
    metrics = await fetchXMetrics(postId);
  } else {
    metrics = await fetchTiktokMetrics(postId);
  }

  logger.info(`Metrics fetched for ${platform} post ${postId}: ${JSON.stringify(metrics)}`);

  return {
    output: { metrics, postId, platform },
    events: [{
      kind: `${platform}_metrics_fetched`,
      tags: [platform, 'metrics', 'fetched'],
      payload: { postId, ...metrics }
    }]
  };
}

/**
 * X (Twitter) メトリクス取得
 * 1. Blotato ID → 実 tweet ID 解決（必要なら）
 * 2. X API v2 GET /2/tweets?ids=...&tweet.fields=public_metrics
 * 3. DB 更新
 */
async function fetchXMetrics(postId) {
  const post = await prisma.xPost.findUnique({ where: { id: postId } });
  if (!post) {
    throw new Error(`XPost not found: ${postId}`);
  }

  // Step 1: Resolve Blotato ID → real tweet ID if needed
  let tweetId = post.xPostId;
  if (!tweetId && post.blotatoPostId) {
    tweetId = await resolveBlotatoId(post.blotatoPostId);
    if (tweetId) {
      await prisma.xPost.update({
        where: { id: postId },
        data: { xPostId: tweetId }
      });
      logger.info(`Resolved Blotato ID ${post.blotatoPostId} → tweet ${tweetId}`);
    }
  }

  // Step 2: Fetch from X API v2
  if (!tweetId) {
    logger.warn(`XPost ${postId}: no tweet ID available (Blotato may still be processing)`);
    return buildMetricsFromDb(post);
  }

  const xBearerToken = process.env.X_BEARER_TOKEN;
  if (!xBearerToken) {
    logger.warn('X_BEARER_TOKEN not set — returning DB metrics only');
    return buildMetricsFromDb(post);
  }

  const res = await fetch(`${X_API_BASE}/tweets?ids=${tweetId}&tweet.fields=public_metrics,created_at`, {
    headers: { Authorization: `Bearer ${xBearerToken}` }
  });

  if (res.status === 429) {
    logger.warn('X API rate limited (429) — returning DB metrics');
    return buildMetricsFromDb(post);
  }

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    logger.warn(`X API error: HTTP ${res.status} — ${text.substring(0, 200)}`);
    return buildMetricsFromDb(post);
  }

  const data = await res.json();

  // X API may return error in body with 200 status (e.g. CreditsDepleted)
  if (data.title === 'CreditsDepleted' || data.errors?.length > 0) {
    logger.warn(`X API credits depleted or error — returning DB metrics`);
    return buildMetricsFromDb(post);
  }

  const tweetData = data.data?.[0];
  if (!tweetData?.public_metrics) {
    logger.warn(`X API returned no metrics for tweet ${tweetId}`);
    return buildMetricsFromDb(post);
  }

  const pm = tweetData.public_metrics;

  // Step 3: Update DB
  await prisma.xPost.update({
    where: { id: postId },
    data: {
      impressionCount: pm.impression_count ?? 0,
      likeCount: pm.like_count ?? 0,
      retweetCount: pm.retweet_count ?? 0,
      replyCount: pm.reply_count ?? 0,
      engagementRate: pm.impression_count > 0
        ? (pm.like_count + pm.retweet_count + pm.reply_count) / pm.impression_count
        : 0,
      metricsFetchedAt: new Date()
    }
  });

  const engagements = (pm.like_count || 0) + (pm.retweet_count || 0) + (pm.reply_count || 0);
  return {
    impressions: pm.impression_count || 0,
    engagements,
    likes: pm.like_count || 0,
    retweets: pm.retweet_count || 0,
    replies: pm.reply_count || 0,
    engagementRate: pm.impression_count > 0
      ? ((engagements / pm.impression_count) * 100).toFixed(2)
      : '0.00'
  };
}

/**
 * Blotato submission ID → 実 tweet ID 解決
 */
async function resolveBlotatoId(blotatoPostId) {
  const apiKey = process.env.BLOTATO_API_KEY;
  if (!apiKey || !blotatoPostId) return null;

  try {
    const res = await fetch(`${BLOTATO_BASE_URL}/posts/${blotatoPostId}`, {
      headers: { 'blotato-api-key': apiKey }
    });
    if (!res.ok) return null;

    const data = await res.json();

    // Blotato returns tweet ID in various fields depending on platform
    let tweetId = data.platformPostId
      || data.externalId
      || data.post?.platformPostId
      || data.post?.id_str;

    // Extract tweet ID from publicUrl (e.g. "https://x.com/.../status/123456")
    if (!tweetId && data.publicUrl) {
      const match = data.publicUrl.match(/\/status\/(\d+)/);
      if (match) tweetId = match[1];
    }

    if (tweetId && String(tweetId).match(/^\d+$/)) {
      return String(tweetId);
    }
    return null;
  } catch (err) {
    logger.warn(`Blotato resolution failed for ${blotatoPostId}: ${err.message}`);
    return null;
  }
}

/**
 * DB の既存値からメトリクスを構築（API取得できない場合のフォールバック）
 */
function buildMetricsFromDb(post) {
  const impressions = Number(post.impressionCount || 0n);
  const likes = Number(post.likeCount || 0n);
  const retweets = Number(post.retweetCount || 0n);
  const replies = Number(post.replyCount || 0n);
  const engagements = likes + retweets + replies;
  return {
    impressions,
    engagements,
    likes,
    retweets,
    replies,
    engagementRate: impressions > 0
      ? ((engagements / impressions) * 100).toFixed(2)
      : Number(post.engagementRate || 0).toFixed(2)
  };
}

/**
 * TikTok メトリクス取得（現状は DB 値のみ、将来 API 接続予定）
 */
async function fetchTiktokMetrics(postId) {
  const post = await prisma.tiktokPost.findUnique({ where: { id: postId } });
  if (!post) {
    throw new Error(`TiktokPost not found: ${postId}`);
  }

  const views = Number(post.viewCount || 0n);
  const likes = Number(post.likeCount || 0n);
  const comments = Number(post.commentCount || 0n);
  const shares = Number(post.shareCount || 0n);
  return {
    views,
    likes,
    comments,
    shares,
    engagementRate: views > 0 ? ((likes / views) * 100).toFixed(2) : '0'
  };
}
