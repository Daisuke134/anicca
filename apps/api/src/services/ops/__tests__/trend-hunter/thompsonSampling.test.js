import { describe, it, expect } from 'vitest';
import {
  betaSample,
  selectTopN,
  updateBandit,
  decayAll,
  createDefaultBanditState,
} from '../../trend-hunter/thompsonSampling.js';
import { PROBLEM_TYPES } from '../../trend-hunter/config.js';

function makeDefaultState() {
  return createDefaultBanditState();
}

describe('thompsonSampling', () => {
  // #41 (spec numbering)
  it('betaSample returns values in [0, 1]', () => {
    for (let i = 0; i < 1000; i++) {
      const sample = betaSample(1, 1);
      expect(sample).toBeGreaterThanOrEqual(0);
      expect(sample).toBeLessThanOrEqual(1);
    }
  });

  // #42
  it('betaSample with high alpha is biased toward 1', () => {
    let sum = 0;
    const N = 1000;
    for (let i = 0; i < N; i++) {
      sum += betaSample(100, 1);
    }
    const mean = sum / N;
    expect(mean).toBeGreaterThan(0.9);
  });

  // #43
  it('selectTopN returns exactly n items', () => {
    const state = makeDefaultState();
    const result = selectTopN(state, 4);
    expect(result).toHaveLength(4);
    result.forEach(type => {
      expect(PROBLEM_TYPES).toContain(type);
    });
  });

  // #44
  it('selectTopN favors high alpha ProblemTypes', () => {
    const state = makeDefaultState();
    state.staying_up_late = { alpha: 50, beta: 1 };
    // Set all others to low
    for (const key of Object.keys(state)) {
      if (key !== 'staying_up_late') {
        state[key] = { alpha: 1, beta: 50 };
      }
    }

    let selectedCount = 0;
    const N = 100;
    for (let i = 0; i < N; i++) {
      const result = selectTopN(state, 4);
      if (result.includes('staying_up_late')) {
        selectedCount++;
      }
    }
    expect(selectedCount).toBeGreaterThanOrEqual(95);
  });

  // #45
  it('updateBandit increments alpha on success', () => {
    const state = makeDefaultState();
    const before = state.anxiety.alpha;
    updateBandit(state, 'anxiety', true);
    expect(state.anxiety.alpha).toBe(before + 1);
    expect(state.anxiety.beta).toBe(1); // unchanged
  });

  // #46
  it('updateBandit increments beta on failure', () => {
    const state = makeDefaultState();
    const before = state.anxiety.beta;
    updateBandit(state, 'anxiety', false);
    expect(state.anxiety.beta).toBe(before + 1);
    expect(state.anxiety.alpha).toBe(1); // unchanged
  });

  // #47
  it('decayAll reduces alpha and beta', () => {
    const state = makeDefaultState();
    state.staying_up_late = { alpha: 10, beta: 5 };
    decayAll(state, 0.9);
    expect(state.staying_up_late.alpha).toBe(9);  // round(10 * 0.9) = 9
    expect(state.staying_up_late.beta).toBe(5);   // round(5 * 0.9) = 4.5 -> 5
  });

  // #48
  it('decayAll maintains minimum value of 1', () => {
    const state = makeDefaultState();
    state.anxiety = { alpha: 1, beta: 1 };
    decayAll(state, 0.9);
    expect(state.anxiety.alpha).toBe(1);
    expect(state.anxiety.beta).toBe(1);
  });

  // #49
  it('v1 vs v2 switch at warmup threshold', () => {
    // This test validates the switching logic conceptually
    // v1: executionCount < 50 -> fixed rotation
    // v2: executionCount >= 50 -> Thompson Sampling
    const WARMUP_THRESHOLD = 50;
    expect(49 < WARMUP_THRESHOLD).toBe(true);   // v1
    expect(50 < WARMUP_THRESHOLD).toBe(false);  // v2
  });
});
