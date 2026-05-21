import { beforeEach, describe, expect, it, vi } from 'vitest';

const { prismaMock } = vi.hoisted(() => ({
  prismaMock: {
    hookPost: undefined,
    hookPostArchive: undefined,
    $transaction: vi.fn(),
  },
}));

vi.mock('../../lib/prisma.js', () => ({
  prisma: prismaMock,
}));

import { cleanOldLowRelevancePosts } from '../hookPostTtlCleaner.js';

describe('hookPostTtlCleaner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    prismaMock.hookPost = undefined;
    prismaMock.hookPostArchive = undefined;
  });

  it('returns safe no-op when hookPost models are unavailable', async () => {
    const result = await cleanOldLowRelevancePosts();
    expect(result.skipped).toBe(true);
    expect(result.deleted).toBe(0);
    expect(result.archived).toBe(0);
  });

  it('archives and deletes matched posts when models are available', async () => {
    const post = {
      id: 'p1',
      relevance: 0.05,
      createdAt: new Date('2025-12-01T00:00:00Z'),
      content: 'stale',
    };
    const upsert = vi.fn().mockResolvedValue({});
    const del = vi.fn().mockResolvedValue({});

    prismaMock.hookPost = {
      findMany: vi.fn().mockResolvedValue([post]),
    };
    prismaMock.hookPostArchive = {};
    prismaMock.$transaction.mockImplementation(async (fn) =>
      fn({
        hookPostArchive: { upsert },
        hookPost: { delete: del },
      })
    );

    const result = await cleanOldLowRelevancePosts({
      nowMs: new Date('2026-02-09T00:00:00Z').getTime(),
    });

    expect(result).toEqual(
      expect.objectContaining({
        deleted: 1,
        archived: 1,
        failed: 0,
        skipped: false,
      })
    );
    expect(upsert).toHaveBeenCalledTimes(1);
    expect(del).toHaveBeenCalledWith({ where: { id: 'p1' } });
  });
});
