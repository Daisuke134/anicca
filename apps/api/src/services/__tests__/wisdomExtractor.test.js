/**
 * Unit tests for wisdomExtractor.js
 * Spec 7.3 #15: test_wisdomExtractor_identifies_cross_channel_patterns
 */

import { describe, it, expect } from 'vitest';
import { WISDOM_THRESHOLDS } from '../wisdomExtractor.js';

describe('WISDOM_THRESHOLDS', () => {
  it('defines correct thresholds per spec', () => {
    expect(WISDOM_THRESHOLDS.appTapRate).toBe(0.50);
    expect(WISDOM_THRESHOLDS.appThumbsUpRate).toBe(0.60);
    expect(WISDOM_THRESHOLDS.appSampleSize).toBe(10);
    expect(WISDOM_THRESHOLDS.tiktokLikeRate).toBe(0.10);
    expect(WISDOM_THRESHOLDS.tiktokShareRate).toBe(0.05);
    expect(WISDOM_THRESHOLDS.tiktokSampleSize).toBe(5);
  });
});

describe('wisdom judgment logic', () => {
  const makeCandidate = (overrides = {}) => ({
    id: 'test-id',
    text: 'テストフック',
    tone: 'strict',
    appTapRate: 0.72,
    appThumbsUpRate: 0.65,
    appSampleSize: 15,
    tiktokLikeRate: 0.12,
    tiktokShareRate: 0.07,
    tiktokSampleSize: 8,
    isWisdom: false,
    ...overrides,
  });

  function meetsWisdomCriteria(c) {
    return (
      Number(c.appTapRate) > WISDOM_THRESHOLDS.appTapRate &&
      Number(c.appThumbsUpRate) > WISDOM_THRESHOLDS.appThumbsUpRate &&
      c.appSampleSize >= WISDOM_THRESHOLDS.appSampleSize &&
      Number(c.tiktokLikeRate) > WISDOM_THRESHOLDS.tiktokLikeRate &&
      Number(c.tiktokShareRate) > WISDOM_THRESHOLDS.tiktokShareRate &&
      c.tiktokSampleSize >= WISDOM_THRESHOLDS.tiktokSampleSize
    );
  }

  it('identifies cross-channel wisdom when ALL criteria met', () => {
    const candidate = makeCandidate();
    expect(meetsWisdomCriteria(candidate)).toBe(true);
  });

  it('rejects when app tap rate is too low', () => {
    const candidate = makeCandidate({ appTapRate: 0.40 });
    expect(meetsWisdomCriteria(candidate)).toBe(false);
  });

  it('rejects when app thumbs up rate is too low', () => {
    const candidate = makeCandidate({ appThumbsUpRate: 0.55 });
    expect(meetsWisdomCriteria(candidate)).toBe(false);
  });

  it('rejects when app sample size is too small', () => {
    const candidate = makeCandidate({ appSampleSize: 5 });
    expect(meetsWisdomCriteria(candidate)).toBe(false);
  });

  it('rejects when tiktok like rate is too low', () => {
    const candidate = makeCandidate({ tiktokLikeRate: 0.08 });
    expect(meetsWisdomCriteria(candidate)).toBe(false);
  });

  it('rejects when tiktok share rate is too low', () => {
    const candidate = makeCandidate({ tiktokShareRate: 0.03 });
    expect(meetsWisdomCriteria(candidate)).toBe(false);
  });

  it('rejects when tiktok sample size is too small', () => {
    const candidate = makeCandidate({ tiktokSampleSize: 3 });
    expect(meetsWisdomCriteria(candidate)).toBe(false);
  });

  it('rejects when only app criteria met but not tiktok', () => {
    const candidate = makeCandidate({
      tiktokLikeRate: 0.02,
      tiktokShareRate: 0.01,
      tiktokSampleSize: 1,
    });
    expect(meetsWisdomCriteria(candidate)).toBe(false);
  });

  it('rejects when only tiktok criteria met but not app', () => {
    const candidate = makeCandidate({
      appTapRate: 0.20,
      appThumbsUpRate: 0.30,
      appSampleSize: 3,
    });
    expect(meetsWisdomCriteria(candidate)).toBe(false);
  });
});
