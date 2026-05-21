import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../services/subscriptionStore.js', () => ({
  getEntitlementState: vi.fn(async () => ({ plan: 'pro', status: 'active', currentPeriodEnd: null })),
}));

import { prismaMock } from '../../test/setup.js';

import { isSlotDue, effectiveDeliveryDayLocal, ymdFromDateOnly, selectFreeDailySlots, runProblemNudgeApnsSender } from '../problemNudgeApnsSenderJob.js';
import { ApnsError } from '../../services/apns/apnsClient.js';
import { getEntitlementState } from '../../services/subscriptionStore.js';

describe('problemNudgeApnsSenderJob helpers', () => {
  it('isSlotDue matches within 30min window', () => {
    const nowUtc = new Date('2026-02-13T07:35:00.000Z');
    expect(isSlotDue({ nowUtc, timezone: 'UTC', scheduledTime: '07:30' })).toBe(true);
    expect(isSlotDue({ nowUtc, timezone: 'UTC', scheduledTime: '07:00' })).toBe(false);
    expect(isSlotDue({ nowUtc, timezone: 'UTC', scheduledTime: '07:36' })).toBe(false);
  });

  it('isSlotDue handles day-wrap window (e.g. 23:45 due at 00:05)', () => {
    const nowUtc = new Date('2026-02-13T00:05:00.000Z');
    expect(isSlotDue({ nowUtc, timezone: 'UTC', scheduledTime: '23:45' })).toBe(true);
  });

  it('effectiveDeliveryDayLocal uses previous local date for staying_up_late 00:00/01:00', () => {
    const nowUtc = new Date('2026-02-13T08:05:00.000Z'); // 00:05 in America/Los_Angeles (PST)
    const tz = 'America/Los_Angeles';
    const a = effectiveDeliveryDayLocal({ nowUtc, timezone: tz, problemType: 'staying_up_late', scheduledTime: '00:00' });
    const b = effectiveDeliveryDayLocal({ nowUtc, timezone: tz, problemType: 'staying_up_late', scheduledTime: '22:00' });
    expect(a).not.toBe(b);
  });

  it('ymdFromDateOnly does not shift date-only values for non-UTC timezones', () => {
    // Regression test: previously we ran DATE through toLocalDateString(Date, timezone),
    // which shifted (e.g. America/Los_Angeles) and broke dayIndex.
    expect(ymdFromDateOnly(new Date('2026-02-13T00:00:00.000Z'))).toBe('2026-02-13');
  });

  it('selectFreeDailySlots picks 3 stable slots closest to 09:00/14:00/20:00', () => {
    const out = selectFreeDailySlots(['obsessive', 'rumination', 'staying_up_late']);
    expect(out).toHaveLength(3);
    expect(out).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ problemType: 'obsessive', scheduledTime: '09:00' }),
        expect.objectContaining({ problemType: 'rumination', scheduledTime: '14:00' }),
        expect.objectContaining({ problemType: 'staying_up_late', scheduledTime: '20:00' }),
      ])
    );
  });
});

describe('runProblemNudgeApnsSender', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.PUSH_ENV = 'dev';
    process.env.APNS_ENDPOINT = 'development';

    prismaMock.$executeRaw.mockResolvedValue(0);
    prismaMock.$transaction.mockImplementation(async fn => fn(prismaMock));

    prismaMock.pushToken.findMany.mockResolvedValue([
      { id: 'ptok-1', profileId: '00000000-0000-0000-0000-000000000001', deviceId: 'device-1', token: 'a'.repeat(64) },
    ]);
    prismaMock.userSetting.findUnique.mockResolvedValue({
      notificationsEnabled: true,
      timezone: 'UTC',
      language: 'en',
    });
    prismaMock.mobileProfile.findMany.mockResolvedValue([{ profile: { struggles: ['anxiety'] } }]);

    prismaMock.userSetting.upsert.mockResolvedValue({
      nudgeDay0LocalDate: new Date('2026-02-01T00:00:00.000Z'),
      timezone: 'UTC',
      nudgeDay0Source: 'profile_created_at',
    });
    prismaMock.profile.findUnique.mockResolvedValue({ createdAt: new Date('2026-02-01T00:00:00.000Z') });

    prismaMock.nudgeDelivery.findFirst.mockResolvedValue(null);
    prismaMock.nudgeDelivery.count.mockResolvedValue(0);
    prismaMock.nudgeDelivery.create.mockResolvedValue({ id: '11111111-1111-1111-1111-111111111111' });
    prismaMock.nudgeDeliverySend.findMany.mockResolvedValue([]);
    prismaMock.nudgeDeliverySend.findUnique.mockResolvedValue(null);
    prismaMock.nudgeDeliverySend.create.mockResolvedValue({ id: 'send-1', status: 'queued', nextAttemptAt: null, attemptCount: 0 });
    prismaMock.nudgeDeliverySend.updateMany.mockResolvedValue({ count: 1 });
    prismaMock.nudgeDeliverySend.update.mockResolvedValue({});
    prismaMock.pushToken.update.mockResolvedValue({});
  });

  it('queues and sends one due delivery', async () => {
    const apnsClient = {
      sendAlert: vi.fn().mockResolvedValue({ ok: true, apnsId: 'apns-1' }),
    };

    const nowUtc = new Date('2026-02-13T12:20:00.000Z'); // 12:15 anxiety slot due at 12:20
    const out = await runProblemNudgeApnsSender(nowUtc, { apnsClient });
    expect(out.ok).toBe(true);
    expect(apnsClient.sendAlert).toHaveBeenCalledTimes(1);
    expect(prismaMock.nudgeDelivery.create).toHaveBeenCalledTimes(1);
    expect(prismaMock.nudgeDeliverySend.create).toHaveBeenCalledTimes(1);
    expect(prismaMock.nudgeDeliverySend.updateMany).toHaveBeenCalledTimes(1);
    expect(prismaMock.nudgeDeliverySend.update).toHaveBeenCalledTimes(1);
  });

  it('free users send only the selected 3 daily slots (example: 14:00 rumination slot)', async () => {
    getEntitlementState.mockResolvedValueOnce({ plan: 'free', status: 'active', currentPeriodEnd: null });

    prismaMock.mobileProfile.findMany.mockResolvedValueOnce([{ profile: { struggles: ['obsessive', 'rumination', 'staying_up_late'] } }]);

    const apnsClient = {
      sendAlert: vi.fn().mockResolvedValue({ ok: true, apnsId: 'apns-1' }),
    };

    // 14:10 UTC is within 30 minutes of 14:00 UTC.
    const nowUtc = new Date('2026-02-13T14:10:00.000Z');
    const out = await runProblemNudgeApnsSender(nowUtc, { apnsClient });
    expect(out.ok).toBe(true);
    expect(apnsClient.sendAlert).toHaveBeenCalledTimes(1);
    expect(apnsClient.sendAlert.mock.calls[0][0].payload.problemType).toBe('rumination');
    expect(apnsClient.sendAlert.mock.calls[0][0].payload.scheduledTime).toBe('14:00');
  });

  it('enforces free cap even if struggles change mid-day (never creates >3 deliveries per day)', async () => {
    getEntitlementState.mockResolvedValue({ plan: 'free', status: 'active', currentPeriodEnd: null });

    // Struggles change across runs.
    prismaMock.mobileProfile.findMany
      .mockResolvedValueOnce([{ profile: { struggles: ['anxiety'] } }])
      .mockResolvedValueOnce([{ profile: { struggles: ['bad_mouthing'] } }])
      .mockResolvedValueOnce([{ profile: { struggles: ['anxiety'] } }])
      .mockResolvedValueOnce([{ profile: { struggles: ['bad_mouthing'] } }]);

    const apnsClient = {
      sendAlert: vi.fn().mockResolvedValue({ ok: true, apnsId: 'apns-1' }),
    };

    const deliveries = new Map(); // key -> deliveryId
    let deliverySeq = 0;
    prismaMock.nudgeDelivery.findFirst.mockImplementation(async ({ where }) => {
      const key = `${where.profileId}|${where.problemType}|${where.scheduledTime}|${where.deliveryDayLocal.toISOString()}`;
      const id = deliveries.get(key);
      return id ? { id } : null;
    });
    prismaMock.nudgeDelivery.create.mockImplementation(async ({ data }) => {
      const key = `${data.profileId}|${data.problemType}|${data.scheduledTime}|${data.deliveryDayLocal.toISOString()}`;
      const id = `delivery-${++deliverySeq}`;
      deliveries.set(key, id);
      return { id };
    });
    prismaMock.nudgeDelivery.count.mockImplementation(async ({ where }) => {
      const suffix = where.deliveryDayLocal.toISOString();
      let c = 0;
      for (const k of deliveries.keys()) {
        if (k.endsWith(suffix)) c += 1;
      }
      return c;
    });

    const sendRows = new Map(); // key -> row
    let sendSeq = 0;
    prismaMock.nudgeDeliverySend.findUnique.mockImplementation(async ({ where }) => {
      const key = `${where.deliveryId_pushTokenId.deliveryId}|${where.deliveryId_pushTokenId.pushTokenId}`;
      return sendRows.get(key) || null;
    });
    prismaMock.nudgeDeliverySend.create.mockImplementation(async ({ data }) => {
      const key = `${data.deliveryId}|${data.pushTokenId}`;
      const row = { id: `send-${++sendSeq}`, status: 'queued', nextAttemptAt: null, attemptCount: 0 };
      sendRows.set(key, row);
      return row;
    });
    prismaMock.nudgeDeliverySend.updateMany.mockResolvedValue({ count: 1 });
    prismaMock.nudgeDeliverySend.update.mockResolvedValue({});

    await runProblemNudgeApnsSender(new Date('2026-02-13T07:35:00.000Z'), { apnsClient }); // anxiety 07:30 due
    await runProblemNudgeApnsSender(new Date('2026-02-13T09:35:00.000Z'), { apnsClient }); // bad_mouthing 09:30 due
    await runProblemNudgeApnsSender(new Date('2026-02-13T12:20:00.000Z'), { apnsClient }); // anxiety 12:15 due
    await runProblemNudgeApnsSender(new Date('2026-02-13T14:35:00.000Z'), { apnsClient }); // bad_mouthing 14:30 due (must be capped)

    expect(deliveries.size).toBe(3);
  });

  it('blocks delivery and stops run on config/auth APNs errors (e.g. 403 BadTopic)', async () => {
    prismaMock.pushToken.findMany.mockResolvedValueOnce([
      { id: 'ptok-1', profileId: '00000000-0000-0000-0000-000000000001', deviceId: 'device-1', token: 'a'.repeat(64) },
      { id: 'ptok-2', profileId: '00000000-0000-0000-0000-000000000002', deviceId: 'device-2', token: 'b'.repeat(64) },
    ]);

    const apnsClient = {
      sendAlert: vi.fn().mockRejectedValue(new ApnsError({ status: 403, reason: 'BadTopic' })),
    };

    const nowUtc = new Date('2026-02-13T12:20:00.000Z'); // 12:15 anxiety slot due at 12:20
    const out1 = await runProblemNudgeApnsSender(nowUtc, { apnsClient });
    expect(out1.ok).toBe(true);
    expect(apnsClient.sendAlert).toHaveBeenCalledTimes(1);
    expect(prismaMock.nudgeDeliverySend.update).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ status: 'failed' }),
      })
    );

    // Next run should skip sending within backoff window (no repeated APNs hammering).
    apnsClient.sendAlert.mockClear();
    prismaMock.nudgeDeliverySend.findUnique.mockResolvedValueOnce({
      id: 'send-1',
      status: 'failed',
      nextAttemptAt: new Date(nowUtc.getTime() + 5 * 60 * 1000),
      attemptCount: 1,
    });
    const out2 = await runProblemNudgeApnsSender(nowUtc, { apnsClient });
    expect(out2.ok).toBe(true);
    expect(apnsClient.sendAlert).toHaveBeenCalledTimes(0);
  });

  it('sends to multiple devices for the same profile (multi-device safe)', async () => {
    prismaMock.pushToken.findMany.mockResolvedValueOnce([
      { id: 'ptok-1', profileId: '00000000-0000-0000-0000-000000000001', deviceId: 'device-1', token: 'a'.repeat(64) },
      { id: 'ptok-2', profileId: '00000000-0000-0000-0000-000000000001', deviceId: 'device-2', token: 'b'.repeat(64) },
    ]);
    prismaMock.mobileProfile.findMany.mockResolvedValueOnce([{ profile: { struggles: ['anxiety'] } }, { profile: { struggles: ['anxiety'] } }]);

    const apnsClient = {
      sendAlert: vi.fn().mockResolvedValue({ ok: true, apnsId: 'apns-1' }),
    };

    prismaMock.nudgeDelivery.findFirst
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({ id: '11111111-1111-1111-1111-111111111111' });

    prismaMock.nudgeDeliverySend.create
      .mockResolvedValueOnce({ id: 'send-1', status: 'queued', nextAttemptAt: null, attemptCount: 0 })
      .mockResolvedValueOnce({ id: 'send-2', status: 'queued', nextAttemptAt: null, attemptCount: 0 });

    const nowUtc = new Date('2026-02-13T12:20:00.000Z');
    const out = await runProblemNudgeApnsSender(nowUtc, { apnsClient });
    expect(out.ok).toBe(true);
    expect(apnsClient.sendAlert).toHaveBeenCalledTimes(2);
  });

  it('defaults to free cap when entitlement lookup fails (still sends, no over-send)', async () => {
    getEntitlementState.mockRejectedValueOnce(new Error('db down'));

    const apnsClient = {
      sendAlert: vi.fn(),
    };

    const nowUtc = new Date('2026-02-13T12:20:00.000Z');
    const out = await runProblemNudgeApnsSender(nowUtc, { apnsClient });
    expect(out.ok).toBe(true);
    expect(apnsClient.sendAlert).toHaveBeenCalledTimes(1);
  });

  it('day-wrap late-night slot uses previous deliveryDayLocal (does not block same-day slot)', async () => {
    // Use a slot at 23:45 (porn_addiction) and send it at 00:05.
    prismaMock.mobileProfile.findMany.mockResolvedValue([{ profile: { struggles: ['porn_addiction'] } }]);

    const apnsClient = {
      sendAlert: vi.fn().mockResolvedValue({ ok: true, apnsId: 'apns-1' }),
    };

    const deliveries = new Map(); // key -> deliveryId
    let deliverySeq = 0;
    prismaMock.nudgeDelivery.findFirst.mockImplementation(async ({ where }) => {
      const key = `${where.profileId}|${where.problemType}|${where.scheduledTime}|${where.deliveryDayLocal.toISOString()}`;
      const id = deliveries.get(key);
      return id ? { id } : null;
    });
    prismaMock.nudgeDelivery.create.mockImplementation(async ({ data }) => {
      const key = `${data.profileId}|${data.problemType}|${data.scheduledTime}|${data.deliveryDayLocal.toISOString()}`;
      const id = `delivery-${++deliverySeq}`;
      deliveries.set(key, id);
      return { id };
    });

    const sendRows = new Map(); // key -> row
    let sendSeq = 0;
    prismaMock.nudgeDeliverySend.findUnique.mockImplementation(async ({ where }) => {
      const key = `${where.deliveryId_pushTokenId.deliveryId}|${where.deliveryId_pushTokenId.pushTokenId}`;
      return sendRows.get(key) || null;
    });
    prismaMock.nudgeDeliverySend.create.mockImplementation(async ({ data }) => {
      const key = `${data.deliveryId}|${data.pushTokenId}`;
      const row = { id: `send-${++sendSeq}`, status: 'queued', nextAttemptAt: null, attemptCount: 0 };
      sendRows.set(key, row);
      return row;
    });
    prismaMock.nudgeDeliverySend.updateMany.mockResolvedValue({ count: 1 });
    prismaMock.nudgeDeliverySend.update.mockResolvedValue({});

    // 00:05 should send the 23:45 slot, attributed to the previous local day.
    const out1 = await runProblemNudgeApnsSender(new Date('2026-02-13T00:05:00.000Z'), { apnsClient });
    expect(out1.ok).toBe(true);
    expect(apnsClient.sendAlert).toHaveBeenCalledTimes(1);
    expect(apnsClient.sendAlert.mock.calls[0][0].payload.problemType).toBe('porn_addiction');
    expect(apnsClient.sendAlert.mock.calls[0][0].payload.scheduledTime).toBe('23:45');
    expect(apnsClient.sendAlert.mock.calls[0][0].payload.deliveryDayLocal).toBe('2026-02-12');

    // Later that day, 23:50 should still send the actual same-day 23:45 slot (not blocked).
    apnsClient.sendAlert.mockClear();
    const out2 = await runProblemNudgeApnsSender(new Date('2026-02-13T23:50:00.000Z'), { apnsClient });
    expect(out2.ok).toBe(true);
    expect(apnsClient.sendAlert).toHaveBeenCalledTimes(1);
    expect(apnsClient.sendAlert.mock.calls[0][0].payload.deliveryDayLocal).toBe('2026-02-13');

    expect(deliveries.size).toBe(2);
  });

  it('enforces free cap per profile even when devices have different struggles (max 3 deliveries/day)', async () => {
    getEntitlementState.mockResolvedValue({ plan: 'free', status: 'active', currentPeriodEnd: null });

    prismaMock.pushToken.findMany.mockResolvedValueOnce([
      { id: 'ptok-1', profileId: '00000000-0000-0000-0000-000000000001', deviceId: 'device-1', token: 'a'.repeat(64) },
      { id: 'ptok-2', profileId: '00000000-0000-0000-0000-000000000001', deviceId: 'device-2', token: 'b'.repeat(64) },
    ]);

    // Two devices disagree; cap must still be enforced at the profile level.
    prismaMock.mobileProfile.findMany.mockResolvedValueOnce([
      { profile: { struggles: ['anxiety'] } },
      { profile: { struggles: ['bad_mouthing'] } },
    ]);

    const apnsClient = {
      sendAlert: vi.fn().mockResolvedValue({ ok: true, apnsId: 'apns-1' }),
    };

    // Minimal in-memory simulation for idempotent delivery creation.
    const deliveries = new Map(); // key -> deliveryId
    let deliverySeq = 0;
    prismaMock.nudgeDelivery.findFirst.mockImplementation(async ({ where }) => {
      const key = `${where.profileId}|${where.problemType}|${where.scheduledTime}|${where.deliveryDayLocal.toISOString()}`;
      const id = deliveries.get(key);
      return id ? { id } : null;
    });
    prismaMock.nudgeDelivery.create.mockImplementation(async ({ data }) => {
      const key = `${data.profileId}|${data.problemType}|${data.scheduledTime}|${data.deliveryDayLocal.toISOString()}`;
      const id = `delivery-${++deliverySeq}`;
      deliveries.set(key, id);
      return { id };
    });

    const sendRows = new Map(); // key -> row
    let sendSeq = 0;
    prismaMock.nudgeDeliverySend.findUnique.mockImplementation(async ({ where }) => {
      const key = `${where.deliveryId_pushTokenId.deliveryId}|${where.deliveryId_pushTokenId.pushTokenId}`;
      return sendRows.get(key) || null;
    });
    prismaMock.nudgeDeliverySend.create.mockImplementation(async ({ data }) => {
      const key = `${data.deliveryId}|${data.pushTokenId}`;
      const row = { id: `send-${++sendSeq}`, status: 'queued', nextAttemptAt: null, attemptCount: 0 };
      sendRows.set(key, row);
      return row;
    });
    prismaMock.nudgeDeliverySend.updateMany.mockResolvedValue({ count: 1 });
    prismaMock.nudgeDeliverySend.update.mockResolvedValue({});

    // Run across times that would create 6 distinct deliveries/day if selection were token-scoped.
    process.env.PUSH_ENV = 'dev';
    process.env.APNS_ENDPOINT = 'development';

    await runProblemNudgeApnsSender(new Date('2026-02-13T07:35:00.000Z'), { apnsClient }); // anxiety 07:30 would be due
    await runProblemNudgeApnsSender(new Date('2026-02-13T09:35:00.000Z'), { apnsClient }); // bad_mouthing 09:30 due
    await runProblemNudgeApnsSender(new Date('2026-02-13T12:20:00.000Z'), { apnsClient }); // anxiety 12:15 would be due
    await runProblemNudgeApnsSender(new Date('2026-02-13T14:35:00.000Z'), { apnsClient }); // bad_mouthing 14:30 due
    await runProblemNudgeApnsSender(new Date('2026-02-13T18:50:00.000Z'), { apnsClient }); // anxiety 18:45 would be due
    await runProblemNudgeApnsSender(new Date('2026-02-13T19:40:00.000Z'), { apnsClient }); // bad_mouthing 19:30 due

    // With profile-scoped selection, the job can create at most 3 deliveries/day for a free profile.
    expect(deliveries.size).toBeLessThanOrEqual(3);
  });
});
