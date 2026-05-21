import { describe, it, expect, vi, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';

vi.mock('../../../middleware/requireInternalAuth.js', () => ({
  default: (req, res, next) => next(),
}));

const prismaMocks = vi.hoisted(() => ({
  researchItem: {
    create: vi.fn(),
    findMany: vi.fn(),
  },
}));

vi.mock('../../../lib/prisma.js', () => ({ default: prismaMocks }));

import researchRouter from '../research.js';

const app = express();
app.use(express.json());
app.use('/api/admin/research', researchRouter);

describe('admin research', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates item', async () => {
    prismaMocks.researchItem.create.mockResolvedValueOnce({
      id: 'r1',
      source: 'x_research',
      query: 'q',
      summary: 's',
      createdAt: new Date('2026-02-09T00:00:00Z'),
    });

    const res = await request(app)
      .post('/api/admin/research/items')
      .send({ source: 'x_research', query: 'q', summary: 's', payload: { a: 1 } });

    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty('id', 'r1');
  });

  it('lists items', async () => {
    prismaMocks.researchItem.findMany.mockResolvedValueOnce([
      { id: 'r1', source: 'x_research', query: null, summary: 's', createdAt: new Date() },
    ]);

    const res = await request(app).get('/api/admin/research/items?source=x_research&limit=10');
    expect(res.status).toBe(200);
    expect(res.body.items).toHaveLength(1);
    expect(prismaMocks.researchItem.findMany).toHaveBeenCalled();
  });
});

