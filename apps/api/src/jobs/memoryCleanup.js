import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('MemoryCleanupJob');

const DAYS_365_MS = 365 * 24 * 60 * 60 * 1000;

export async function runMemoryCleanup(options = {}) {
  const now = options.now instanceof Date ? options.now : new Date();
  const retentionCutoff = new Date(now.getTime() - DAYS_365_MS);

  const expired = await prisma.memoryItem.deleteMany({
    where: { expiresAt: { lt: now } },
  });

  const oldNullExpiry = await prisma.memoryItem.deleteMany({
    where: { expiresAt: null, createdAt: { lt: retentionCutoff } },
  });

  const result = {
    deletedExpired: expired?.count || 0,
    deletedOldNullExpiry: oldNullExpiry?.count || 0,
    now: now.toISOString(),
  };

  logger.info('Memory cleanup completed', result);
  return result;
}

export default runMemoryCleanup;

