import test from 'node:test';
import assert from 'node:assert/strict';

import { inspectX402Challenge } from '../src/inspector.mjs';

const challenge = {
  x402Version: 2,
  accepts: [{
    scheme: 'exact',
    network: 'eip155:8453',
    amount: '30000',
    asset: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    payTo: '0x2222222222222222222222222222222222222222',
    maxTimeoutSeconds: 300,
  }],
};

test('decodes a Base64 x402 v2 challenge into a strict allowlisted summary', () => {
  const header = Buffer.from(JSON.stringify(challenge)).toString('base64');
  assert.deepEqual(inspectX402Challenge(header), {
    x402Version: 2,
    accepts: [{
      scheme: 'exact',
      network: 'eip155:8453',
      amount: '30000',
      asset: '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913',
      payTo: '0x2222222222222222222222222222222222222222',
      maxTimeoutSeconds: 300,
    }],
  });
});

test('rejects unsupported versions, malformed requirements, duplicates, and oversized input', () => {
  const invalid = [
    { ...challenge, x402Version: 1 },
    { ...challenge, accepts: [{ ...challenge.accepts[0], scheme: 'upto' }] },
    { ...challenge, accepts: [{ ...challenge.accepts[0], network: 'base' }] },
    { ...challenge, accepts: [{ ...challenge.accepts[0], amount: '-1' }] },
    { ...challenge, accepts: [{ ...challenge.accepts[0], payTo: 'not-an-address' }] },
    { ...challenge, accepts: [challenge.accepts[0], challenge.accepts[0]] },
    'x'.repeat(70 * 1024),
  ];
  for (const value of invalid) assert.throws(() => inspectX402Challenge(value));
});
