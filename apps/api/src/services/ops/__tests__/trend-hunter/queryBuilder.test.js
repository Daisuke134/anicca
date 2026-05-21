import { describe, it, expect } from 'vitest';
import { buildQuery } from '../../trend-hunter/queryBuilder.js';
import { PROBLEM_TYPES } from '../../trend-hunter/config.js';

describe('queryBuilder', () => {
  // #1
  it('builds empathy query in Japanese for staying_up_late', () => {
    const query = buildQuery('staying_up_late', 'empathy', 'ja');
    expect(query).toContain('また3時だ');
    expect(typeof query).toBe('string');
    expect(query.length).toBeGreaterThan(0);
  });

  // #2
  it('builds solution query in English for staying_up_late', () => {
    const query = buildQuery('staying_up_late', 'solution', 'en');
    expect(query).toContain('how to fix sleep schedule');
    expect(typeof query).toBe('string');
    expect(query.length).toBeGreaterThan(0);
  });

  // #3
  it('returns non-empty strings for all 13 ProblemTypes', () => {
    for (const problemType of PROBLEM_TYPES) {
      for (const contentType of ['empathy', 'solution']) {
        for (const lang of ['ja', 'en']) {
          const query = buildQuery(problemType, contentType, lang);
          expect(query).toBeDefined();
          expect(query).not.toBeNull();
          expect(typeof query).toBe('string');
          expect(query.length).toBeGreaterThan(0);
        }
      }
    }
  });

  // #4
  it('throws for unknown ProblemType', () => {
    expect(() => buildQuery('invalid_type', 'empathy', 'ja')).toThrow();
  });

  // #5
  it('appends min_faves when provided', () => {
    const query = buildQuery('anxiety', 'empathy', 'en', { minFaves: 1000 });
    expect(query).toContain('min_faves:1000');
  });
});
