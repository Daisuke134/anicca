import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('WisdomExtractor');

/**
 * C1: Wisdom Extraction Service
 *
 * Scans hook_candidates for hooks that perform well across BOTH channels
 * (app + TikTok) and marks them as wisdom. Also upserts into wisdom_patterns.
 *
 * Wisdom criteria (ALL must be met):
 * - App: tap_rate > 50%, thumbs_up_rate > 60%, sample_size >= 10
 * - TikTok: like_rate > 10%, share_rate > 5%, sample_size >= 5
 */

const WISDOM_THRESHOLDS = {
  appTapRate: 0.50,
  appThumbsUpRate: 0.60,
  appSampleSize: 10,
  tiktokLikeRate: 0.10,
  tiktokShareRate: 0.05,
  tiktokSampleSize: 5,
};

/**
 * Extract wisdom patterns from hook_candidates.
 * Idempotent: safe to run multiple times.
 *
 * @param {import('../../generated/prisma/index.js').PrismaClient} prisma
 * @returns {Promise<{ promoted: number, demoted: number }>}
 */
export async function extractWisdom(prisma) {
  // 1. Find candidates meeting ALL wisdom criteria
  const wisdomCandidates = await prisma.hookCandidate.findMany({
    where: {
      appTapRate: { gt: WISDOM_THRESHOLDS.appTapRate },
      appThumbsUpRate: { gt: WISDOM_THRESHOLDS.appThumbsUpRate },
      appSampleSize: { gte: WISDOM_THRESHOLDS.appSampleSize },
      tiktokLikeRate: { gt: WISDOM_THRESHOLDS.tiktokLikeRate },
      tiktokShareRate: { gt: WISDOM_THRESHOLDS.tiktokShareRate },
      tiktokSampleSize: { gte: WISDOM_THRESHOLDS.tiktokSampleSize },
    },
  });

  const wisdomIds = new Set(wisdomCandidates.map((c) => c.id));

  // 2. Promote: set is_wisdom = true + upsert wisdom_patterns
  let promoted = 0;
  for (const c of wisdomCandidates) {
    if (!c.isWisdom) {
      await prisma.hookCandidate.update({
        where: { id: c.id },
        data: { isWisdom: true, updatedAt: new Date() },
      });
      promoted++;
    }

    // Upsert wisdom_pattern (keyed by pattern_name = hook text)
    const appEvidence = {
      tapRate: Number(c.appTapRate),
      thumbsUpRate: Number(c.appThumbsUpRate),
      sampleSize: c.appSampleSize,
    };
    const tiktokEvidence = {
      likeRate: Number(c.tiktokLikeRate),
      shareRate: Number(c.tiktokShareRate),
      sampleSize: c.tiktokSampleSize,
    };

    // Use raw upsert since patternName has no unique constraint in Prisma
    await prisma.$executeRaw`
      INSERT INTO wisdom_patterns (
        id, pattern_name, description, target_user_types, effective_tone,
        effective_hook_pattern, app_evidence, tiktok_evidence,
        confidence, verified_at, created_at, updated_at
      ) VALUES (
        gen_random_uuid(),
        ${c.text},
        ${`Cross-channel proven hook (${c.tone})`},
        ${c.targetUserTypes},
        ${c.tone},
        ${c.text},
        ${JSON.stringify(appEvidence)}::jsonb,
        ${JSON.stringify(tiktokEvidence)}::jsonb,
        0.8000,
        NOW(), NOW(), NOW()
      )
      ON CONFLICT (pattern_name) DO UPDATE SET
        app_evidence = ${JSON.stringify(appEvidence)}::jsonb,
        tiktok_evidence = ${JSON.stringify(tiktokEvidence)}::jsonb,
        verified_at = NOW(),
        updated_at = NOW()
    `;
  }

  // 3. Demote: remove is_wisdom from candidates that no longer qualify
  const previousWisdom = await prisma.hookCandidate.findMany({
    where: { isWisdom: true },
  });
  let demoted = 0;
  for (const c of previousWisdom) {
    if (!wisdomIds.has(c.id)) {
      await prisma.hookCandidate.update({
        where: { id: c.id },
        data: { isWisdom: false, updatedAt: new Date() },
      });
      demoted++;
    }
  }

  logger.info(`Wisdom extraction complete: ${promoted} promoted, ${demoted} demoted, ${wisdomCandidates.length} total wisdom`);
  return { promoted, demoted, total: wisdomCandidates.length };
}

export { WISDOM_THRESHOLDS };
