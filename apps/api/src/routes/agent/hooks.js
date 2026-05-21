import { Router } from 'express';
import { z } from 'zod';
import { prisma } from '../../lib/prisma.js';

const router = Router();

const PROBLEM_TYPES = [
  'staying_up_late',
  'cant_wake_up',
  'self_loathing',
  'rumination',
  'procrastination',
  'anxiety',
  'lying',
  'bad_mouthing',
  'porn_addiction',
  'alcohol_dependency',
  'anger',
  'obsessive',
  'loneliness',
];

const CreateHookSchema = z.object({
  content: z.string().min(1).max(500),
  problemType: z.enum(PROBLEM_TYPES),
  tone: z.enum(['gentle', 'understanding', 'encouraging', 'empathetic', 'playful']).default('gentle'),
  source: z.string().min(1).max(50).optional(),
});

const platformSchema = z.enum(['app', 'x', 'tiktok', 'moltbook', 'slack']);
const UpdateStatsSchema = z.object({
  platform: platformSchema,
  engagementRate: z.number().min(0).max(1).optional(),
  sampleSize: z.number().int().min(0).optional(),
  highPerformer: z.boolean().optional(),
}).refine(
  (value) => value.engagementRate !== undefined || value.sampleSize !== undefined || value.highPerformer !== undefined,
  { message: 'at least one stats field is required' }
);

function buildStatsPatch({ platform, engagementRate, sampleSize, highPerformer }) {
  const patch = {};

  if (platform === 'app') {
    if (engagementRate !== undefined) patch.appTapRate = engagementRate;
    if (sampleSize !== undefined) patch.appSampleSize = sampleSize;
    return patch;
  }
  if (platform === 'x') {
    if (engagementRate !== undefined) patch.xEngagementRate = engagementRate;
    if (sampleSize !== undefined) patch.xSampleSize = sampleSize;
    if (highPerformer !== undefined) patch.xHighPerformer = highPerformer;
    return patch;
  }
  if (platform === 'tiktok') {
    if (engagementRate !== undefined) patch.tiktokLikeRate = engagementRate;
    if (sampleSize !== undefined) patch.tiktokSampleSize = sampleSize;
    if (highPerformer !== undefined) patch.tiktokHighPerformer = highPerformer;
    return patch;
  }
  if (platform === 'moltbook') {
    if (engagementRate !== undefined) patch.moltbookUpvoteRate = engagementRate;
    if (sampleSize !== undefined) patch.moltbookSampleSize = sampleSize;
    if (highPerformer !== undefined) patch.moltbookHighPerformer = highPerformer;
    return patch;
  }
  if (platform === 'slack') {
    if (engagementRate !== undefined) patch.slackReactionRate = engagementRate;
    if (sampleSize !== undefined) patch.slackSampleSize = sampleSize;
    if (highPerformer !== undefined) patch.slackHighPerformer = highPerformer;
    return patch;
  }
  return patch;
}

router.post('/', async (req, res) => {
  const parsed = CreateHookSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      error: 'Bad Request',
      issues: parsed.error.issues,
    });
  }

  try {
    const hook = await prisma.hookCandidate.create({
      data: {
        text: parsed.data.content,
        tone: parsed.data.tone,
        targetProblemTypes: [parsed.data.problemType],
        source: parsed.data.source || 'manual',
      },
      select: {
        id: true,
        text: true,
        tone: true,
        targetProblemTypes: true,
        source: true,
        createdAt: true,
      },
    });

    return res.status(201).json({
      id: hook.id,
      content: hook.text,
      tone: hook.tone,
      problemType: hook.targetProblemTypes[0] || null,
      source: hook.source,
      createdAt: hook.createdAt,
    });
  } catch (error) {
    if (error?.code === 'P2002') {
      return res.status(409).json({
        error: 'Conflict',
        message: 'Hook already exists for the same content and tone',
      });
    }
    console.error('[Agent Hooks] create error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
    });
  }
});

router.patch('/:id/stats', async (req, res) => {
  const parsed = UpdateStatsSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      error: 'Bad Request',
      issues: parsed.error.issues,
    });
  }

  const patch = buildStatsPatch(parsed.data);
  if (Object.keys(patch).length === 0) {
    return res.status(400).json({
      error: 'Bad Request',
      message: 'No applicable fields to update',
    });
  }

  try {
    const updated = await prisma.hookCandidate.update({
      where: { id: req.params.id },
      data: patch,
      select: {
        id: true,
        appTapRate: true,
        appSampleSize: true,
        xEngagementRate: true,
        xSampleSize: true,
        xHighPerformer: true,
        tiktokLikeRate: true,
        tiktokSampleSize: true,
        tiktokHighPerformer: true,
        moltbookUpvoteRate: true,
        moltbookSampleSize: true,
        moltbookHighPerformer: true,
        slackReactionRate: true,
        slackSampleSize: true,
        slackHighPerformer: true,
        updatedAt: true,
      },
    });

    return res.json(updated);
  } catch (error) {
    if (error?.code === 'P2025') {
      return res.status(404).json({
        error: 'Not Found',
        message: 'Hook not found',
      });
    }
    console.error('[Agent Hooks] stats update error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
    });
  }
});

export default router;
