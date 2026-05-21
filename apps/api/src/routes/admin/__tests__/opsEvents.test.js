import { describe, it, expect, vi, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';

vi.mock('../../../middleware/requireInternalAuth.js', () => ({
  default: (req, res, next) => next(),
}));

const prismaMocks = vi.hoisted(() => ({
  agentAuditLog: {
    create: vi.fn(),
    findFirst: vi.fn(),
    count: vi.fn(),
  },
}));

const slackMocks = vi.hoisted(() => ({
  sendSlackMessage: vi.fn(),
}));

vi.mock('../../../lib/prisma.js', () => ({ default: prismaMocks }));
vi.mock('../../../services/slackNotifier.js', () => ({ sendSlackMessage: slackMocks.sendSlackMessage }));

import opsEventsRouter from '../opsEvents.js';

const app = express();
app.use(express.json());
app.use('/api/admin/ops', opsEventsRouter);

describe('POST /api/admin/ops/events', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns 400 when eventType is missing', async () => {
    const res = await request(app).post('/api/admin/ops/events').send({});
    expect(res.status).toBe(400);
  });

  it('records event and sends slack once for first x_credits_depleted in 24h', async () => {
    prismaMocks.agentAuditLog.create.mockResolvedValueOnce({});
    prismaMocks.agentAuditLog.findFirst.mockResolvedValueOnce(null);
    prismaMocks.agentAuditLog.count.mockResolvedValueOnce(1);
    slackMocks.sendSlackMessage.mockResolvedValue({ sent: true });

    const res = await request(app)
      .post('/api/admin/ops/events')
      .send({ eventType: 'x_credits_depleted', platform: 'x', payload: { reason: '429' } });

    expect(res.status).toBe(200);
    expect(prismaMocks.agentAuditLog.create).toHaveBeenCalledTimes(1);
    expect(slackMocks.sendSlackMessage).toHaveBeenCalledTimes(2);
  });

  it('suppresses slack for duplicate x_credits_depleted', async () => {
    prismaMocks.agentAuditLog.create.mockResolvedValueOnce({});
    prismaMocks.agentAuditLog.findFirst.mockResolvedValueOnce({ createdAt: new Date() });
    prismaMocks.agentAuditLog.count.mockResolvedValueOnce(2);

    const res = await request(app)
      .post('/api/admin/ops/events')
      .send({ eventType: 'x_credits_depleted', platform: 'x', payload: { reason: '429' } });

    expect(res.status).toBe(200);
    expect(slackMocks.sendSlackMessage).toHaveBeenCalledTimes(0);
  });
});
