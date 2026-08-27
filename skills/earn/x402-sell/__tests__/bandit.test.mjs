import test from 'node:test';
import assert from 'node:assert/strict';

import { allocateBandit } from '../bandit.mjs';

const products = [
  { path: '/winner', external: 2, attempts: 10, ageWakes: 100 },
  { path: '/new-product', external: 0, attempts: 2, ageWakes: 5 },
  { path: '/never-earned', external: 0, attempts: 40, ageWakes: 60 },
];

test('allocateBandit classifies products by external earnings and maturity', () => {
  const result = allocateBandit(products);
  const decisions = Object.fromEntries(result.ranked.map(({ path, decision }) => [path, decision]));

  assert.equal(decisions['/winner'], 'KEEP');
  assert.equal(decisions['/new-product'], 'EXPLORE');
  assert.equal(decisions['/never-earned'], 'DROP');
  assert.deepEqual(result.keep, ['/winner']);
  assert.deepEqual(result.explore, ['/new-product']);
  assert.deepEqual(result.drop, ['/never-earned']);
});

test('allocateBandit sums total attempts', () => {
  assert.equal(allocateBandit(products).totalAttempts, 52);
});

test('allocateBandit calculates UCB1-style score components', () => {
  const result = allocateBandit(products);
  const winner = result.ranked.find(({ path }) => path === '/winner');
  const expectedExploration = 1.5 * Math.sqrt(Math.log(53) / 11);

  assert.equal(winner.exploitation, 0.2);
  assert.equal(winner.exploration, expectedExploration);
  assert.equal(winner.score, 0.2 + expectedExploration);
});

test('allocateBandit ranks products by descending score', () => {
  const result = allocateBandit(products);

  assert.deepEqual(result.ranked.map(({ path }) => path), [
    '/new-product',
    '/winner',
    '/never-earned',
  ]);
  assert.ok(result.ranked.every((item, index, ranked) => index === 0 || ranked[index - 1].score >= item.score));
});
