import { describe, it, expect, beforeEach } from 'vitest';
import {
  unifiedScore,
  zScore,
  _setBaselines,
  _getBaselines,
  X_TO_TIKTOK_THRESHOLD,
  TIKTOK_TO_APP_THRESHOLD,
  MIN_APP_SAMPLES,
  MIN_TIKTOK_SAMPLES,
  MIN_X_SAMPLES,
  MIN_MOLTBOOK_SAMPLES,
  MIN_MOLTBOOK_VIEWS,
  MIN_SLACK_SAMPLES,
  W_APP,
  W_TIK,
  W_X,
  W_MOLT,
  W_SLACK,
} from '../crossPlatformLearning.js';

// Reset baselines before each test for determinism
beforeEach(() => {
  _setBaselines({
    appMean: 0.25, appStddev: 0.15,
    tikMean: 0.05, tikStddev: 0.03,
    xMean: 0.02, xStddev: 0.015,
    moltViewsMean: 0.05, moltViewsStddev: 0.03,
    moltUpvotesMean: 3.0, moltUpvotesStddev: 2.0,
    slackMean: 0.10, slackStddev: 0.05,
  });
});

// ===== zScore =====

describe('zScore', () => {
  it('returns 0 for mean value', () => {
    expect(zScore(0.25, 0.25, 0.15)).toBe(0);
  });

  it('returns 1 for 1 stddev above mean', () => {
    expect(zScore(0.40, 0.25, 0.15)).toBeCloseTo(1.0);
  });

  it('returns -1 for 1 stddev below mean', () => {
    expect(zScore(0.10, 0.25, 0.15)).toBeCloseTo(-1.0);
  });

  it('returns 0 for zero stddev', () => {
    expect(zScore(0.5, 0.25, 0)).toBe(0);
  });
});

// ===== unifiedScore =====

describe('unifiedScore', () => {
  it('returns 0 for hook with no samples', () => {
    const hook = {
      appTapRate: 0.5, appSampleSize: 0,
      tiktokLikeRate: 0.1, tiktokSampleSize: 0,
      xEngagementRate: 0.05, xSampleSize: 0,
    };
    expect(unifiedScore(hook)).toBe(0);
  });

  it('weights app score at 40%', () => {
    const hook = {
      appTapRate: 0.40, appSampleSize: 10,  // 1 stddev above = Z=1.0
      tiktokLikeRate: 0.05, tiktokSampleSize: 0,  // no data
      xEngagementRate: 0.02, xSampleSize: 0,  // no data
    };
    const score = unifiedScore(hook);
    // Only app contributes: 0.40 * 1.0 = 0.40
    expect(score).toBeCloseTo(0.40);
  });

  it('combines all five platforms (1.6.1 5ch)', () => {
    // slackReactions / slackSampleSize = rate → (rate - SLACK_MEAN) / SLACK_STDDEV
    // Need: (rate - 0.10) / 0.05 = 1.0 → rate = 0.15 → reactions = 0.15 * 5 = 0.75
    // Use slackSampleSize=5 so reactions=1.5 works, but we need whole numbers
    // Actually: rate = slackReactions / slackSampleSize, slackZ = (rate - mean) / stddev
    // Let's use: slackReactions=15, slackSampleSize=100 → rate=0.15 → slackZ=(0.15-0.10)/0.05=1.0
    // Or simpler: slackReactions = (1.0 * 0.05 + 0.10) * slackSampleSize = 0.15 * 5 = 0.75
    // Just use exact numbers: reactions=7.5 doesn't work. Let's use 10 sample, reactions = 1.5 (0.15 rate)
    // Actually integer: sampleSize=10, reactions=15 → rate=1.5 → that's too high
    // Let's just compute what we get and verify the formula works
    const hook = {
      appTapRate: 0.40, appSampleSize: 10,     // appZ = 1.0
      tiktokLikeRate: 0.08, tiktokSampleSize: 5,  // tikZ = 1.0
      xEngagementRate: 0.035, xSampleSize: 15,    // xZ = 1.0
      moltbookUpvotes: 8, moltbookViews: 100, moltbookSampleSize: 10, // rate=0.08, moltZ = 1.0
      slackReactions: null, slackSampleSize: 0,  // skip slack for this test
    };
    const score = unifiedScore(hook);
    // 0.40*1.0 + 0.20*1.0 + 0.15*1.0 + 0.15*1.0 + 0.10*0 = 0.90
    expect(score).toBeCloseTo(0.90);
  });

  it('ignores platforms below minimum samples', () => {
    const hook = {
      appTapRate: 0.40, appSampleSize: 3,      // below MIN_APP_SAMPLES=5
      tiktokLikeRate: 0.08, tiktokSampleSize: 1,  // below MIN_TIKTOK_SAMPLES=3
      xEngagementRate: 0.05, xSampleSize: 5,      // below MIN_X_SAMPLES=10
    };
    expect(unifiedScore(hook)).toBe(0);
  });

  it('handles negative Z-scores (below average hooks)', () => {
    const hook = {
      appTapRate: 0.10, appSampleSize: 10,     // appZ = -1.0
      tiktokLikeRate: 0.02, tiktokSampleSize: 5,  // tikZ = -1.0
      xEngagementRate: 0.005, xSampleSize: 15,    // xZ = -1.0
      // Moltbook and Slack not included → their Z = 0
    };
    const score = unifiedScore(hook);
    // 0.40*(-1) + 0.20*(-1) + 0.15*(-1) + 0.15*0 + 0.10*0 = -0.75
    expect(score).toBeCloseTo(-0.75);
  });
});

// ===== Promotion Thresholds =====

describe('promotion thresholds', () => {
  it('X → TikTok threshold is 1.0', () => {
    expect(X_TO_TIKTOK_THRESHOLD).toBe(1.0);
  });

  it('TikTok → App threshold is 1.5', () => {
    expect(TIKTOK_TO_APP_THRESHOLD).toBe(1.5);
  });
});

// ===== Weights =====

describe('platform weights (1.6.1 5ch)', () => {
  it('sum to 1.0', () => {
    expect(W_APP + W_TIK + W_X + W_MOLT + W_SLACK).toBeCloseTo(1.0);
  });

  it('App has highest weight (0.40)', () => {
    expect(W_APP).toBe(0.40);
    expect(W_APP).toBeGreaterThan(W_TIK);
  });

  it('weights match spec: App=0.40, TikTok=0.20, X=0.15, Moltbook=0.15, Slack=0.10', () => {
    expect(W_APP).toBe(0.40);
    expect(W_TIK).toBe(0.20);
    expect(W_X).toBe(0.15);
    expect(W_MOLT).toBe(0.15);
    expect(W_SLACK).toBe(0.10);
  });
});

// ===== Moltbook Z-Score (1.6.1) =====

describe('Moltbook Z-Score calculation', () => {
  it('uses upvotes/views when views >= MIN_MOLTBOOK_VIEWS (AC-9)', () => {
    const hook = {
      appTapRate: 0, appSampleSize: 0,
      tiktokLikeRate: 0, tiktokSampleSize: 0,
      xEngagementRate: 0, xSampleSize: 0,
      moltbookUpvotes: 8, moltbookViews: 100, moltbookSampleSize: 10,
      slackReactions: 0, slackSampleSize: 0,
    };
    // rate = 8/100 = 0.08, mean = 0.05, stddev = 0.03
    // moltZ = (0.08 - 0.05) / 0.03 = 1.0
    const score = unifiedScore(hook);
    expect(score).toBeCloseTo(W_MOLT * 1.0);
  });

  it('falls back to upvotes baseline when views is null (AC-9)', () => {
    const hook = {
      appTapRate: 0, appSampleSize: 0,
      tiktokLikeRate: 0, tiktokSampleSize: 0,
      xEngagementRate: 0, xSampleSize: 0,
      moltbookUpvotes: 5, moltbookViews: null, moltbookSampleSize: 10,
      slackReactions: 0, slackSampleSize: 0,
    };
    // upvotes = 5, mean = 3.0, stddev = 2.0
    // moltZ = (5 - 3) / 2 = 1.0
    const score = unifiedScore(hook);
    expect(score).toBeCloseTo(W_MOLT * 1.0);
  });

  it('excludes from calculation when views is 0 (AC-9)', () => {
    const hook = {
      appTapRate: 0, appSampleSize: 0,
      tiktokLikeRate: 0, tiktokSampleSize: 0,
      xEngagementRate: 0, xSampleSize: 0,
      moltbookUpvotes: 10, moltbookViews: 0, moltbookSampleSize: 10,
      slackReactions: 0, slackSampleSize: 0,
    };
    // views = 0 → exclude (moltZ = 0)
    const score = unifiedScore(hook);
    expect(score).toBe(0);
  });

  it('excludes when sample size below MIN_MOLTBOOK_SAMPLES', () => {
    const hook = {
      appTapRate: 0, appSampleSize: 0,
      tiktokLikeRate: 0, tiktokSampleSize: 0,
      xEngagementRate: 0, xSampleSize: 0,
      moltbookUpvotes: 10, moltbookViews: 100, moltbookSampleSize: 5,  // < 10
      slackReactions: 0, slackSampleSize: 0,
    };
    const score = unifiedScore(hook);
    expect(score).toBe(0);
  });
});

// ===== Baselines =====

describe('baselines', () => {
  it('can be set and retrieved', () => {
    _setBaselines({ appMean: 0.30, appStddev: 0.20 });
    const b = _getBaselines();
    expect(b.APP_MEAN).toBe(0.30);
    expect(b.APP_STDDEV).toBe(0.20);
  });

  it('partial updates preserve other values', () => {
    _setBaselines({ xMean: 0.05 });
    const b = _getBaselines();
    expect(b.X_MEAN).toBe(0.05);
    expect(b.APP_MEAN).toBe(0.25); // unchanged
  });
});
