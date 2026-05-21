import { beforeEach, describe, expect, it, vi } from 'vitest';
import express from 'express';
import request from 'supertest';

import { prismaMock } from '../../../test/setup.js';

const requireAuthMock = vi.fn();
const resolveProfileIdMock = vi.fn();
const ensureDeviceProfileIdMock = vi.fn();
const getEntitlementStateMock = vi.fn();

const apnsMocks = vi.hoisted(() => {
  class MockApnsError extends Error {
    constructor({ status, reason }) {
      super(`APNs error: ${status} ${reason || ''}`.trim());
      this.name = 'ApnsError';
      this.status = status;
      this.reason = reason || null;
    }
  }
  const client = {
    // eslint-disable-next-line no-underscore-dangle
    _getJwt: vi.fn(),
    sendAlert: vi.fn(),
  };
  return { MockApnsError, client };
});

vi.mock('../../../services/apns/apnsClient.js', () => ({
  ApnsError: apnsMocks.MockApnsError,
  default: class MockApnsClient {
    static fromEnv() {
      return apnsMocks.client;
    }
  },
}));

vi.mock('../../../middleware/requireAuth.js', () => ({
  default: (...args) => requireAuthMock(...args),
}));

vi.mock('../../../services/mobile/userIdResolver.js', () => ({
  resolveProfileId: (...args) => resolveProfileIdMock(...args),
  ensureDeviceProfileId: (...args) => ensureDeviceProfileIdMock(...args),
}));

vi.mock('../../../services/subscriptionStore.js', () => ({
  getEntitlementState: (...args) => getEntitlementStateMock(...args),
}));

import pushRouter from '../push.js';

const app = express();
app.use(express.json());
app.use('/api/mobile/push', pushRouter);

describe('POST /api/mobile/push/token', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env.PUSH_ENV;
    delete process.env.PROBLEM_NUDGE_APNS_SENDER_ENABLED;
    delete process.env.APNS_ENDPOINT;

    // Default env alignment for APNs probe gate.
    process.env.PUSH_ENV = 'dev';
    process.env.APNS_ENDPOINT = 'development';

    // Default mocks
    prismaMock.$transaction.mockImplementation(async (fn) => fn(prismaMock));
    ensureDeviceProfileIdMock.mockResolvedValue('00000000-0000-0000-0000-000000000001');

    prismaMock.userSetting.upsert.mockResolvedValue({});
    prismaMock.userSetting.findUnique.mockResolvedValue({ nudgeDay0LocalDate: null, timezone: 'UTC', nudgeDay0Source: null });
    prismaMock.profile.findUnique.mockResolvedValue({ createdAt: new Date('2026-02-01T00:00:00.000Z') });

    prismaMock.pushToken.findUnique.mockResolvedValue(null);
    prismaMock.pushToken.upsert.mockResolvedValue({});

    // Default: free users are not eligible for remote Problem nudges.
    getEntitlementStateMock.mockResolvedValue({ plan: 'free' });
  });

  it('returns 400 when device-id missing', async () => {
    const res = await request(app).post('/api/mobile/push/token').send({ token: 'a'.repeat(64) });
    expect(res.status).toBe(400);
  });

  it('returns 400 when token invalid', async () => {
    const res = await request(app)
      .post('/api/mobile/push/token')
      .set('device-id', 'device-1')
      .send({ token: 'not-hex' });
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe('INVALID_TOKEN');
  });

  it('upserts token by device/env and clears disabled', async () => {
    const token = 'a'.repeat(64);
    const res = await request(app)
      .post('/api/mobile/push/token')
      .set('device-id', 'device-1')
      .set('x-timezone', 'America/Los_Angeles')
      .set('x-lang', 'ja')
      .send({ token });

    expect(res.status).toBe(200);
    expect(res.body.ok).toBe(true);
    expect(res.body.remoteDeliveryEnabled).toBe(false);
    expect(prismaMock.pushToken.upsert).toHaveBeenCalledTimes(1);
  });

  it('remoteDeliveryEnabled becomes true when APNs probe returns 400', async () => {
    process.env.PROBLEM_NUDGE_APNS_SENDER_ENABLED = 'true';
    apnsMocks.client._getJwt.mockResolvedValueOnce('jwt');
    apnsMocks.client.sendAlert.mockRejectedValueOnce(new apnsMocks.MockApnsError({ status: 400, reason: 'BadDeviceToken' }));

    const res = await request(app)
      .post('/api/mobile/push/token')
      .set('device-id', 'device-1')
      .send({ token: 'a'.repeat(64) });

    expect(res.status).toBe(200);
    expect(res.body.remoteDeliveryEnabled).toBe(true);
    // Problem nudges are delivered via APNs for all users once remote is enabled.
    expect(res.body.remoteProblemNudgesEnabled).toBe(true);
  });

  it('remoteProblemNudgesEnabled does not depend on entitlement (free/pro)', async () => {
    process.env.PROBLEM_NUDGE_APNS_SENDER_ENABLED = 'true';
    apnsMocks.client._getJwt.mockResolvedValueOnce('jwt');
    apnsMocks.client.sendAlert.mockRejectedValueOnce(new apnsMocks.MockApnsError({ status: 400, reason: 'BadDeviceToken' }));

    const res = await request(app)
      .post('/api/mobile/push/token')
      .set('device-id', 'device-1')
      .send({ token: 'a'.repeat(64) });

    expect(res.status).toBe(200);
    expect(res.body.remoteDeliveryEnabled).toBe(true);
    expect(res.body.remoteProblemNudgesEnabled).toBe(true);
  });

  it('remoteDeliveryEnabled stays false when APNs probe returns 400 but reason is config-related', async () => {
    process.env.PROBLEM_NUDGE_APNS_SENDER_ENABLED = 'true';
    apnsMocks.client._getJwt.mockResolvedValueOnce('jwt');
    apnsMocks.client.sendAlert.mockRejectedValueOnce(new apnsMocks.MockApnsError({ status: 400, reason: 'BadTopic' }));

    const res = await request(app)
      .post('/api/mobile/push/token')
      .set('device-id', 'device-1')
      .send({ token: 'a'.repeat(64) });

    expect(res.status).toBe(200);
    expect(res.body.remoteDeliveryEnabled).toBe(false);
  });

  it('remoteDeliveryEnabled becomes false when APNs probe returns 403', async () => {
    process.env.PROBLEM_NUDGE_APNS_SENDER_ENABLED = 'true';
    apnsMocks.client._getJwt.mockResolvedValueOnce('jwt');
    apnsMocks.client.sendAlert.mockRejectedValueOnce(new apnsMocks.MockApnsError({ status: 403, reason: 'InvalidProviderToken' }));

    const res = await request(app)
      .post('/api/mobile/push/token')
      .set('device-id', 'device-1')
      .send({ token: 'a'.repeat(64) });

    expect(res.status).toBe(200);
    expect(res.body.remoteDeliveryEnabled).toBe(false);
  });

  it('ignores invalid timezone instead of 500', async () => {
    const token = 'd'.repeat(64);
    const res = await request(app)
      .post('/api/mobile/push/token')
      .set('device-id', 'device-1')
      .set('x-timezone', 'Not/AZone')
      .send({ token });
    expect(res.status).toBe(200);
    expect(res.body.remoteDeliveryEnabled).toBe(false);
    // Should not write invalid tz
    expect(prismaMock.userSetting.upsert).not.toHaveBeenCalledWith(expect.objectContaining({
      update: expect.objectContaining({ timezone: 'Not/AZone' }),
    }));
  });

  it('deletes conflicting token/env row for other device', async () => {
    const token = 'b'.repeat(64);
    prismaMock.pushToken.findUnique.mockResolvedValueOnce({ id: 'tok-1', deviceId: 'device-other' });

    const res = await request(app)
      .post('/api/mobile/push/token')
      .set('device-id', 'device-1')
      .send({ token });

    expect(res.status).toBe(200);
    expect(prismaMock.pushToken.delete).toHaveBeenCalledWith({ where: { id: 'tok-1' } });
  });

  it('with Bearer token uses resolveProfileId (auth-based binding)', async () => {
    const token = 'c'.repeat(64);
    requireAuthMock.mockResolvedValueOnce({ sub: 'apple-user-1' });
    resolveProfileIdMock.mockResolvedValueOnce('00000000-0000-0000-0000-000000000999');

    const res = await request(app)
      .post('/api/mobile/push/token')
      .set('device-id', 'device-1')
      .set('Authorization', 'Bearer xxx')
      .send({ token });

    expect(res.status).toBe(200);
    expect(resolveProfileIdMock).toHaveBeenCalledWith('apple-user-1');
  });

  it('with Bearer token returns 401 if profile cannot be resolved (no device fallback)', async () => {
    const token = 'c'.repeat(64);
    requireAuthMock.mockResolvedValueOnce({ sub: 'apple-user-1' });
    resolveProfileIdMock.mockResolvedValueOnce(null);

    const res = await request(app)
      .post('/api/mobile/push/token')
      .set('device-id', 'device-1')
      .set('Authorization', 'Bearer xxx')
      .send({ token });

    expect(res.status).toBe(401);
    expect(ensureDeviceProfileIdMock).not.toHaveBeenCalled();
  });
});
