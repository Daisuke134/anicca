/**
 * Posts API Tests (1.6.1)
 * 
 * Tests for GET /api/agent/posts/recent
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';

// Set env before importing router
process.env.ANICCA_AGENT_TOKEN = 'test-token-12345';

// Mock auth middleware
vi.mock('../../../middleware/requireAgentAuth.js', () => ({
  requireAgentAuth: (req, res, next) => {
    req.agentAuth = { tokenType: 'current' };
    next();
  },
}));

// Mock Prisma
vi.mock('../../../lib/prisma.js', () => ({
  prisma: {
    agentPost: {
      findMany: vi.fn(),
    },
  },
}));

import postsRouter from '../posts.js';
import { prisma } from '../../../lib/prisma.js';

// Create test app
const app = express();
app.use(express.json());
app.use('/posts', postsRouter);

describe('GET /posts/recent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return recent posts with default parameters', async () => {
    const mockPosts = [
      {
        id: 'uuid-1',
        platform: 'moltbook',
        externalPostId: 'ext-1',
        content: 'Test content',
        upvotes: 5,
        views: null,
        likes: 0,
        shares: 0,
        createdAt: new Date('2026-02-01T12:00:00Z'),
      },
    ];
    prisma.agentPost.findMany.mockResolvedValue(mockPosts);

    const res = await request(app).get('/posts/recent');

    expect(res.status).toBe(200);
    expect(res.body.posts).toHaveLength(1);
    expect(res.body.hasMore).toBe(false);
    expect(res.body.nextCursor).toBe(null);
  });

  it('should filter by platform', async () => {
    prisma.agentPost.findMany.mockResolvedValue([]);

    const res = await request(app).get('/posts/recent?platform=moltbook');

    expect(res.status).toBe(200);
    expect(prisma.agentPost.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: expect.objectContaining({
          platform: 'moltbook',
        }),
      })
    );
  });

  it('should reject invalid platform', async () => {
    const res = await request(app).get('/posts/recent?platform=invalid');

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('INVALID_PLATFORM');
  });

  it('should reject invalid days (too high)', async () => {
    const res = await request(app).get('/posts/recent?days=31');

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('INVALID_DAYS');
  });

  it('should reject invalid days (too low)', async () => {
    const res = await request(app).get('/posts/recent?days=0');

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('INVALID_DAYS');
  });

  it('should reject non-numeric days', async () => {
    const res = await request(app).get('/posts/recent?days=abc');

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('INVALID_DAYS');
  });

  it('should reject non-numeric limit', async () => {
    const res = await request(app).get('/posts/recent?limit=abc');

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('INVALID_LIMIT');
  });

  it('should handle pagination with cursor (ISO date string)', async () => {
    const mockPosts = [
      { id: 'uuid-2', platform: 'moltbook', createdAt: new Date('2026-02-01T10:00:00Z') },
      { id: 'uuid-3', platform: 'moltbook', createdAt: new Date('2026-02-01T09:00:00Z') },
    ];
    prisma.agentPost.findMany.mockResolvedValue(mockPosts);

    const res = await request(app).get('/posts/recent?cursor=2026-02-01T12:00:00Z');

    expect(res.status).toBe(200);
    expect(prisma.agentPost.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: expect.objectContaining({
          createdAt: expect.objectContaining({
            lt: expect.any(Date),
          }),
        }),
      })
    );
  });

  it('should reject invalid cursor format', async () => {
    const res = await request(app).get('/posts/recent?cursor=invalid-date');

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('INVALID_CURSOR');
  });

  it('should indicate hasMore when more results exist', async () => {
    // Return 51 posts (limit is 50 by default)
    const mockPosts = Array(51).fill(null).map((_, i) => ({
      id: `uuid-${i}`,
      platform: 'moltbook',
      createdAt: new Date(Date.now() - i * 60000), // Each 1 minute apart
    }));
    prisma.agentPost.findMany.mockResolvedValue(mockPosts);

    const res = await request(app).get('/posts/recent');

    expect(res.status).toBe(200);
    expect(res.body.posts).toHaveLength(50);
    expect(res.body.hasMore).toBe(true);
    expect(res.body.nextCursor).toBeTruthy(); // ISO date string
  });

  it('should respect custom limit', async () => {
    prisma.agentPost.findMany.mockResolvedValue([]);

    await request(app).get('/posts/recent?limit=10');

    expect(prisma.agentPost.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        take: 11, // +1 for hasMore check
      })
    );
  });

  it('should cap limit at 100', async () => {
    prisma.agentPost.findMany.mockResolvedValue([]);

    await request(app).get('/posts/recent?limit=200');

    expect(prisma.agentPost.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        take: 101, // 100 + 1
      })
    );
  });

  it('should clamp negative limit to minimum (1)', async () => {
    prisma.agentPost.findMany.mockResolvedValue([]);

    await request(app).get('/posts/recent?limit=-5');

    expect(prisma.agentPost.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        take: 2, // 1 + 1
      })
    );
  });

  it('should not expose error details in 500 response', async () => {
    prisma.agentPost.findMany.mockRejectedValue(new Error('Database connection failed'));

    const res = await request(app).get('/posts/recent');

    expect(res.status).toBe(500);
    expect(res.body.error).toBe('Internal Server Error');
    expect(res.body.message).toBeUndefined();
  });
});
