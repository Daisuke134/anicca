import test from 'node:test';
import assert from 'node:assert/strict';

import { classifyTask, selectTask } from './taskmarket-work.mjs';

const NOW = Date.parse('2026-07-28T08:00:00Z');
const IMAGE_BRIEF = [
  'Make one still image, 1:1 square.',
  'FLOOR: made with a real frontier image model such as GPT Image 2 or better.',
  'DELIVER: one finished hero image, plus concept-note.md and sources.md.',
].join(' ');

function task(overrides = {}) {
  return {
    id: '0x' + '1'.repeat(64),
    status: 'open',
    phase: 'active',
    submissionWindowOpen: true,
    stakeRequired: false,
    description: IMAGE_BRIEF,
    reward: '5000000',
    netReward: '4625000',
    submissionCount: 20,
    expiryTime: '2026-07-29T08:00:00Z',
    ...overrides,
  };
}

test('classifyTask accepts one unstaked frontier still-image delivery', () => {
  assert.deepEqual(classifyTask(task(), { maxImageCostUsd: 0.06 }), {
    supported: true,
    reason: 'supported_still_image',
  });
});

test('classifyTask rejects closed, staked, unsupported, and uneconomic tasks', () => {
  assert.equal(classifyTask(task({ submissionWindowOpen: false }), { maxImageCostUsd: 0.06 }).reason, 'submission_window_closed');
  assert.equal(classifyTask(task({ stakeRequired: true }), { maxImageCostUsd: 0.06 }).reason, 'stake_required');
  assert.equal(classifyTask(task({ description: 'Produce one short film with three scenes.' }), { maxImageCostUsd: 0.06 }).reason, 'unsupported_deliverable');
  assert.equal(classifyTask(task({ netReward: '1100000' }), { maxImageCostUsd: 0.06 }).reason, 'reward_below_20x_cost');
});

test('selectTask excludes owned submissions and ranks expiry, competition, then reward', () => {
  const submittedId = '0x' + '2'.repeat(64);
  const laterLowCompetition = task({
    id: '0x' + '3'.repeat(64),
    expiryTime: '2026-07-30T08:00:00Z',
    submissionCount: 1,
    netReward: '9000000',
  });
  const earliestCrowded = task({
    id: '0x' + '4'.repeat(64),
    expiryTime: '2026-07-29T07:00:00Z',
    submissionCount: 50,
  });
  const earliestSparse = task({
    id: '0x' + '5'.repeat(64),
    expiryTime: '2026-07-29T07:00:00Z',
    submissionCount: 10,
    netReward: '4000000',
  });
  const alreadySubmitted = task({ id: submittedId, expiryTime: '2026-07-28T09:00:00Z' });

  const selected = selectTask({
    tasks: [laterLowCompetition, earliestCrowded, alreadySubmitted, earliestSparse],
    submissions: [{ id: 'sub_1', taskId: submittedId }],
    now: NOW,
    maxImageCostUsd: 0.06,
  });

  assert.equal(selected.id, earliestSparse.id);
});

test('selectTask returns null for expired or unsupported inventory', () => {
  const selected = selectTask({
    tasks: [
      task({ expiryTime: '2026-07-28T07:59:59Z' }),
      task({ description: 'Build a single-page flashcard web app.' }),
    ],
    submissions: [],
    now: NOW,
    maxImageCostUsd: 0.06,
  });
  assert.equal(selected, null);
});
