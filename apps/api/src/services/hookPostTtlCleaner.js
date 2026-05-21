import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('HookPostTtlCleaner');

export const RELEVANCE_THRESHOLD = 0.1;
export const AGE_DAYS = 30;

function hasHookPostModels() {
  return Boolean(
    prisma &&
      prisma.hookPost &&
      prisma.hookPostArchive &&
      typeof prisma.$transaction === 'function'
  );
}

/**
 * Clean old low-relevance hook posts with archive-first semantics.
 * If hookPost models are not available in current Prisma schema, returns a safe no-op result.
 */
export async function cleanOldLowRelevancePosts(options = {}) {
  if (!hasHookPostModels()) {
    return { deleted: 0, archived: 0, failed: 0, skipped: true, reason: 'hookPost models not available' };
  }

  const nowMs = options.nowMs || Date.now();
  const cutoffDate = new Date(nowMs - AGE_DAYS * 24 * 60 * 60 * 1000);
  const targets = await prisma.hookPost.findMany({
    where: {
      relevance: { lt: RELEVANCE_THRESHOLD },
      createdAt: { lt: cutoffDate },
    },
  });

  let deleted = 0;
  let archived = 0;
  let failed = 0;

  for (const post of targets) {
    try {
      await prisma.$transaction(async (tx) => {
        const { id, createdAt, updatedAt, ...rest } = post;
        await tx.hookPostArchive.upsert({
          where: { originalId: id },
          create: {
            originalId: id,
            originalCreatedAt: createdAt,
            ...rest,
          },
          update: {},
        });
        await tx.hookPost.delete({ where: { id } });
      });
      deleted += 1;
      archived += 1;
    } catch (error) {
      if (error?.code === 'P2025') {
        logger.info(`HookPost ${post.id} already removed`);
        continue;
      }
      failed += 1;
      logger.error(`Failed to clean HookPost ${post.id}`, error);
    }
  }

  return { deleted, archived, failed, skipped: false };
}

export default {
  cleanOldLowRelevancePosts,
  RELEVANCE_THRESHOLD,
  AGE_DAYS,
};
