import test from 'node:test';
import assert from 'node:assert/strict';

import { activateExperiment, sellerLabelFor } from '../store-activate.mjs';

test('sellerLabelFor maps each isolated agent home to its own launchd seller', () => {
  assert.equal(sellerLabelFor({ ANICCA_HOME: '/Users/a/.blockrun' }), 'ai.anicca.x402-franklin1');
  assert.equal(sellerLabelFor({ ANICCA_HOME: '/Users/a/.franklin2-home/.blockrun' }), 'ai.anicca.x402-franklin2');
  assert.equal(sellerLabelFor({ ANICCA_HOME: '/Users/a/.anicca-founder' }), 'ai.anicca.x402-claude-p');
  assert.equal(sellerLabelFor({ ANICCA_HOME: '/tmp/unknown' }), null);
});

test('activateExperiment restarts only the matching seller then re-registers', async () => {
  const calls = [];
  const out = await activateExperiment(
    { ANICCA_HOME: '/Users/a/.blockrun', X402_PUBLIC_URL: 'https://seller.example' },
    {
      restart: async (label) => calls.push(['restart', label]),
      wait: async () => calls.push(['wait']),
      update: async () => { calls.push(['update']); return { registered: true, productCount: 5 }; },
    },
  );

  assert.deepEqual(calls, [
    ['restart', 'ai.anicca.x402-franklin1'],
    ['wait'],
    ['update'],
  ]);
  assert.deepEqual(out, { activated: true, restarted: true, registered: true, productCount: 5 });
});

test('activateExperiment fails honestly for an unknown home and performs no side effect', async () => {
  let called = false;
  const out = await activateExperiment({ ANICCA_HOME: '/tmp/unknown' }, {
    restart: async () => { called = true; },
    update: async () => { called = true; },
  });
  assert.equal(called, false);
  assert.deepEqual(out, { activated: false, restarted: false, reason: 'unknown seller instance' });
});
