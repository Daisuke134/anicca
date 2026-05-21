import { describe, it, expect, vi } from 'vitest';

const prismaMock = vi.hoisted(() => ({
  agentAuditLog: {
    findMany: vi.fn(),
    findFirst: vi.fn(),
    create: vi.fn(async ({ data }) => ({ id: 'a1', ...data })),
  },
}));

vi.mock('../../lib/prisma.js', () => ({ prisma: prismaMock }));

const sendMock = vi.fn();
vi.mock('../../services/mobile/nudgeSendService.js', () => ({
  sendNudgeInternal: (...args) => sendMock(...args),
}));

import { runAppNudgeSenderJob } from '../appNudgeSenderJob.js';

describe('appNudgeSenderJob', () => {
  it('returns ok=false when NUDGE_ALPHA_USER_ID missing', async () => {
    delete process.env.NUDGE_ALPHA_USER_ID;
    const res = await runAppNudgeSenderJob({ nowMs: Date.now() });
    expect(res.ok).toBe(false);
  });

  it('enqueues for recent suffering_detected and records audit', async () => {
    process.env.NUDGE_ALPHA_USER_ID = '00000000-0000-0000-0000-000000000001';
    prismaMock.agentAuditLog.findMany.mockResolvedValueOnce([
      { id: 'audit-1', platform: 'moltbook', requestPayload: { externalPostId: 'p1', severityScore: 0.65 }, createdAt: new Date() },
    ]);
    prismaMock.agentAuditLog.findFirst.mockResolvedValueOnce(null);
    sendMock.mockResolvedValueOnce({ sent: true, nudgeId: 'n1', quota: { limit: 3, used: 1 } });

    const res = await runAppNudgeSenderJob({ nowMs: Date.now() });
    expect(res.ok).toBe(true);
    expect(res.enqueued).toBe(1);
    expect(prismaMock.agentAuditLog.create).toHaveBeenCalled();
  });
});

