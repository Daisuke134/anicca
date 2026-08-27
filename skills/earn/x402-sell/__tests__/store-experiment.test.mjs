import test from 'node:test';
import assert from 'node:assert/strict';

import { decideExperiment, EXPERIMENT_INTERVAL_MS } from '../store-experiment.mjs';

const T0 = Date.parse('2026-07-22T12:00:00Z');
const variants = [{ id: 'eco-margin' }, { id: 'eco-market' }, { id: 'eco-premium' }];

test('first improve creates one experiment with the current external baseline', () => {
  const out = decideExperiment({ state: null, externalCount: 0, now: T0, variants });
  assert.equal(out.action, 'applied');
  assert.deepEqual(out.state, {
    experimentId: 'eco-margin',
    variantIndex: 0,
    startedAt: T0,
    baselineExternalCount: 0,
    status: 'running',
  });
});

test('a wake before five minutes is idempotent and does not rotate', () => {
  const state = {
    experimentId: 'eco-margin', variantIndex: 0, startedAt: T0,
    baselineExternalCount: 0, status: 'running',
  };
  const out = decideExperiment({ state, externalCount: 0, now: T0 + EXPERIMENT_INTERVAL_MS - 1, variants });
  assert.equal(out.action, 'waiting');
  assert.equal(out.state, state);
});

test('five minutes without external revenue rotates exactly once', () => {
  const state = {
    experimentId: 'eco-margin', variantIndex: 0, startedAt: T0,
    baselineExternalCount: 0, status: 'running',
  };
  const out = decideExperiment({ state, externalCount: 0, now: T0 + EXPERIMENT_INTERVAL_MS, variants });
  assert.equal(out.action, 'applied');
  assert.equal(out.state.experimentId, 'eco-market');
  assert.equal(out.state.variantIndex, 1);
  assert.equal(out.state.startedAt, T0 + EXPERIMENT_INTERVAL_MS);
});

test('an external settlement marks a winner and holds the active variant', () => {
  const state = {
    experimentId: 'eco-market', variantIndex: 1, startedAt: T0,
    baselineExternalCount: 3, status: 'running',
  };
  const out = decideExperiment({ state, externalCount: 4, now: T0 + 60_000, variants });
  assert.equal(out.action, 'winner');
  assert.equal(out.state.experimentId, 'eco-market');
  assert.equal(out.state.status, 'winner');
  assert.equal(out.rewardExternalCount, 1);
});

test('self-pay cannot produce a winner because only externalCount enters the reward', () => {
  const state = {
    experimentId: 'eco-margin', variantIndex: 0, startedAt: T0,
    baselineExternalCount: 0, status: 'running',
  };
  const out = decideExperiment({
    state,
    externalCount: 0,
    settledCountIncludingSelf: 99,
    now: T0 + EXPERIMENT_INTERVAL_MS,
    variants,
  });
  assert.equal(out.action, 'applied');
  assert.equal(out.rewardExternalCount, 0);
});
