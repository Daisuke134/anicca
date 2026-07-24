"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  acquireExclusiveLock,
  appendLedgerEntry,
  runDailyPass,
  summarizeSevenDays,
} = require("./daily-dev-loop");

function tempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "lm-daily-dev-"));
}

function writeExecutable(file, source) {
  fs.writeFileSync(file, source, { mode: 0o700 });
}

test("appendLedgerEntry writes one closed-schema JSONL record without arbitrary fields", () => {
  const dir = tempDir();
  const ledger = path.join(dir, "daily-ledger.jsonl");
  const written = appendLedgerEntry(ledger, {
    run_id: "20260724T181500-123",
    day: "2026-07-24",
    started_at: "2026-07-24T09:15:00.000Z",
    finished_at: "2026-07-24T09:15:01.000Z",
    outcome: "no_op",
    reason: "no_unattempted_open_issue",
    issue_number: null,
    pr_url: null,
    duration_ms: 1000,
    recovered_stale_lock: false,
    raw_provider_error: "must not persist",
  });

  assert.deepEqual(Object.keys(written).sort(), [
    "day",
    "duration_ms",
    "finished_at",
    "issue_number",
    "outcome",
    "pr_url",
    "reason",
    "recovered_stale_lock",
    "run_id",
    "schema_version",
    "started_at",
  ]);
  assert.equal(fs.statSync(ledger).mode & 0o077, 0);
  assert.deepEqual(JSON.parse(fs.readFileSync(ledger, "utf8")), written);
});

test("acquireExclusiveLock recovers a dead stale owner but never steals a live lock", () => {
  const dir = tempDir();
  const lock = path.join(dir, "daily.lock");
  fs.writeFileSync(lock, JSON.stringify({ pid: 999999, started_ms: 1 }), { mode: 0o600 });

  const recovered = acquireExclusiveLock(lock, {
    nowMs: 100_000,
    staleMs: 10_000,
    isPidAlive: () => false,
    pid: 321,
  });
  assert.equal(recovered.acquired, true);
  assert.equal(recovered.recoveredStale, true);
  recovered.release();

  fs.writeFileSync(lock, JSON.stringify({ pid: 777, started_ms: 90_000 }), { mode: 0o600 });
  const busy = acquireExclusiveLock(lock, {
    nowMs: 100_000,
    staleMs: 10_000,
    isPidAlive: () => true,
    pid: 321,
  });
  assert.deepEqual(busy, { acquired: false, recoveredStale: false, reason: "active_lock" });
});

test("runDailyPass records a bounded no-op with the D0 machine result", async () => {
  const dir = tempDir();
  const child = path.join(dir, "no-op.sh");
  writeExecutable(child, `#!/bin/bash
printf '%s\n' '{"status":"no_op","reason":"no_unattempted_open_issue","issue_number":null,"pr_url":null}' > "$LM_DEV_RESULT_PATH"
`);

  const result = await runDailyPass({
    command: child,
    stateDir: dir,
    timeoutMs: 2_000,
    now: () => new Date("2026-07-24T09:15:00.000Z"),
  });

  assert.equal(result.outcome, "no_op");
  assert.equal(result.reason, "no_unattempted_open_issue");
  const rows = fs.readFileSync(path.join(dir, "daily-ledger.jsonl"), "utf8").trim().split("\n");
  assert.equal(rows.length, 1);
});

test("runDailyPass kills a hung child at the hard timeout and records timeout recovery", async () => {
  const dir = tempDir();
  const child = path.join(dir, "hang.sh");
  writeExecutable(child, "#!/bin/bash\nsleep 60\n");

  const result = await runDailyPass({
    command: child,
    stateDir: dir,
    timeoutMs: 50,
    killGraceMs: 20,
  });

  assert.equal(result.outcome, "timed_out");
  assert.equal(result.reason, "hard_timeout");
  assert.equal(fs.existsSync(path.join(dir, "daily.lock")), false);
});

test("summarizeSevenDays requires seven real consecutive day keys and preserves no-op reasons", () => {
  const rows = Array.from({ length: 7 }, (_, index) => ({
    day: `2026-07-${String(18 + index).padStart(2, "0")}`,
    outcome: index === 2 ? "no_op" : "pr_open",
    reason: index === 2 ? "no_unattempted_open_issue" : "pr_created",
    issue_number: index === 2 ? null : 100 + index,
    pr_url: index === 2 ? null : `https://github.com/Daisuke134/life-manager/pull/${200 + index}`,
  }));
  assert.equal(summarizeSevenDays(rows).ready, true);

  const missingDay = rows.filter((row) => row.day !== "2026-07-21");
  assert.equal(summarizeSevenDays(missingDay).ready, false);
});
