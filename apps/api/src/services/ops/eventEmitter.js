import { prisma } from '../../lib/prisma.js';
import { logger } from '../../lib/logger.js';

/**
 * Emit event + auto-evaluate Reaction Matrix
 *
 * @param {string} source - Event source ('x-poster', 'trend-hunter', etc.)
 * @param {string} kind - Event type ('tweet_posted', 'suffering_detected', etc.)
 * @param {string[]} tags - Tag array (['tweet', 'posted'])
 * @param {Object} payload - Event-specific data
 * @param {string} [missionId] - Related mission ID
 * @returns {Promise<Object>} Created event
 */
export async function emitEvent(source, kind, tags, payload = {}, missionId = null) {
  const event = await prisma.opsEvent.create({
    data: { source, kind, tags, payload, missionId }
  });

  // Auto-evaluate Reaction Matrix (dynamic import to avoid circular refs)
  try {
    const { evaluateReactionMatrix } = await import('./reactionProcessor.js');
    await evaluateReactionMatrix(event);
  } catch (err) {
    logger.warn(`Reaction matrix evaluation failed for event ${event.id}:`, err.message);
  }

  return event;
}
