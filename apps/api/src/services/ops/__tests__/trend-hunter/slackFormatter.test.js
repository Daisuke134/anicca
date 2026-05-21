import { describe, it, expect } from 'vitest';
import { formatSlackMessage } from '../../trend-hunter/slackFormatter.js';

describe('slackFormatter', () => {
  // #31
  it('formats normal results with source counts', () => {
    const result = formatSlackMessage({
      targetTypes: ['staying_up_late', 'cant_wake_up'],
      sourceCounts: { tiktok: 3, reddit: 5, x: 10, github: 0 },
      filteredCount: 8,
      savedCount: 4,
      empathyCount: 2,
      solutionCount: 2,
      errors: [],
    });
    expect(result).toContain('TikTok');
    expect(result).toContain('Reddit');
    expect(result).toContain('4');
    expect(typeof result).toBe('string');
  });

  // #32
  it('formats all-zero results', () => {
    const result = formatSlackMessage({
      targetTypes: ['staying_up_late'],
      sourceCounts: { tiktok: 0, reddit: 0, x: 0, github: 0 },
      filteredCount: 0,
      savedCount: 0,
      empathyCount: 0,
      solutionCount: 0,
      errors: [],
    });
    expect(result).toContain('0');
  });

  // #33
  it('includes error info for source failures', () => {
    const result = formatSlackMessage({
      targetTypes: ['staying_up_late'],
      sourceCounts: { tiktok: 3, reddit: 0, x: 5, github: 0 },
      filteredCount: 4,
      savedCount: 2,
      empathyCount: 1,
      solutionCount: 1,
      errors: [{ source: 'reddit', error: 'Rate limited' }],
    });
    expect(result).toContain('Reddit');
    expect(result).toContain('エラー');
  });
});
