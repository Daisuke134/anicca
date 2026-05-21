import { describe, it, expect, vi, beforeEach } from 'vitest';

const prismaMock = vi.hoisted(() => ({
  agentAuditLog: {
    findFirst: vi.fn(async () => null),
    create: vi.fn(async ({ data }) => ({ id: 'a1', ...data })),
  },
}));

const sendMock = vi.hoisted(() => ({
  sendNudgeInternal: vi.fn(async () => ({ sent: true, nudgeId: 'n1', quota: { limit: 3, used: 1 } })),
}));

vi.mock('../../lib/prisma.js', () => ({ prisma: prismaMock }));
vi.mock('../../services/mobile/nudgeSendService.js', () => ({
  sendNudgeInternal: sendMock.sendNudgeInternal,
}));

import { runProactiveAppNudgeJob } from '../proactiveAppNudgeJob.js';

describe('proactiveAppNudgeJob', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.NUDGE_ALPHA_USER_ID = '11111111-1111-1111-1111-111111111111';
  });

  it('enqueues a proactive nudge with dedupeKey', async () => {
    const res = await runProactiveAppNudgeJob({ dateJst: '2026-02-10', slot: 'morning' });
    expect(res.ok).toBe(true);
    expect(res.dedupeKey).toBe('app:proactive:2026-02-10:morning');
    expect(sendMock.sendNudgeInternal).toHaveBeenCalledTimes(1);
    expect(prismaMock.agentAuditLog.create).toHaveBeenCalled();
  });

  it('returns deduped if audit log already exists', async () => {
    prismaMock.agentAuditLog.findFirst.mockResolvedValueOnce({ id: 'existing' });
    const res = await runProactiveAppNudgeJob({ dateJst: '2026-02-10', slot: 'morning' });
    expect(res.ok).toBe(true);
    expect(res.deduped).toBe(true);
    expect(sendMock.sendNudgeInternal).toHaveBeenCalledTimes(0);
  });
});

