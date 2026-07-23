import test from 'node:test';
import assert from 'node:assert/strict';
import { createSiweMessage } from 'viem/siwe';

import { validateSpawnxchangeChallenge } from '../lib/spawnxchange-channel.mjs';

const ADDRESS = '0x3EcCAD24794ca298D25378E9902A251322ea8749';
const NOW_MS = Date.parse('2026-07-23T02:21:30.000Z');

function challenge(overrides = {}) {
  return createSiweMessage({
    address: ADDRESS,
    chainId: 8453,
    domain: 'spawnxchange.com',
    nonce: 'AbCdEf12',
    statement: 'Register on SpawnXchange',
    uri: 'https://spawnxchange.com',
    version: '1',
    issuedAt: new Date('2026-07-23T02:21:22.000Z'),
    expirationTime: new Date('2026-07-23T02:26:22.000Z'),
    ...overrides,
  });
}

test('accepts only the pinned, short-lived Base registration challenge', () => {
  assert.deepEqual(validateSpawnxchangeChallenge({
    message: challenge(),
    expectedAddress: ADDRESS,
    nowMs: NOW_MS,
  }), {
    domain: 'spawnxchange.com',
    address: ADDRESS.toLowerCase(),
    chainId: 8453,
    expirationTime: '2026-07-23T02:26:22.000Z',
  });

  const rejected = [
    challenge({ domain: 'evil.example' }),
    challenge({ chainId: 1 }),
    challenge({ statement: 'Transfer all funds' }),
    challenge({ uri: 'https://evil.example' }),
    challenge({ expirationTime: new Date('2026-07-23T03:21:22.000Z') }),
  ];
  for (const message of rejected) {
    assert.throws(() => validateSpawnxchangeChallenge({ message, expectedAddress: ADDRESS, nowMs: NOW_MS }));
  }
});
