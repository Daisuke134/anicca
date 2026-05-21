import { beforeEach, describe, expect, it, vi } from 'vitest';
import express from 'express';
import request from 'supertest';

vi.mock('../../../lib/prisma.js', () => ({
  prisma: {
    hookCandidate: {
      findUnique: vi.fn(),
    },
    xPost: {
      create: vi.fn(),
      findUnique: vi.fn(),
    },
    tiktokPost: {
      create: vi.fn(),
      findUnique: vi.fn(),
    },
  },
}));

import { prisma } from '../../../lib/prisma.js';
import hookPostsRouter from '../hookPosts.js';

const app = express();
app.use(express.json());
app.use('/hook-posts', hookPostsRouter);

describe('HookPosts API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates x hook post', async () => {
    prisma.hookCandidate.findUnique.mockResolvedValueOnce({
      id: '1c739f7e-2098-4558-9af5-ff7ee6894bd9',
    });
    prisma.xPost.create.mockResolvedValueOnce({
      id: 'xpost-1',
      createdAt: new Date('2026-02-09T11:00:00Z'),
    });

    const res = await request(app).post('/hook-posts').send({
      platform: 'x',
      hookId: '1c739f7e-2098-4558-9af5-ff7ee6894bd9',
      content: 'small step, then breathe',
      verificationScore: 4,
      externalPostId: 'tweet-111',
    });

    expect(res.status).toBe(201);
    expect(res.body).toEqual(
      expect.objectContaining({
        id: 'xpost-1',
        platform: 'x',
      })
    );
    expect(prisma.xPost.create).toHaveBeenCalled();
  });

  it('returns 400 for invalid hook id', async () => {
    prisma.hookCandidate.findUnique.mockResolvedValueOnce(null);

    const res = await request(app).post('/hook-posts').send({
      platform: 'x',
      hookId: '1c739f7e-2098-4558-9af5-ff7ee6894bd9',
      content: 'small step, then breathe',
      verificationScore: 4,
    });

    expect(res.status).toBe(400);
    expect(res.body.message).toContain('Invalid hookId');
  });

  it('reads normalized x post by id', async () => {
    prisma.xPost.findUnique.mockResolvedValueOnce({
      id: 'xpost-1',
      text: 'small step',
      xPostId: 'tweet-111',
      createdAt: new Date('2026-02-09T11:00:00Z'),
      hookCandidate: {
        id: 'hook-1',
        text: 'hook text',
        tone: 'gentle',
        targetProblemTypes: ['anxiety'],
      },
    });

    const res = await request(app).get('/hook-posts/xpost-1');

    expect(res.status).toBe(200);
    expect(res.body.platform).toBe('x');
    expect(res.body.hook.content).toBe('hook text');
  });

  it('returns 404 when post id is not found', async () => {
    prisma.xPost.findUnique.mockResolvedValueOnce(null);
    prisma.tiktokPost.findUnique.mockResolvedValueOnce(null);

    const res = await request(app).get('/hook-posts/not-found');
    expect(res.status).toBe(404);
    expect(res.body.error).toBe('Not Found');
  });

  it('returns 400 for invalid platform', async () => {
    const res = await request(app).post('/hook-posts').send({
      platform: 'instagram',
      hookId: '1c739f7e-2098-4558-9af5-ff7ee6894bd9',
      content: 'invalid platform',
      verificationScore: 4,
    });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Bad Request');
  });

  it('returns 400 for out-of-range verificationScore', async () => {
    const res = await request(app).post('/hook-posts').send({
      platform: 'x',
      hookId: '1c739f7e-2098-4558-9af5-ff7ee6894bd9',
      content: 'invalid score',
      verificationScore: 6,
    });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Bad Request');
  });

  it('returns 400 when content is missing', async () => {
    const res = await request(app).post('/hook-posts').send({
      platform: 'x',
      hookId: '1c739f7e-2098-4558-9af5-ff7ee6894bd9',
      verificationScore: 4,
    });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Bad Request');
  });
});
