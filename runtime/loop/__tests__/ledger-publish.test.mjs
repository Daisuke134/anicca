// franklin-ledger-push (P2) — behavioral-spec.md REQ-701..709 / verification-architecture.md
// PROP-701..716. iter1 redesign (impl-review FIND-001..005): the orchestrator now publishes into a
// DEDICATED per-instance orphan clone, never the shared checkout — so the effectful-shell tests
// below use REAL git (mirrors skills/earn/lib/__tests__/evolve.test.mjs's own established
// real-git-in-tmp-dir precedent) against a `file://` BARE-repo fixture created fresh per test.
// NO test in this file ever touches the real ~/anicca repo, a real remote, or the network — every
// "origin" is a throwaway bare repo under os.tmpdir(). Pure-core tests (decidePublish/
// extractWakeId/projectLedgerLine/redactBroaderSecretPatterns) run with zero I/O and, for the
// non-fatality / setup-failure paths, an injected mock `git` is still used (no real git needed).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

import {
  decidePublish,
  extractWakeId,
  projectLedgerLine,
  redactBroaderSecretPatterns,
  publishLedgerCycle,
  DEFAULT_MIN_LINES,
  DEFAULT_MIN_INTERVAL_MS,
} from '../ledger-publish.mjs';

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

// Bare "origin" repo + a "shared checkout" cloned from it (mirrors this repo's own real topology:
// `repoRoot` here plays the role of `~/anicca`'s shared checkout; ledger-publish.mjs reads ONLY
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

function baseOpts(dir, instance = 'franklin') {
  return {
    enabled: true,
    ledgerPath: path.join(dir, 'home', 'state', 'ledger.jsonl'),
    markerPath: path.join(dir, 'home', 'state', '.ledger-publish-marker'),
    instance,
    now: () => 0,
  };
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

// ── PROP-705: extractWakeId (pure) — unchanged ──────────────────────────────────────────────────

test('PROP-705: extractWakeId returns the wake_id field of a valid JSON line, "unknown" otherwise', () => {
  assert.equal(extractWakeId(JSON.stringify({ ts: 1, wake_id: '01HZABC', kind: 'wake' })), '01HZABC');
  assert.equal(extractWakeId('{not valid json'), 'unknown');
  assert.equal(extractWakeId(JSON.stringify({ ts: 1, kind: 'wake' })), 'unknown');
  assert.equal(extractWakeId(JSON.stringify({ wake_id: 42 })), 'unknown');
});

// ── FIND-003 / REQ-702,706 / PROP-706..710: projectLedgerLine + redactBroaderSecretPatterns (pure) ─

test('PROP-706: projectLedgerLine keeps every allowlisted field, drops the model-authored `args` object and any other unknown field', () => {
  const raw = JSON.stringify({
    ts: 1, wake_id: 'w1', kind: 'wake', slot: 'earn/clip', attemptsUsed: 1, profitable: true,
    exit_code: 0, sleep_s: 120, model: 'sonnet',
    args: { reason: 'anything the model wrote, unfiltered' },
    daemon_secret: 'should never appear',
  });
  const out = JSON.parse(projectLedgerLine(raw));
  assert.deepEqual(out, {
    ts: 1, wake_id: 'w1', kind: 'wake', slot: 'earn/clip', attemptsUsed: 1, profitable: true,
    exit_code: 0, sleep_s: 120, model: 'sonnet',
  });
  assert.ok(!('args' in out), 'args must be dropped, not published');
  assert.ok(!('daemon_secret' in out), 'unknown fields must be dropped');
});

test('PROP-707: projectLedgerLine passes through net_/earn_/cost_ numeric fields, drops non-numeric values for the same keys', () => {
  const good = JSON.parse(projectLedgerLine(JSON.stringify({ ts: 1, net_usdc: 1.5, earn_usdc: 2, cost_usdc: 0.5 })));
  assert.deepEqual(good, { ts: 1, net_usdc: 1.5, earn_usdc: 2, cost_usdc: 0.5 });
  const bad = JSON.parse(projectLedgerLine(JSON.stringify({ ts: 1, net_usdc: 'not-a-number' })));
  assert.ok(!('net_usdc' in bad));
});

test('PROP-708: projectLedgerLine passes through a hash-shaped tx field, drops a non-hash-shaped tx value', () => {
  const goodTx = '0x' + 'a'.repeat(64);
  const good = JSON.parse(projectLedgerLine(JSON.stringify({ ts: 1, tx: goodTx })));
  assert.equal(good.tx, goodTx);
  const bad = JSON.parse(projectLedgerLine(JSON.stringify({ ts: 1, tx: 'not-a-hash' })));
  assert.ok(!('tx' in bad));
});

test('PROP-709: projectLedgerLine redacts a private-key pattern AND a Solana-shaped base58 run AND a generic 40+ hex run inside result/skip_reason, caps at 200 chars', () => {
  const privKey = '0x' + 'a'.repeat(64);
  const solanaLike = '1' + 'A'.repeat(87); // base58-alphabet-safe 88-char run
  const longHex = 'f'.repeat(48);
  const longText = `leaked=${privKey} sol=${solanaLike} hex=${longHex} ` + 'x'.repeat(300);
  const out = JSON.parse(projectLedgerLine(JSON.stringify({ ts: 1, result: longText })));
  assert.ok(!out.result.includes(privKey));
  assert.ok(!out.result.includes(solanaLike));
  assert.ok(!out.result.includes(longHex));
  assert.ok(out.result.includes('[REDACTED]'));
  assert.ok(out.result.length <= 200);
});

test('PROP-710: projectLedgerLine returns null for malformed JSON or a non-object line (dropped, never published raw)', () => {
  assert.equal(projectLedgerLine('{not json'), null);
  assert.equal(projectLedgerLine('[1,2,3]'), null);
  assert.equal(projectLedgerLine('"just a string"'), null);
});

test("redactBroaderSecretPatterns: a 40-hex string alone is redacted (stricter than env-filter.mjs's 64-hex-only contract, deliberately, for published free text)", () => {
  const addr = '0x' + 'b'.repeat(40);
  assert.ok(!redactBroaderSecretPatterns(`addr=${addr}`).includes(addr));
});

// ── REQ-701: default OFF — unchanged, zero I/O ──────────────────────────────────────────────────

test('REQ-701: enabled:false performs zero git calls and zero fs writes', async () => {
  const dir = tmpDir('ledger-publish-off-');
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, [{ ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 }]);
  const { git, calls } = makeMockGit();
  const result = await publishLedgerCycle({ ...opts, enabled: false, git });
  assert.deepEqual(result, { published: false, pushed: false, reason: 'disabled' });
  assert.equal(calls.length, 0);
  assert.equal(fs.existsSync(path.join(dir, 'home', 'state', '.ledger-publish-repo')), false);
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
  assert.ok(logs.length >= 1);
});

test('REQ-703: publish-repo clone failure is non-fatal, reason "setup-failed", no destination file created', async () => {
  const dir = tmpDir('ledger-publish-badclone-');
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, [{ ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 }]);
  const { git } = makeMockGit({ failOn: ['clone'] });
  const result = await publishLedgerCycle({ ...opts, originUrl: 'file:///does/not/exist', git });
  assert.equal(result.reason, 'setup-failed');
  assert.equal(fs.existsSync(path.join(dir, 'home', 'state', '.ledger-publish-repo', 'franklin.jsonl')), false);
});

// ── REQ-705 / PROP-711: dedicated per-instance orphan publish repo — real git, throwaway origin ──

test("REQ-705/PROP-711: first-ever publish creates a DEDICATED clone on orphan branch ledger-<instance>, never touches the shared checkout's main", async () => {
  const dir = tmpDir('ledger-publish-first-');
  const { originDir, sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(10));

  const beforeHead = sh(['rev-parse', 'HEAD'], sharedCheckout).trim();
  const beforeStatus = sh(['status', '--porcelain'], sharedCheckout).trim();

  const result = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 0 });

  assert.equal(result.published, true);
  assert.equal(result.pushed, true);

  const afterHead = sh(['rev-parse', 'HEAD'], sharedCheckout).trim();
  const afterStatus = sh(['status', '--porcelain'], sharedCheckout).trim();
  assert.equal(afterHead, beforeHead, 'shared checkout HEAD must be byte-identical after publish');
  assert.equal(afterStatus, beforeStatus, 'shared checkout working tree/index must be untouched');

  const verifyDir = cloneBranch(originDir, 'ledger-franklin');
  const files = fs.readdirSync(verifyDir).filter((f) => f !== '.git');
  assert.deepEqual(files.sort(), ['README.md', 'franklin.jsonl']);
  const lines = readLines(path.join(verifyDir, 'franklin.jsonl'));
  assert.equal(lines.length, 10);
  assert.deepEqual(JSON.parse(lines[0]), { ts: 0, wake_id: 'w0', kind: 'wake', sleep_s: 120, profitable: false });

  // origin's own default branch is untouched by this publish.
  const mainTip = sh(['ls-remote', fileUrl(originDir), 'refs/heads/main'], dir).trim();
  assert.ok(mainTip.length > 0);
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
  assert.deepEqual(files.sort(), ['README.md', 'franklin.jsonl'], 'the published branch must contain ONLY the instance jsonl + README, nothing from the shared checkout');
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
    assert.ok(fs.existsSync(path.join(verifyDir, 'clawrouter.jsonl')));
  } finally {
    if (priorInstance === undefined) delete process.env.ANICCA_INSTANCE;
    else process.env.ANICCA_INSTANCE = priorInstance;
  }
});

test('REQ-703/PROP-717: a persistently failing push (both the initial attempt AND the recovery retry) is non-fatal — never throws, retains pendingLinesSincePush for the next cycle', async () => {
  const dir = tmpDir('ledger-publish-pushdown-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(10));

  // Cycle 1: everything real, establishes the branch on origin with a successful push.
  const first = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 0 });
  assert.equal(first.pushed, true);

  // Cycle 2: new lines, but `push` ALWAYS throws (both the primary attempt and the recovery's own
  // retry) — simulates a persistent network outage rather than a genuine divergence.
  writeLines(opts.ledgerPath, [...makeLines(10), ...makeLines(5, 10)]);
  const realGit = (args, cwd) => execFileSync('git', args, { cwd, encoding: 'utf8' });
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
  assert.equal(threw, false, 'publishLedgerCycle must never throw even when push AND recovery both fail');
  assert.ok(second && typeof second === 'object');
  assert.equal(second.pushed, false);
  assert.ok(logs.length >= 1);

  const marker = JSON.parse(fs.readFileSync(opts.markerPath, 'utf8'));
  assert.ok(marker.pendingLinesSincePush > 0, 'unpushed lines must remain pending so the next cycle retries the push');
  assert.equal(marker.pushedLineCount, 10, 'pushedLineCount must stay at the last CONFIRMED-pushed value, not silently advance');
});

// ── REQ-708 / PROP-712,713: same-instance overlap lock ────────────────────────────────────────────

test('REQ-708/PROP-712: a live-held lock (this process\'s own pid) causes the cycle to skip with reason "locked", no publish-repo writes', async () => {
  const dir = tmpDir('ledger-publish-lockheld-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(1));
  const lockDir = path.join(dir, 'home', 'state', '.ledger-publish-franklin.lock');
  fs.mkdirSync(lockDir, { recursive: true });
  fs.writeFileSync(path.join(lockDir, 'pid'), String(process.pid));

  const result = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, lockDir });
  assert.equal(result.reason, 'locked');
  assert.equal(fs.existsSync(path.join(dir, 'home', 'state', '.ledger-publish-repo')), false);
});

test('REQ-708/PROP-713: a stale lock (dead pid) is reclaimed and the cycle proceeds normally', async () => {
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
  assert.equal(readLines(path.join(verifyDir, 'franklin.jsonl')).length, 10);
});

// ── REQ-709 / PROP-714: divergence recovery on a rejected push ────────────────────────────────────

test('REQ-709/PROP-714: a push rejected by a non-fast-forward divergence is recovered — fetch+hard-reset+reproject-from-pushedLineCount+retry, no line dropped or duplicated', async () => {
  const dir = tmpDir('ledger-publish-divergence-');
  const { originDir, sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(10));

  const first = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 0 });
  assert.equal(first.pushed, true, 'sanity: first cycle establishes the branch on origin');

  // Simulate a divergent write to origin's ledger-franklin branch from OUTSIDE this process (e.g. a
  // stale local publish-repo state after an unclean shutdown, or a manual op) -- forces the NEXT
  // push this cycle attempts to be rejected as non-fast-forward.
  const outsideWriter = cloneBranch(originDir, 'ledger-franklin');
  fs.writeFileSync(path.join(outsideWriter, 'external-marker.txt'), 'someone else pushed this\n');
  sh(['add', 'external-marker.txt'], outsideWriter);
  sh(['-c', 'user.name=t', '-c', 'user.email=t@t.local', 'commit', '-q', '-m', 'external divergent commit'], outsideWriter);
  sh(['push', '-q', 'origin', 'ledger-franklin'], outsideWriter);

  // 12 more source lines (>=10 threshold) so this cycle both commits locally and attempts a push
  // that origin will now reject.
  writeLines(opts.ledgerPath, [...makeLines(10), ...makeLines(12, 10)]);

  const second = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 1_000_000 });
  assert.equal(second.pushed, true, 'divergence recovery must still result in a successful push this cycle');

  const verifyDir = cloneBranch(originDir, 'ledger-franklin');
  const lines = readLines(path.join(verifyDir, 'franklin.jsonl')).map((l) => JSON.parse(l));
  const wakeIds = lines.map((l) => l.wake_id);
  const uniqueWakeIds = new Set(wakeIds);
  assert.equal(wakeIds.length, uniqueWakeIds.size, 'no wake_id may appear twice — no duplicate re-publish');
  for (let i = 0; i < 22; i++) {
    assert.ok(uniqueWakeIds.has(`w${i}`), `w${i} must be present — no line silently dropped by the recovery`);
  }
  assert.ok(fs.existsSync(path.join(verifyDir, 'external-marker.txt')), 'the external divergent commit must be preserved (reset --hard onto origin, not a force-overwrite)');

  const marker = JSON.parse(fs.readFileSync(opts.markerPath, 'utf8'));
  assert.equal(marker.pushedLineCount, 22);
  assert.equal(marker.pendingLinesSincePush, 0);
});

// ── REQ-702/707 / PROP-715,716: idempotent local-append cursor across a failed local commit ──────

test('REQ-707/PROP-715: a local commit failure never causes a subsequent cycle to duplicate-append the same source lines', async () => {
  const dir = tmpDir('ledger-publish-idempotent-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(1));

  // First cycle: real setup succeeds, but the commit call itself is forced to fail via an injected
  // git wrapper that delegates to the real git for every call EXCEPT 'commit'.
  const realGit = (args, cwd) => execFileSync('git', args, { cwd, encoding: 'utf8' });
  const commitFailingGit = (args, cwd) => {
    if (args[0] === 'commit' || (args[0] === '-c' && args.includes('commit'))) throw new Error('mock commit failure');
    return realGit(args, cwd);
  };
  const logs1 = [];
  const first = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, git: commitFailingGit, log: (m) => logs1.push(m), now: () => 0 });
  assert.equal(first.published, false, 'a failed commit must not report published:true');
  const destPath = path.join(dir, 'home', 'state', '.ledger-publish-repo', 'franklin.jsonl');
  assert.equal(readLines(destPath).length, 1, 'the append to the working file still happens despite the later commit failure');

  // Second cycle: source ledger.jsonl UNCHANGED — must see zero new source lines (cursor already
  // advanced past line 0 in cycle 1), never re-append.
  const second = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 0 });
  assert.equal(second.reason, 'no-new-lines');
  assert.equal(readLines(destPath).length, 1, 'destination must contain the source line exactly once, never duplicated');
});

test('REQ-704 integration: 5 pending lines under the 10-line/15-min throttle commits locally but does NOT push', async () => {
  const dir = tmpDir('ledger-publish-nopush-');
  const { sharedCheckout } = setupOrigin(dir);
  const opts = baseOpts(dir);
  writeLines(opts.ledgerPath, makeLines(5));

  const result = await publishLedgerCycle({ ...opts, repoRoot: sharedCheckout, now: () => 1000 });
  assert.equal(result.published, true);
  assert.equal(result.pushed, false);

  const marker = JSON.parse(fs.readFileSync(opts.markerPath, 'utf8'));
  assert.equal(marker.pendingLinesSincePush, 5);
  assert.equal(marker.pushedLineCount, 0);
});
