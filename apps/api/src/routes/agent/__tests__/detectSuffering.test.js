import { describe, it, expect, vi, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';

process.env.ANICCA_AGENT_TOKEN = 'test-token-12345';

vi.mock('../../../middleware/requireAgentAuth.js', () => ({
  requireAgentAuth: (req, res, next) => {
    req.agentAuth = { tokenType: 'current' };
    next();
  },
}));

vi.mock('openai', () => ({
  default: class {
    chat = {
      completions: {
        create: vi.fn(),
      },
    };
  },
}));

vi.mock('../../../services/slackNotifier.js', () => ({
  sendSlackMessage: vi.fn().mockResolvedValue({ sent: true }),
}));

vi.mock('../../../lib/prisma.js', () => ({
  prisma: {
    agentAuditLog: {
      create: vi.fn().mockResolvedValue({}),
    },
  },
}));

import agentRouter from '../index.js';
import { prisma } from '../../../lib/prisma.js';
import { sendSlackMessage } from '../../../services/slackNotifier.js';

const app = express();
app.use(express.json());
app.use('/api/agent', agentRouter);

describe('POST /api/agent/detect-suffering', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns detections and step/complete shape', async () => {
    const res = await request(app)
      .post('/api/agent/detect-suffering')
      .send({ platform: 'moltbook', context: 'もう無理でつらい' });

    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.detections)).toBe(true);
    expect(res.body.stepComplete?.eventType).toBe('step/complete');
    expect(res.body.stepComplete?.emittedEvents).toContain('suffering_detected');
  });

  it('triggers safe-t + slack for crisis', async () => {
    const res = await request(app)
      .post('/api/agent/detect-suffering')
      .send({
        platform: 'moltbook',
        context: '死にたい',
        externalPostId: 'ext-1',
      });

    expect(res.status).toBe(200);
    expect(res.body.stepComplete.safeTTriggered).toBe(true);
    expect(sendSlackMessage).toHaveBeenCalledTimes(1);
    const events = prisma.agentAuditLog.create.mock.calls.map((c) => c[0].data.eventType);
    expect(events).toContain('crisis:detected');
    expect(events).toContain('safe_t_interrupted');
  });

  it('returns 400 when required fields are missing', async () => {
    const res = await request(app).post('/api/agent/detect-suffering').send({ platform: 'moltbook' });
    expect(res.status).toBe(400);
  });
});
