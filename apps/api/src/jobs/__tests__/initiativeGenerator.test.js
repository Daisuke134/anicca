import { describe, it, expect, vi } from 'vitest';

const prismaMock = vi.hoisted(() => ({
  agentAuditLog: {
    findMany: vi.fn(),
  },
  initiative: {
    create: vi.fn(async ({ data }) => ({ id: 'i1', ...data })),
  },
  $queryRaw: vi.fn(),
}));

vi.mock('../../lib/prisma.js', () => ({ prisma: prismaMock }));

import { runInitiativeGenerator } from '../initiativeGenerator.js';

describe('initiativeGenerator', () => {
  it('creates initiatives when thresholds are met', async () => {
    prismaMock.agentAuditLog.findMany.mockResolvedValueOnce([
      // 5 suffering + 3 failures in window
      ...Array.from({ length: 5 }).map(() => ({ eventType: 'suffering_detected', createdAt: new Date() })),
      ...Array.from({ length: 3 }).map(() => ({ eventType: 'x_post_failed', createdAt: new Date() })),
    ]);

    prismaMock.$queryRaw.mockResolvedValueOnce([{ tap_rate: 0.2 }]);

    const res = await runInitiativeGenerator({ nowMs: Date.now() });
    expect(res.createdCount).toBe(3);
    expect(prismaMock.initiative.create).toHaveBeenCalledTimes(3);
  });

  it('creates none when below thresholds', async () => {
    prismaMock.agentAuditLog.findMany.mockResolvedValueOnce([]);

    prismaMock.$queryRaw.mockResolvedValueOnce([{ tap_rate: 0.5 }]);

    const res = await runInitiativeGenerator({ nowMs: Date.now() });
    expect(res.createdCount).toBe(0);
  });
});
