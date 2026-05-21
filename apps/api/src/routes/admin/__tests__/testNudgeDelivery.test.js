import { beforeEach, describe, expect, it, vi } from 'vitest';
import express from 'express';
import request from 'supertest';

import { prismaMock } from '../../../test/setup.js';

const ensureDeviceProfileIdMock = vi.fn();
vi.mock('../../../services/mobile/userIdResolver.js', () => ({
  ensureDeviceProfileId: (...args) => ensureDeviceProfileIdMock(...args),
}));

import adminTestRouter from '../test.js';

const app = express();
app.use(express.json());
app.use('/api/admin/test', adminTestRouter);

describe('POST /api/admin/test/nudge-delivery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.INTERNAL_API_TOKEN = 'internal-token';

    ensureDeviceProfileIdMock.mockResolvedValue('00000000-0000-0000-0000-000000000001');
    prismaMock.userSetting.findUnique.mockResolvedValue({
      timezone: 'UTC',
      language: 'en',
      nudgeDay0LocalDate: new Date('2026-02-01T00:00:00.000Z'),
    });
    prismaMock.nudgeDelivery.create.mockResolvedValue({ id: '11111111-1111-1111-1111-111111111111' });
  });

  it('requires internal auth', async () => {
    const res = await request(app).post('/api/admin/test/nudge-delivery').send({});
    expect(res.status).toBe(401);
  });

  it('seeds and returns id', async () => {
    const res = await request(app)
      .post('/api/admin/test/nudge-delivery')
      .set('Authorization', 'Bearer internal-token')
      .send({
        deviceId: 'device-1',
        problemType: 'anxiety',
        scheduledTime: '07:30',
        nowUtcIso: '2026-02-13T15:30:00.000Z',
      });
    expect(res.status).toBe(200);
    expect(res.body.ok).toBe(true);
    expect(res.body.id).toBeTruthy();
  });
});

