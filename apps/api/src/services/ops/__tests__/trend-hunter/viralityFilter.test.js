import { describe, it, expect } from 'vitest';
import { filterByVirality } from '../../trend-hunter/viralityFilter.js';
import { VIRALITY_THRESHOLDS } from '../../trend-hunter/config.js';

function makeTrend(source, engagement) {
  return {
    id: `test-${source}-${engagement}`,
    source,
    problemType: 'staying_up_late',
    contentType: 'empathy',
    lang: 'en',
    text: 'test',
    url: null,
    metrics: { engagement },
    author: null,
    raw: {},
  };
}

describe('viralityFilter', () => {
  // #21
  it('passes trends above threshold', () => {
    const trends = [makeTrend('x', 5000)];
    const result = filterByVirality(trends, VIRALITY_THRESHOLDS);
    expect(result).toHaveLength(1);
  });

  // #22
  it('filters out trends below threshold', () => {
    const trends = [makeTrend('x', 500)];
    const result = filterByVirality(trends, VIRALITY_THRESHOLDS);
    expect(result).toHaveLength(0);
  });

  // #23
  it('passes trends at exact threshold (>=)', () => {
    const trends = [makeTrend('x', 1000)];
    const result = filterByVirality(trends, VIRALITY_THRESHOLDS);
    expect(result).toHaveLength(1);
  });

  // #24
  it('filters mixed set correctly', () => {
    const trends = [
      makeTrend('x', 5000),
      makeTrend('x', 500),
      makeTrend('x', 1000),
      makeTrend('x', 100),
      makeTrend('x', 2000),
    ];
    const result = filterByVirality(trends, VIRALITY_THRESHOLDS);
    expect(result).toHaveLength(3);
  });

  // #25
  it('applies source-specific thresholds', () => {
    const trends = [
      makeTrend('x', 1000),       // x >= 1000 -> pass
      makeTrend('reddit', 100),   // reddit >= 100 -> pass
      makeTrend('tiktok', 10000), // tiktok >= 10000 -> pass
      makeTrend('x', 999),        // x < 1000 -> fail
      makeTrend('reddit', 99),    // reddit < 100 -> fail
      makeTrend('tiktok', 9999),  // tiktok < 10000 -> fail
    ];
    const result = filterByVirality(trends, VIRALITY_THRESHOLDS);
    expect(result).toHaveLength(3);
  });
});
