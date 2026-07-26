#!/usr/bin/env node
"use strict";

// CLI entry for the unattended merge guard (spec §10 row 10e).
//
//   node scripts/dev-merge-guard.js --pr 1094 --review-cmd "my-fresh-reviewer"
//   node scripts/dev-merge-guard.js --pr 1094 --review-cmd "..." --dry-run
//
// --review-cmd receives the PR diff on stdin and must answer on stdout with
// {"verdict":"pass"|"fail","findings":[...]}. Anything else counts as FAIL. In production this
// command spawns a fresh-context reviewer; the guard only cares about the JSON contract.
//
// This atomic deliberately installs no schedule. Re-enabling the daily run belongs to 10f.

const { execFileSync } = require("node:child_process");
const {
  createGuardDeps,
  createReviewCommandHook,
  guardLedgerPath,
  runMergeGuard,
} = require("../lib/dev-merge-guard.js");


function parseArgs(argv) {
  const options = { dryRun: false };
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (flag === "--pr") options.pr = Number(argv[++index]);
    else if (flag === "--review-cmd") options.reviewCmd = String(argv[++index] || "");
    else if (flag === "--ledger") options.ledger = String(argv[++index] || "");
    else if (flag === "--dry-run") options.dryRun = true;
    else throw new Error(`dev_merge_guard_argument_invalid: ${flag}`);
  }
  if (!Number.isInteger(options.pr) || options.pr < 1) {
    throw new Error("dev_merge_guard_pr_required");
  }
  if (!options.reviewCmd) {
    // A guard with no fresh adversary is not a guard. Refuse rather than silently pass stage 3.
    throw new Error("dev_merge_guard_review_required");
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


async function main() {
  const options = parseArgs(process.argv.slice(2));
  const deps = createGuardDeps({
    exec,
    fetch: globalThis.fetch,
    ledgerPath: options.ledger || guardLedgerPath(),
  });
  deps.review = createReviewCommandHook(options.reviewCmd, { exec });

  if (options.dryRun) {
    // Everything up to (not including) the merge, so a guard change can be exercised without
    // promoting anything.
    deps.merge = async () => ({ ok: false, reason: "dry_run" });
  }

  const result = await runMergeGuard({ prNumber: options.pr, deps });
  process.stdout.write(`${JSON.stringify({
    verdict: result.verdict,
    pr: options.pr,
    stopped_at_stage: result.stoppedAtStage,
    stop_reason: result.stopReason,
    stages_passed: result.stagesPassed,
    stages_failed: result.stagesFailed,
    merge_sha: result.mergeSha,
    deploy_id: result.deployId,
    health: result.health,
    rollback: result.rollback,
    run_id: result.runId,
    ledger: deps.ledgerPath,
  })}\n`);
  if (result.verdict !== "merged_deployed") process.exitCode = 3;
}


if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`dev-merge-guard failed: ${error.message}\n`);
    process.exitCode = 1;
  });
}


module.exports = { parseArgs };
