import { prisma } from '../../lib/prisma.js';
import { getPolicy } from './policyService.js';
import { logger } from '../../lib/logger.js';

/**
 * Recover steps stuck in 'running' state beyond threshold
 * @returns {Promise<{recovered: number, missionsFailed: number}>}
 */
export async function recoverStaleSteps() {
  const thresholdPolicy = await getPolicy('stale_threshold_min');
  const thresholdMin = thresholdPolicy?.value ?? 30;
  const staleThreshold = new Date(Date.now() - thresholdMin * 60 * 1000);

  const staleSteps = await prisma.opsMissionStep.findMany({
    where: {
      status: 'running',
      reservedAt: { lt: staleThreshold }
    },
    select: { id: true, missionId: true }
  });

  let recovered = 0;
  let missionsFailed = 0;

  for (const step of staleSteps) {
    // Status guard: only update if still running (prevents overwriting worker completion)
    const updated = await prisma.opsMissionStep.updateMany({
      where: { id: step.id, status: 'running' },
      data: {
        status: 'failed',
        lastError: `Stale: no progress for ${thresholdMin} minutes`,
        completedAt: new Date()
      }
    });

    if (updated.count === 0) continue; // Already completed by worker
    recovered++;

    const finalized = await maybeFinalizeMission(step.missionId);
    if (finalized === 'failed') missionsFailed++;
  }

  if (recovered > 0) {
    logger.warn(`Recovered ${recovered} stale steps, ${missionsFailed} missions failed`);
  }

  return { recovered, missionsFailed };
}

/**
 * Check if all steps of a mission are done, and finalize if so.
 * When any step fails, immediately cancel all remaining queued steps
 * to prevent queue clogging in /step/next.
 * @param {string} missionId
 * @returns {Promise<'succeeded'|'failed'|null>}
 */
export async function maybeFinalizeMission(missionId) {
  return prisma.$transaction(async (tx) => {
    const steps = await tx.opsMissionStep.findMany({
      where: { missionId },
      select: { status: true }
    });

    const anyFailed = steps.some(s => s.status === 'failed');

    // Cancel queued steps if any step failed (prevent queue clogging)
    if (anyFailed) {
      await tx.opsMissionStep.updateMany({
        where: { missionId, status: 'queued' },
        data: { status: 'cancelled', completedAt: new Date() }
      });
    }

    // If any steps are still running, wait for them (stale recovery will catch them)
    const hasRunning = steps.some(s => s.status === 'running');
    if (hasRunning) return null;

    // All steps are terminal: succeeded/failed, or queued→cancelled by the block above
    const allDone = steps.every(s =>
      s.status === 'succeeded' || s.status === 'failed' ||
      (anyFailed && s.status === 'queued') // these were just cancelled
    );
    if (!allDone) return null;

    const finalStatus = anyFailed ? 'failed' : 'succeeded';

    await tx.opsMission.update({
      where: { id: missionId },
      data: { status: finalStatus, completedAt: new Date() }
    });

    const mission = await tx.opsMission.findUnique({
      where: { id: missionId },
      include: { proposal: true }
    });

    // Emit event outside transaction
    setImmediate(async () => {
      try {
        const { emitEvent } = await import('./eventEmitter.js');
        await emitEvent(
          mission.proposal.skillName,
          `mission:${finalStatus}`,
          ['mission', finalStatus],
          { missionId, proposalId: mission.proposalId }
        );
      } catch (err) {
        logger.warn(`Failed to emit mission finalization event: ${err.message}`);
      }
    });

    return finalStatus;
  });
}
