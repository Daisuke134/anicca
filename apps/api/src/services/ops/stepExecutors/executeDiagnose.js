import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * 失敗したミッションの原因を分析し、学びを記録
 *
 * Input: { eventId: string }
 * Output: { diagnosis: string, rootCause: string, recommendation: string }
 */
export async function executeDiagnose({ input, proposalPayload }) {
  const eventId = input.eventId || proposalPayload.eventId;
  const event = await prisma.opsEvent.findUnique({ where: { id: eventId } });

  if (!event) {
    throw new Error(`Event not found: ${eventId}`);
  }

  const missionId = event.payload?.missionId;
  const mission = missionId ? await prisma.opsMission.findUnique({
    where: { id: missionId },
    include: {
      steps: { orderBy: { stepOrder: 'asc' } },
      proposal: true
    }
  }) : null;

  const failedSteps = mission?.steps?.filter(s => s.status === 'failed') || [];

  const diagnosis = await callLLM(`以下のミッション失敗を診断:
Mission: ${mission?.proposal?.title || 'unknown'}
Skill: ${event.source}
Failed Steps: ${JSON.stringify(failedSteps.map(s => ({
    kind: s.stepKind,
    error: s.lastError
  })))}

根本原因を特定し、再発防止策を提案:`);

  logger.info(`Diagnosis complete for mission ${missionId}`);

  return {
    output: {
      diagnosis,
      failedMissionId: missionId,
      failedStepKinds: failedSteps.map(s => s.stepKind)
    },
    events: [{
      kind: 'diagnosis:completed',
      tags: ['diagnosis', 'completed'],
      payload: { missionId, diagnosisPreview: diagnosis.substring(0, 200) }
    }]
  };
}
