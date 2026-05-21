import { prisma } from '../../lib/prisma.js';
import { logger } from '../../lib/logger.js';

/**
 * Promote high-performing insights to long-term memory (WisdomPattern).
 * Called by heartbeat every 5 minutes.
 *
 * Criteria for promotion:
 * - HookCandidate with high engagement rate (>5%) and sufficient sample size (>=5)
 * - Not already promoted (no existing WisdomPattern with same text)
 *
 * @returns {Promise<{promoted: number}>}
 */
export async function promoteInsights() {
  let promoted = 0;

  try {
    // Find high-performing hooks that haven't been promoted
    const candidates = await prisma.hookCandidate.findMany({
      where: {
        OR: [
          { xHighPerformer: true, xSampleSize: { gte: 5 } },
          { tiktokHighPerformer: true, tiktokSampleSize: { gte: 5 } }
        ]
      },
      take: 10
    });

    for (const hook of candidates) {
      // Generate unique pattern name from hook id
      const patternName = `hook-${hook.id.substring(0, 8)}`;

      // Check if already promoted (patternName is unique in WisdomPattern)
      const existing = await prisma.wisdomPattern.findFirst({
        where: { patternName }
      });
      if (existing) continue;

      try {
        await prisma.wisdomPattern.create({
          data: {
            patternName,
            description: hook.text?.substring(0, 500) || '',
            targetUserTypes: hook.targetProblemTypes || [],
            effectiveHookPattern: hook.text,
            confidence: hook.xEngagementRate ?? hook.tiktokEngagementRate ?? 0,
            appEvidence: { sourceHookId: hook.id },
            tiktokEvidence: {},
            verifiedAt: new Date()
          }
        });
        promoted++;
        logger.info(`Insight promoted to WisdomPattern: ${hook.id} — "${hook.text?.substring(0, 50)}"`);
      } catch (err) {
        logger.warn(`InsightPromoter: failed to promote hook ${hook.id}: ${err.message}`);
      }
    }
  } catch (err) {
    logger.warn(`InsightPromoter: ${err.message}`);
  }

  return { promoted };
}
