import { prisma } from '../../../lib/prisma.js';
import { logger } from '../../../lib/logger.js';

const BLOTATO_BASE_URL = 'https://backend.blotato.com/v2';

/**
 * TikTok投稿
 *
 * Input: { content: string, hookId: string, verificationScore: number }
 * Output: { postId: string }
 * Events: tiktok_posted
 */
export async function executePostTiktok({ input, missionId, proposalPayload }) {
  const { content, hookId, verificationScore } = input;

  if (!content) {
    throw new Error('post_tiktok requires input.content');
  }

  let blotatoPostId = null;
  const apiKey = process.env.BLOTATO_API_KEY;
  const tiktokAccountId =
    process.env.BLOTATO_TIKTOK_ACCOUNT_ID || process.env.BLOTATO_ACCOUNT_ID_EN;
  const mediaUrls = normalizeMediaUrls(
    input?.mediaUrls || proposalPayload?.mediaUrls,
    input?.mediaUrl || proposalPayload?.mediaUrl
  );

  if (apiKey && tiktokAccountId) {
    if (mediaUrls.length === 0) {
      throw new Error('post_tiktok requires at least one media URL (input.mediaUrls)');
    }

    const res = await fetch(`${BLOTATO_BASE_URL}/posts`, {
      method: 'POST',
      headers: {
        'blotato-api-key': apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        post: {
          accountId: tiktokAccountId,
          content: {
            // Keep conservative limit to avoid provider-side mismatch.
            text: content.slice(0, 2000),
            mediaUrls,
            platform: 'tiktok'
          },
          target: {
            targetType: 'tiktok',
            privacyLevel: 'PUBLIC_TO_EVERYONE',
            disabledComments: false,
            disabledDuet: false,
            disabledStitch: false,
            isBrandedContent: false,
            isYourBrand: false,
            isAiGenerated: false,
            autoAddMusic: true
          }
        }
      })
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`Blotato TikTok post failed: HTTP ${res.status} — ${text}`);
    }

    const data = await res.json();
    blotatoPostId = data.postSubmissionId || data.id || null;
    logger.info(`Blotato TikTok post submitted: ${blotatoPostId}`);
  } else {
    logger.warn('BLOTATO_API_KEY or BLOTATO_TIKTOK_ACCOUNT_ID not set — skipping actual TikTok post');
  }

  const tiktokPost = await prisma.tiktokPost.create({
    data: {
      caption: content,
      hookCandidateId: hookId || null,
      blotatoPostId: blotatoPostId ? String(blotatoPostId) : null,
      slot: input.slot || null,
      postedAt: new Date(),
      agentReasoning: JSON.stringify({ verificationScore, missionId })
    }
  });

  logger.info(`TikTok post recorded: ${tiktokPost.id}`);

  return {
    output: {
      postId: tiktokPost.id,
      platform: 'tiktok'
    },
    events: [{
      kind: 'tiktok_posted',
      tags: ['tiktok', 'posted'],
      payload: {
        postId: tiktokPost.id,
        blotatoPostId,
        hookId,
        contentPreview: content.substring(0, 50)
      }
    }]
  };
}

function normalizeMediaUrls(multi, single) {
  const fromArray = Array.isArray(multi) ? multi : [];
  const combined = [...fromArray, single].filter(Boolean);
  return combined
    .map(v => String(v).trim())
    .filter(v => /^https?:\/\//i.test(v));
}
