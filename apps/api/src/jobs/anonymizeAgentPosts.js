/**
 * Anonymize Agent Posts Job (1.6.1)
 * 
 * Runs daily to anonymize agent_posts older than 90 days.
 * Per spec section 6.5:
 * - Sets external_post_id, platform_user_id, content, reasoning to NULL
 * - Sets anonymized_at timestamp
 * - Preserves: hook, upvotes, views, Z-scores (for learning)
 */

import { prisma } from '../lib/prisma.js';

const RETENTION_DAYS = 90;

/**
 * Anonymize agent posts older than RETENTION_DAYS.
 * 
 * @returns {Promise<{ count: number }>} Number of anonymized posts
 */
export async function runAnonymization() {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - RETENTION_DAYS);

  const result = await prisma.$executeRaw`
    UPDATE agent_posts
    SET 
      external_post_id = NULL,
      platform_user_id = NULL,
      content = NULL,
      reasoning = NULL,
      anonymized_at = NOW()
    WHERE created_at < ${cutoffDate}
      AND anonymized_at IS NULL
  `;

  console.log(`[Anonymization] Anonymized ${result} agent posts older than ${RETENTION_DAYS} days`);

  // Audit log
  await prisma.agentAuditLog.create({
    data: {
      eventType: 'anonymization_batch',
      requestPayload: { cutoffDate: cutoffDate.toISOString() },
      responsePayload: { count: result },
      executedBy: 'system',
    },
  });

  return { count: result };
}

export default runAnonymization;
