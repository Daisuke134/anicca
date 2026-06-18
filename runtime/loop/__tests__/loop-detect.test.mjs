// PROP-008, PROP-009 — loop-detect.mjs unit tests
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isLooping } from '../loop-detect.mjs';

// PROP-008: last 3 identical -> true
test('PROP-008: returns true when last 3 entries are identical', () => {
  const actions = [
    { slot: 'earn', args: {} },
    { slot: 'earn', args: {} },
    { slot: 'earn', args: {} },
  ];
  assert.equal(isLooping(actions, 3), true);
});

// PROP-008: last 3 identical with mixed earlier history
test('PROP-008: true when last 3 identical even with different earlier entries', () => {
  const actions = [
    { slot: 'report', args: {} },
    { slot: 'earn', args: {} },
    { slot: 'earn', args: {} },
    { slot: 'earn', args: {} },
  ];
  assert.equal(isLooping(actions, 3), true);
});

// PROP-008: window of 1 with repeated call -> true
test('PROP-008: window of 1 detects immediately on first repeated call', () => {
  const actions = [{ slot: 'earn', args: {} }];
  assert.equal(isLooping(actions, 1), true);
});

// PROP-008: same slot but different args -> false (not looping)
test('PROP-008: false when args differ between identical slots', () => {
  const actions = [
    { slot: 'earn', args: { mode: 'discover' } },
    { slot: 'earn', args: { mode: 'execute' } },
    { slot: 'earn', args: { mode: 'discover' } },
  ];
  assert.equal(isLooping(actions, 3), false);
});

// PROP-009: fewer than window entries -> false
test('PROP-009: returns false when fewer than window entries', () => {
  const actions = [
    { slot: 'earn', args: {} },
    { slot: 'earn', args: {} },
  ];
  assert.equal(isLooping(actions, 3), false);
});

// PROP-009: empty array -> false
test('PROP-009: returns false for empty array', () => {
  assert.equal(isLooping([], 3), false);
});

// PROP-009: single entry with window=3 -> false
test('PROP-009: single entry with window=3 returns false', () => {
  assert.equal(isLooping([{ slot: 'earn', args: {} }], 3), false);
});

// PROP-009: window=0 is treated as disabled (never looping)
test('PROP-009: window=0 always returns false (disabled)', () => {
  const actions = [{ slot: 'earn', args: {} }, { slot: 'earn', args: {} }, { slot: 'earn', args: {} }];
  assert.equal(isLooping(actions, 0), false);
});

// Different slots -> not looping
test('PROP-009: different slots in window -> false', () => {
  const actions = [
    { slot: 'earn', args: {} },
    { slot: 'report', args: {} },
    { slot: 'earn', args: {} },
  ];
  assert.equal(isLooping(actions, 3), false);
});

// Exactly window-1 identical entries -> false
test('PROP-009: exactly window-1 identical entries returns false', () => {
  const actions = [
    { slot: 'earn', args: {} },
    { slot: 'earn', args: {} },
  ];
  assert.equal(isLooping(actions, 3), false);
});
