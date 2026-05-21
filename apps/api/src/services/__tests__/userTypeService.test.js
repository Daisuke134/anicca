/**
 * Unit tests for userTypeService.js
 * Tests: classifyUserType (pure function) + formatApiResponse
 */

import { describe, it, expect } from 'vitest';
import { classifyUserType, TYPE_NAMES } from '../userTypeService.js';

describe('classifyUserType', () => {
  it('returns correct type for perfectionist problems', () => {
    // Arrange: problems strongly associated with T1
    const problems = ['self_loathing', 'procrastination'];

    // Act
    const result = classifyUserType(problems);

    // Assert
    expect(result.primaryType).toBe('T1');
    expect(result.confidence).toBeGreaterThan(0);
    expect(result.scores.T1).toBeGreaterThan(result.scores.T2);
    expect(result.scores.T1).toBeGreaterThan(result.scores.T3);
    expect(result.scores.T1).toBeGreaterThan(result.scores.T4);
  });

  it('returns correct type for comparison-tendency problems', () => {
    const problems = ['rumination', 'bad_mouthing', 'loneliness'];
    const result = classifyUserType(problems);

    expect(result.primaryType).toBe('T2');
    expect(result.scores.T2).toBeGreaterThan(result.scores.T1);
  });

  it('returns correct type for impulsive problems', () => {
    const problems = ['staying_up_late', 'porn_addiction', 'alcohol_dependency'];
    const result = classifyUserType(problems);

    expect(result.primaryType).toBe('T3');
    expect(result.scores.T3).toBeGreaterThan(result.scores.T1);
  });

  it('returns correct type for anxiety problems', () => {
    const problems = ['anxiety', 'rumination'];
    const result = classifyUserType(problems);

    expect(result.primaryType).toBe('T4');
    expect(result.scores.T4).toBeGreaterThan(result.scores.T3);
  });

  it('calculates confidence correctly', () => {
    const problems = ['self_loathing'];
    const result = classifyUserType(problems);

    // T1=3, T2=2, T3=0, T4=1 → total=6, T1/total=0.5
    expect(result.confidence).toBeCloseTo(0.5);
    expect(result.scores).toEqual({ T1: 3, T2: 2, T3: 0, T4: 1 });
  });

  it('returns default T4 with confidence 0 for empty problems', () => {
    const result = classifyUserType([]);

    expect(result.primaryType).toBe('T4');
    expect(result.confidence).toBe(0);
    expect(result.scores).toEqual({ T1: 0, T2: 0, T3: 0, T4: 0 });
  });

  it('returns default T4 with confidence 0 for null/undefined', () => {
    expect(classifyUserType(null).primaryType).toBe('T4');
    expect(classifyUserType(null).confidence).toBe(0);
    expect(classifyUserType(undefined).primaryType).toBe('T4');
  });

  it('ignores unknown problem types', () => {
    const problems = ['self_loathing', 'unknown_problem'];
    const result = classifyUserType(problems);

    // Should be same as just self_loathing
    expect(result.primaryType).toBe('T1');
    expect(result.scores).toEqual({ T1: 3, T2: 2, T3: 0, T4: 1 });
  });

  it('handles all 13 problem types without error', () => {
    const allProblems = [
      'staying_up_late', 'cant_wake_up', 'self_loathing', 'rumination',
      'procrastination', 'anxiety', 'lying', 'bad_mouthing', 'porn_addiction',
      'alcohol_dependency', 'anger', 'obsessive', 'loneliness'
    ];
    const result = classifyUserType(allProblems);

    expect(['T1', 'T2', 'T3', 'T4']).toContain(result.primaryType);
    expect(result.confidence).toBeGreaterThan(0);
    expect(result.confidence).toBeLessThanOrEqual(1);
  });
});

describe('TYPE_NAMES', () => {
  it('has all 4 types', () => {
    expect(TYPE_NAMES).toEqual({
      T1: '完璧主義',
      T2: '比較傾向',
      T3: '衝動型',
      T4: '不安型',
    });
  });
});
