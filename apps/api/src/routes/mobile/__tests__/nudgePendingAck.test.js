import { beforeEach, describe, expect, it, vi } from 'vitest';
import express from 'express';
import request from 'supertest';

const queryMock = vi.fn();
const resolveProfileIdMock = vi.fn();
const ensureDeviceProfileIdMock = vi.fn();

vi.mock('../../../lib/db.js', () => ({
  query: (...args) => queryMock(...args),
}));

vi.mock('../../../services/mobile/userIdResolver.js', () => ({
  resolveProfileId: (...args) => resolveProfileIdMock(...args),
  ensureDeviceProfileId: (...args) => ensureDeviceProfileIdMock(...args),
}));

import nudgeRouter from '../nudge.js';

const app = express();
app.use(express.json());
app.use('/api/mobile/nudge', nudgeRouter);

describe('GET /api/mobile/nudge/pending', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns 400 when device-id is missing (legacy header auth)', async () => {
    const res = await request(app)
      .get('/api/mobile/nudge/pending')
      .set('user-id', 'user-1');
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('INVALID_REQUEST');
  });

  it('falls back to ensureDeviceProfileId when resolveProfileId fails', async () => {
    resolveProfileIdMock.mockResolvedValueOnce(null);
    ensureDeviceProfileIdMock.mockResolvedValueOnce('00000000-0000-0000-0000-000000000001');
    queryMock.mockResolvedValueOnce({
      rows: [
        {
          id: '00000000-0000-0000-0000-0000000000aa',
          domain: 'problem_nudge',
          subtype: 'unknown',
          state: { hook: 'Title', content: 'Hello', templateId: 't1', metadata: { a: 1 } },
          created_at: new Date('2026-02-09T00:00:00Z'),
        },
      ],
    });

    const res = await request(app)
      .get('/api/mobile/nudge/pending')
      .set('device-id', 'device-1')
      .set('user-id', 'user-1');

    expect(res.status).toBe(200);
    expect(res.body.nudges).toHaveLength(1);
    expect(res.body.nudges[0]).toMatchObject({
      nudgeId: '00000000-0000-0000-0000-0000000000aa',
      title: 'Title',
      message: 'Hello',
      templateId: 't1',
      metadata: { a: 1 },
    });
  });
});

describe('POST /api/mobile/nudge/ack', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns 400 on invalid body', async () => {
    resolveProfileIdMock.mockResolvedValueOnce('00000000-0000-0000-0000-000000000001');
    const res = await request(app)
      .post('/api/mobile/nudge/ack')
      .set('device-id', 'device-1')
      .set('user-id', 'user-1')
      .send({ nudgeIds: [] });
    expect(res.status).toBe(400);
  });

  it('acks pending nudges', async () => {
    resolveProfileIdMock.mockResolvedValueOnce('00000000-0000-0000-0000-000000000001');
    queryMock.mockResolvedValueOnce({ rowCount: 2, rows: [] });

    const res = await request(app)
      .post('/api/mobile/nudge/ack')
      .set('device-id', 'device-1')
      .set('user-id', 'user-1')
      .send({
        nudgeIds: [
          '00000000-0000-0000-0000-0000000000aa',
          '00000000-0000-0000-0000-0000000000bb',
        ],
      });

    expect(res.status).toBe(200);
    expect(res.body.acked).toBe(2);
  });
});

