import { describe, it, expect, vi } from 'vitest';

const prismaMock = vi.hoisted(() => ({
  agentAuditLog: {
    findMany: vi.fn(),
  },
}));

vi.mock('../../lib/prisma.js', () => ({
  prisma: prismaMock,
}));

const upsertMock = vi.hoisted(() => vi.fn());
vi.mock('../../services/memoryItemService.js', () => ({
  upsertMemoryItem: upsertMock,
}));

import { runMemoryExtraction } from '../memoryExtractor.js';

describe('memoryExtractor', () => {
  it('upserts deterministic keys once each', async () => {
    prismaMock.agentAuditLog.findMany.mockResolvedValueOnce([
      { eventType: 'x_detect_only', createdAt: new Date() },
      { eventType: 'x_detect_only', createdAt: new Date() },
      { eventType: 'safe_t_interrupted', createdAt: new Date() },
      { eventType: 'x_credits_depleted', createdAt: new Date() },
    ]);

    const res = await runMemoryExtraction({ nowMs: Date.now() });
    expect(res.scanned).toBe(4);
    expect(res.upserts).toBe(3);
    const keys = upsertMock.mock.calls.map((c) => c[0].key).sort();
    expect(keys).toEqual(['safe_t_interrupt', 'x_detect_only', 'x_posting_paused'].sort());
  });
});
