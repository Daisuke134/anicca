import { beforeEach, describe, expect, it, vi } from 'vitest';
import express from 'express';
import request from 'supertest';

process.env.INTERNAL_API_TOKEN = 'internal-token';
process.env.NUDGE_DAILY_QUOTA = '3';
delete process.env.NUDGE_SEND_KILL_SWITCH;

const queryMock = vi.fn();
const resolveProfileIdMock = vi.fn();

vi.mock('../../../lib/db.js', () => ({
  query: (...args) => queryMock(...args),
}));

vi.mock('../../../services/mobile/userIdResolver.js', () => ({
  resolveProfileId: (...args) => resolveProfileIdMock(...args),
}));

import nudgeRouter from '../nudge.js';

const app = express();
app.use(express.json());
app.use('/api/mobile/nudge', nudgeRouter);

describe('POST /api/mobile/nudge/send', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.INTERNAL_API_TOKEN = 'internal-token';
    process.env.NUDGE_DAILY_QUOTA = '3';
    delete process.env.NUDGE_SEND_KILL_SWITCH;
  });

  it('returns 401 without internal auth token', async () => {
    const res = await request(app).post('/api/mobile/nudge/send').send({
      userId: 'user-1',
      message: 'test',
    });
    expect(res.status).toBe(401);
  });

  it('returns 503 when kill switch is enabled', async () => {
    process.env.NUDGE_SEND_KILL_SWITCH = 'true';
    const res = await request(app)
      .post('/api/mobile/nudge/send')
      .set('Authorization', 'Bearer internal-token')
      .send({
        userId: 'user-1',
        message: 'test',
      });
    expect(res.status).toBe(503);
    expect(res.body.error.code).toBe('KILL_SWITCH_ENABLED');
  });

  it('returns 429 when daily quota is exceeded', async () => {
    resolveProfileIdMock.mockResolvedValueOnce('00000000-0000-0000-0000-000000000001');
    queryMock
      .mockResolvedValueOnce({ rowCount: 1, rows: [] }) // ensure profile insert
      .mockResolvedValueOnce({ rows: [{ count: 3 }] }); // quota count

    const res = await request(app)
      .post('/api/mobile/nudge/send')
      .set('Authorization', 'Bearer internal-token')
      .send({
        userId: 'user-1',
        message: 'test',
      });

    expect(res.status).toBe(429);
    expect(res.body.error.code).toBe('DAILY_QUOTA_EXCEEDED');
    expect(queryMock).toHaveBeenCalledTimes(2);
  });

  it('stores send_nudge event and returns sent=true', async () => {
    resolveProfileIdMock.mockResolvedValueOnce('00000000-0000-0000-0000-000000000001');
    queryMock
      .mockResolvedValueOnce({ rowCount: 1, rows: [] }) // ensure profile insert
      .mockResolvedValueOnce({ rows: [] }) // dedupe lookup
      .mockResolvedValueOnce({ rows: [{ count: 1 }] }) // quota count
      .mockResolvedValueOnce({ rowCount: 1, rows: [] });

    const res = await request(app)
      .post('/api/mobile/nudge/send')
      .set('Authorization', 'Bearer internal-token')
      .send({
        userId: 'user-1',
        message: 'Take one small breath',
        title: 'Pause',
        problemType: 'anxiety',
        dedupeKey: 'x:post123',
      });

    expect(res.status).toBe(200);
    expect(res.body.sent).toBe(true);
    // profile ensure + dedupe lookup + count + insert
    expect(queryMock).toHaveBeenCalledTimes(4);
  });
});
