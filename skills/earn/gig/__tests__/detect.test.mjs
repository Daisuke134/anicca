// node:test — detect() shape + safety (offline-safe). Real network is exercised by the
// E2E wake (task #10), not here. Here we assert: never throws, always a valid feed shape,
// no creds ⇒ dealwork contributes 0 (never invents jobs), output is JSON-serializable.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import { detect } from '../lib/detect.mjs';

test('returns a valid feed shape even with no creds / network blocked', async () => {
  const f = await detect({ envFile: path.join(os.tmpdir(), 'nonexistent-' + Date.now() + '.env') });
  assert.equal(typeof f.generated_at, 'number');
  assert.ok(f.counts && typeof f.counts.total === 'number');
  assert.ok(Array.isArray(f.jobs));
  // no creds ⇒ dealwork cannot have contributed (anti-fabrication)
  assert.equal(f.counts.dealwork, 0);
  // serializable
  assert.doesNotThrow(() => JSON.stringify(f));
});
