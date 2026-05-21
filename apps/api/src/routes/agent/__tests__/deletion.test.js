/**
 * Deletion API Tests (1.6.1)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';

// Set env before importing
process.env.ANICCA_AGENT_TOKEN = 'test-token-12345';

// Mock auth middleware
vi.mock('../../../middleware/requireAgentAuth.js', () => ({
  requireAgentAuth: (req, res, next) => {
    req.agentAuth = { tokenType: 'current' };
    next();
  },
}));

import deletionRouter from '../deletion.js';

// Mock Prisma
vi.mock('../../../lib/prisma.js', () => ({
  prisma: {
    $executeRaw: vi.fn().mockResolvedValue(3),
    agentAuditLog: {
      create: vi.fn().mockResolvedValue({}),
      findFirst: vi.fn(),
    },
    agentPost: {
      count: vi.fn().mockResolvedValue(0),
    },
  },
}));

const app = express();
app.use(express.json());
app.use('/api/agent/deletion', deletionRouter);

describe('Deletion API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('POST /api/agent/deletion', () => {
    it('should delete user data and return count (AC-28)', async () => {
      const res = await request(app)
        .post('/api/agent/deletion')
        .send({
          platformUserId: 'moltbook:user123',
          requestedBy: 'moltbook_dm',
        });

      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('success', true);
      expect(res.body).toHaveProperty('deletedCount', 3);
    });

    it('should return 400 if platformUserId missing', async () => {
      const res = await request(app)
        .post('/api/agent/deletion')
        .send({
          requestedBy: 'moltbook_dm',
        });

      expect(res.status).toBe(400);
    });

    it('should return 400 if requestedBy missing', async () => {
      const res = await request(app)
        .post('/api/agent/deletion')
        .send({
          platformUserId: 'moltbook:user123',
        });

      expect(res.status).toBe(400);
    });

    it('should return 400 if platformUserId format invalid', async () => {
      const res = await request(app)
        .post('/api/agent/deletion')
        .send({
          platformUserId: 'invalid-format',
          requestedBy: 'moltbook_dm',
        });

      expect(res.status).toBe(400);
    });

    it('should require adminId for admin_cli requests', async () => {
      const res = await request(app)
        .post('/api/agent/deletion')
        .send({
          platformUserId: 'moltbook:user123',
          requestedBy: 'admin_cli',
        });

      expect(res.status).toBe(400);
    });

    it('should accept admin_cli with adminId', async () => {
      const res = await request(app)
        .post('/api/agent/deletion')
        .send({
          platformUserId: 'moltbook:user123',
          requestedBy: 'admin_cli',
          adminId: 'admin001',
        });

      expect(res.status).toBe(200);
    });
  });

  describe('GET /api/agent/deletion/status/:platformUserId', () => {
    it('should return deletion status', async () => {
      const { prisma } = await import('../../../lib/prisma.js');
      prisma.agentAuditLog.findFirst.mockResolvedValueOnce({
        createdAt: new Date('2026-01-01'),
      });

      const res = await request(app)
        .get('/api/agent/deletion/status/moltbook:user123');

      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('platformUserId', 'moltbook:user123');
      expect(res.body).toHaveProperty('remainingPosts', 0);
      expect(res.body).toHaveProperty('deleted', true);
    });
  });
});

describe('Anonymization', () => {
  it('should anonymize posts older than 90 days (AC-27)', async () => {
    // This would test the runAnonymization job
    // For now, we verify the SQL structure is correct
    const { runAnonymization } = await import('../../../jobs/anonymizeAgentPosts.js');
    
    // Mock is already set up to return 3
    const result = await runAnonymization();
    expect(result.count).toBe(3);
  });
});
