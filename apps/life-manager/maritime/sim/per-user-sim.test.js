'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { simulate, validateProfile, appendLedger, ledgerStats, defaultLedgerPath } = require('./per-user-sim.js');

function tempLedger(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lm-sim-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  return path.join(dir, 'per-user-predictions.jsonl');
}

test('per-user simulation selects confidence for confidence+self_doubt daily struggle', () => {
  const result = simulate({ personId: 'lm_test_1', profile: { desired_state: 'confidence', pain_point: 'self_doubt', struggle_frequency: 'daily', local_hour: 8 } });
  assert.equal(result.decision.category, 'confidence');
  assert.equal(result.decision.nudges_per_day, 2);
  assert.equal(result.decision.delivery_window, 'morning');
  assert.equal(result.decision.delivery_at_local, '07:30');
  assert.equal(result.synthetic_input, false);
  // 0.18 + 0.38*0.95 + 0.09 - 0 = 0.631
  assert.ok(Math.abs(result.decision.predicted_daily_response_probability - 0.631) < 1e-9);
  assert.ok(result.baseline.chosen_fit > result.baseline.expected_fit);
  assert.ok(result.decision.fit_margin_over_next >= 0);
  assert.equal(result.history_used, false);
});

test('per-user simulation is deterministic per profile and monotone in struggle frequency', () => {
  const base = { desired_state: 'calm', pain_point: 'anxiety' };
  const rarely = simulate({ profile: { ...base, struggle_frequency: 'rarely' } });
  const many = simulate({ profile: { ...base, struggle_frequency: 'many_times_daily' } });
  assert.equal(rarely.decision.category, many.decision.category);
  assert.equal(many.decision.nudges_per_day, 3);
  assert.ok(many.decision.predicted_daily_response_probability > rarely.decision.predicted_daily_response_probability);
  assert.equal(rarely.decision.delivery_window, 'morning');
  assert.equal(simulate({ profile: { ...base, struggle_frequency: 'weekly', local_hour: 23 } }).decision.delivery_window, 'late');
});

test('all four desired states and four pain points stay inside the frozen score bounds', () => {
  for (const desired_state of ['confidence', 'focus', 'calm', 'energy']) {
    for (const pain_point of ['stress', 'anxiety', 'sleep', 'self_doubt']) {
      const result = simulate({ profile: { desired_state, pain_point, struggle_frequency: 'daily' } });
      assert.equal(result.candidates.length, 7);
      for (const candidate of result.candidates) {
        assert.ok(candidate.fit >= 0 && candidate.fit <= 1);
        assert.ok(candidate.predicted_daily_response_probability >= 0.02 && candidate.predicted_daily_response_probability <= 0.92);
      }
      assert.equal(result.synthetic_input, true);
    }
  }
});

test('profile validation rejects unknown values and bad hours', () => {
  assert.equal(validateProfile(null).error, 'profile_required');
  assert.equal(validateProfile({ desired_state: 'rich', pain_point: 'stress', struggle_frequency: 'daily' }).error, 'desired_state_invalid');
  assert.equal(validateProfile({ desired_state: 'calm', pain_point: 'boredom', struggle_frequency: 'daily' }).error, 'pain_point_invalid');
  assert.equal(validateProfile({ desired_state: 'calm', pain_point: 'stress', struggle_frequency: 'hourly' }).error, 'struggle_frequency_invalid');
  assert.equal(validateProfile({ desired_state: 'calm', pain_point: 'stress', struggle_frequency: 'daily', local_hour: 24 }).error, 'local_hour_invalid');
  const ok = validateProfile({ desired_state: 'calm', pain_point: 'stress', struggle_frequency: 'daily' });
  assert.deepEqual(ok.profile, { desired_state: 'calm', pain_point: 'stress', struggle_frequency: 'daily', local_hour: null });
});

test('ledger appends one row per simulation and stats count distinct persons', t => {
  const ledgerPath = tempLedger(t);
  const a = simulate({ personId: 'lm_a', profile: { desired_state: 'focus', pain_point: 'stress', struggle_frequency: 'weekly' } });
  const b = simulate({ personId: 'lm_b', profile: { desired_state: 'energy', pain_point: 'sleep', struggle_frequency: 'daily' } });
  const c = simulate({ personId: 'lm_a', profile: { desired_state: 'focus', pain_point: 'stress', struggle_frequency: 'weekly' } });
  for (const row of [a, b, c]) assert.equal(appendLedger(row, { ledgerPath }), true);
  const stats = ledgerStats({ ledgerPath });
  assert.equal(stats.rows, 3);
  assert.equal(stats.distinct_persons, 2);
  assert.equal(stats.engine, 'anicca-society-sim-run2-v1');
  assert.ok(stats.by_category[a.decision.category] >= 1);
});

test('missing ledger is empty stats, not an error', (t) => {
  const ledgerPath = tempLedger(t);
  assert.deepEqual(ledgerStats({ ledgerPath }), { engine: 'anicca-society-sim-run2-v1', rows: 0, distinct_persons: 0, by_category: {}, last_simulated_at: null });
  assert.equal(defaultLedgerPath({ LM_SIM_STATE_DIR: '/tmp/lm-sim-test' }), '/tmp/lm-sim-test/per-user-predictions.jsonl');
});
