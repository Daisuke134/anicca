import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('normalized candidates are reverified and recorded by a five-minute one-shot LaunchAgent', () => {
  const runner = readFileSync(new URL('../settlement-recorder.mjs', import.meta.url), 'utf8');
  const boot = readFileSync(new URL('../settlement-recorder-boot.sh', import.meta.url), 'utf8');
  const plist = readFileSync(new URL('../launchd/ai.anicca.x402-settlement-recorder.plist', import.meta.url), 'utf8');

  assert.match(runner, /x402-sale-candidates\.jsonl/);
  assert.match(runner, /collectVerifiedSaleCandidates/);
  assert.match(runner, /appendUniqueExternalInflows/);
  assert.match(runner, /walletLedgerPath/);
  assert.match(runner, /SELF_WALLETS/);
  assert.match(runner, /verified_external_revenue/);
  assert.match(boot, /exec \/usr\/bin\/env node "\$DIR\/settlement-recorder\.mjs"/);
  assert.match(plist, /<string>ai\.anicca\.x402-settlement-recorder<\/string>/);
  assert.match(plist, /<key>RunAtLoad<\/key><true\/>/);
  assert.match(plist, /<key>StartInterval<\/key><integer>300<\/integer>/);
  assert.doesNotMatch(plist, /<key>KeepAlive<\/key>/);
});
