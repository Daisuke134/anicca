import { describe, it, expect, vi } from 'vitest';

// Mock crossPlatformLearning before importing syncCrossPlatform
vi.mock('../../agents/crossPlatformLearning.js', () => ({
  refreshBaselines: vi.fn().mockResolvedValue(undefined),
  syncXMetricsToHookCandidates: vi.fn().mockResolvedValue(undefined),
  identifyPromotions: vi.fn().mockResolvedValue({ xToTiktok: [], tiktokToApp: [] }),
  executePromotions: vi.fn().mockResolvedValue(undefined),
}));

import { runCrossPlatformSync } from '../syncCrossPlatform.js';
import {
  refreshBaselines,
  syncXMetricsToHookCandidates,
  identifyPromotions,
  executePromotions,
} from '../../agents/crossPlatformLearning.js';

describe('runCrossPlatformSync', () => {
  const mockQuery = vi.fn();

  it('calls all four pipeline functions in order (#4)', async () => {
    identifyPromotions.mockResolvedValue({
      xToTiktok: [{ id: 'x1' }],
      tiktokToApp: [{ id: 't1' }, { id: 't2' }],
    });

    await runCrossPlatformSync(mockQuery);

    expect(refreshBaselines).toHaveBeenCalledWith(mockQuery);
    expect(syncXMetricsToHookCandidates).toHaveBeenCalledWith(mockQuery);
    expect(identifyPromotions).toHaveBeenCalledWith(mockQuery);
    expect(executePromotions).toHaveBeenCalledWith(mockQuery, ['x1'], 'x_promoted');
    expect(executePromotions).toHaveBeenCalledWith(mockQuery, ['t1', 't2'], 'tiktok_promoted');

    // Verify order: refreshBaselines before syncX, syncX before identify, etc.
    const refreshOrder = refreshBaselines.mock.invocationCallOrder[0];
    const syncOrder = syncXMetricsToHookCandidates.mock.invocationCallOrder[0];
    const identifyOrder = identifyPromotions.mock.invocationCallOrder[0];
    expect(refreshOrder).toBeLessThan(syncOrder);
    expect(syncOrder).toBeLessThan(identifyOrder);
  });

  it('handles empty promotion data gracefully (#5)', async () => {
    identifyPromotions.mockResolvedValue({ xToTiktok: [], tiktokToApp: [] });

    await runCrossPlatformSync(mockQuery);

    expect(executePromotions).toHaveBeenCalledWith(mockQuery, [], 'x_promoted');
    expect(executePromotions).toHaveBeenCalledWith(mockQuery, [], 'tiktok_promoted');
  });
});
