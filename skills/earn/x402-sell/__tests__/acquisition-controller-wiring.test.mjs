import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('acquisition controller is a five-minute one-shot LaunchAgent with a private action log', () => {
  const runner = readFileSync(new URL('../acquisition-controller.mjs', import.meta.url), 'utf8');
  const boot = readFileSync(new URL('../acquisition-controller-boot.sh', import.meta.url), 'utf8');
  const plist = readFileSync(new URL('../launchd/ai.anicca.x402-acquisition-controller.plist', import.meta.url), 'utf8');

  assert.match(runner, /runAcquisitionCycle/);
  assert.match(runner, /the402-inbox\.sqlite/);
  assert.match(runner, /x402-acquisition-actions\.jsonl/);
  assert.match(runner, /0o600/);
  assert.doesNotMatch(runner, /Moltbook|posts\/.*comments|create.*post/i);
  assert.match(boot, /exec \/usr\/bin\/env node "\$DIR\/acquisition-controller\.mjs"/);
  assert.match(plist, /<string>ai\.anicca\.x402-acquisition-controller<\/string>/);
  assert.match(plist, /<key>RunAtLoad<\/key><true\/>/);
  assert.match(plist, /<key>StartInterval<\/key><integer>300<\/integer>/);
  assert.doesNotMatch(plist, /<key>KeepAlive<\/key>/);
});
