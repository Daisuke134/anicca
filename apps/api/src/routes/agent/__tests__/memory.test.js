import { describe, it, expect, beforeEach, vi } from 'vitest';
import request from 'supertest';
import express from 'express';

process.env.ANICCA_AGENT_TOKEN = 'test-token-12345';

vi.mock('../../../middleware/requireAgentAuth.js', () => ({
  requireAgentAuth: (req, _res, next) => {
    req.agentAuth = { tokenType: 'current' };
    next();
  },
}));

const mockMem0 = {
  addProfile: vi.fn(),
  addBehaviorSummary: vi.fn(),
  addInteraction: vi.fn(),
  addNudgeMeta: vi.fn(),
  search: vi.fn(),
};

vi.mock('../../../modules/memory/mem0Client.js', () => ({
  getMem0Client: vi.fn(async () => mockMem0),
}));

import memoryRouter from '../memory.js';

const app = express();
app.use(express.json());
app.use('/api/agent/memory', memoryRouter);

describe('Agent Memory API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('POST /api/agent/memory/memorize', () => {
    it('stores memory with interaction category by default', async () => {
      mockMem0.addInteraction.mockResolvedValueOnce([{ id: 'mem-1' }]);

      const res = await request(app)
        .post('/api/agent/memory/memorize')
        .send({
          userId: 'user-1',
          content: 'I slept better after reducing doomscrolling.',
        });

      expect(res.status).toBe(201);
      expect(res.body).toEqual({
        success: true,
        category: 'interaction',
        memoryId: 'mem-1',
        resourceId: 'mem-1',
        itemsExtracted: 1,
        categoriesUpdated: [],
      });
      expect(mockMem0.addInteraction).toHaveBeenCalledWith({
        userId: 'user-1',
        content: 'I slept better after reducing doomscrolling.',
        metadata: {},
      });
    });

    it('routes to the correct category writer', async () => {
      mockMem0.addProfile.mockResolvedValueOnce({ id: 'profile-1' });

      const res = await request(app)
        .post('/api/agent/memory/memorize')
        .send({
          userId: 'user-1',
          content: 'User prefers short, gentle nudges.',
          category: 'profile',
          metadata: { source: 'manual' },
        });

      expect(res.status).toBe(201);
      expect(res.body.memoryId).toBe('profile-1');
      expect(mockMem0.addProfile).toHaveBeenCalledWith({
        userId: 'user-1',
        content: 'User prefers short, gentle nudges.',
        metadata: { source: 'manual' },
      });
    });

    it('returns 400 for invalid payload', async () => {
      const res = await request(app)
        .post('/api/agent/memory/memorize')
        .send({
          userId: '',
          content: '',
          category: 'unknown',
        });

      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Bad Request');
    });
  });

  describe('POST /api/agent/memory/retrieve', () => {
    it('returns normalized memory search results', async () => {
      mockMem0.search.mockResolvedValueOnce({
        results: [
          { id: 'm1', memory: 'First memory', score: 0.88, metadata: { tag: 'sleep', category: 'habit/sleep' } },
          { memory_id: 'm2', content: 'Second memory', relevance: 0.76, metadata: { categoryPath: 'habit/recovery' } },
        ],
      });

      const res = await request(app)
        .post('/api/agent/memory/retrieve')
        .send({
          userId: 'user-1',
          query: 'sleep',
          topK: 2,
        });

      expect(res.status).toBe(200);
      expect(res.body).toEqual({
        items: [
          {
            id: 'm1',
            content: 'First memory',
            relevanceScore: 0.88,
            categoryPath: 'habit/sleep',
            metadata: { tag: 'sleep', category: 'habit/sleep' },
          },
          {
            id: 'm2',
            content: 'Second memory',
            relevanceScore: 0.76,
            categoryPath: 'habit/recovery',
            metadata: { categoryPath: 'habit/recovery' },
          },
        ],
        count: 2,
        fallbackUsed: false,
        source: 'cag',
      });
      expect(mockMem0.search).toHaveBeenCalledWith({
        userId: 'user-1',
        query: 'sleep',
        topK: 2,
      });
    });

    it('falls back from cag to rag when cag misses', async () => {
      mockMem0.search
        .mockResolvedValueOnce({ results: [] })
        .mockResolvedValueOnce({
          results: [
            { id: 'm3', content: 'RAG memory', score: 0.51, metadata: { categoryPath: 'rag/path' } },
          ],
        });

      const res = await request(app)
        .post('/api/agent/memory/retrieve')
        .send({
          userId: 'user-1',
          query: 'night anxiety',
          mode: 'cag',
        });

      expect(res.status).toBe(200);
      expect(res.body.fallbackUsed).toBe(true);
      expect(res.body.source).toBe('rag');
      expect(res.body.items[0].categoryPath).toBe('rag/path');
      expect(mockMem0.search).toHaveBeenCalledTimes(2);
    });

    it('falls back to llm when cag and rag miss', async () => {
      mockMem0.search
        .mockResolvedValueOnce({ results: [] })
        .mockResolvedValueOnce({ results: [] })
        .mockResolvedValueOnce({
          results: [{ id: 'm4', content: 'LLM memory', relevanceScore: 0.41 }],
        });

      const res = await request(app)
        .post('/api/agent/memory/retrieve')
        .send({
          userId: 'user-1',
          query: 'empty chain',
        });

      expect(res.status).toBe(200);
      expect(res.body.fallbackUsed).toBe(true);
      expect(res.body.source).toBe('llm');
      expect(res.body.items[0].categoryPath).toBe('uncategorized');
      expect(mockMem0.search).toHaveBeenCalledTimes(3);
    });

    it('supports explicit rag mode', async () => {
      mockMem0.search.mockResolvedValueOnce({
        results: [{ id: 'm5', content: 'rag only', score: 0.33 }],
      });

      const res = await request(app)
        .post('/api/agent/memory/retrieve')
        .send({
          userId: 'user-1',
          query: 'focus',
          mode: 'rag',
        });

      expect(res.status).toBe(200);
      expect(res.body.fallbackUsed).toBe(false);
      expect(res.body.source).toBe('rag');
    });

    it('supports explicit llm mode', async () => {
      mockMem0.search.mockResolvedValueOnce({
        results: [{ id: 'm6', content: 'llm only', score: 0.22 }],
      });

      const res = await request(app)
        .post('/api/agent/memory/retrieve')
        .send({
          userId: 'user-1',
          query: 'focus',
          mode: 'llm',
          limit: 1,
        });

      expect(res.status).toBe(200);
      expect(res.body.fallbackUsed).toBe(false);
      expect(res.body.source).toBe('llm');
      expect(mockMem0.search).toHaveBeenCalledWith({
        userId: 'user-1',
        query: 'focus',
        topK: 1,
      });
    });

    it('returns 400 for invalid retrieve payload', async () => {
      const res = await request(app)
        .post('/api/agent/memory/retrieve')
        .send({
          userId: 'user-1',
          query: '',
          topK: 99,
        });

      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Bad Request');
    });
  });
});
