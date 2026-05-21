import { describe, it, expect, vi, beforeEach } from 'vitest';

const prismaMocks = vi.hoisted(() => ({
  memoryItem: {
    deleteMany: vi.fn(),
  },
}));

vi.mock('../../lib/prisma.js', () => ({ prisma: prismaMocks }));

import { runMemoryCleanup } from '../memoryCleanup.js';

describe('memoryCleanup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('deletes expired and old null-expiry items', async () => {
    prismaMocks.memoryItem.deleteMany
      .mockResolvedValueOnce({ count: 2 })
      .mockResolvedValueOnce({ count: 3 });

    const now = new Date('2026-02-09T00:00:00.000Z');
    const result = await runMemoryCleanup({ now });

    expect(result.deletedExpired).toBe(2);
    expect(result.deletedOldNullExpiry).toBe(3);
    expect(prismaMocks.memoryItem.deleteMany).toHaveBeenCalledTimes(2);
  });
});

