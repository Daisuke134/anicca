import { prisma } from '../../lib/prisma.js';
import { logger } from '../../lib/logger.js';
import { checkCapGate } from './capGates.js';
import { getPolicy } from './policyService.js';
import { emitEvent } from './eventEmitter.js';

/**
 * Create proposal + Cap Gate + Auto-Approve + Mission generation
 * All sources (Cron, Trigger, Reaction, Manual) go through this function
 *
 * @param {Object} input
 * @param {string} input.skillName
 * @param {string} input.source - 'cron' | 'trigger' | 'reaction' | 'manual'
 * @param {string} input.title
 * @param {Object} input.payload
 * @param {Array<{kind: string, order: number, input?: Object}>} input.steps
 * @returns {Promise<{proposalId: string|null, status: string, missionId?: string, rejectReason?: string}>}
 */
export async function createProposalAndMaybeAutoApprove(input) {
  const { skillName, source, title, payload, steps } = input;

  // 1. Daily proposal limit check
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  const todayCount = await prisma.opsProposal.count({
    where: { createdAt: { gte: todayStart } }
  });
  if (todayCount >= 100) {
    logger.warn(`Daily proposal limit reached (${todayCount}/100)`);
    return { proposalId: null, status: 'rejected', rejectReason: 'daily_proposal_limit' };
  }

  // 2. Cap Gate check per step kind
  for (const step of steps) {
    const gateResult = await checkCapGate(step.kind);
    if (!gateResult.ok) {
      const proposal = await prisma.opsProposal.create({
        data: {
          skillName,
          source,
          status: 'rejected',
          title,
          payload,
          rejectReason: gateResult.reason,
          resolvedAt: new Date()
        }
      });

      await emitEvent(skillName, 'proposal:rejected', ['proposal', 'rejected'], {
        proposalId: proposal.id,
        reason: gateResult.reason
      });

      logger.info(`Proposal rejected: ${title} — ${gateResult.reason}`);
      return { proposalId: proposal.id, status: 'rejected', rejectReason: gateResult.reason };
    }
  }

  // 3. Create proposal (include steps in payload for approval handler)
  const proposal = await prisma.opsProposal.create({
    data: {
      skillName,
      source,
      status: 'pending',
      title,
      payload: { ...payload, steps }
    }
  });

  // 4. Record event
  await emitEvent(skillName, 'proposal:created', ['proposal', 'created'], {
    proposalId: proposal.id,
    source
  });

  // 5. Auto-Approve evaluation
  // Kill Switch: these step kinds NEVER auto-approve, regardless of policy
  const KILL_SWITCH_DENY = new Set(['post_x', 'post_tiktok', 'send_nudge', 'deploy', 'reply_dm']);
  const hasKillSwitchStep = steps.some(s => KILL_SWITCH_DENY.has(s.kind));

  const autoApprovePolicy = await getPolicy('auto_approve');
  const allStepsAutoApprovable = !hasKillSwitchStep && steps.every(
    s => autoApprovePolicy?.allowed_step_kinds?.includes(s.kind)
  );

  if (autoApprovePolicy?.enabled && allStepsAutoApprovable) {
    const mission = await prisma.opsMission.create({
      data: {
        proposalId: proposal.id,
        status: 'running',
        steps: {
          create: steps.map(s => ({
            stepKind: s.kind,
            stepOrder: s.order,
            status: 'queued',
            input: s.input || {}
          }))
        }
      },
      include: { steps: true }
    });

    await prisma.opsProposal.update({
      where: { id: proposal.id },
      data: { status: 'accepted', resolvedAt: new Date() }
    });

    await emitEvent(skillName, 'proposal:auto_approved', ['proposal', 'approved', 'auto'], {
      proposalId: proposal.id,
      missionId: mission.id
    });

    logger.info(`Proposal auto-approved: ${title} → Mission ${mission.id}`);
    return { proposalId: proposal.id, status: 'accepted', missionId: mission.id };
  }

  // Not auto-approvable → pending (waiting for human approval)
  try {
    const { sendApprovalNotification } = await import('./approvalNotifier.js');
    await sendApprovalNotification(proposal);
  } catch (err) {
    logger.warn(`Failed to send approval notification: ${err.message}`);
  }

  logger.info(`Proposal awaiting approval: ${title}`);
  return { proposalId: proposal.id, status: 'pending' };
}
