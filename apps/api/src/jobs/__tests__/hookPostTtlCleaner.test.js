import { beforeEach, describe, expect, it, vi } from 'vitest';

const serviceMocks = vi.hoisted(() => ({
  cleanOldLowRelevancePosts: vi.fn(),
  notifyPostSuccess: vi.fn(),
  notifyDLQEntry: vi.fn(),
}));

vi.mock('../../services/hookPostTtlCleaner.js', () => ({
  cleanOldLowRelevancePosts: serviceMocks.cleanOldLowRelevancePosts,
}));

vi.mock('../../services/slackNotifier.js', () => ({
  notifyPostSuccess: serviceMocks.notifyPostSuccess,
  notifyDLQEntry: serviceMocks.notifyDLQEntry,
}));

import { runHookPostTtlCleaner } from '../hookPostTtlCleaner.js';

describe('runHookPostTtlCleaner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns immediately when cleaner is skipped', async () => {
    serviceMocks.cleanOldLowRelevancePosts.mockResolvedValueOnce({
      deleted: 0,
      archived: 0,
      failed: 0,
      skipped: true,
      reason: 'not available',
    });

    const result = await runHookPostTtlCleaner();

    expect(result.skipped).toBe(true);
    expect(serviceMocks.notifyPostSuccess).not.toHaveBeenCalled();
    expect(serviceMocks.notifyDLQEntry).not.toHaveBeenCalled();
  });

  it('sends success notification when records are archived', async () => {
    serviceMocks.cleanOldLowRelevancePosts.mockResolvedValueOnce({
      deleted: 2,
      archived: 2,
      failed: 0,
      skipped: false,
    });

    await runHookPostTtlCleaner();

    expect(serviceMocks.notifyPostSuccess).toHaveBeenCalledTimes(1);
    expect(serviceMocks.notifyDLQEntry).not.toHaveBeenCalled();
  });

  it('sends dlq notification on failures', async () => {
    serviceMocks.cleanOldLowRelevancePosts.mockResolvedValueOnce({
      deleted: 1,
      archived: 1,
      failed: 3,
      skipped: false,
    });

    await runHookPostTtlCleaner();

    expect(serviceMocks.notifyDLQEntry).toHaveBeenCalledTimes(1);
  });
});
