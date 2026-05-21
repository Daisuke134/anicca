import { Router } from 'express';
import { z } from 'zod';
import { prisma } from '../../lib/prisma.js';

const router = Router();

const CreateHookPostSchema = z.object({
  platform: z.enum(['x', 'tiktok']),
  hookId: z.string().uuid(),
  content: z.string().min(1).max(2000),
  mediaUrl: z.string().url().optional(),
  externalPostId: z.string().max(100).optional(),
  verificationScore: z.number().int().min(0).max(5),
});

async function findHookOrNull(hookId) {
  return prisma.hookCandidate.findUnique({
    where: { id: hookId },
    select: { id: true, text: true, tone: true, targetProblemTypes: true },
  });
}

router.post('/', async (req, res) => {
  const parsed = CreateHookPostSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      error: 'Bad Request',
      issues: parsed.error.issues,
    });
  }

  try {
    const payload = parsed.data;
    const hook = await findHookOrNull(payload.hookId);
    if (!hook) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'Invalid hookId: hook not found',
      });
    }

    const meta = [
      `verification_score=${payload.verificationScore}`,
      payload.mediaUrl ? `media_url=${payload.mediaUrl}` : null,
    ].filter(Boolean).join(' ');

    if (payload.platform === 'x') {
      const post = await prisma.xPost.create({
        data: {
          hookCandidateId: payload.hookId,
          text: payload.content,
          xPostId: payload.externalPostId || null,
          postedAt: new Date(),
          agentReasoning: meta || null,
        },
        select: { id: true, createdAt: true },
      });
      return res.status(201).json({ id: post.id, platform: 'x', createdAt: post.createdAt });
    }

    const post = await prisma.tiktokPost.create({
      data: {
        hookCandidateId: payload.hookId,
        caption: payload.content,
        tiktokVideoId: payload.externalPostId || null,
        postedAt: new Date(),
        agentReasoning: meta || null,
      },
      select: { id: true, createdAt: true },
    });
    return res.status(201).json({ id: post.id, platform: 'tiktok', createdAt: post.createdAt });
  } catch (error) {
    if (error?.code === 'P2002') {
      return res.status(409).json({
        error: 'Conflict',
        message: 'externalPostId is already registered',
      });
    }
    console.error('[Agent HookPosts] create error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
    });
  }
});

router.get('/:id', async (req, res) => {
  const id = req.params.id;

  try {
    const xPost = await prisma.xPost.findUnique({
      where: { id },
      include: {
        hookCandidate: {
          select: { id: true, text: true, tone: true, targetProblemTypes: true },
        },
      },
    });
    if (xPost) {
      return res.json({
        id: xPost.id,
        platform: 'x',
        content: xPost.text,
        externalPostId: xPost.xPostId,
        createdAt: xPost.createdAt,
        hook: xPost.hookCandidate
          ? {
            id: xPost.hookCandidate.id,
            content: xPost.hookCandidate.text,
            tone: xPost.hookCandidate.tone,
            problemType: xPost.hookCandidate.targetProblemTypes[0] || null,
          }
          : null,
      });
    }

    const tiktokPost = await prisma.tiktokPost.findUnique({
      where: { id },
      include: {
        hookCandidate: {
          select: { id: true, text: true, tone: true, targetProblemTypes: true },
        },
      },
    });
    if (tiktokPost) {
      return res.json({
        id: tiktokPost.id,
        platform: 'tiktok',
        content: tiktokPost.caption,
        externalPostId: tiktokPost.tiktokVideoId,
        createdAt: tiktokPost.createdAt,
        hook: tiktokPost.hookCandidate
          ? {
            id: tiktokPost.hookCandidate.id,
            content: tiktokPost.hookCandidate.text,
            tone: tiktokPost.hookCandidate.tone,
            problemType: tiktokPost.hookCandidate.targetProblemTypes[0] || null,
          }
          : null,
      });
    }

    return res.status(404).json({
      error: 'Not Found',
      message: 'HookPost not found',
    });
  } catch (error) {
    console.error('[Agent HookPosts] get error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
    });
  }
});

export default router;
