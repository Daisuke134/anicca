"use strict";

// Tests for the daily self-build pass (spec §10 row 10f, §9.3).
//
// Everything here is deps-injected: no gh, no git, no network, no real guard run. The one thing
// that IS real is the ledger file, because the ledger is the evidence 10f is measured by and a
// mocked ledger would prove nothing.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  SELF_BUILD_VERDICTS,
  SELF_BUILD_PROTECTED_PATHS,
  selfBuildLedgerPath,
  inspectGuardLock,
  pickEligiblePr,
  readSelfBuildDays,
  selfBuildStreak,
  runSelfBuildDay,
} = require("./self-build-daily.js");
const {
  GUARD_LOCK_STALE_MS,
  classifyChangedPath,
  verifyLedgerTail,
} = require("./dev-merge-guard.js");


function tempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "lm-self-build-"));
}


// A PR shaped exactly like `gh pr view --json ...` answers for a loop-authored fix PR.
function eligiblePr(number, createdAt, overrides = {}) {
  return {
    number,
    createdAt,
    state: "OPEN",
    baseRefName: "main",
    headRefName: `feature/lm-dev-${number}`,
    headRefOid: "a".repeat(40),
    mergeable: "MERGEABLE",
    author: { login: "Daisuke134" },
    files: [{ path: "apps/life-manager/lib/travel.js" }],
    ...overrides,
  };
}


function depsFor(prs, options = {}) {
  const byNumber = new Map(prs.map((pr) => [pr.number, pr]));
  const calls = { guard: [], prechecked: [] };
  return {
    calls,
    listErrorFixPrs: async () => prs.map((pr) => ({ number: pr.number, createdAt: pr.createdAt })),
    getPullRequest: async (number) => {
      calls.prechecked.push(number);
      return byNumber.get(number) ?? null;
    },
    listChangedFiles: async ({ headOid }) => {
      const pr = prs.find((entry) => entry.headRefOid === headOid) || prs[0];
      return (pr.files || []).map((entry) => entry.path);
    },
    runGuard: options.runGuard || (async ({ prNumber }) => {
      calls.guard.push(prNumber);
      return { runId: `run-${prNumber}`, verdict: "stopped", stopReason: "review" };
    }),
    readGuardLedger: options.readGuardLedger || (() => []),
    now: options.now || (() => new Date("2026-07-28T00:00:00.000Z")),
    alert: async () => ({ delivered: false }),
  };
}


test("the day ledger path honours $LM_SELFBUILD_LEDGER and otherwise defaults under ~/.life-manager", () => {
  assert.equal(
    selfBuildLedgerPath({ LM_SELFBUILD_LEDGER: "/tmp/x.jsonl" }),
    "/tmp/x.jsonl",
  );
  assert.equal(
    selfBuildLedgerPath({ HOME: "/Users/anicca" }),
    "/Users/anicca/.life-manager/state/self-build-days.jsonl",
  );
});


test("the oldest open eligible error-fix PR is the one picked", async () => {
  const prs = [
    eligiblePr(300, "2026-07-26T09:00:00Z"),
    eligiblePr(100, "2026-07-20T09:00:00Z"),
    eligiblePr(200, "2026-07-22T09:00:00Z"),
  ];
  const deps = depsFor(prs);
  const picked = await pickEligiblePr({ deps });
  assert.equal(picked.prNumber, 100);
  assert.equal(picked.skipped.length, 0);
  // Oldest-first: the precheck must not have burned a read on a newer PR before deciding.
  assert.deepEqual(deps.calls.prechecked, [100]);
});


test("an ineligible oldest PR is skipped with its reasons and the next-oldest eligible one wins", async () => {
  const prs = [
    eligiblePr(100, "2026-07-20T09:00:00Z", { headRefName: "wip/hand-edit" }),
    eligiblePr(200, "2026-07-22T09:00:00Z"),
  ];
  const picked = await pickEligiblePr({ deps: depsFor(prs) });
  assert.equal(picked.prNumber, 200);
  assert.equal(picked.skipped.length, 1);
  assert.equal(picked.skipped[0].pr, 100);
  assert.ok(picked.skipped[0].reasons.includes("branch_name"));
});


test("the eligibility precheck is dry: nothing is merged, deployed or written by picking", async () => {
  const prs = [eligiblePr(100, "2026-07-20T09:00:00Z")];
  const deps = depsFor(prs);
  await pickEligiblePr({ deps });
  assert.deepEqual(deps.calls.guard, [], "the precheck must never invoke the guard");
});


test("a day with no eligible PR still accrues a ledger day, with an honest no-op reason", async () => {
  const dir = tempDir();
  const ledgerPath = path.join(dir, "self-build-days.jsonl");
  const prs = [eligiblePr(100, "2026-07-20T09:00:00Z", { mergeable: "CONFLICTING" })];
  const row = await runSelfBuildDay({
    deps: depsFor(prs),
    options: { ledgerPath, guardLockPath: path.join(dir, "guard.lock") },
  });

  assert.equal(row.verdict, "no_op");
  assert.equal(row.no_op_reason, "no_eligible_pr");
  assert.equal(row.pr, null);
  assert.equal(row.guard_run_ref, null);
  assert.equal(row.day, "2026-07-28");

  const rows = readSelfBuildDays(ledgerPath);
  assert.equal(rows.length, 1, "a no-op day is still a ledger day (spec: 各日 issue/PR/no-op理由)");
  assert.equal(selfBuildStreak(ledgerPath).distinctDays, 1);
});


test("no open error-fix PR at all is a distinct, honest no-op reason", async () => {
  const dir = tempDir();
  const ledgerPath = path.join(dir, "days.jsonl");
  const row = await runSelfBuildDay({
    deps: depsFor([]),
    options: { ledgerPath, guardLockPath: path.join(dir, "guard.lock") },
  });
  assert.equal(row.verdict, "no_op");
  assert.equal(row.no_op_reason, "no_open_error_fix_pr");
});


test("a real guard run is recorded with its verdict and its guard run reference", async () => {
  const dir = tempDir();
  const ledgerPath = path.join(dir, "days.jsonl");
  const deps = depsFor([eligiblePr(1094, "2026-07-24T09:00:00Z")], {
    runGuard: async () => ({ runId: "20260728000000-pr1094-abcd1234", verdict: "merged_deployed" }),
  });
  const row = await runSelfBuildDay({
    deps,
    options: { ledgerPath, guardLockPath: path.join(dir, "guard.lock") },
  });

  assert.equal(row.pr, 1094);
  assert.equal(row.verdict, "merged_deployed");
  assert.equal(row.guard_run_ref, "20260728000000-pr1094-abcd1234");
  assert.equal(row.no_op_reason, null);
  assert.ok(SELF_BUILD_VERDICTS.includes(row.verdict));
});


test("the self-build sources are handed to the guard as protected paths, so the loop cannot rewrite its own picker or judge", async () => {
  const dir = tempDir();
  let seenProtected = null;
  const deps = depsFor([eligiblePr(1094, "2026-07-24T09:00:00Z")], {
    runGuard: async ({ options }) => {
      seenProtected = options?.protectedPaths ?? null;
      return { runId: "r1", verdict: "stopped" };
    },
  });
  await runSelfBuildDay({
    deps,
    options: { ledgerPath: path.join(dir, "days.jsonl"), guardLockPath: path.join(dir, "guard.lock") },
  });

  assert.ok(Array.isArray(seenProtected));
  for (const file of SELF_BUILD_PROTECTED_PATHS) {
    assert.ok(seenProtected.includes(file), `${file} must be protected`);
    // And a protected path really is refused by the guard's own classifier.
    assert.deepEqual(
      classifyChangedPath(file, { protectedPaths: seenProtected }),
      { allowed: false, rule: "deny:guard-self" },
    );
  }
});


test("a stale guard lockfile (>30 min) is recovered and the recovery is recorded on the day row", async () => {
  const dir = tempDir();
  const lockPath = path.join(dir, "guard.lock");
  const now = new Date("2026-07-28T00:00:00.000Z");
  fs.writeFileSync(lockPath, JSON.stringify({
    pid: 999_999,
    acquired_at_ms: now.getTime() - (GUARD_LOCK_STALE_MS + 60_000),
  }), { mode: 0o600 });

  const state = inspectGuardLock(lockPath, { now: () => now });
  assert.equal(state.held, true);
  assert.equal(state.stale, true);

  const row = await runSelfBuildDay({
    deps: depsFor([eligiblePr(1094, "2026-07-24T09:00:00Z")], { now: () => now }),
    options: { ledgerPath: path.join(dir, "days.jsonl"), guardLockPath: lockPath },
  });
  assert.equal(row.recovered_stale_lock, true);
  assert.equal(row.pr, 1094, "a stale lock must not stop the day; it is taken over");
});


test("a live guard lock is never stolen: the day is recorded as locked and no guard runs", async () => {
  const dir = tempDir();
  const lockPath = path.join(dir, "guard.lock");
  const now = new Date("2026-07-28T00:00:00.000Z");
  fs.writeFileSync(lockPath, JSON.stringify({
    pid: process.pid,
    acquired_at_ms: now.getTime() - 60_000,
  }), { mode: 0o600 });

  const deps = depsFor([eligiblePr(1094, "2026-07-24T09:00:00Z")], { now: () => now });
  const row = await runSelfBuildDay({
    deps,
    options: { ledgerPath: path.join(dir, "days.jsonl"), guardLockPath: lockPath },
  });
  assert.equal(row.verdict, "locked");
  assert.equal(row.no_op_reason, "guard_lock_held");
  assert.equal(row.recovered_stale_lock, false);
  assert.deepEqual(deps.calls.guard, []);
});


test("a guard run over the budget is aborted and recorded as timeout, keeping the partial ledger row", async () => {
  const dir = tempDir();
  let aborted = false;
  const deps = depsFor([eligiblePr(1094, "2026-07-24T09:00:00Z")], {
    runGuard: ({ signal }) => new Promise((resolve) => {
      signal.addEventListener("abort", () => {
        aborted = true;
        resolve({ runId: null, verdict: "aborted" });
      });
    }),
    readGuardLedger: () => ([
      { run_id: "20260728000000-pr1094-dead", pr: 1094, verdict: "stopped", started_at: "2026-07-28T00:00:00.000Z" },
    ]),
  });
  const row = await runSelfBuildDay({
    deps,
    options: {
      ledgerPath: path.join(dir, "days.jsonl"),
      guardLockPath: path.join(dir, "guard.lock"),
      budgetMs: 20,
    },
  });

  assert.equal(aborted, true, "the budget must actually kill the run, not just report on it");
  assert.equal(row.verdict, "timeout");
  assert.equal(row.guard_run_ref, "20260728000000-pr1094-dead");
  assert.equal(row.guard_verdict, "stopped", "the partial row's verdict is kept rather than invented");
});


test("a timeout with no partial ledger row says so instead of inventing a verdict", async () => {
  const dir = tempDir();
  const deps = depsFor([eligiblePr(1094, "2026-07-24T09:00:00Z")], {
    runGuard: ({ signal }) => new Promise((resolve) => {
      signal.addEventListener("abort", () => resolve(null));
    }),
    readGuardLedger: () => [],
  });
  const row = await runSelfBuildDay({
    deps,
    options: {
      ledgerPath: path.join(dir, "days.jsonl"),
      guardLockPath: path.join(dir, "guard.lock"),
      budgetMs: 20,
    },
  });
  assert.equal(row.verdict, "timeout");
  assert.equal(row.guard_run_ref, null);
  assert.equal(row.guard_verdict, null);
});


test("a guard that throws produces an errored day row rather than a missing day", async () => {
  const dir = tempDir();
  const ledgerPath = path.join(dir, "days.jsonl");
  const deps = depsFor([eligiblePr(1094, "2026-07-24T09:00:00Z")], {
    runGuard: async () => { throw new Error("gh exploded"); },
  });
  const row = await runSelfBuildDay({
    deps,
    options: { ledgerPath, guardLockPath: path.join(dir, "guard.lock") },
  });
  assert.equal(row.verdict, "errored");
  assert.match(String(row.error), /gh exploded/);
  assert.equal(readSelfBuildDays(ledgerPath).length, 1);
});


test("an unrecognised guard verdict is flagged, not laundered into a pass", async () => {
  const dir = tempDir();
  const deps = depsFor([eligiblePr(1094, "2026-07-24T09:00:00Z")], {
    runGuard: async () => ({ runId: "r1", verdict: "everything_is_fine" }),
  });
  const row = await runSelfBuildDay({
    deps,
    options: { ledgerPath: path.join(dir, "days.jsonl"), guardLockPath: path.join(dir, "guard.lock") },
  });
  assert.equal(row.verdict, "unrecognized_guard_verdict");
  assert.equal(row.guard_verdict, "everything_is_fine");
});


test("selfBuildStreak counts distinct days and reads out the seven-day done condition", () => {
  const days = (list) => list.map((day) => ({ day, verdict: "no_op" }));

  const six = selfBuildStreak(days([
    "2026-07-21", "2026-07-22", "2026-07-23", "2026-07-24", "2026-07-25", "2026-07-26",
  ]));
  assert.equal(six.distinctDays, 6);
  assert.equal(six.remaining, 1);
  assert.equal(six.ready, false);

  const seven = selfBuildStreak(days([
    "2026-07-21", "2026-07-22", "2026-07-23", "2026-07-24", "2026-07-25", "2026-07-26",
    "2026-07-27",
  ]));
  assert.equal(seven.distinctDays, 7);
  assert.equal(seven.consecutiveDays, 7);
  assert.equal(seven.remaining, 0);
  assert.equal(seven.ready, true);
});


test("two runs on the same day accrue ONE day: duplicates cannot fake the seven-day gate", () => {
  const streak = selfBuildStreak([
    { day: "2026-07-21", verdict: "no_op" },
    { day: "2026-07-21", verdict: "merged_deployed" },
    { day: "2026-07-21", verdict: "stopped" },
    { day: "2026-07-22", verdict: "no_op" },
  ]);
  assert.equal(streak.distinctDays, 2);
  assert.equal(streak.ready, false);
});


test("a gap breaks the consecutive count while distinct days keep accruing", () => {
  const streak = selfBuildStreak([
    { day: "2026-07-01", verdict: "no_op" },
    { day: "2026-07-21", verdict: "no_op" },
    { day: "2026-07-22", verdict: "no_op" },
  ]);
  assert.equal(streak.distinctDays, 3);
  assert.equal(streak.consecutiveDays, 2);
  assert.equal(streak.lastDay, "2026-07-22");
});


test("malformed day values are ignored rather than counted as progress", () => {
  const streak = selfBuildStreak([
    { day: "2026-07-21", verdict: "no_op" },
    { day: "yesterday", verdict: "no_op" },
    { day: null, verdict: "no_op" },
  ]);
  assert.equal(streak.distinctDays, 1);
});


test("day rows are hash-chained, so an edited or deleted day is detectable", async () => {
  const dir = tempDir();
  const ledgerPath = path.join(dir, "days.jsonl");
  const lockPath = path.join(dir, "guard.lock");
  for (const day of ["2026-07-26T00:00:00.000Z", "2026-07-27T00:00:00.000Z"]) {
    await runSelfBuildDay({
      deps: depsFor([], { now: () => new Date(day) }),
      options: { ledgerPath, guardLockPath: lockPath },
    });
  }
  assert.equal(verifyLedgerTail(ledgerPath).ok, true);

  const lines = fs.readFileSync(ledgerPath, "utf8").split("\n").filter(Boolean);
  const tampered = JSON.parse(lines[0]);
  tampered.verdict = "merged_deployed";
  fs.writeFileSync(ledgerPath, `${JSON.stringify(tampered)}\n${lines[1]}\n`);
  assert.equal(verifyLedgerTail(ledgerPath).ok, false);
});


test("the ledger file is written 0600 — a day ledger is evidence, not world-readable chatter", async () => {
  const dir = tempDir();
  const ledgerPath = path.join(dir, "days.jsonl");
  await runSelfBuildDay({
    deps: depsFor([]),
    options: { ledgerPath, guardLockPath: path.join(dir, "guard.lock") },
  });
  assert.equal(fs.statSync(ledgerPath).mode & 0o777, 0o600);
});
