import { beforeEach, describe, expect, it, vi } from 'vitest';
import express from 'express';
import request from 'supertest';

vi.mock('../../../lib/prisma.js', () => ({
  prisma: {
    hookCandidate: {
      create: vi.fn(),
      update: vi.fn(),
    },
  },
}));

import { prisma } from '../../../lib/prisma.js';
import hooksRouter from '../hooks.js';

const app = express();
app.use(express.json());
app.use('/hooks', hooksRouter);

describe('Hooks API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates hook candidate', async () => {
    prisma.hookCandidate.create.mockResolvedValueOnce({
      id: 'hook-1',
      text: 'You are not broken.',
      tone: 'gentle',
      targetProblemTypes: ['anxiety'],
      source: 'manual',
      createdAt: new Date('2026-02-09T10:00:00Z'),
    });

    const res = await request(app).post('/hooks').send({
      content: 'You are not broken.',
      problemType: 'anxiety',
      tone: 'gentle',
    });

    expect(res.status).toBe(201);
    expect(res.body.id).toBe('hook-1');
    expect(res.body.content).toBe('You are not broken.');
  });

  it('returns 400 on invalid create payload', async () => {
    const res = await request(app).post('/hooks').send({
      content: '',
      problemType: 'invalid',
    });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Bad Request');
  });

  it('updates stats for a platform', async () => {
    prisma.hookCandidate.update.mockResolvedValueOnce({
      id: 'hook-1',
      appTapRate: 0.42,
      appSampleSize: 12,
      xEngagementRate: 0,
      xSampleSize: 0,
      xHighPerformer: false,
      tiktokLikeRate: 0,
      tiktokSampleSize: 0,
      tiktokHighPerformer: false,
      moltbookUpvoteRate: 0,
      moltbookSampleSize: 0,
      moltbookHighPerformer: false,
      slackReactionRate: 0,
      slackSampleSize: 0,
      slackHighPerformer: false,
      updatedAt: new Date('2026-02-09T10:00:00Z'),
    });

    const res = await request(app).patch('/hooks/hook-1/stats').send({
      platform: 'app',
      engagementRate: 0.42,
      sampleSize: 12,
    });

    expect(res.status).toBe(200);
    expect(prisma.hookCandidate.update).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: 'hook-1' },
        data: { appTapRate: 0.42, appSampleSize: 12 },
      })
    );
  });

  it('returns 404 when updating stats for unknown hook', async () => {
    prisma.hookCandidate.update.mockRejectedValueOnce({ code: 'P2025' });

    const res = await request(app).patch('/hooks/missing/stats').send({
      platform: 'x',
      engagementRate: 0.3,
    });

    expect(res.status).toBe(404);
    expect(res.body.error).toBe('Not Found');
  });

  it('returns 400 when stats payload has no fields', async () => {
    const res = await request(app).patch('/hooks/hook-1/stats').send({
      platform: 'x',
    });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Bad Request');
  });
});
