// franklin-ledger-push (P2) — behavioral-spec.md REQ-701..709 / verification-architecture.md
// PROP-701..7xx. impl-review iter2 rewrite (FIND-001..006): the orchestrator now publishes BOTH a
// wake source (state/ledger.jsonl) and an earn/money source (skills/earn/state/earn-ledger.jsonl,
// FIND-001) onto the same dedicated per-instance orphan branch as two separate files, and NEVER
// trusts the marker's cached pushedLineCount as ground truth (FIND-002) -- every cycle reconciles
// each source's cursor directly against the actual, just-synced destination file's line count. The
// effectful-shell tests below use REAL git (mirrors skills/earn/lib/__tests__/evolve.test.mjs's own
// established real-git-in-tmp-dir precedent) against a `file://` BARE-repo fixture created fresh per
// test. NO test in this file ever touches the real the canonical checkout repo, a real remote, or the network --
// every "origin" is a throwaway bare repo under os.tmpdir(). Pure-core tests run with zero I/O; for
// the non-fatality/setup-failure paths an injected mock `git` is still used (no real git needed).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

import {
  decidePublish,
  extractWakeId,
  extractEarnRef,
  projectWakeLine,
  projectEarnLine,
  redactBroaderSecretPatterns,
  publishLedgerCycle,
  DEFAULT_MIN_LINES,
  DEFAULT_MIN_INTERVAL_MS,
} from '../ledger-publish.mjs';
// impl-review iter3 FIND-001: import the REAL classifier (never a re-implementation of its logic)
// so the projection tests prove the published line actually round-trips through the repo's own
// single source of truth for "is this a profitable, GATE-0 earn".
import { isProfitable } from '../../../skills/_shared/lib/ledger.mjs';

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function fileUrl(p) {
  return 'file://' + p;
}

function sh(args, cwd) {
  return execFileSync('git', args, { cwd, encoding: 'utf8' });
}

function writeLines(filePath, objs) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, objs.map((o) => JSON.stringify(o)).join('\n') + '\n');
}

function makeLines(n, offset = 0) {
  return Array.from({ length: n }, (_, i) => ({ ts: i + offset, wake_id: `w${i + offset}`, kind: 'wake', sleep_s: 120, profitable: false }));
}

function makeEarnLines(n, offset = 0) {
  return Array.from({ length: n }, (_, i) => ({
    ts: i + offset, wallet: '0xabc', source: 'sol-trade', task: `wake ${i + offset} swap`,
    earn_usdc: 1.5, cost_usdc: 0, net_usdc: 1.5, wake: `e${i + offset}`,
  }));
}

// Bare "origin" repo + a "shared checkout" cloned from it (mirrors this repo's own real topology:
// `repoRoot` here plays the role of `the canonical checkout`'s shared checkout; ledger-publish.mjs reads ONLY
// `git remote get-url origin` from it and never anything else).
function setupOrigin(dir) {
  const originDir = path.join(dir, 'origin.git');
  const sharedCheckout = path.join(dir, 'shared-checkout');
  fs.mkdirSync(originDir, { recursive: true });
  sh(['init', '--bare', '-q', '-b', 'main', originDir]);
  sh(['clone', '-q', fileUrl(originDir), sharedCheckout]);
  sh(['-c', 'user.name=t', '-c', 'user.email=t@t.local', 'commit', '--allow-empty', '-q', '-m', 'init'], sharedCheckout);
  sh(['push', '-q', 'origin', 'main'], sharedCheckout);
  return { originDir, sharedCheckout };
}

function cloneBranch(originDir, branch) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ledger-publish-verify-'));
  sh(['clone', '-q', '--branch', branch, '--single-branch', fileUrl(originDir), dir]);
  return dir;
}

function readLines(filePath) {
  if (!fs.existsSync(filePath)) return [];
  return fs.readFileSync(filePath, 'utf8').split('\n').filter((l) => l.trim().length > 0);
}

// A mock git recorder for the pure non-fatality / setup-failure paths (no real git process).
function makeMockGit({ failOn = [] } = {}) {
  const calls = [];
  const git = (args, cwd) => {
    calls.push({ args, cwd });
    if (failOn.includes(args[0])) throw new Error(`mock git failure: ${args.join(' ')}`);
    return '';
  };
  return { git, calls };
}

const realGit = (args, cwd) => execFileSync('git', args, { cwd, encoding: 'utf8' });

function baseOpts(dir, instance = 'franklin') {
  return {
    enabled: true,
    ledgerPath: path.join(dir, 'home', 'state', 'ledger.jsonl'),
    markerPath: path.join(dir, 'home', 'state', '.ledger-publish-marker'),
    instance,
    now: () => 0,
  };
}

function publishRepoDirFor(dir) {
  return path.join(dir, 'home', 'state', '.ledger-publish-repo');
}

// ── REQ-704 / PROP-701..704: decidePublish (pure throttle decision) — unchanged by the redesign ──

test('PROP-701: pendingLineCount<=0 never pushes, regardless of nowMs/lastPushTs', () => {
  assert.equal(decidePublish({ pendingLineCount: 0, lastPushTs: 0, nowMs: 999_999_999 }).shouldPush, false);
  assert.equal(decidePublish({ pendingLineCount: -1, lastPushTs: 0, nowMs: 999_999_999 }).shouldPush, false);
});

test('PROP-702: pendingLineCount >= DEFAULT_MIN_LINES(10) always pushes, even with zero elapsed time', () => {
  const decision = decidePublish({ pendingLineCount: DEFAULT_MIN_LINES, lastPushTs: 1000, nowMs: 1000 });
  assert.equal(decision.shouldPush, true);
  assert.equal(decision.reason, 'line-threshold');
});

test('PROP-702 boundary: 9 pending lines does NOT push on line-count alone', () => {
  assert.equal(decidePublish({ pendingLineCount: DEFAULT_MIN_LINES - 1, lastPushTs: 0, nowMs: 0 }).shouldPush, false);
});

test('PROP-703: 1 pending line pushes once >= 15 minutes have elapsed since last push', () => {
  const decision = decidePublish({ pendingLineCount: 1, lastPushTs: 0, nowMs: DEFAULT_MIN_INTERVAL_MS });
  assert.equal(decision.shouldPush, true);
  assert.equal(decision.reason, 'time-threshold');
});

test('PROP-704: 1ms before the 15-minute floor, with pending<10, never pushes ("throttled")', () => {
  const decision = decidePublish({ pendingLineCount: 1, lastPushTs: 0, nowMs: DEFAULT_MIN_INTERVAL_MS - 1 });
  assert.equal(decision.shouldPush, false);
  assert.equal(decision.reason, 'throttled');
});

// ── PROP-705: extractWakeId / extractEarnRef (pure) ─────────────────────────────────────────────

test('PROP-705: extractWakeId returns the wake_id field of a valid JSON line, "unknown" otherwise', () => {
  assert.equal(extractWakeId(JSON.stringify({ ts: 1, wake_id: '01HZABC', kind: 'wake' })), '01HZABC');
  assert.equal(extractWakeId('{not valid json'), 'unknown');
  assert.equal(extractWakeId(JSON.stringify({ ts: 1, kind: 'wake' })), 'unknown');
  assert.equal(extractWakeId(JSON.stringify({ wake_id: 42 })), 'unknown');
});

test('extractEarnRef returns the `wake` field of a valid earn-ledger line, "unknown" otherwise', () => {
  assert.equal(extractEarnRef(JSON.stringify({ ts: 1, wake: 'e42', source: 'sol-trade' })), 'e42');
  assert.equal(extractEarnRef('{not valid json'), 'unknown');
  assert.equal(extractEarnRef(JSON.stringify({ ts: 1, source: 'sol-trade' })), 'unknown');
});

// ── FIND-001/003 / REQ-702,706 — projectWakeLine + redactBroaderSecretPatterns (pure) ────────────

test('projectWakeLine keeps every allowlisted field, drops the model-authored `args` object and any other unknown field', () => {
  const raw = JSON.stringify({
    ts: 1, wake_id: 'w1', kind: 'wake', slot: 'earn/clip', attemptsUsed: 1, profitable: true,
    exit_code: 0, sleep_s: 120, model: 'sonnet',
    args: { reason: 'anything the model wrote, unfiltered' },
    daemon_secret: 'should never appear',
  });
  const out = JSON.parse(projectWakeLine(raw));
  assert.deepEqual(out, {
    ts: 1, wake_id: 'w1', kind: 'wake', slot: 'earn/clip', attemptsUsed: 1, profitable: true,
    exit_code: 0, sleep_s: 120, model: 'sonnet',
  });
  assert.ok(!('args' in out), 'args must be dropped, not published');
  assert.ok(!('daemon_secret' in out), 'unknown fields must be dropped');
});

test('projectWakeLine passes through net_/earn_/cost_ numeric fields, drops non-numeric values for the same keys', () => {
  const good = JSON.parse(projectWakeLine(JSON.stringify({ ts: 1, net_usdc: 1.5, earn_usdc: 2, cost_usdc: 0.5 })));
  assert.deepEqual(good, { ts: 1, net_usdc: 1.5, earn_usdc: 2, cost_usdc: 0.5 });
  const bad = JSON.parse(projectWakeLine(JSON.stringify({ ts: 1, net_usdc: 'not-a-number' })));
  assert.ok(!('net_usdc' in bad));
});

test('projectWakeLine passes through a hash-shaped tx field, drops a non-hash-shaped tx value', () => {
  const goodTx = '0x' + 'a'.repeat(64);
  const good = JSON.parse(projectWakeLine(JSON.stringify({ ts: 1, tx: goodTx })));
  assert.equal(good.tx, goodTx);
  const bad = JSON.parse(projectWakeLine(JSON.stringify({ ts: 1, tx: 'not-a-hash' })));
  assert.ok(!('tx' in bad));
});

test('projectWakeLine redacts a private-key pattern AND a Solana-shaped base58 run AND a generic 40+ hex run inside result/skip_reason, caps at 200 chars', () => {
  const privKey = '0x' + 'a'.repeat(64);
  const solanaLike = '1' + 'A'.repeat(87); // base58-alphabet-safe 88-char run
  const longHex = 'f'.repeat(48);
  const longText = `leaked=${privKey} sol=${solanaLike} hex=${longHex} ` + 'x'.repeat(300);
  const out = JSON.parse(projectWakeLine(JSON.stringify({ ts: 1, result: longText })));
  assert.ok(!out.result.includes(privKey));
  assert.ok(!out.result.includes(solanaLike));
  assert.ok(!out.result.includes(longHex));
  assert.ok(out.result.includes('[REDACTED]'));
  assert.ok(out.result.length <= 200);
});

test('projectWakeLine returns null for malformed JSON or a non-object line (dropped, never published raw)', () => {
  assert.equal(projectWakeLine('{not json'), null);
  assert.equal(projectWakeLine('[1,2,3]'), null);
  assert.equal(projectWakeLine('"just a string"'), null);
});

test("redactBroaderSecretPatterns: a 40-hex string alone is redacted (stricter than env-filter.mjs's 64-hex-only contract, deliberately, for published free text)", () => {
  const addr = '0x' + 'b'.repeat(40);
  assert.ok(!redactBroaderSecretPatterns(`addr=${addr}`).includes(addr));
});

// ── FIND-001: projectEarnLine (pure) — the money-evidence allowlist ────────────────────────────

test('FIND-001 (iter3, critical): projectEarnLine keeps every allowlisted money field INCLUDING external/confirmed/fill_tid — required by isProfitable(), never dropped', () => {
  const raw = JSON.stringify({
    ts: 1, wallet: '0xabc123', source: 'sol-trade', wake: 'e1',
    earn_usdc: 2.5, cost_usdc: 0.1, net_usdc: 2.4,
    tx: '0x' + 'a'.repeat(64), sig: 'a'.repeat(88), status: '0x1', chain: 'solana',
    task: 'jupiter swap round-trip', confirmed: true, external: true, fill_tid: 42,
  });
  const out = JSON.parse(projectEarnLine(raw));
  assert.deepEqual(out, {
    ts: 1, wallet: '0xabc123', source: 'sol-trade', wake: 'e1',
    earn_usdc: 2.5, cost_usdc: 0.1, net_usdc: 2.4,
    tx: '0x' + 'a'.repeat(64), sig: 'a'.repeat(88), status: '0x1', chain: 'solana',
    task: 'jupiter swap round-trip', confirmed: true, external: true, fill_tid: 42,
  });
  assert.equal(out.confirmed, true, 'FIND-001: confirmed must be preserved — isProfitable() needs it for solOk/hlOk');
  assert.equal(out.external, true, 'FIND-001: external must be preserved — isProfitable() gates false unconditionally without it');
  assert.equal(out.fill_tid, 42, 'FIND-001: fill_tid must be preserved — HL\'s only settlement reference');
  // FIND-001's own restored acceptance criterion: this line, as PUBLISHED, must actually classify
  // as profitable through the repo's REAL classifier (never a re-implementation of its rules).
  assert.equal(isProfitable(out), true, 'a real profitable earn line must round-trip to isProfitable()===true after projection');
});

test('FIND-001 (iter3): projectEarnLine round-trips a Solana-only profitable line (sig+confirmed, no tx) through the real isProfitable()', () => {
  const raw = JSON.stringify({
    ts: 1, wallet: 'SoLwaLLetAddr', source: 'sol-trade', wake: 'e2',
    earn_usdc: 1.2, cost_usdc: 0, net_usdc: 1.2,
    sig: 'a'.repeat(88), confirmed: true, external: true, chain: 'solana',
  });
  const out = JSON.parse(projectEarnLine(raw));
  assert.equal(out.sig, 'a'.repeat(88));
  assert.equal(out.confirmed, true);
  assert.equal(out.external, true);
  assert.equal(isProfitable(out), true, 'solOk path: sig+confirmed+external+net_usdc>0 must classify as profitable');
});

test('FIND-001 (iter3): projectEarnLine round-trips a Hyperliquid-only profitable line (fill_tid+confirmed, no tx/sig) through the real isProfitable()', () => {
  const raw = JSON.stringify({
    ts: 1, wallet: 'hl-wallet', source: 'hl-trade', wake: 'e3',
    earn_usdc: 3.0, cost_usdc: 0.5, net_usdc: 2.5,
    chain: 'hyperliquid', fill_tid: 987654321, confirmed: true, external: true,
  });
  const out = JSON.parse(projectEarnLine(raw));
  assert.equal(out.fill_tid, 987654321);
  assert.equal(out.confirmed, true);
  assert.equal(out.chain, 'hyperliquid');
  assert.equal(isProfitable(out), true, 'hlOk path: fill_tid+confirmed+external+chain==="hyperliquid"+net_usdc>0 must classify as profitable');
});

test('FIND-001 (iter3): projectEarnLine drops external/confirmed/fill_tid when NOT the correct type (fail-closed, never coerced)', () => {
  const out = JSON.parse(projectEarnLine(JSON.stringify({
    ts: 1, external: 'true', confirmed: 1, fill_tid: {},
  })));
  assert.ok(!('external' in out), 'a non-boolean external must be dropped, never coerced to true');
  assert.ok(!('confirmed' in out), 'a non-boolean confirmed must be dropped, never coerced to true');
  assert.ok(!('fill_tid' in out), 'a non-number fill_tid must be dropped');
});

test('FIND-001 (iter4): projectEarnLine accepts ONLY a numeric fill_tid — a string form is DROPPED even when it is id-shaped or secret-shaped, since no real HL writer ever produces a string fill_tid (reconcile.py always writes a JSON integer) and the string branch bypassed both redaction layers', () => {
  const numeric = JSON.parse(projectEarnLine(JSON.stringify({ ts: 1, fill_tid: 987654321 })));
  assert.equal(numeric.fill_tid, 987654321, 'a finite-number fill_tid must round-trip unchanged');

  const idShaped = JSON.parse(projectEarnLine(JSON.stringify({ ts: 1, fill_tid: 'hl-fill:12345' })));
  assert.ok(!('fill_tid' in idShaped), 'an id-shaped string fill_tid must be dropped, not published — no real writer produces this shape');

  // A long mixed-case alphanumeric run in the SETTLEMENT_ID_VALUE charset (the shape the removed
  // regex would have accepted) -- deliberately NOT prefixed with any recognized API-key/token
  // format (e.g. no `sk_live_`/`ghp_`/`AKIA` prefix), so this fixture itself never trips a real
  // secret scanner while still proving the field-shape gap the removed branch had.
  const secretShaped = JSON.parse(projectEarnLine(JSON.stringify({
    ts: 1, fill_tid: 'q9fB2kLmN0pQrStUvWxYz1234567890AbCdEfGhIjKlMnOpQrStUvWxYz0011',
  })));
  assert.ok(!('fill_tid' in secretShaped), 'a secret/API-key-shaped string fill_tid must be dropped, never published verbatim to the public branch');

  const malformed = JSON.parse(projectEarnLine(JSON.stringify({ ts: 1, fill_tid: 'has a space and $ymbol!' })));
  assert.ok(!('fill_tid' in malformed), 'a malformed string fill_tid must also be dropped');
});

test('FIND-003 (iter3): projectEarnLine now shape-validates sig (base58, 64-88 chars) instead of a bare length check — a non-base58 or wrong-length value is dropped', () => {
  const good = JSON.parse(projectEarnLine(JSON.stringify({ ts: 1, sig: 'a'.repeat(88) })));
  assert.equal(good.sig, 'a'.repeat(88));
  const wrongAlphabet = JSON.parse(projectEarnLine(JSON.stringify({ ts: 1, sig: '0'.repeat(88) }))); // '0' is outside the base58 alphabet
  assert.ok(!('sig' in wrongAlphabet), 'a non-base58-shaped sig must be dropped, not published verbatim');
  const tooShort = JSON.parse(projectEarnLine(JSON.stringify({ ts: 1, sig: 'a'.repeat(10) })));
  assert.ok(!('sig' in tooShort), 'a sig shorter than the real 64-88-char signature shape must be dropped');
});

test('FIND-001: projectEarnLine drops a non-hash-shaped tx value, redacts+caps the free-text task field', () => {
  const bad = JSON.parse(projectEarnLine(JSON.stringify({ ts: 1, tx: 'not-a-hash' })));
  assert.ok(!('tx' in bad));
  const privKey = '0x' + 'a'.repeat(64);
  const longTask = `secret=${privKey} ` + 'x'.repeat(300);
  const out = JSON.parse(projectEarnLine(JSON.stringify({ ts: 1, task: longTask })));
  assert.ok(!out.task.includes(privKey));
  assert.ok(out.task.includes('[REDACTED]'));
  assert.ok(out.task.length <= 200);
});

test('FIND-001: projectEarnLine returns null for malformed JSON or a non-object line', () => {
  assert.equal(projectEarnLine('{not json'), null);
  assert.equal(projectEarnLine('[1,2,3]'), null);
});

// ── REQ-701: default OFF — unchanged, zero I/O ──────────────────────────────────────────────────

test('REQ-701: enabled:false performs zero git calls and zero fs writes', async () => {
  const dir = tmpDir('ledger-publish-off-');
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, [{ ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 }]);
  const { git, calls } = makeMockGit();
  const result = await publishLedgerCycle({ ...opts, enabled: false, git });
  assert.deepEqual(result, { published: false, pushed: false, reason: 'disabled', publishFailureStreak: 0 });
  assert.equal(calls.length, 0);
  assert.equal(fs.existsSync(publishRepoDirFor(dir)), false);
});

test('REQ-701: process.env.LEDGER_PUBLISH_ENABLED default resolution — unset env means disabled', async () => {
  const prior = process.env.LEDGER_PUBLISH_ENABLED;
  delete process.env.LEDGER_PUBLISH_ENABLED;
  try {
    const dir = tmpDir('ledger-publish-envoff-');
    const opts = baseOpts(dir);
    writeLines(opts.ledgerPath, [{ ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 }]);
    const { git, calls } = makeMockGit();
    const { enabled, ...rest } = opts;
    const result = await publishLedgerCycle({ ...rest, git });
    assert.equal(result.reason, 'disabled');
    assert.equal(calls.length, 0);
  } finally {
    if (prior === undefined) delete process.env.LEDGER_PUBLISH_ENABLED;
    else process.env.LEDGER_PUBLISH_ENABLED = prior;
  }
});

// ── REQ-703: non-fatality on setup/commit/push failure (mock git, no real remote needed) ─────────

test('REQ-703: origin-url resolution failure ("git remote get-url" throws) is non-fatal, reason "setup-failed"', async () => {
  const dir = tmpDir('ledger-publish-badorigin-');
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, [{ ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 }]);
  const { git } = makeMockGit({ failOn: ['remote'] });
  const logs = [];
  let threw = false;
  let result;
  try {
    result = await publishLedgerCycle({ ...opts, repoRoot: dir, git, log: (m) => logs.push(m) });
  } catch {
    threw = true;
  }
  assert.equal(threw, false);
  assert.equal(result.reason, 'setup-failed');
  assert.equal(result.publishFailureStreak, 1);
  assert.ok(logs.length >= 1);
});

test('REQ-703: publish-repo clone failure is non-fatal, reason "setup-failed", no destination file created', async () => {
  const dir = tmpDir('ledger-publish-badclone-');
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, [{ ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 }]);
  const { git } = makeMockGit({ failOn: ['clone'] });
  const result = await publishLedgerCycle({ ...opts, originUrl: 'file:///does/not/exist', git });
  assert.equal(result.reason, 'setup-failed');
  assert.equal(fs.existsSync(path.join(publishRepoDirFor(dir), 'franklin-wake.jsonl')), false);
});

// ── REQ-705 / FIND-001: dedicated per-instance orphan publish repo, BOTH sources — real git ──────

test("REQ-705/FIND-001: first-ever publish creates a DEDICATED clone on orphan branch ledger-<instance> containing BOTH wake and earn files, never touches the shared checkout's main", async () => {
  const dir = tmpDir('ledger-publish-first-');
  const { originDir, sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(10));
  const earnLedgerPath = path.join(dir, 'home', 'skills', 'earn', 'state', 'earn-ledger.jsonl');
  writeLines(earnLedgerPath, makeEarnLines(3));

  const beforeHead = sh(['rev-parse', 'HEAD'], sharedCheckout).trim();
  const beforeStatus = sh(['status', '--porcelain'], sharedCheckout).trim();

  const result = await publishLedgerCycle({ ...opts, earnLedgerPath, repoRoot: sharedCheckout, now: () => 0 });

  assert.equal(result.published, true);
  assert.equal(result.pushed, true);

  const afterHead = sh(['rev-parse', 'HEAD'], sharedCheckout).trim();
  const afterStatus = sh(['status', '--porcelain'], sharedCheckout).trim();
  assert.equal(afterHead, beforeHead, 'shared checkout HEAD must be byte-identical after publish');
  assert.equal(afterStatus, beforeStatus, 'shared checkout working tree/index must be untouched');

  const verifyDir = cloneBranch(originDir, 'ledger-franklin');
  const files = fs.readdirSync(verifyDir).filter((f) => f !== '.git');
  assert.deepEqual(files.sort(), ['README.md', 'franklin-earn.jsonl', 'franklin-wake.jsonl']);

  const wakeLines = readLines(path.join(verifyDir, 'franklin-wake.jsonl'));
  assert.equal(wakeLines.length, 10);
  assert.deepEqual(JSON.parse(wakeLines[0]), { ts: 0, wake_id: 'w0', kind: 'wake', sleep_s: 120, profitable: false });

  const earnLines = readLines(path.join(verifyDir, 'franklin-earn.jsonl')).map((l) => JSON.parse(l));
  assert.equal(earnLines.length, 3);
  assert.equal(earnLines[0].net_usdc, 1.5, 'money evidence (net_usdc) must actually be published — FIND-001');
  assert.equal(earnLines[0].wake, 'e0');

  // origin's own default branch is untouched by this publish.
  const mainTip = sh(['ls-remote', fileUrl(originDir), 'refs/heads/main'], dir).trim();
  assert.ok(mainTip.length > 0);
});

test('FIND-006: the dedicated clone is shallow (--depth 1) and stays shallow across a subsequent fetch/push cycle', async () => {
  const dir = tmpDir('ledger-publish-shallow-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(10));

  const first = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 0 });
  assert.equal(first.pushed, true);
  const publishRepoDir = publishRepoDirFor(dir);
  assert.ok(fs.existsSync(path.join(publishRepoDir, '.git', 'shallow')), 'the dedicated clone must be shallow (.git/shallow present)');

  writeLines(opts.ledgerPath, [...makeLines(10), ...makeLines(10, 10)]);
  const second = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 2_000_000 });
  assert.equal(second.pushed, true);
  assert.ok(fs.existsSync(path.join(publishRepoDir, '.git', 'shallow')), 'the clone must still be shallow after a second fetch/push cycle');
});

// ── FIND-001/002 leak test: a dirty + committed-but-unpushed shared checkout survives untouched ──

test('leak test (FIND-001/002): a shared checkout with an uncommitted AND a committed-but-unpushed change is completely untouched by a publish cycle', async () => {
  const dir = tmpDir('ledger-publish-leak-');
  const { originDir, sharedCheckout } = setupOrigin(dir);

  // Simulate evolve.mjs's promote() (or another instance) having just committed something LOCALLY
  // to the shared checkout's main, not yet pushed -- plus an unrelated dirty (uncommitted) file.
  fs.writeFileSync(path.join(sharedCheckout, 'baseline-genome.json'), '{"knob":1}\n');
  sh(['add', 'baseline-genome.json'], sharedCheckout);
  sh(['-c', 'user.name=t', '-c', 'user.email=t@t.local', 'commit', '-q', '-m', 'unrelated local commit'], sharedCheckout);
  fs.writeFileSync(path.join(sharedCheckout, 'scratch.txt'), 'dirty uncommitted content\n');

  const beforeHead = sh(['rev-parse', 'HEAD'], sharedCheckout).trim();
  const beforeStatus = sh(['status', '--porcelain'], sharedCheckout).trim();
  const beforeBranch = sh(['branch', '--show-current'], sharedCheckout).trim();
  const beforeRemoteMain = sh(['ls-remote', fileUrl(originDir), 'refs/heads/main'], dir).trim();

  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(12));
  const result = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 0 });
  assert.equal(result.pushed, true, 'sanity: the publish cycle itself must have actually run and pushed');

  const afterHead = sh(['rev-parse', 'HEAD'], sharedCheckout).trim();
  const afterStatus = sh(['status', '--porcelain'], sharedCheckout).trim();
  const afterBranch = sh(['branch', '--show-current'], sharedCheckout).trim();
  const afterRemoteMain = sh(['ls-remote', fileUrl(originDir), 'refs/heads/main'], dir).trim();

  assert.equal(afterHead, beforeHead, 'HEAD commit must be unchanged');
  assert.equal(afterStatus, beforeStatus, 'dirty/staged state must be byte-identical (unrelated commit still unpushed, scratch.txt still dirty)');
  assert.equal(afterBranch, beforeBranch, 'current branch must be unchanged (still main)');
  assert.equal(afterRemoteMain, beforeRemoteMain, 'origin main must be unchanged — the publish never pushed to it');
  assert.ok(afterStatus.includes('scratch.txt'), 'the dirty file must still be there, untouched');

  const verifyDir = cloneBranch(originDir, 'ledger-franklin');
  const files = fs.readdirSync(verifyDir).filter((f) => f !== '.git');
  assert.deepEqual(files.sort(), ['README.md', 'franklin-wake.jsonl'], 'the published branch must contain ONLY the wake file (no earn lines this cycle) + README, nothing from the shared checkout');
});

test('REQ-702: ANICCA_INSTANCE default falls back to "clawrouter" when instance is omitted', async () => {
  const dir = tmpDir('ledger-publish-defaultinst-');
  const { originDir, sharedCheckout } = setupOrigin(dir);
  const priorInstance = process.env.ANICCA_INSTANCE;
  delete process.env.ANICCA_INSTANCE;
  try {
    const opts = baseOpts(dir);
    delete opts.instance;
    writeLines(opts.ledgerPath, makeLines(10));
    const result = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 0 });
    assert.equal(result.published, true);
    const verifyDir = cloneBranch(originDir, 'ledger-clawrouter');
    assert.ok(fs.existsSync(path.join(verifyDir, 'clawrouter-wake.jsonl')));
  } finally {
    if (priorInstance === undefined) delete process.env.ANICCA_INSTANCE;
    else process.env.ANICCA_INSTANCE = priorInstance;
  }
});

test('REQ-703/PROP-717: a persistently failing push (both the initial attempt AND the retry) is non-fatal — never throws, marker.wake.pushedLineCount stays at the last CONFIRMED value, streak increments', async () => {
  const dir = tmpDir('ledger-publish-pushdown-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(10));

  // Cycle 1: everything real, establishes the branch on origin with a successful push.
  const first = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 0 });
  assert.equal(first.pushed, true);

  // Cycle 2: new lines, but `push` ALWAYS throws — simulates a persistent network outage.
  writeLines(opts.ledgerPath, [...makeLines(10), ...makeLines(5, 10)]);
  const pushDeadGit = (args, cwd) => {
    if (args[0] === 'push') throw new Error('mock: network unreachable');
    return realGit(args, cwd);
  };
  const logs = [];
  let threw = false;
  let second;
  try {
    second = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, git: pushDeadGit, log: (m) => logs.push(m), now: () => 2_000_000 });
  } catch {
    threw = true;
  }
  assert.equal(threw, false, 'publishLedgerCycle must never throw even when push AND its retry both fail');
  assert.ok(second && typeof second === 'object');
  assert.equal(second.pushed, false);
  assert.ok(second.publishFailureStreak >= 1);
  assert.ok(logs.length >= 1);

  const marker = JSON.parse(fs.readFileSync(opts.markerPath, 'utf8'));
  assert.equal(marker.wake.pushedLineCount, 10, 'pushedLineCount must stay at the last CONFIRMED-pushed value, not silently advance');
});

// ── REQ-708 / PROP-712,713: same-instance overlap lock ────────────────────────────────────────────

test('REQ-708: a live-held lock (this process\'s own pid) causes the cycle to skip with reason "locked", no publish-repo writes', async () => {
  const dir = tmpDir('ledger-publish-lockheld-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(1));
  const lockDir = path.join(dir, 'home', 'state', '.ledger-publish-franklin.lock');
  fs.mkdirSync(lockDir, { recursive: true });
  fs.writeFileSync(path.join(lockDir, 'pid'), String(process.pid));

  const result = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, lockDir });
  assert.equal(result.reason, 'locked');
  assert.equal(fs.existsSync(publishRepoDirFor(dir)), false);
});

test('REQ-708: a stale lock (dead pid) is reclaimed and the cycle proceeds normally', async () => {
  const dir = tmpDir('ledger-publish-lockstale-');
  const { originDir, sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(10));
  const lockDir = path.join(dir, 'home', 'state', '.ledger-publish-franklin.lock');
  fs.mkdirSync(lockDir, { recursive: true });
  fs.writeFileSync(path.join(lockDir, 'pid'), '999999999'); // astronomically unlikely to be alive

  const result = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, lockDir, now: () => 0 });
  assert.equal(result.published, true);
  assert.equal(result.pushed, true);
  assert.equal(fs.existsSync(lockDir), false, 'lock must be released again after a successful cycle');

  const verifyDir = cloneBranch(originDir, 'ledger-franklin');
  assert.equal(readLines(path.join(verifyDir, 'franklin-wake.jsonl')).length, 10);
});

// ── FIND-002/FIND-003: publish-repo LOSS between cycles (the real reachable trigger) ─────────────

test('FIND-002/FIND-003: publishRepoDir loss between cycles is fully self-healing — every source line still ends up on the branch exactly once, no gap', async () => {
  const dir = tmpDir('ledger-publish-repoloss-');
  const { originDir, sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(12));

  // Cycle 1: `push` ALWAYS throws (both the primary attempt and the retry's own push) — simulates a
  // persistent network outage DURING this cycle, so nothing ever actually reaches origin.
  const pushDeadGit = (args, cwd) => {
    if (args[0] === 'push') throw new Error('mock: network unreachable');
    return realGit(args, cwd);
  };
  const first = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, git: pushDeadGit, now: () => 0 });
  assert.equal(first.pushed, false, 'sanity: cycle 1 never actually reached origin');

  // Between cycles: the DEDICATED publish-repo directory is lost entirely (deleted/recreated — a
  // manual `rm -rf` during troubleshooting, a redeploy, or any external wipe of
  // $ANICCA_HOME/state/.ledger-publish-repo). This is the REALISTIC, reachable trigger for this bug
  // class in THIS single-writer-per-branch topology — REQ-705 makes an outside writer colliding on
  // the same EXCLUSIVE per-instance branch structurally impossible, so that is deliberately NOT what
  // this test exercises (FIND-003).
  fs.rmSync(publishRepoDirFor(dir), { recursive: true, force: true });

  // Cycle 2: real git throughout, no more injected failures. The SOURCE ledger (state/ledger.jsonl,
  // never touched by the publish-repo loss) still durably has all 12 lines.
  const second = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 2_000_000 });
  assert.equal(second.pushed, true, 'cycle 2 must successfully reach origin');

  const verifyDir = cloneBranch(originDir, 'ledger-franklin');
  const lines = readLines(path.join(verifyDir, 'franklin-wake.jsonl')).map((l) => JSON.parse(l));
  const wakeIds = lines.map((l) => l.wake_id);
  assert.equal(new Set(wakeIds).size, wakeIds.length, 'no wake_id may appear twice — no duplicate re-publish');
  for (let i = 0; i < 12; i++) {
    assert.ok(wakeIds.includes(`w${i}`), `w${i} must be present — no line silently dropped by the repo-loss recovery`);
  }

  const marker = JSON.parse(fs.readFileSync(opts.markerPath, 'utf8'));
  assert.equal(marker.wake.pushedLineCount, 12);
});

test('FIND-002: a push rejected mid-cycle by a real divergence (an outside writer, simulating a stale local state) is recovered via re-sync+reproject+retry, no line dropped or duplicated', async () => {
  const dir = tmpDir('ledger-publish-divergence-');
  const { originDir, sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(10));

  const first = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 0 });
  assert.equal(first.pushed, true, 'sanity: first cycle establishes the branch on origin');

  const outsideWriter = cloneBranch(originDir, 'ledger-franklin');
  fs.writeFileSync(path.join(outsideWriter, 'external-marker.txt'), 'someone else pushed this\n');
  sh(['add', 'external-marker.txt'], outsideWriter);
  sh(['-c', 'user.name=t', '-c', 'user.email=t@t.local', 'commit', '-q', '-m', 'external divergent commit'], outsideWriter);
  sh(['push', '-q', 'origin', 'ledger-franklin'], outsideWriter);

  writeLines(opts.ledgerPath, [...makeLines(10), ...makeLines(12, 10)]);

  const second = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 1_000_000 });
  assert.equal(second.pushed, true, 'divergence recovery must still result in a successful push this cycle');

  const verifyDir = cloneBranch(originDir, 'ledger-franklin');
  const lines = readLines(path.join(verifyDir, 'franklin-wake.jsonl')).map((l) => JSON.parse(l));
  const wakeIds = lines.map((l) => l.wake_id);
  const uniqueWakeIds = new Set(wakeIds);
  assert.equal(wakeIds.length, uniqueWakeIds.size, 'no wake_id may appear twice — no duplicate re-publish');
  for (let i = 0; i < 22; i++) {
    assert.ok(uniqueWakeIds.has(`w${i}`), `w${i} must be present — no line silently dropped by the recovery`);
  }
  assert.ok(fs.existsSync(path.join(verifyDir, 'external-marker.txt')), 'the external divergent commit must be preserved (reset --hard onto origin, not a force-overwrite)');

  const marker = JSON.parse(fs.readFileSync(opts.markerPath, 'utf8'));
  assert.equal(marker.wake.pushedLineCount, 22);
});

test('FIND-002 (iter3, major): pushed must be false when the retry issues NO git push (post-reset reconcile found nothing pending) — not misreported true', async () => {
  const dir = tmpDir('ledger-publish-phantompush-');
  const { originDir, sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(10));

  // The FIRST `git push` call actually lands on origin (real push executes) but the client THEN
  // throws — simulating a network timeout/ambiguous failure observed AFTER the push already
  // succeeded server-side. Every subsequent push call (there must be none) would be a bug.
  let pushCalls = 0;
  const phantomSuccessGit = (args, cwd) => {
    if (args[0] === 'push') {
      pushCalls += 1;
      if (pushCalls === 1) {
        realGit(args, cwd); // actually lands on origin
        throw new Error('mock: client-side timeout after the push already succeeded');
      }
    }
    return realGit(args, cwd);
  };

  const result = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, git: phantomSuccessGit, now: () => 0 });

  assert.equal(pushCalls, 1, 'sanity: exactly ONE push call total — the retry must find nothing pending (already on origin) and must NOT issue a second push');
  assert.equal(result.pushed, false, 'FIND-002: pushed must be false — no push was (re-)issued and observed to succeed inside the retry branch this cycle, even though content already reached origin via the phantom-successful primary attempt');

  // Sanity: the content genuinely IS on origin (no data loss) — only the truthfulness of the
  // `pushed` flag/marker bookkeeping for THIS cycle's own retry branch is under test here.
  const verifyDir = cloneBranch(originDir, 'ledger-franklin');
  assert.equal(readLines(path.join(verifyDir, 'franklin-wake.jsonl')).length, 10, 'sanity: the phantom-successful primary push really did land on origin');
});

// ── REQ-703: commit failure is caught locally (never the generic outer 'error' catch) ────────────

test('REQ-703: a commit failure is logged and non-fatal, and the next cycle recovers cleanly with no duplication', async () => {
  const dir = tmpDir('ledger-publish-commitfail-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(1));

  const commitFailingGit = (args, cwd) => {
    if (args.includes('commit')) throw new Error('mock commit failure');
    return realGit(args, cwd);
  };
  const logs1 = [];
  const first = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, git: commitFailingGit, log: (m) => logs1.push(m), now: () => 0 });
  assert.equal(first.published, false, 'a failed commit must not report published:true');
  assert.notEqual(first.reason, 'error', 'a commit failure must be caught locally, not fall through to the generic outer catch');
  assert.ok(logs1.some((l) => l.includes('commit failed')));

  const second = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 2_000_000 });
  assert.equal(second.published, true);
  assert.equal(second.pushed, true);

  const marker = JSON.parse(fs.readFileSync(opts.markerPath, 'utf8'));
  assert.equal(marker.wake.pushedLineCount, 1, 'exactly one line published — no duplication from the earlier failed-commit cycle');
});

test('REQ-704 integration: 5 pending lines under the 10-line/15-min throttle commits locally but does NOT push, and marker.wake.pushedLineCount stays 0 (unconfirmed)', async () => {
  const dir = tmpDir('ledger-publish-nopush-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(5));

  const result = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 1000 });
  assert.equal(result.published, true);
  assert.equal(result.pushed, false);

  const marker = JSON.parse(fs.readFileSync(opts.markerPath, 'utf8'));
  assert.equal(marker.wake.pushedLineCount, 0);
});

// ── FIND-005: consecutive-failure streak + escalation-ready return value ─────────────────────────

test('FIND-005: publishFailureStreak accumulates across consecutive setup failures and resets to 0 on the next successful setup', async () => {
  const dir = tmpDir('ledger-publish-streak-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(1));

  const { git: badGit } = makeMockGit({ failOn: ['remote'] });
  let result;
  for (let i = 0; i < 5; i++) {
    result = await publishLedgerCycle({ ...opts, repoRoot: dir, git: badGit });
    assert.equal(result.reason, 'setup-failed');
  }
  assert.equal(result.publishFailureStreak, 5, 'streak must reach 5 after 5 consecutive setup failures (index.mjs escalates at this threshold)');

  const recovered = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 0 });
  assert.notEqual(recovered.reason, 'setup-failed');
  assert.equal(recovered.publishFailureStreak, 0, 'a successful setup must reset the streak back to 0');
});

test('FIND-005: a failing ls-remote reachability probe at first-ever setup logs clearly and does not block the cycle (non-fatal, no credential-shaped token in the log)', async () => {
  const dir = tmpDir('ledger-publish-reachability-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(10));

  const lsRemoteDeadGit = (args, cwd) => {
    if (args[0] === 'ls-remote') throw new Error('mock: ls-remote auth failure');
    return realGit(args, cwd);
  };
  const logs = [];
  const result = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, git: lsRemoteDeadGit, log: (m) => logs.push(m), now: () => 0 });

  assert.equal(result.pushed, true, 'a failed reachability PROBE must never block the actual publish cycle');
  assert.ok(logs.some((l) => l.includes('reachability') && l.includes('ls-remote auth failure')));
  assert.ok(!logs.some((l) => /ghp_|gho_|github_pat_|Authorization:/i.test(l)), 'no credential-shaped token ever appears in a log line');
});

test('FIND-005: the reachability probe runs only once (at first-ever dedicated-clone setup), never again once the clone already exists', async () => {
  const dir = tmpDir('ledger-publish-reachability-once-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(5));

  let lsRemoteCalls = 0;
  const countingGit = (args, cwd) => {
    if (args[0] === 'ls-remote') lsRemoteCalls += 1;
    return realGit(args, cwd);
  };
  await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, git: countingGit, now: () => 0 });
  assert.equal(lsRemoteCalls, 1);

  writeLines(opts.ledgerPath, [...makeLines(5), ...makeLines(10, 5)]);
  await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, git: countingGit, now: () => 2_000_000 });
  assert.equal(lsRemoteCalls, 1, 'ls-remote must not be called again once the dedicated clone already exists');
});
