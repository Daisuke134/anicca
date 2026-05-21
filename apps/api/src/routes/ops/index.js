import { Router } from 'express';
import heartbeatRouter from './heartbeat.js';
import eventsRouter from './events.js';
import { z } from 'zod';
import { createProposalAndMaybeAutoApprove } from '../../services/ops/proposalService.js';
import { emitEvent } from '../../services/ops/eventEmitter.js';
import { prisma } from '../../lib/prisma.js';
import { maybeFinalizeMission } from '../../services/ops/staleRecovery.js';
import { logger } from '../../lib/logger.js';

const router = Router();

// Sub-routers
router.use(heartbeatRouter);
router.use(eventsRouter);

// --- Proposal API ---

const ProposalInputSchema = z.object({
  skillName: z.string().max(50),
  source: z.enum(['cron', 'trigger', 'reaction', 'manual']),
  title: z.string().max(500),
  payload: z.record(z.unknown()).default({}),
  steps: z.array(z.object({
    kind: z.string().max(50),
    order: z.number().int().min(0),
    input: z.record(z.unknown()).optional()
  })).min(1)
});

/**
 * POST /api/ops/proposal
 */
router.post('/proposal', async (req, res) => {
  try {
    const parsed = ProposalInputSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.flatten() });
    }
    const result = await createProposalAndMaybeAutoApprove(parsed.data);
    res.json(result);
  } catch (err) {
    logger.error(`POST /proposal failed: ${err.message}`);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// --- Proposal Approval (manual) ---

/**
 * POST /api/ops/proposal/:id/approve
 * Manually approve a pending proposal → creates Mission with steps
 */
router.post('/proposal/:id/approve', async (req, res) => {
  try {
    const { id } = req.params;
    const proposal = await prisma.opsProposal.findUnique({ where: { id } });

    if (!proposal) {
      return res.status(404).json({ error: 'Proposal not found' });
    }
    if (proposal.status !== 'pending') {
      return res.status(409).json({ error: `Proposal is already ${proposal.status}` });
    }

    const steps = proposal.payload?.steps || [];
    if (steps.length === 0) {
      return res.status(400).json({ error: 'Proposal has no steps' });
    }

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
      where: { id },
      data: { status: 'accepted', resolvedAt: new Date() }
    });

    await emitEvent(proposal.skillName, 'proposal:approved', ['proposal', 'approved', 'manual'], {
      proposalId: id,
      missionId: mission.id
    });

    logger.info(`Proposal manually approved: ${proposal.title} → Mission ${mission.id}`);
    res.json({ ok: true, missionId: mission.id, steps: mission.steps.length });
  } catch (err) {
    logger.error(`POST /proposal/:id/approve failed: ${err.message}`);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// --- Step Execution API (VPS Worker) ---

/**
 * GET /api/ops/step/next
 * Atomic claim with updateMany to prevent double-claim.
 * Skips steps whose mission is failed/cancelled, and steps whose predecessor hasn't succeeded.
 */
router.get('/step/next', async (req, res) => {
  try {
  const step = await prisma.$transaction(async (tx) => {
    // Get candidates: queued steps in running missions only
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
      // Check previous step is completed (sequential execution)
      if (candidate.stepOrder > 0) {
        const prevStep = await tx.opsMissionStep.findFirst({
          where: {
            missionId: candidate.missionId,
            stepOrder: candidate.stepOrder - 1
          },
          select: { status: true, output: true }
        });
        if (!prevStep || prevStep.status !== 'succeeded') {
          continue; // Skip — predecessor not ready, try next candidate
        }

        // Data passing: inject previous step output into input
        if (prevStep.output) {
          candidate.input = { ...(candidate.input || {}), ...prevStep.output };
        }
      }

      // Atomic claim: updateMany with status guard prevents double-claim
      const claimed = await tx.opsMissionStep.updateMany({
        where: { id: candidate.id, status: 'queued' },
        data: { status: 'running', reservedAt: new Date(), input: candidate.input || {} }
      });

      if (claimed.count === 0) {
        continue; // Already claimed by another worker, try next
      }

      return candidate;
    }

    return null;
  });

  if (!step) {
    return res.json({ step: null });
  }

  res.json({
    step: {
      id: step.id,
      missionId: step.missionId,
      stepKind: step.stepKind,
      stepOrder: step.stepOrder,
      input: step.input,
      proposalPayload: step.mission.proposal.payload,
      skillName: step.mission.proposal.skillName
    }
  });
  } catch (err) {
    logger.error(`GET /step/next failed: ${err.message}`);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// --- Step Complete ---

const StepCompleteSchema = z.object({
  status: z.enum(['succeeded', 'failed']),
  output: z.record(z.unknown()).optional(),
  error: z.string().optional(),
  events: z.array(z.object({
    kind: z.string(),
    tags: z.array(z.string()).optional(),
    payload: z.record(z.unknown()).optional()
  })).optional()
});

/**
 * PATCH /api/ops/step/:id/complete
 */
router.patch('/step/:id/complete', async (req, res) => {
  try {
    const { id } = req.params;
    const parsed = StepCompleteSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: parsed.error.flatten() });
    }

    const { status, output, error, events } = parsed.data;

    // Atomic status guard: only running steps can be completed
    const updated = await prisma.opsMissionStep.updateMany({
      where: { id, status: 'running' },
      data: {
        status,
        output: output || {},
        lastError: error || null,
        completedAt: new Date()
      }
    });

    if (updated.count === 0) {
      return res.status(409).json({
        error: `Step ${id} is not in 'running' state or not found`
      });
    }

    // Get missionId for event emission and finalization
    const step = await prisma.opsMissionStep.findUnique({
      where: { id },
      select: { missionId: true }
    });

    // Emit events from step executor
    if (events && events.length > 0 && step) {
      const mission = await prisma.opsMission.findUnique({
        where: { id: step.missionId },
        include: { proposal: { select: { skillName: true } } }
      });
      const source = mission?.proposal?.skillName || 'unknown';

      for (const evt of events) {
        await emitEvent(
          source,
          evt.kind,
          evt.tags || [],
          { ...evt.payload, stepId: id },
          step.missionId
        );
      }
    }

    const missionStatus = step ? await maybeFinalizeMission(step.missionId) : null;

    res.json({ ok: true, stepStatus: status, missionStatus });
  } catch (err) {
    logger.error(`PATCH /step/:id/complete failed: ${err.message}`);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
