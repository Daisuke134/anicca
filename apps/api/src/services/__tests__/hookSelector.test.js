/**
 * Unit tests for hookSelector.js
 * Spec 7.3 #16: test_hookSelector_prioritizes_tiktok_high_performers
 * Spec 7.3 #17: test_hookSelector_thompson_sampling_balance
 */

import { describe, it, expect } from 'vitest';
import { selectHook, betaSample, EXPLORE_PROBABILITY } from '../hookSelector.js';

const makeCandidate = (overrides = {}) => ({
  id: 'hook-1',
  text: 'テストフック',
  tone: 'strict',
  appTapRate: 0.50,
  appSampleSize: 20,
  tiktokLikeRate: 0.10,
  tiktokSampleSize: 10,
  explorationWeight: 1.0,
  isWisdom: false,
  tiktokHighPerformer: false,
  ...overrides,
});

describe('selectHook', () => {
  it('returns null for empty candidates', () => {
    expect(selectHook([])).toBeNull();
    expect(selectHook(null)).toBeNull();
  });

  it('returns a valid selection with hook and strategy', () => {
    const candidates = [makeCandidate()];
    const result = selectHook(candidates);
    expect(result).not.toBeNull();
    expect(result.hook).toBeDefined();
    expect(['exploit', 'explore']).toContain(result.strategy);
    expect(typeof result.score).toBe('number');
  });

  it('prioritizes high-performing hooks in exploit mode', () => {
    const highPerformer = makeCandidate({
      id: 'high',
      text: '高成績',
      appTapRate: 0.80,
      appSampleSize: 50,
      tiktokLikeRate: 0.15,
      tiktokSampleSize: 20,
    });
    const lowPerformer = makeCandidate({
      id: 'low',
      text: '低成績',
      appTapRate: 0.10,
      appSampleSize: 50,
      tiktokLikeRate: 0.02,
      tiktokSampleSize: 20,
    });

    // Run 50 times — high performer should win majority in exploit
    let highWins = 0;
    for (let i = 0; i < 50; i++) {
      const result = selectHook([highPerformer, lowPerformer]);
      if (result.strategy === 'exploit' && result.hook.id === 'high') highWins++;
    }
    // High performer should win most exploit rounds (allowing for stochastic variation)
    expect(highWins).toBeGreaterThan(20);
  });

  it('gives wisdom hooks a bonus', () => {
    const wisdomHook = makeCandidate({
      id: 'wisdom',
      text: 'wisdom',
      appTapRate: 0.50,
      appSampleSize: 20,
      isWisdom: true,
    });
    const normalHook = makeCandidate({
      id: 'normal',
      text: 'normal',
      appTapRate: 0.50,
      appSampleSize: 20,
      isWisdom: false,
    });

    let wisdomWins = 0;
    for (let i = 0; i < 100; i++) {
      const result = selectHook([wisdomHook, normalHook]);
      if (result.strategy === 'exploit' && result.hook.id === 'wisdom') wisdomWins++;
    }
    // Wisdom should win more often due to bonus (but not always due to stochasticity)
    expect(wisdomWins).toBeGreaterThan(30);
  });
});

describe('thompson sampling balance (80/20)', () => {
  it('selects explore ~20% of the time over many runs', () => {
    const candidates = [
      makeCandidate({ id: 'a', explorationWeight: 1.0 }),
      makeCandidate({ id: 'b', explorationWeight: 0.5 }),
    ];

    let exploreCount = 0;
    const N = 500;
    for (let i = 0; i < N; i++) {
      const result = selectHook(candidates);
      if (result.strategy === 'explore') exploreCount++;
    }

    const exploreRate = exploreCount / N;
    // Should be roughly 20% ± tolerance (allow 10-35% for statistical variation)
    expect(exploreRate).toBeGreaterThan(0.10);
    expect(exploreRate).toBeLessThan(0.35);
  });

  it('explore mode selects highest exploration_weight', () => {
    const highExplore = makeCandidate({
      id: 'high-explore',
      explorationWeight: 5.0,
    });
    const lowExplore = makeCandidate({
      id: 'low-explore',
      explorationWeight: 0.1,
    });

    // Force explore by running many times and checking explore selections
    let highSelected = 0;
    let exploreRuns = 0;
    for (let i = 0; i < 200; i++) {
      const result = selectHook([highExplore, lowExplore]);
      if (result.strategy === 'explore') {
        exploreRuns++;
        if (result.hook.id === 'high-explore') highSelected++;
      }
    }
    // When exploring, should always pick highest weight
    if (exploreRuns > 0) {
      expect(highSelected).toBe(exploreRuns);
    }
  });
});

describe('betaSample', () => {
  it('returns values between 0 and 1', () => {
    for (let i = 0; i < 100; i++) {
      const sample = betaSample(2, 5);
      expect(sample).toBeGreaterThanOrEqual(0);
      expect(sample).toBeLessThanOrEqual(1);
    }
  });

  it('higher alpha produces higher mean', () => {
    let sumHigh = 0;
    let sumLow = 0;
    const N = 1000;
    for (let i = 0; i < N; i++) {
      sumHigh += betaSample(10, 2);
      sumLow += betaSample(2, 10);
    }
    expect(sumHigh / N).toBeGreaterThan(sumLow / N);
  });
});
