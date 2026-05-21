import { describe, it, expect, vi } from 'vitest';

const prismaMock = vi.hoisted(() => ({
  agentAuditLog: {
    create: vi.fn(async ({ data }) => ({ id: 'a1', ...data })),
  },
}));

vi.mock('../../lib/prisma.js', () => ({ prisma: prismaMock }));

const slackMock = vi.fn();
vi.mock('../../services/slackNotifier.js', () => ({
  sendSlackMessage: (...args) => slackMock(...args),
}));

import { runSufferingDetectorJob } from '../sufferingDetectorJob.js';

describe('sufferingDetectorJob', () => {
  it('emits audit logs and attempts slack on crisis', async () => {
    const res = await runSufferingDetectorJob({
      feed: [
        { platform: 'moltbook', region: 'JP', externalPostId: 'e1', platformUserId: 'moltbook:u', context: 'つらい', severityScore: 0.65 },
        { platform: 'moltbook', region: 'JP', externalPostId: 'e2', platformUserId: 'moltbook:u', context: '死にたい', severityScore: 0.95 },
      ],
    });
    expect(res.ok).toBe(true);
    expect(prismaMock.agentAuditLog.create).toHaveBeenCalled();
    expect(slackMock).toHaveBeenCalled();
  });
});

