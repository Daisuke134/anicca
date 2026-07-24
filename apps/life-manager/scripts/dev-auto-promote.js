#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const {
  evaluatePromotion,
  decideDeploymentOutcome,
} = require("../lib/dev-auto-promote.js");


const REPO = "Daisuke134/life-manager";
const RAILWAY_PROJECT = "f9c524cb-ba4a-43bb-9639-ff736afd9ec1";
const RAILWAY_SERVICE = "life-call";
const RAILWAY_ENVIRONMENT = "production";
const HEALTH_URL = "https://life-call-production.up.railway.app/health";
const APP_DIR = path.resolve(__dirname, "..");
const REPO_DIR = path.resolve(APP_DIR, "../..");
const RUN_AGENT = process.env.LM_DEV_RUN_AGENT
  || path.join(process.env.HOME, "anicca/skills/earn/marketing-engine/run_agent.sh");
const REVIEW_SCHEMA = path.join(__dirname, "dev-auto-promote-review.schema.json");
const TERMINAL_FAILURES = new Set(["FAILED", "CRASHED", "REMOVED"]);


function run(file, args, options = {}) {
  return String(execFileSync(file, args, {
    cwd: options.cwd || REPO_DIR,
    encoding: "utf8",
    input: options.input,
    stdio: options.inherit ? "inherit" : ["pipe", "pipe", "pipe"],
    timeout: options.timeout || 20 * 60 * 1000,
    maxBuffer: 20 * 1024 * 1024,
  }) || "").trim();
}


function parseArgs(argv) {
  const result = { evaluateOnly: false };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--pr") result.pr = Number(argv[++index]);
    else if (argv[index] === "--issue") result.issue = Number(argv[++index]);
    else if (argv[index] === "--evaluate-only") result.evaluateOnly = true;
    else throw new Error("auto_promote_argument_invalid");
  }
  if (!Number.isInteger(result.pr) || result.pr < 1
      || !Number.isInteger(result.issue) || result.issue < 1) {
    throw new Error("auto_promote_argument_invalid");
  }
  return result;
}


function ghJson(args) {
  return JSON.parse(run("gh", [...args, "-R", REPO]) || "null");
}


function productionAddedLines(diff) {
  const lines = [];
  let current = "";
  for (const line of String(diff || "").split("\n")) {
    const match = line.match(/^diff --git a\/(.+) b\/(.+)$/);
    if (match) {
      current = match[2];
      continue;
    }
    const production = /^apps\/life-manager\/(?!.*\.test\.js$)(?:lib|scripts)\//.test(current);
    if (production && line.startsWith("+") && !line.startsWith("+++")) {
      lines.push(line.slice(1));
    }
  }
  return lines;
}


function loadCandidate(prNumber, issueNumber, gates) {
  const pr = ghJson([
    "pr", "view", String(prNumber),
    "--json", "number,state,baseRefName,headRefOid,mergeable,files,closingIssuesReferences,url",
  ]);
  const issue = ghJson([
    "issue", "view", String(issueNumber),
    "--json", "number,state,title,body,labels,url",
  ]);
  const openPrs = ghJson([
    "pr", "list", "--state", "open", "--limit", "100",
    "--json", "number,body",
  ]);
  const diff = run("gh", ["pr", "diff", String(prNumber), "-R", REPO, "--patch"]);
  const localHeadOid = run("git", ["rev-parse", "HEAD"]);
  const exactFix = new RegExp(`(^|\\n)Fixes #${issueNumber}\\.(\\n|$)`);
  const matchingPrs = openPrs.filter((value) => exactFix.test(String(value.body || "")));
  return {
    issueNumber,
    closingIssueNumbers: (pr.closingIssuesReferences || []).map((value) => Number(value.number)),
    openPrsForIssue: matchingPrs.length,
    issueIsPrivacySafeError:
      issue.state === "OPEN"
      && /^\[error\]\s/.test(String(issue.title || ""))
      && /<!-- lm-intake:err:sha256:[a-f0-9]{32} -->/.test(String(issue.body || ""))
      && (issue.labels || []).some((label) => label.name === "lm:type:self-heal"),
    baseRefName: pr.baseRefName,
    headOid: pr.headRefOid,
    localHeadOid,
    mergeable: pr.mergeable,
    changedFiles: (pr.files || []).map((value) => value.path),
    addedLines: productionAddedLines(diff),
    gates,
    pr,
    issue,
  };
}


function runFullGates() {
  run("npm", ["test"], { cwd: APP_DIR, inherit: true });
  run("npm", ["run", "eval"], { cwd: APP_DIR, inherit: true });
  run("npm", ["run", "eval:panel-privacy"], { cwd: APP_DIR, inherit: true });
}


function runFreshAdversary(prNumber, issueNumber, headOid, changedFiles) {
  const evidenceDir = path.join(
    process.env.HOME,
    ".openclaw/state/agent-runner-evidence",
    `life-manager-promote-${prNumber}`,
    `${Math.floor(Date.now() / 1000)}-${process.pid}`,
  );
  fs.mkdirSync(evidenceDir, { recursive: true, mode: 0o700 });
  const prompt = [
    "You are a fresh-context, artifact-only adversarial release reviewer.",
    `Review Life Manager PR #${prNumber} for privacy-safe error issue #${issueNumber}.`,
    `The exact candidate head is ${headOid}.`,
    `Changed paths: ${changedFiles.join(", ")}`,
    "Read origin/main...HEAD and relevant tests/spec only. Do not edit, commit, push, merge, deploy,",
    "contact providers, or expose secrets/PII. Find concrete correctness, privacy, path-scope,",
    "test weakness, rollback, or production-safety blockers. PASS only when blocking_findings is empty.",
  ].join("\n");
  const output = run(RUN_AGENT, [
    "--task-class", "high-value-agent",
    "--evidence-dir", evidenceDir,
    "--task-label", `life-manager-promote-${prNumber}`,
    "--loop", "life-manager-dev-promote",
    "--schema", REVIEW_SCHEMA,
    "--workdir", REPO_DIR,
    "--print-result",
  ], { input: `${prompt}\n` });
  const result = JSON.parse(output);
  return {
    passed: result.status === "pass"
      && Array.isArray(result.blocking_findings)
      && result.blocking_findings.length === 0,
    evidenceDir,
    result,
  };
}


function deploymentDetail(id) {
  const query = "query($id:String!){deployment(id:$id){id status createdAt canRollback meta}}";
  const response = JSON.parse(run("railway", [
    "api", query,
    "--variables", JSON.stringify({ id }),
  ]));
  return response.data.deployment;
}


function listDeployments() {
  return JSON.parse(run("railway", [
    "deployment", "list",
    "-p", RAILWAY_PROJECT,
    "-s", RAILWAY_SERVICE,
    "-e", RAILWAY_ENVIRONMENT,
    "--limit", "20",
    "--json",
  ]));
}


function currentSuccessfulDeployment() {
  for (const item of listDeployments()) {
    const detail = deploymentDetail(item.id);
    if (detail.status === "SUCCESS" && detail.meta && detail.meta.commitHash) return detail;
  }
  throw new Error("auto_promote_previous_deployment_missing");
}


async function readHealth() {
  try {
    const response = await fetch(HEALTH_URL, {
      headers: { "user-agent": "life-manager-auto-promote/1" },
      signal: AbortSignal.timeout(15000),
    });
    const body = await response.json();
    return response.ok && body && body.ok === true && body.service === "life-call";
  } catch {
    return false;
  }
}


async function waitForExactDeployment(commitHash, timeoutMs = 15 * 60 * 1000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    for (const item of listDeployments()) {
      const detail = deploymentDetail(item.id);
      if (detail.meta && detail.meta.commitHash === commitHash) {
        if (detail.status === "SUCCESS" || TERMINAL_FAILURES.has(detail.status)) return detail;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 10000));
  }
  throw new Error("auto_promote_deployment_timeout");
}


function deploymentRollback(id) {
  const mutation = "mutation($id:String!){deploymentRollback(id:$id)}";
  const response = JSON.parse(run("railway", [
    "api", mutation,
    "--variables", JSON.stringify({ id }),
  ]));
  if (!response.data || response.data.deploymentRollback !== true) {
    throw new Error("auto_promote_rollback_failed");
  }
}


async function main() {
  const options = parseArgs(process.argv.slice(2));
  const optimisticGates = {
    tests: true,
    evals: true,
    privacy: true,
    adversary: true,
    cleanWorktree: true,
  };
  let candidate = loadCandidate(options.pr, options.issue, optimisticGates);
  let guard = evaluatePromotion(candidate);
  if (!guard.allowed || options.evaluateOnly) {
    process.stdout.write(`${JSON.stringify({
      status: guard.allowed ? "eligible" : "refused",
      pr: options.pr,
      issue: options.issue,
      guard,
    })}\n`);
    if (!guard.allowed) process.exitCode = 3;
    return;
  }

  runFullGates();
  const review = runFreshAdversary(
    options.pr,
    options.issue,
    candidate.headOid,
    candidate.changedFiles,
  );
  const cleanWorktree = run("git", ["status", "--porcelain"]) === "";
  candidate = loadCandidate(options.pr, options.issue, {
    tests: true,
    evals: true,
    privacy: true,
    adversary: review.passed,
    cleanWorktree,
  });
  guard = evaluatePromotion(candidate);
  if (!guard.allowed) throw new Error(`auto_promote_guard_refused:${guard.reasons.join(",")}`);

  const previous = currentSuccessfulDeployment();
  const previousDeploymentHealthy = await readHealth();
  if (!previousDeploymentHealthy) throw new Error("auto_promote_previous_health_red");

  run("gh", [
    "pr", "merge", String(options.pr),
    "-R", REPO,
    "--squash", "--admin", "--delete-branch",
  ]);
  const merged = ghJson([
    "pr", "view", String(options.pr),
    "--json", "state,mergeCommit,url",
  ]);
  if (merged.state !== "MERGED" || !merged.mergeCommit || !merged.mergeCommit.oid) {
    throw new Error("auto_promote_merge_readback_failed");
  }

  const deployment = await waitForExactDeployment(merged.mergeCommit.oid);
  const healthOk = deployment.status === "SUCCESS" && await readHealth();
  const outcome = decideDeploymentOutcome({
    exactCommit: deployment.meta && deployment.meta.commitHash === merged.mergeCommit.oid,
    deploymentStatus: deployment.status,
    healthOk,
    previousDeploymentHealthy,
  });
  if (outcome.action === "rollback") {
    if (!previous.canRollback) throw new Error("auto_promote_rollback_unavailable");
    deploymentRollback(previous.id);
    const restored = await waitForExactDeployment(previous.meta.commitHash);
    if (restored.status !== "SUCCESS" || !(await readHealth())) {
      throw new Error("auto_promote_rollback_health_red");
    }
    throw new Error("auto_promote_deployment_rolled_back");
  }
  if (outcome.action !== "complete") throw new Error(`auto_promote_deployment_${outcome.action}`);

  const issue = ghJson([
    "issue", "view", String(options.issue),
    "--json", "state,url",
  ]);
  if (issue.state !== "CLOSED") throw new Error("auto_promote_issue_not_closed");
  process.stdout.write(`${JSON.stringify({
    status: "deployed",
    issue: issue.url,
    pr: merged.url,
    mergeCommit: merged.mergeCommit.oid,
    deploymentId: deployment.id,
    deploymentCommit: deployment.meta.commitHash,
    health: "ok",
    adversaryEvidenceDir: review.evidenceDir,
  })}\n`);
}


main().catch((error) => {
  process.stderr.write(`dev-auto-promote failed: ${error.message}\n`);
  process.exitCode = 1;
});
