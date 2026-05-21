import { describe, it, expect, vi } from 'vitest';

const prismaMock = vi.hoisted(() => ({
  memoryItem: {
    upsert: vi.fn(),
  },
}));

vi.mock('../../lib/prisma.js', () => ({
  prisma: prismaMock,
}));

import { upsertMemoryItem } from '../memoryItemService.js';

describe('memoryItemService', () => {
  it('validates inputs', async () => {
    await expect(upsertMemoryItem({})).rejects.toThrow('scope');
    await expect(upsertMemoryItem({ scope: 'global', category: 'bad', key: 'k', value: 'v', source: 's' }))
      .rejects.toThrow('invalid category');
  });

  it('upserts with composite key and truncates to 800 chars', async () => {
    prismaMock.memoryItem.upsert.mockResolvedValueOnce({ id: 'm1' });

    const res = await upsertMemoryItem({
      scope: 'global',
      category: 'ops',
      key: 'x_detect_only',
      value: 'a'.repeat(900),
      confidence: 0.9,
      source: 'ops_event',
    });

    expect(res.id).toBe('m1');
    const args = prismaMock.memoryItem.upsert.mock.calls[0][0];
    expect(args.where.scope_category_key).toEqual({ scope: 'global', category: 'ops', key: 'x_detect_only' });
    expect(args.create.value.length).toBe(800);
  });
});
