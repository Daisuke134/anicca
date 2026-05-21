import { beforeEach, describe, expect, it, vi } from 'vitest';
import express from 'express';
import request from 'supertest';

import { prismaMock } from '../../../test/setup.js';

const requireAuthMock = vi.fn();
const resolveProfileIdMock = vi.fn();
const ensureDeviceProfileIdMock = vi.fn(); // used by other endpoints in this router

vi.mock('../../../middleware/requireAuth.js', () => ({
  default: (...args) => requireAuthMock(...args),
}));

vi.mock('../../../services/mobile/userIdResolver.js', () => ({
  resolveProfileId: (...args) => resolveProfileIdMock(...args),
  ensureDeviceProfileId: (...args) => ensureDeviceProfileIdMock(...args),
}));

import nudgeRouter from '../nudge.js';

const app = express();
app.use(express.json());
app.use('/api/mobile/nudge', nudgeRouter);

describe('GET /api/mobile/nudge/delivery/:id', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.PUSH_ENV = 'dev';
    prismaMock.pushToken.findUnique.mockResolvedValue({
      profileId: '00000000-0000-0000-0000-000000000001',
      disabledAt: null,
    });
    prismaMock.nudgeDelivery.findFirst.mockResolvedValue({
      id: '11111111-1111-1111-1111-111111111111',
      problemType: 'anxiety',
      scheduledTime: '07:30',
      deliveryDayLocal: new Date('2026-02-13T00:00:00.000Z'),
      timezone: 'America/Los_Angeles',
      lang: 'en',
      variantIndex: 0,
      messageTitle: 'You are safe',
      messageBody: 'Morning: You are safe',
      messageDetail: 'Morning: Take one breath',
    });
  });

  it('returns 400 when device-id missing', async () => {
    const res = await request(app).get('/api/mobile/nudge/delivery/11111111-1111-1111-1111-111111111111');
    expect(res.status).toBe(400);
  });

  it('returns 400 when id is not uuid (even if device-id present)', async () => {
    const res = await request(app)
      .get('/api/mobile/nudge/delivery/111')
      .set('device-id', 'device-1');
    expect(res.status).toBe(400);
    expect(prismaMock.pushToken.findUnique).not.toHaveBeenCalled();
    expect(prismaMock.nudgeDelivery.findFirst).not.toHaveBeenCalled();
  });

  it('returns 404 when delivery not found', async () => {
    prismaMock.nudgeDelivery.findFirst.mockResolvedValueOnce(null);
    const res = await request(app)
      .get('/api/mobile/nudge/delivery/11111111-1111-1111-1111-111111111111')
      .set('device-id', 'device-1');
    expect(res.status).toBe(404);
  });

  it('returns delivery snapshot for device-bound request', async () => {
    const res = await request(app)
      .get('/api/mobile/nudge/delivery/11111111-1111-1111-1111-111111111111')
      .set('device-id', 'device-1');
    expect(res.status).toBe(200);
    expect(res.body.problemType).toBe('anxiety');
    expect(res.body.hook).toBeTruthy();
    expect(res.body.detail).toBeTruthy();
    expect(ensureDeviceProfileIdMock).not.toHaveBeenCalled();
  });

  it('returns 401 when no active push token for device', async () => {
    prismaMock.pushToken.findUnique.mockResolvedValueOnce(null);
    const res = await request(app)
      .get('/api/mobile/nudge/delivery/11111111-1111-1111-1111-111111111111')
      .set('device-id', 'device-1');
    expect(res.status).toBe(401);
  });

  it('with Bearer validates profile matches push token profile', async () => {
    requireAuthMock.mockResolvedValueOnce({ sub: 'apple-user-1' });
    resolveProfileIdMock.mockResolvedValueOnce('00000000-0000-0000-0000-000000000001');
    const res = await request(app)
      .get('/api/mobile/nudge/delivery/11111111-1111-1111-1111-111111111111')
      .set('device-id', 'device-1')
      .set('Authorization', 'Bearer xxx');
    expect(res.status).toBe(200);
    expect(resolveProfileIdMock).toHaveBeenCalledWith('apple-user-1');
    expect(ensureDeviceProfileIdMock).not.toHaveBeenCalled();
  });

  it('returns 401 when Bearer is present but cannot resolve profile', async () => {
    requireAuthMock.mockResolvedValueOnce({ sub: 'apple-user-1' });
    resolveProfileIdMock.mockResolvedValueOnce(null);
    const res = await request(app)
      .get('/api/mobile/nudge/delivery/11111111-1111-1111-1111-111111111111')
      .set('device-id', 'device-1')
      .set('Authorization', 'Bearer xxx');
    expect(res.status).toBe(401);
  });

  it('returns 403 when Bearer resolves to different profile than push token', async () => {
    requireAuthMock.mockResolvedValueOnce({ sub: 'apple-user-1' });
    resolveProfileIdMock.mockResolvedValueOnce('00000000-0000-0000-0000-000000000999');
    const res = await request(app)
      .get('/api/mobile/nudge/delivery/11111111-1111-1111-1111-111111111111')
      .set('device-id', 'device-1')
      .set('Authorization', 'Bearer xxx');
    expect(res.status).toBe(403);
  });

  it('returns 500 when push token lookup fails', async () => {
    prismaMock.pushToken.findUnique.mockRejectedValueOnce(new Error('db down'));
    const res = await request(app)
      .get('/api/mobile/nudge/delivery/11111111-1111-1111-1111-111111111111')
      .set('device-id', 'device-1');
    expect(res.status).toBe(500);
  });
});
