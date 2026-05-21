import { prisma } from '../../lib/prisma.js';
import { getExecutor } from './stepExecutors/registry.js';
import { emitEvent } from './eventEmitter.js';
import { maybeFinalizeMission } from './staleRecovery.js';
import { logger } from '../../lib/logger.js';

/**
 * Process up to `maxSteps` queued steps per heartbeat cycle.
 * Claim → Execute → Complete in a single server-side loop.
 *
 * Called from heartbeat every 5min.
 */
export async function processQueuedSteps(maxSteps = 3) {
  let executed = 0;
  let failed = 0;

  for (let i = 0; i < maxSteps; i++) {
    const step = await claimNextStep();
    if (!step) break;

    try {
      await executeAndComplete(step);
      executed++;
    } catch (error) {
      failed++;
      logger.error(`Step ${step.id} (${step.stepKind}) execution failed:`, error);
      await failStep(step.id, error.message, step.missionId);
    }
  }

  return { executed, failed };
}

/**
 * Claim the next queued step (same logic as GET /step/next).
 */
async function claimNextStep() {
  return prisma.$transaction(async (tx) => {
    const candidates = await tx.opsMissionStep.findMany({
      where: {
        status: 'queued',
        mission: { status: 'running' }
      },
      orderBy: [
        { createdAt: 'asc' },
        { stepOrder: 'asc' }
      ],
      take: 10,
      include: {
        mission: {
          include: { proposal: true }
        }
      }
    });

    for (const candidate of candidates) {
      if (candidate.stepOrder > 0) {
        const prevStep = await tx.opsMissionStep.findFirst({
          where: {
            missionId: candidate.missionId,
            stepOrder: candidate.stepOrder - 1
          },
          select: { status: true, output: true }
        });
        if (!prevStep || prevStep.status !== 'succeeded') {
          continue;
        }
        if (prevStep.output) {
          candidate.input = { ...(candidate.input || {}), ...prevStep.output };
        }
      }

      const claimed = await tx.opsMissionStep.updateMany({
        where: { id: candidate.id, status: 'queued' },
        data: { status: 'running', reservedAt: new Date(), input: candidate.input || {} }
      });

      if (claimed.count === 0) continue;
      return candidate;
    }

    return null;
  });
}

/**
 * Execute a claimed step and mark it complete.
 */
async function executeAndComplete(step) {
  const executor = getExecutor(step.stepKind);

  const result = await executor({
    input: step.input || {},
    missionId: step.missionId,
    proposalPayload: step.mission.proposal.payload,
    skillName: step.mission.proposal.skillName
  });

  await prisma.opsMissionStep.updateMany({
    where: { id: step.id, status: 'running' },
    data: {
      status: 'succeeded',
      output: result.output || {},
      completedAt: new Date()
    }
  });

  if (result.events?.length > 0) {
    const source = step.mission.proposal.skillName;
    for (const evt of result.events) {
      await emitEvent(
        source,
        evt.kind,
        evt.tags || [],
        { ...evt.payload, stepId: step.id },
        step.missionId
      );
    }
  }

  await maybeFinalizeMission(step.missionId);
  logger.info(`Step ${step.id} (${step.stepKind}) completed successfully`);
}

/**
 * Mark a step as failed.
 */
async function failStep(stepId, errorMessage, missionId) {
  await prisma.opsMissionStep.updateMany({
    where: { id: stepId, status: 'running' },
    data: {
      status: 'failed',
      lastError: errorMessage,
      completedAt: new Date()
    }
  });

  if (missionId) {
    await maybeFinalizeMission(missionId);
  }
}
