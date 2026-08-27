import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { runExperimentTick } from '../experiment-tick.mjs';

const here = dirname(fileURLToPath(import.meta.url));

test('independent tick activates only a newly applied experiment', async () => {
  const calls = [];
  const result = await runExperimentTick({}, {
    improve: () => ({ experiment: { action: 'applied', price: '$0.012' } }),
    activate: async () => { calls.push('activate'); return { activated: true }; },
  });
  assert.deepEqual(calls, ['activate']);
  assert.equal(result.activation.activated, true);
});

test('waiting tick is read-only and does not restart the seller', async () => {
  let activated = false;
  const result = await runExperimentTick({}, {
    improve: () => ({ experiment: { action: 'waiting', price: '$0.015' } }),
    activate: async () => { activated = true; },
  });
  assert.equal(activated, false);
  assert.equal(result.experiment.action, 'waiting');
});

test('franklin1 launchd runs the controller independently every five minutes', () => {
  const plist = readFileSync(join(here, '..', 'launchd', 'ai.anicca.x402-experiment-franklin1.plist'), 'utf8');
  assert.match(plist, /<key>StartInterval<\/key>\s*<integer>300<\/integer>/);
  assert.match(plist, /<key>RunAtLoad<\/key>\s*<true\/>/);
  assert.match(plist, /<string>\/Users\/anicca\/anicca\/skills\/earn\/x402-sell\/experiment-tick\.mjs<\/string>/);
  assert.match(plist, /<key>ANICCA_HOME<\/key>\s*<string>\/Users\/anicca\/\.blockrun<\/string>/);
});
