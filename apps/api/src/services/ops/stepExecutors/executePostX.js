import { prisma } from '../../../lib/prisma.js';
import { logger } from '../../../lib/logger.js';

const BLOTATO_BASE_URL = 'https://backend.blotato.com/v2';

/**
 * X (Twitter) に Blotato API 経由で投稿 → DB保存
 *
 * Input: { content: string, hookId: string, verificationScore: number }
 * Output: { postId: string, blotatoPostId: string, platform: string }
 * Events: tweet_posted
 */
export async function executePostX({ input, missionId }) {
  const { content, hookId, verificationScore } = input;

  if (!content) {
    throw new Error('post_x requires input.content');
  }

  let blotatoPostId = null;

  const apiKey = process.env.BLOTATO_API_KEY;
  const accountId = process.env.BLOTATO_ACCOUNT_ID_EN;

  if (apiKey && accountId) {
    const res = await fetch(`${BLOTATO_BASE_URL}/posts`, {
      method: 'POST',
      headers: {
        'blotato-api-key': apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        post: {
          accountId,
          content: {
            text: content.slice(0, 280),
            mediaUrls: [],
            platform: 'twitter'
          },
          target: {
            targetType: 'twitter'
          }
        }
      })
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`Blotato post failed: HTTP ${res.status} — ${text}`);
    }

    const data = await res.json();
    blotatoPostId = data.postSubmissionId || data.id || null;
    logger.info(`Blotato post submitted: ${blotatoPostId}`);
  } else {
    logger.warn('BLOTATO_API_KEY or BLOTATO_ACCOUNT_ID_EN not set — skipping actual X post');
  }

  const xPost = await prisma.xPost.create({
    data: {
      text: content.slice(0, 280),
      hookCandidateId: hookId || null,
      blotatoPostId: blotatoPostId ? String(blotatoPostId) : null,
      slot: input.slot || null,
      postedAt: new Date(),
      agentReasoning: JSON.stringify({ verificationScore, missionId })
    }
  });

  logger.info(`X post recorded: ${xPost.id} (blotato: ${blotatoPostId})`);

  return {
    output: {
      postId: xPost.id,
      dbRecordId: xPost.id,
      blotatoPostId,
      platform: 'x'
    },
    events: [{
      kind: 'tweet_posted',
      tags: ['tweet', 'posted'],
      payload: {
        postId: xPost.id,
        blotatoPostId,
        hookId,
        verificationScore,
        contentPreview: content.substring(0, 50)
      }
    }]
  };
}
