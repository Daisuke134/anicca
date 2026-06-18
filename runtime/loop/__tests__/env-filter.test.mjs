// PROP-005, PROP-006, PROP-018, PROP-020 — env-filter.mjs unit tests
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scrubPrivateKeys } from '../env-filter.mjs';

// PROP-005: removes _WALLET_KEY suffix pattern
test('PROP-005: removes BLOCKRUN_WALLET_KEY', () => {
  const env = { BLOCKRUN_WALLET_KEY: '0xdeadbeef', PATH: '/usr/bin' };
  const result = scrubPrivateKeys(env);
  assert.equal(result.BLOCKRUN_WALLET_KEY, undefined);
  assert.equal(result.PATH, '/usr/bin');
});

// PROP-005: removes _PRIVATE_KEY suffix
test('PROP-005: removes MY_PRIVATE_KEY', () => {
  const env = { MY_PRIVATE_KEY: 'secret', OTHER: 'keep' };
  const result = scrubPrivateKeys(env);
  assert.equal(result.MY_PRIVATE_KEY, undefined);
  assert.equal(result.OTHER, 'keep');
});

// PROP-005: removes _PRIV_KEY suffix
test('PROP-005: removes WALLET_PRIV_KEY', () => {
  const env = { WALLET_PRIV_KEY: 'secret', SAFE: 'keep' };
  const result = scrubPrivateKeys(env);
  assert.equal(result.WALLET_PRIV_KEY, undefined);
  assert.equal(result.SAFE, 'keep');
});

// PROP-005: removes all matching keys from a mixed env
test('PROP-005: removes all matching keys from mixed env', () => {
  const env = {
    BLOCKRUN_WALLET_KEY: 'v1',
    ETH_PRIVATE_KEY: 'v2',
    MY_PRIV_KEY: 'v3',
    NODE_ENV: 'test',
    HOME: '/home/user',
  };
  const result = scrubPrivateKeys(env);
  assert.equal(result.BLOCKRUN_WALLET_KEY, undefined);
  assert.equal(result.ETH_PRIVATE_KEY, undefined);
  assert.equal(result.MY_PRIV_KEY, undefined);
  assert.equal(result.NODE_ENV, 'test');
  assert.equal(result.HOME, '/home/user');
});

// PROP-006: idempotent — calling twice returns same filtered result
test('PROP-006: scrubPrivateKeys is idempotent', () => {
  const env = { BLOCKRUN_WALLET_KEY: 'secret', SAFE: 'keep' };
  const once = scrubPrivateKeys(env);
  const twice = scrubPrivateKeys(once);
  assert.deepEqual(once, twice);
  assert.equal(twice.BLOCKRUN_WALLET_KEY, undefined);
});

// PROP-006: idempotent does not mutate original
test('PROP-006: does not mutate original env', () => {
  const env = { BLOCKRUN_WALLET_KEY: 'secret', SAFE: 'keep' };
  scrubPrivateKeys(env);
  assert.equal(env.BLOCKRUN_WALLET_KEY, 'secret'); // original unchanged
});

// PROP-018: BLOCKRUN_WALLET_KEY always removed regardless of env shape
test('PROP-018: BLOCKRUN_WALLET_KEY always removed', () => {
  const envs = [
    { BLOCKRUN_WALLET_KEY: 'a' },
    { BLOCKRUN_WALLET_KEY: '', OTHER: 'x' },
    { BLOCKRUN_WALLET_KEY: null, X: 'y' },
  ];
  for (const env of envs) {
    const result = scrubPrivateKeys(env);
    assert.ok(!('BLOCKRUN_WALLET_KEY' in result), 'BLOCKRUN_WALLET_KEY must not be in result');
  }
});

// PROP-020: wallet address (40-hex 0x…) is permitted — not scrubbed
test('PROP-020: wallet address (0x + 40 hex) is NOT scrubbed', () => {
  const addr = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'.slice(0, 42);
  const env = { ANICCA_WALLET_ADDRESS: addr, SAFE: 'keep' };
  const result = scrubPrivateKeys(env);
  assert.equal(result.ANICCA_WALLET_ADDRESS, addr);
});

// PROP-020: 64-hex private key pattern detection in a string
test('PROP-020: private key pattern (0x + 64 hex) detected in observation string', async () => {
  // The scrub module exports a helper to detect and redact private-key patterns in strings
  const { redactPrivateKeyPatterns } = await import('../env-filter.mjs');
  const privKey = '0x' + 'a'.repeat(64);
  const obs = `output: ${privKey} end`;
  const redacted = redactPrivateKeyPatterns(obs);
  assert.ok(!redacted.includes(privKey), 'private key must be redacted');
  assert.ok(redacted.includes('[REDACTED]'), 'must contain [REDACTED] marker');
});

// PROP-020: wallet address (40 hex) survives redactPrivateKeyPatterns
test('PROP-020: wallet address survives redactPrivateKeyPatterns', async () => {
  const { redactPrivateKeyPatterns } = await import('../env-filter.mjs');
  const addr = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA9604';
  const obs = `wallet=${addr}`;
  const redacted = redactPrivateKeyPatterns(obs);
  assert.ok(redacted.includes(addr), 'wallet address must survive');
});
