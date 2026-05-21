import { prisma } from '../../lib/prisma.js';
import { createProposalAndMaybeAutoApprove } from './proposalService.js';
import { logger } from '../../lib/logger.js';

/**
 * Evaluate trigger rules against recent events
 * Uses corrected delay_min logic from 08-event-trigger-system.md §19
 *
 * @param {number} timeoutMs
 * @returns {Promise<{evaluated: number, fired: number}>}
 */
export async function evaluateTriggers(timeoutMs = 4000) {
  const deadline = Date.now() + timeoutMs;
  let evaluated = 0;
  let fired = 0;

  const rules = await prisma.opsTriggerRule.findMany({
    where: { enabled: true }
  });

  for (const rule of rules) {
    if (Date.now() > deadline) break;

    // Cooldown check
    if (rule.lastFiredAt) {
      const minutesSince = (Date.now() - rule.lastFiredAt.getTime()) / (1000 * 60);
      if (minutesSince < rule.cooldownMin) continue;
    }

    // Search window calculation (§19.2 fix)
    const delayMin = rule.condition?.delay_min ?? 0;
    const searchWindowMs = delayMin > 0
      ? delayMin * 1.5 * 60 * 1000
      : 5 * 60 * 1000;
    const since = rule.lastFiredAt || new Date(Date.now() - searchWindowMs);

    const matchingEvents = await prisma.opsEvent.findMany({
      where: {
        kind: rule.eventKind,
        createdAt: { gt: since }
      },
      take: 10,
      orderBy: { createdAt: 'desc' }
    });

    evaluated += matchingEvents.length;

    if (matchingEvents.length > 0) {
      const conditionMet = checkTriggerCondition(rule.condition, matchingEvents[0]);
      if (!conditionMet) continue;

      const template = rule.proposalTemplate;
      try {
        // CAS update: only fire if lastFiredAt hasn't changed since read
        const casUpdate = await prisma.opsTriggerRule.updateMany({
          where: { id: rule.id, lastFiredAt: rule.lastFiredAt },
          data: { lastFiredAt: new Date() }
        });
        if (casUpdate.count === 0) continue; // Already fired by another worker

        const result = await createProposalAndMaybeAutoApprove({
          skillName: template.skill_name,
          source: 'trigger',
          title: template.title,
          payload: { triggeredBy: rule.name, eventId: matchingEvents[0].id },
          steps: template.steps.map(s => ({ kind: s.kind, order: s.order }))
        });

        fired++;
        logger.info(`Trigger fired: ${rule.name} → proposal ${result.proposalId}`);
      } catch (err) {
        logger.warn(`Trigger ${rule.name} failed:`, err.message);
      }
    }
  }

  return { evaluated, fired };
}

/**
 * Check trigger condition (§19.3 corrected version)
 * @param {Object} condition
 * @param {Object} event
 * @returns {boolean}
 */
function checkTriggerCondition(condition, event) {
  const delayMin = condition.delay_min ?? null;
  if (delayMin != null && delayMin > 0) {
    const eventAgeMin = (Date.now() - event.createdAt.getTime()) / (1000 * 60);
    if (eventAgeMin < delayMin) return false;
    if (eventAgeMin > delayMin * 2) return false;
  }

  if (condition.min_severity) {
    const severity = event.payload?.severity ?? 0;
    if (severity < condition.min_severity) return false;
  }

  return true;
}

// Export for testing
export { checkTriggerCondition };
