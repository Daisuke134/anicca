import { describe, it, expect, vi } from 'vitest';

const prismaMock = vi.hoisted(() => ({
  agentAuditLog: {
    create: vi.fn(async ({ data }) => ({ id: 'a1', ...data })),
  },
}));

vi.mock('../../lib/prisma.js', () => ({ prisma: prismaMock }));

import { runMoltbookShadowMonitorJob } from '../moltbookShadowMonitorJob.js';

describe('moltbookShadowMonitorJob', () => {
  it('generates shadow reply and writes audit logs', async () => {
    const res = await runMoltbookShadowMonitorJob({
      feed: [
        { externalPostId: 'p1', platformUserId: 'moltbook:u', region: 'JP', context: 'しんどい', optIn: true },
      ],
    });
    expect(res.ok).toBe(true);
    expect(res.generated).toBe(1);
    expect(prismaMock.agentAuditLog.create).toHaveBeenCalled();
  });
});

