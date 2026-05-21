import { prisma } from '../../lib/prisma.js';
import { getPolicy } from './policyService.js';
import { createProposalAndMaybeAutoApprove } from './proposalService.js';
import { logger } from '../../lib/logger.js';

/**
 * Process pending reactions from queue
 * @param {number} timeoutMs
 * @returns {Promise<{processed: number, proposals: number}>}
 */
export async function processReactionQueue(timeoutMs = 3000) {
  const deadline = Date.now() + timeoutMs;
  let processed = 0;
  let proposals = 0;

  const pendingReactions = await prisma.opsReaction.findMany({
    where: { status: 'pending' },
    take: 20,
    orderBy: { createdAt: 'asc' }
  });

  for (const reaction of pendingReactions) {
    if (Date.now() > deadline) break;

    // Atomic claim: prevent duplicate processing in parallel heartbeats
    const claimed = await prisma.opsReaction.updateMany({
      where: { id: reaction.id, status: 'pending' },
      data: { status: 'processing' }
    });
    if (claimed.count === 0) continue; // Already claimed by another worker

    try {
      const result = await createProposalAndMaybeAutoApprove({
        skillName: reaction.targetSkill,
        source: 'reaction',
        title: `Reaction: ${reaction.actionType} (from event ${reaction.eventId})`,
        payload: { eventId: reaction.eventId, actionType: reaction.actionType },
        steps: [{ kind: reaction.actionType, order: 0 }]
      });

      await prisma.opsReaction.update({
        where: { id: reaction.id },
        data: { status: 'processed', processedAt: new Date() }
      });

      processed++;
      if (result.status === 'accepted') proposals++;
    } catch (err) {
      // Revert to pending on failure so it can be retried
      await prisma.opsReaction.update({
        where: { id: reaction.id },
        data: { status: 'pending' }
      });
      logger.warn(`Reaction ${reaction.id} processing failed, reverted to pending: ${err.message}`);
    }
  }

  return { processed, proposals };
}

/**
 * Evaluate Reaction Matrix against an event and queue matching reactions
 * Called from emitEvent()
 * @param {Object} event
 */
export async function evaluateReactionMatrix(event) {
  const matrix = await getPolicy('reaction_matrix');
  if (!matrix?.patterns) return;

  for (const pattern of matrix.patterns) {
    // Source match ('*' matches all)
    if (pattern.source !== '*' && pattern.source !== event.source) continue;

    // Tags match (all pattern tags must be in event tags)
    const tagsMatch = pattern.tags.every(t => event.tags.includes(t));
    if (!tagsMatch) continue;

    // Probability check
    if (Math.random() > pattern.probability) continue;

    // Cooldown check (cooldown in minutes)
    const recentReaction = await prisma.opsReaction.findFirst({
      where: {
        targetSkill: pattern.target,
        actionType: pattern.type,
        createdAt: { gt: new Date(Date.now() - pattern.cooldown * 60 * 1000) }
      }
    });
    if (recentReaction) continue;

    // Queue reaction
    await prisma.opsReaction.create({
      data: {
        eventId: event.id,
        targetSkill: pattern.target,
        actionType: pattern.type,
        status: 'pending'
      }
    });

    logger.info(`Reaction queued: ${event.source}→${pattern.target} (${pattern.type}, p=${pattern.probability})`);
  }
}
