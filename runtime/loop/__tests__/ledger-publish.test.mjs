// franklin-ledger-push (P2) — behavioral-spec.md REQ-701..707 / verification-architecture.md
// PROP-701..710. Pure-core tests (decidePublish/extractWakeId) run with zero I/O; effectful-shell
// tests use a real tmp dir (fs) + an injected mock `git` function so no test ever touches the real
// ~/anicca repo, a real remote, or the network — mirrors evolve.test.mjs's tmp-dir isolation while
// swapping real git for a mock (this feature's own spec calls for an injectable git wrapper).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import {
  decidePublish,
  extractWakeId,
  publishLedgerCycle,
  DEFAULT_MIN_LINES,
  DEFAULT_MIN_INTERVAL_MS,
} from '../ledger-publish.mjs';

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function writeLines(filePath, lines) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, lines.map((l) => JSON.stringify(l)).join('\n') + '\n');
}

function readLines(filePath) {
  if (!fs.existsSync(filePath)) return [];
  return fs.readFileSync(filePath, 'utf8').split('\n').filter((l) => l.trim().length > 0);
}

// A mock git recorder: records every invocation `[args, cwd]`; throws for any arg-array whose FIRST
// element is listed in `failOn` (mirrors evolve.test.mjs's convention of driving git via
// execFileSync-shaped calls, but injected so no real process/network is touched).
function makeMockGit({ failOn = [] } = {}) {
  const calls = [];
  const git = (args, cwd) => {
    calls.push({ args, cwd });
    if (failOn.includes(args[0]) || (args[0] === '-c' && failOn.includes('commit') && args.includes('commit'))) {
      throw new Error(`mock git failure: ${args.join(' ')}`);
    }
    return '';
  };
  return { git, calls };
}

// ── REQ-704 / PROP-701..704: decidePublish (pure throttle decision) ───────────────────────────────

test('PROP-701: pendingLineCount<=0 never pushes, regardless of nowMs/lastPushTs', () => {
  const d1 = decidePublish({ pendingLineCount: 0, lastPushTs: 0, nowMs: 999_999_999 });
  assert.equal(d1.shouldPush, false);
  const d2 = decidePublish({ pendingLineCount: -1, lastPushTs: 0, nowMs: 999_999_999 });
  assert.equal(d2.shouldPush, false);
});

test('PROP-702: pendingLineCount >= DEFAULT_MIN_LINES(10) always pushes, even with zero elapsed time', () => {
  const decision = decidePublish({ pendingLineCount: DEFAULT_MIN_LINES, lastPushTs: 1000, nowMs: 1000 });
  assert.equal(decision.shouldPush, true);
  assert.equal(decision.reason, 'line-threshold');
});

test('PROP-702 boundary: 9 pending lines (below threshold) does NOT push on line-count alone', () => {
  const decision = decidePublish({ pendingLineCount: DEFAULT_MIN_LINES - 1, lastPushTs: 0, nowMs: 0 });
  assert.equal(decision.shouldPush, false);
});

test('PROP-703: 1 pending line pushes once >= 15 minutes have elapsed since last push', () => {
  const lastPushTs = 0;
  const nowMs = DEFAULT_MIN_INTERVAL_MS; // exactly at the boundary (>=)
  const decision = decidePublish({ pendingLineCount: 1, lastPushTs, nowMs });
  assert.equal(decision.shouldPush, true);
  assert.equal(decision.reason, 'time-threshold');
});

test('PROP-704: 1ms before the 15-minute floor, with pending<10, never pushes ("throttled")', () => {
  const decision = decidePublish({ pendingLineCount: 1, lastPushTs: 0, nowMs: DEFAULT_MIN_INTERVAL_MS - 1 });
  assert.equal(decision.shouldPush, false);
  assert.equal(decision.reason, 'throttled');
});

test('PROP-704: never-pushed-before (lastPushTs=0) with 1 pending line and small nowMs stays throttled (no first-push bypass)', () => {
  const decision = decidePublish({ pendingLineCount: 1, lastPushTs: 0, nowMs: 5000 });
  assert.equal(decision.shouldPush, false);
});

// ── PROP-705: extractWakeId (pure) ─────────────────────────────────────────────────────────────────

test('PROP-705: extractWakeId returns the wake_id field of a valid JSON line', () => {
  const line = JSON.stringify({ ts: 1, wake_id: '01HZABC', kind: 'wake', sleep_s: 120 });
  assert.equal(extractWakeId(line), '01HZABC');
});

test('PROP-705: extractWakeId returns "unknown" for malformed JSON', () => {
  assert.equal(extractWakeId('{not valid json'), 'unknown');
});

test('PROP-705: extractWakeId returns "unknown" when wake_id is missing or not a string', () => {
  assert.equal(extractWakeId(JSON.stringify({ ts: 1, kind: 'wake' })), 'unknown');
  assert.equal(extractWakeId(JSON.stringify({ wake_id: 42 })), 'unknown');
});

// ── REQ-701 / PROP-707: default OFF ─────────────────────────────────────────────────────────────────

test('REQ-701/PROP-707: enabled:false performs zero git calls and zero fs writes', async () => {
  const dir = tmpDir('ledger-publish-off-');
  const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
  writeLines(ledgerPath, [{ ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 }]);
  const { git, calls } = makeMockGit();
  const destPath = path.join(dir, 'repo', 'state', 'franklin-ledger', 'franklin.jsonl');

  const result = await publishLedgerCycle({
    enabled: false,
    ledgerPath,
    destPath,
    markerPath: path.join(dir, 'home', 'state', '.ledger-publish-marker'),
    instance: 'franklin',
    git,
  });

  assert.deepEqual(result, { published: false, pushed: false, reason: 'disabled' });
  assert.equal(calls.length, 0, 'no git calls when disabled');
  assert.equal(fs.existsSync(destPath), false, 'no destination file created when disabled');
});

test('REQ-701: process.env.LEDGER_PUBLISH_ENABLED default resolution — unset env means disabled with no opts.enabled override', async () => {
  const prior = process.env.LEDGER_PUBLISH_ENABLED;
  delete process.env.LEDGER_PUBLISH_ENABLED;
  try {
    const dir = tmpDir('ledger-publish-envoff-');
    const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
    writeLines(ledgerPath, [{ ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 }]);
    const { git, calls } = makeMockGit();
    const result = await publishLedgerCycle({
      ledgerPath,
      destPath: path.join(dir, 'repo', 'state', 'franklin-ledger', 'franklin.jsonl'),
      markerPath: path.join(dir, 'home', 'state', '.ledger-publish-marker'),
      instance: 'franklin',
      git,
    });
    assert.equal(result.reason, 'disabled');
    assert.equal(calls.length, 0);
  } finally {
    if (prior === undefined) delete process.env.LEDGER_PUBLISH_ENABLED;
    else process.env.LEDGER_PUBLISH_ENABLED = prior;
  }
});

// ── REQ-702 / PROP-710: enabled -> copies + path-scoped commit ────────────────────────────────────

test('REQ-702/PROP-710: enabled with new source lines copies (redacted) into destPath and issues the exact path-scoped git idiom', async () => {
  const dir = tmpDir('ledger-publish-on-');
  const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
  const line1 = { ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 };
  const line2 = { ts: 2, wake_id: 'w2', kind: 'wake', sleep_s: 120 };
  writeLines(ledgerPath, [line1, line2]);
  const destPath = path.join(dir, 'repo', 'state', 'franklin-ledger', 'franklin.jsonl');
  const markerPath = path.join(dir, 'home', 'state', '.ledger-publish-marker');
  const { git, calls } = makeMockGit();

  const result = await publishLedgerCycle({
    enabled: true,
    ledgerPath,
    destPath,
    markerPath,
    instance: 'franklin',
    repoRoot: path.join(dir, 'repo'),
    git,
    now: () => 0,
  });

  assert.equal(result.published, true);
  const written = readLines(destPath);
  assert.equal(written.length, 2);
  assert.deepEqual(JSON.parse(written[0]), line1);
  assert.deepEqual(JSON.parse(written[1]), line2);

  // exact idiom: fetch, merge --ff-only, add -- destPath, commit -m "ledger(franklin): wake w2" -- destPath
  assert.equal(calls[0].args[0], 'fetch');
  assert.equal(calls[1].args[0], 'merge');
  assert.equal(calls[1].args[1], '--ff-only');
  const addCall = calls.find((c) => c.args[0] === 'add');
  assert.deepEqual(addCall.args, ['add', '--', destPath]);
  const commitCall = calls.find((c) => c.args.includes('commit'));
  assert.ok(commitCall, 'a commit call must have been made');
  assert.ok(commitCall.args.includes('-c'), 'must set user.name/user.email like evolve.mjs (never rely on ambient git config)');
  const msgIdx = commitCall.args.indexOf('-m');
  assert.equal(commitCall.args[msgIdx + 1], 'ledger(franklin): wake w2');
  assert.deepEqual(commitCall.args.slice(-2), ['--', destPath], 'commit must be path-scoped, never git commit -a');
});

test('REQ-702: with zero new source lines and zero pending backlog, no append/commit is attempted', async () => {
  const dir = tmpDir('ledger-publish-nonew-');
  const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
  writeLines(ledgerPath, []);
  const destPath = path.join(dir, 'repo', 'state', 'franklin-ledger', 'franklin.jsonl');
  const { git, calls } = makeMockGit();

  const result = await publishLedgerCycle({
    enabled: true,
    ledgerPath,
    destPath,
    markerPath: path.join(dir, 'home', 'state', '.ledger-publish-marker'),
    instance: 'franklin',
    repoRoot: path.join(dir, 'repo'),
    git,
  });

  assert.equal(result.reason, 'no-new-lines');
  assert.equal(calls.length, 0);
  assert.equal(fs.existsSync(destPath), false);
});

test('REQ-702: ANICCA_INSTANCE default falls back to "clawrouter" when instance is omitted', async () => {
  const dir = tmpDir('ledger-publish-defaultinst-');
  const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
  writeLines(ledgerPath, [{ ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 }]);
  const priorInstance = process.env.ANICCA_INSTANCE;
  delete process.env.ANICCA_INSTANCE;
  try {
    const destPath = path.join(dir, 'repo', 'state', 'franklin-ledger', 'clawrouter.jsonl');
    const { git } = makeMockGit();
    const result = await publishLedgerCycle({
      enabled: true,
      ledgerPath,
      destPath,
      markerPath: path.join(dir, 'home', 'state', '.ledger-publish-marker'),
      repoRoot: path.join(dir, 'repo'),
      git,
    });
    assert.equal(result.published, true);
    assert.ok(fs.existsSync(destPath));
  } finally {
    if (priorInstance === undefined) delete process.env.ANICCA_INSTANCE;
    else process.env.ANICCA_INSTANCE = priorInstance;
  }
});

// ── REQ-703 / PROP-708: non-fatal git failure at each call site ───────────────────────────────────

for (const failStage of ['fetch', 'merge', 'commit', 'push']) {
  test(`REQ-703/PROP-708: git failure at '${failStage}' is logged, never thrown, cycle resolves`, async () => {
    const dir = tmpDir(`ledger-publish-fail-${failStage}-`);
    const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
    // 12 lines so the line-threshold would trigger a push attempt (exercises the push call site too).
    const lines = Array.from({ length: 12 }, (_, i) => ({ ts: i, wake_id: `w${i}`, kind: 'wake', sleep_s: 120 }));
    writeLines(ledgerPath, lines);
    const destPath = path.join(dir, 'repo', 'state', 'franklin-ledger', 'franklin.jsonl');
    const { git } = makeMockGit({ failOn: [failStage] });
    const logs = [];

    let threw = false;
    let result;
    try {
      result = await publishLedgerCycle({
        enabled: true,
        ledgerPath,
        destPath,
        markerPath: path.join(dir, 'home', 'state', '.ledger-publish-marker'),
        instance: 'franklin',
        repoRoot: path.join(dir, 'repo'),
        git,
        log: (msg) => logs.push(msg),
        now: () => 0,
      });
    } catch {
      threw = true;
    }

    assert.equal(threw, false, `publishLedgerCycle must never throw (failStage=${failStage})`);
    assert.ok(result && typeof result === 'object', 'must resolve to a result object');
    assert.ok(logs.length >= 1, `must log at least one line on ${failStage} failure`);
  });
}

// ── REQ-705: sync-before-commit skip on failure ────────────────────────────────────────────────────

test('REQ-705: git merge failure skips the ENTIRE cycle — no destPath write, no marker mutation', async () => {
  const dir = tmpDir('ledger-publish-syncfail-');
  const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
  writeLines(ledgerPath, [{ ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 }]);
  const destPath = path.join(dir, 'repo', 'state', 'franklin-ledger', 'franklin.jsonl');
  const markerPath = path.join(dir, 'home', 'state', '.ledger-publish-marker');
  const { git } = makeMockGit({ failOn: ['merge'] });

  const result = await publishLedgerCycle({
    enabled: true,
    ledgerPath,
    destPath,
    markerPath,
    instance: 'franklin',
    repoRoot: path.join(dir, 'repo'),
    git,
  });

  assert.equal(result.reason, 'sync-failed');
  assert.equal(fs.existsSync(destPath), false, 'destination file must not be created when sync fails');
  assert.equal(fs.existsSync(markerPath), false, 'marker must not be written when sync fails');
});

// ── REQ-706 / PROP-706: redaction pass-through ─────────────────────────────────────────────────────

test('REQ-706/PROP-706: a 64-hex private-key pattern in a ledger line is redacted in the destination file', async () => {
  const dir = tmpDir('ledger-publish-redact-');
  const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
  const fakeKey = '0x' + 'a'.repeat(64);
  const fakeAddress = '0x' + 'b'.repeat(40);
  fs.mkdirSync(path.dirname(ledgerPath), { recursive: true });
  // Deliberately write a hand-crafted line (not via formatRecord) to prove the SECOND redaction pass
  // this module applies independently catches a hypothetical unredacted value.
  fs.writeFileSync(
    ledgerPath,
    JSON.stringify({ ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120, leaked: fakeKey, addr: fakeAddress }) + '\n',
  );
  const destPath = path.join(dir, 'repo', 'state', 'franklin-ledger', 'franklin.jsonl');
  const { git } = makeMockGit();

  await publishLedgerCycle({
    enabled: true,
    ledgerPath,
    destPath,
    markerPath: path.join(dir, 'home', 'state', '.ledger-publish-marker'),
    instance: 'franklin',
    repoRoot: path.join(dir, 'repo'),
    git,
  });

  const written = readLines(destPath)[0];
  assert.ok(!written.includes(fakeKey), 'private-key pattern must never appear in the published file');
  assert.ok(written.includes('[REDACTED]'), 'redacted marker must be present');
  assert.ok(written.includes(fakeAddress), 'a 40-hex wallet address must be left untouched (not a secret)');
});

// ── REQ-707 / PROP-709: idempotent cursor advance across a failed commit ──────────────────────────

test('REQ-707/PROP-709: a commit failure on cycle 1 never causes cycle 2 to duplicate-append the same source lines', async () => {
  const dir = tmpDir('ledger-publish-idempotent-');
  const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
  const line1 = { ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 };
  writeLines(ledgerPath, [line1]);
  const destPath = path.join(dir, 'repo', 'state', 'franklin-ledger', 'franklin.jsonl');
  const markerPath = path.join(dir, 'home', 'state', '.ledger-publish-marker');

  const failing = makeMockGit({ failOn: ['commit'] });
  await publishLedgerCycle({
    enabled: true, ledgerPath, destPath, markerPath, instance: 'franklin',
    repoRoot: path.join(dir, 'repo'), git: failing.git, now: () => 0,
  });
  assert.equal(readLines(destPath).length, 1, 'cycle 1 still appends despite the later commit failure');

  // Cycle 2: source ledger.jsonl UNCHANGED (no new wake happened) — same file, same content.
  const succeeding = makeMockGit();
  const result2 = await publishLedgerCycle({
    enabled: true, ledgerPath, destPath, markerPath, instance: 'franklin',
    repoRoot: path.join(dir, 'repo'), git: succeeding.git, now: () => 0,
  });

  const finalLines = readLines(destPath);
  assert.equal(finalLines.length, 1, 'destination must contain the source line exactly once, never duplicated');
  assert.equal(result2.reason, 'no-new-lines', 'cycle 2 sees zero NEW source lines because the cursor already advanced past line1 in cycle 1');
});

test('REQ-707: a genuinely new line appended between cycles is copied exactly once, appended after the first', async () => {
  const dir = tmpDir('ledger-publish-idempotent2-');
  const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
  const line1 = { ts: 1, wake_id: 'w1', kind: 'wake', sleep_s: 120 };
  const line2 = { ts: 2, wake_id: 'w2', kind: 'wake', sleep_s: 120 };
  writeLines(ledgerPath, [line1]);
  const destPath = path.join(dir, 'repo', 'state', 'franklin-ledger', 'franklin.jsonl');
  const markerPath = path.join(dir, 'home', 'state', '.ledger-publish-marker');

  const failing = makeMockGit({ failOn: ['commit'] });
  await publishLedgerCycle({
    enabled: true, ledgerPath, destPath, markerPath, instance: 'franklin',
    repoRoot: path.join(dir, 'repo'), git: failing.git, now: () => 0,
  });

  // A new wake happened: ledger.jsonl grew by one more line.
  fs.appendFileSync(ledgerPath, JSON.stringify(line2) + '\n');

  const succeeding = makeMockGit();
  await publishLedgerCycle({
    enabled: true, ledgerPath, destPath, markerPath, instance: 'franklin',
    repoRoot: path.join(dir, 'repo'), git: succeeding.git, now: () => 0,
  });

  const finalLines = readLines(destPath).map((l) => JSON.parse(l));
  assert.equal(finalLines.length, 2, 'both lines present, neither duplicated');
  assert.deepEqual(finalLines[0], line1);
  assert.deepEqual(finalLines[1], line2);
});

// ── REQ-704 integration: push only fires once the throttle is crossed ─────────────────────────────

test('REQ-704 integration: 5 pending lines under the 10-line / 15-min throttle → commits locally but does NOT push', async () => {
  const dir = tmpDir('ledger-publish-nopush-');
  const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
  const lines = Array.from({ length: 5 }, (_, i) => ({ ts: i, wake_id: `w${i}`, kind: 'wake', sleep_s: 120 }));
  writeLines(ledgerPath, lines);
  const destPath = path.join(dir, 'repo', 'state', 'franklin-ledger', 'franklin.jsonl');
  const { git, calls } = makeMockGit();

  const result = await publishLedgerCycle({
    enabled: true,
    ledgerPath,
    destPath,
    markerPath: path.join(dir, 'home', 'state', '.ledger-publish-marker'),
    instance: 'franklin',
    repoRoot: path.join(dir, 'repo'),
    git,
    now: () => 1000, // small elapsed since lastPushTs default 0, well under 15min
  });

  assert.equal(result.published, true);
  assert.equal(result.pushed, false);
  assert.equal(calls.some((c) => c.args[0] === 'push'), false, 'push must not be attempted under throttle');
});

test('REQ-704 integration: >=10 pending lines DOES push, and marker resets pendingLinesSincePush to 0 after a successful push', async () => {
  const dir = tmpDir('ledger-publish-push-');
  const ledgerPath = path.join(dir, 'home', 'state', 'ledger.jsonl');
  const lines = Array.from({ length: 10 }, (_, i) => ({ ts: i, wake_id: `w${i}`, kind: 'wake', sleep_s: 120 }));
  writeLines(ledgerPath, lines);
  const destPath = path.join(dir, 'repo', 'state', 'franklin-ledger', 'franklin.jsonl');
  const markerPath = path.join(dir, 'home', 'state', '.ledger-publish-marker');
  const { git, calls } = makeMockGit();

  const result = await publishLedgerCycle({
    enabled: true,
    ledgerPath,
    destPath,
    markerPath,
    instance: 'franklin',
    repoRoot: path.join(dir, 'repo'),
    git,
    now: () => 5000,
  });

  assert.equal(result.pushed, true);
  assert.ok(calls.some((c) => c.args[0] === 'push' && c.args[1] === 'origin' && c.args[2] === 'main'));

  const marker = JSON.parse(fs.readFileSync(markerPath, 'utf8'));
  assert.equal(marker.pendingLinesSincePush, 0);
  assert.equal(marker.lastPushTs, 5000);
});
