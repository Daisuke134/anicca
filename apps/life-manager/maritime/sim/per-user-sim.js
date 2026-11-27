'use strict';
// Per-user behaviour simulation (Anicca × Maritime, First 1,000).
// Implements the frozen Run-2 model from
// tools/society-sim/run2_maritime_per_user.py (anicca-ops) in pure Node so it
// can run inside the Maritime tenant VM with no extra dependencies.
//
// Input : one person's onboarding answers (desired_state, pain_point,
//         struggle_frequency) plus optional local_hour.
// Output: a scored candidate set and the single intervention the simulator
//         selects, with timing and amount. Manager decides; the user is never
//         asked to configure timing, amount or wording.
//
// This is a simulation: outputs are hypotheses for this person, not measured
// effects on humans. Observed outcomes are logged separately for evaluation.

const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');

const ENGINE = 'anicca-society-sim-run2-v1';
const DESIRED = ['confidence', 'focus', 'calm', 'energy'];
const PAINS = ['stress', 'anxiety', 'sleep', 'self_doubt'];
const FREQS = ['rarely', 'weekly', 'daily', 'many_times_daily'];
const CATEGORIES = ['confidence', 'focus', 'stress_relief', 'grounding', 'rest', 'self_compassion', 'gratitude'];
const FREQ_NEED = { rarely: 0.0, weekly: 0.04, daily: 0.09, many_times_daily: 0.13 };
const FREQ_BURDEN = { rarely: 0.05, weekly: 0.02, daily: 0.0, many_times_daily: -0.02 };
const NUDGES_PER_DAY = { rarely: 1, weekly: 1, daily: 2, many_times_daily: 3 };
// Row = desired_state, column = category. Source: files/onboarding-answer-change-mapping-2026-11-14.md
const FIT_DESIRED = {
  confidence: [1.0, 0.4, 0.3, 0.3, 0.2, 0.8, 0.5],
  focus: [0.4, 1.0, 0.3, 0.6, 0.2, 0.2, 0.3],
  calm: [0.3, 0.3, 0.9, 1.0, 0.7, 0.6, 0.5],
  energy: [0.6, 0.7, 0.2, 0.2, 0.4, 0.3, 0.6],
};
const FIT_PAIN = {
  stress: [0.3, 0.3, 1.0, 0.7, 0.5, 0.5, 0.4],
  anxiety: [0.3, 0.2, 0.7, 1.0, 0.5, 0.7, 0.3],
  sleep: [0.1, 0.1, 0.5, 0.5, 1.0, 0.3, 0.3],
  self_doubt: [0.9, 0.3, 0.3, 0.3, 0.2, 1.0, 0.6],
};
// Plain-language copy for the selected intervention. One line each; no claims.
const COPY = {
  confidence: 'One sentence about a thing you already did well.',
  focus: 'One sentence naming the single next action.',
  stress_relief: 'One slow breath and one sentence that names the pressure.',
  grounding: 'One sentence about what is physically around you right now.',
  rest: 'One sentence that gives tonight permission to be enough.',
  self_compassion: 'One sentence you would say to a friend in your place.',
  gratitude: 'One sentence about one small thing that went right.',
};
const WINDOW = [
  { until: 11, name: 'morning', local: '07:30' },
  { until: 17, name: 'midday', local: '12:30' },
  { until: 22, name: 'evening', local: '20:30' },
  { until: 24, name: 'late', local: '22:30' },
];

function clamp(value, low, high) { return Math.min(high, Math.max(low, value)); }

function validateProfile(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { error: 'profile_required' };
  const { desired_state: desired, pain_point: pain, struggle_frequency: freq } = raw;
  if (!DESIRED.includes(desired)) return { error: 'desired_state_invalid' };
  if (!PAINS.includes(pain)) return { error: 'pain_point_invalid' };
  if (!FREQS.includes(freq)) return { error: 'struggle_frequency_invalid' };
  let localHour = null;
  if (raw.local_hour !== undefined && raw.local_hour !== null) {
    if (!Number.isInteger(raw.local_hour) || raw.local_hour < 0 || raw.local_hour > 23) return { error: 'local_hour_invalid' };
    localHour = raw.local_hour;
  }
  return { profile: { desired_state: desired, pain_point: pain, struggle_frequency: freq, local_hour: localHour } };
}

function windowFor(localHour) {
  if (localHour === null || localHour === undefined) return WINDOW[0];
  return WINDOW.find(window => localHour < window.until) || WINDOW[WINDOW.length - 1];
}

// Frozen Run-2 equations. Fit = 0.5 * fit(desired) + 0.5 * fit(pain).
// p = clip(0.18 + 0.38 * fit + need - burden, 0.02, 0.92).
function simulate({ profile, personId = null }) {
  const desired = FIT_DESIRED[profile.desired_state];
  const pain = FIT_PAIN[profile.pain_point];
  const need = FREQ_NEED[profile.struggle_frequency];
  const burden = FREQ_BURDEN[profile.struggle_frequency];
  const candidates = CATEGORIES.map((category, index) => {
    const fit = Math.round((0.5 * desired[index] + 0.5 * pain[index]) * 10000) / 10000;
    const probability = Math.round(clamp(0.18 + 0.38 * fit + need - burden, 0.02, 0.92) * 10000) / 10000;
    return { category, fit, predicted_daily_response_probability: probability };
  }).sort((a, b) => b.fit - a.fit || a.category.localeCompare(b.category));
  const top = candidates[0];
  const second = candidates[1];
  const genericFit = candidates.reduce((sum, candidate) => sum + candidate.fit, 0) / candidates.length;
  const window = windowFor(profile.local_hour);
  return {
    engine: ENGINE,
    simulation_id: randomUUID(),
    person_id: personId,
    input: profile,
    candidates,
    decision: {
      category: top.category,
      predicted_daily_response_probability: top.predicted_daily_response_probability,
      fit_margin_over_next: Math.round((top.fit - second.fit) * 10000) / 10000,
      nudges_per_day: NUDGES_PER_DAY[profile.struggle_frequency],
      delivery_window: window.name,
      delivery_at_local: window.local,
      first_line: COPY[top.category],
    },
    baseline: {
      policy: 'generic_uniform_category',
      expected_fit: Math.round(genericFit * 10000) / 10000,
      chosen_fit: top.fit,
    },
    history_used: false,
    synthetic_input: personId ? false : true,
    simulated_at: new Date().toISOString(),
    disclaimer: 'simulation hypothesis, not measured effect on a human',
  };
}

function defaultLedgerPath(env = process.env) {
  const root = env.LM_SIM_STATE_DIR
    || path.join('/data', env.LM_RUNTIME_TENANT_ID || 'unknown', 'state', 'sim');
  return path.join(root, 'per-user-predictions.jsonl');
}

function appendLedger(result, { ledgerPath = defaultLedgerPath(), fsImpl = fs } = {}) {
  try {
    fsImpl.mkdirSync(path.dirname(ledgerPath), { recursive: true, mode: 0o700 });
    fsImpl.appendFileSync(ledgerPath, JSON.stringify(result) + '\n', { mode: 0o600 });
    return true;
  } catch { return false; }
}

function readLedger({ ledgerPath = defaultLedgerPath(), limit = 1000, fsImpl = fs } = {}) {
  try {
    const lines = fsImpl.readFileSync(ledgerPath, 'utf8').split('\n').filter(Boolean);
    return lines.slice(-limit).map(line => { try { return JSON.parse(line); } catch { return null; } }).filter(Boolean);
  } catch { return []; }
}

function ledgerStats(options = {}) {
  const rows = readLedger(options);
  const byCategory = {};
  for (const row of rows) {
    const category = row?.decision?.category || 'unknown';
    byCategory[category] = (byCategory[category] || 0) + 1;
  }
  return {
    engine: ENGINE,
    rows: rows.length,
    distinct_persons: new Set(rows.map(row => row.person_id).filter(Boolean)).size,
    by_category: byCategory,
    last_simulated_at: rows.length ? rows[rows.length - 1].simulated_at : null,
  };
}

module.exports = { ENGINE, CATEGORIES, DESIRED, PAINS, FREQS, validateProfile, simulate, defaultLedgerPath, appendLedger, readLedger, ledgerStats };
