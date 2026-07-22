import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const runScript = readFileSync(join(here, '..', '..', 'run.sh'), 'utf8');

test('every x402 wake evaluates the five-minute revenue experiment before the model action', () => {
  const controller = runScript.indexOf('# FIVE-MINUTE REVENUE CONTROLLER');
  const firstActionBranch = runScript.indexOf('if [ "$ACTION" = "review" ]; then');

  assert.notEqual(controller, -1, 'missing deterministic five-minute controller wiring');
  assert.ok(controller < firstActionBranch, 'controller must run before any model-selected action can exit');
  assert.equal(
    (runScript.match(/node "\$X402DIR\/store-improve\.mjs"/g) || []).length,
    1,
    'controller must be invoked once per wake, not duplicated by action=improve',
  );
});
