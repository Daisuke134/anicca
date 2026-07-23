import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('sale observer is wired as a five-minute one-shot LaunchAgent with a private candidate store', () => {
  const runner = readFileSync(new URL('../sale-observer.mjs', import.meta.url), 'utf8');
  const boot = readFileSync(new URL('../sale-observer-boot.sh', import.meta.url), 'utf8');
  const plist = readFileSync(new URL('../launchd/ai.anicca.x402-sale-observer.plist', import.meta.url), 'utf8');

  assert.match(runner, /appendUniqueSaleCandidates/);
  assert.match(runner, /x402-sale-candidates\.jsonl/);
  assert.match(runner, /import\.meta\.url ===/);
  assert.match(runner, /candidate_not_verified_revenue/);
  assert.doesNotMatch(runner, /console\.(?:log|error)\([^\n]*(?:apiKey|api_key|credentials)/i);
  assert.match(boot, /exec \/usr\/bin\/env node "\$DIR\/sale-observer\.mjs"/);
  assert.match(plist, /<string>ai\.anicca\.x402-sale-observer<\/string>/);
  assert.match(plist, /<key>RunAtLoad<\/key><true\/>/);
  assert.match(plist, /<key>StartInterval<\/key><integer>300<\/integer>/);
  assert.doesNotMatch(plist, /<key>KeepAlive<\/key>/);
});
