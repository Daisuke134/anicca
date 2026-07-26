#!/usr/bin/env node
"use strict";

// CLI entry for one daily self-build pass (spec §10 row 10f).
//
//   node scripts/self-build-daily.js                 # one real pass
//   node scripts/self-build-daily.js --dry-run       # pick + precheck only, guard never runs
//   node scripts/self-build-daily.js --status        # read the ledger, print the 7-day readout
//
// Prints ONE JSON object on stdout: the day row plus the seven-day readout. The launchd entrypoint
// (skills/life-manager/self-build-daily.sh) reads that object and reports it to Telegram verbatim.
//
// The guard runs as a CHILD PROCESS, not in-process, for one reason: a 20-minute budget has to be
// enforceable. An in-process guard stuck in a network read cannot be interrupted; a detached child
// can have its whole process group killed. The child is `scripts/dev-merge-guard.js`, unchanged.
//
// This file installs no schedule. See scripts/enable-self-build-launchd.sh.

const path = require("node:path");
const { execFileSync, spawn } = require("node:child_process");

const {
  createGuardDeps,
  guardLedgerPath,
  guardLockPath,
  readLedgerRows,
} = require("../lib/dev-merge-guard.js");
const {
  DEFAULT_BUDGET_MS,
  SELF_BUILD_PROTECTED_PATHS,
  readSelfBuildDays,
  runSelfBuildDay,
  selfBuildLedgerPath,
  selfBuildStreak,
} = require("../lib/self-build-daily.js");

const APP_DIR = path.resolve(__dirname, "..");
const REPO = "Daisuke134/life-manager";
const GUARD_CLI = path.join(APP_DIR, "scripts/dev-merge-guard.js");
const REVIEW_CLI = path.join(APP_DIR, "scripts/dev-adversary-review.js");

// Only branches the loop itself produces. A hand-written branch is a human's PR and a human merges
// it; the unattended path never touches work it did not create.
const LOOP_BRANCH = /^(?:feature\/lm-dev-[1-9][0-9]*|fix\/[A-Za-z0-9][A-Za-z0-9._/-]*)$/;
const LOOP_AUTHORS = new Set(["Daisuke134"]);


function parseArgs(argv) {
  const options = { dryRun: false, status: false };
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (flag === "--dry-run") options.dryRun = true;
    else if (flag === "--status") options.status = true;
    else if (flag === "--ledger") options.ledger = String(argv[++index] || "");
    else if (flag === "--budget-ms") options.budgetMs = Number(argv[++index]);
    else throw new Error(`self_build_daily_argument_invalid: ${flag}`);
  }
  return options;
}


function exec(file, args, execOptions = {}) {
  return execFileSync(file, args, {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
    stdio: ["pipe", "pipe", "pipe"],
    ...execOptions,
  });
}


// One detached guard child, killable as a group. Resolves with the guard's own stdout JSON, or with
// null when the run was aborted/unparseable — the caller then reads the guard ledger for the truth.
function spawnGuard({ prNumber, signal, reviewCommand }) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [
      GUARD_CLI, "--pr", String(prNumber), "--review-cmd", reviewCommand,
    ], {
      cwd: APP_DIR,
      detached: process.platform !== "win32",
      env: process.env,
      stdio: ["ignore", "pipe", "inherit"],
    });

    let stdout = "";
    child.stdout.on("data", (chunk) => { stdout += String(chunk); });

    const killGroup = (sig) => {
      try {
        if (process.platform !== "win32") process.kill(-child.pid, sig);
        else child.kill(sig);
      } catch {
        // already gone
      }
    };
    const onAbort = () => {
      killGroup("SIGTERM");
      setTimeout(() => killGroup("SIGKILL"), 5_000).unref();
    };
    signal?.addEventListener("abort", onAbort, { once: true });

    child.once("error", (error) => {
      signal?.removeEventListener("abort", onAbort);
      reject(error);
    });
    child.once("close", () => {
      signal?.removeEventListener("abort", onAbort);
      let parsed = null;
      try { parsed = JSON.parse(stdout.trim().split("\n").at(-1) || "null"); } catch { parsed = null; }
      resolve(parsed ? { runId: parsed.run_id ?? null, verdict: parsed.verdict ?? null, raw: parsed } : null);
    });
  });
}


function createSelfBuildDeps(io = {}) {
  const guardIo = createGuardDeps({ exec: io.exec || exec, fetch: globalThis.fetch });
  const reviewCommand = io.reviewCommand || `${process.execPath} ${REVIEW_CLI}`;
  const gh = io.gh || ((args) => exec("gh", args));

  return {
    reviewCommand,
    listErrorFixPrs: async () => {
      const raw = gh([
        "pr", "list", "-R", REPO, "--state", "open", "--base", "main", "--limit", "100",
        "--json", "number,createdAt,headRefName,author",
      ]);
      const list = JSON.parse(String(raw || "[]"));
      return list
        .filter((pr) => LOOP_BRANCH.test(String(pr?.headRefName || "")))
        .filter((pr) => LOOP_AUTHORS.has(String(pr?.author?.login || "")))
        .map((pr) => ({ number: Number(pr.number), createdAt: String(pr.createdAt) }));
    },
    getPullRequest: guardIo.getPullRequest,
    listChangedFiles: guardIo.listChangedFiles,
    alert: guardIo.alert,
    readGuardLedger: () => readLedgerRows(guardLedgerPath()),
    runGuard: io.runGuard
      || (({ prNumber, signal }) => spawnGuard({ prNumber, signal, reviewCommand })),
  };
}


async function main() {
  const options = parseArgs(process.argv.slice(2));
  const ledgerPath = options.ledger || selfBuildLedgerPath();

  if (options.status) {
    process.stdout.write(`${JSON.stringify({
      ledger: ledgerPath,
      streak: selfBuildStreak(readSelfBuildDays(ledgerPath)),
    })}\n`);
    return;
  }

  const deps = createSelfBuildDeps();
  if (options.dryRun) {
    // Everything up to (not including) the guard, so the picker can be exercised without promoting
    // anything. Matches `scripts/dev-merge-guard.js --dry-run` in spirit.
    deps.runGuard = async () => ({ runId: null, verdict: "stopped", raw: { dry_run: true } });
  }

  const row = await runSelfBuildDay({
    deps,
    options: {
      ledgerPath,
      guardLedgerPath: guardLedgerPath(),
      guardLockPath: guardLockPath(guardLedgerPath()),
      budgetMs: Number.isFinite(options.budgetMs) ? options.budgetMs : DEFAULT_BUDGET_MS,
      protectedPaths: [...SELF_BUILD_PROTECTED_PATHS],
    },
  });

  process.stdout.write(`${JSON.stringify({
    ...row,
    dry_run: options.dryRun,
    ledger: ledgerPath,
    streak: selfBuildStreak(readSelfBuildDays(ledgerPath)),
  })}\n`);

  // Exit code carries the honest shape of the day: 0 = the pass completed (including a legitimate
  // no-op), 3 = the day ran but did not merge, 1 = the pass itself broke.
  if (row.verdict === "errored") process.exitCode = 1;
  else if (!["merged_deployed", "no_op"].includes(row.verdict)) process.exitCode = 3;
}


if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`self-build-daily failed: ${error?.message || error}\n`);
    process.exitCode = 1;
  });
}


module.exports = { LOOP_BRANCH, createSelfBuildDeps, parseArgs, spawnGuard };
