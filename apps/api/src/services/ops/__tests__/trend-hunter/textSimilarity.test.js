import { describe, it, expect } from 'vitest';
import { jaccardBigram, isDuplicate } from '../../trend-hunter/textSimilarity.js';
import { SIMILARITY_THRESHOLD } from '../../trend-hunter/config.js';

describe('textSimilarity', () => {
  // #26
  it('returns 1.0 for identical strings', () => {
    expect(jaccardBigram('hello world', 'hello world')).toBe(1.0);
  });

  // #27
  it('returns low score for completely different strings', () => {
    expect(jaccardBigram('hello world', 'goodbye moon')).toBeLessThan(0.3);
  });

  // #28
  it('returns intermediate score for partial match', () => {
    const score = jaccardBigram('夜更かし やめたい', '夜更かし やめられない つらい');
    expect(score).toBeGreaterThan(0.3);
    expect(score).toBeLessThan(0.8);
  });

  // #29
  it('returns 0 for empty string', () => {
    expect(jaccardBigram('', 'hello')).toBe(0);
  });

  // #30
  it('correctly identifies duplicates above threshold', () => {
    const text1 = '毎晩同じ約束を自分にして、毎晩破る。6年間ずっとこれ。';
    const text2 = '毎晩同じ約束を自分にして、毎晩破る。6年間ずっとこれだ。';
    expect(isDuplicate(text1, text2, SIMILARITY_THRESHOLD)).toBe(true);
  });
});
