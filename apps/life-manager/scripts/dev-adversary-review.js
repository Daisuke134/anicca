#!/usr/bin/env node
"use strict";

// The fresh adversary the merge guard calls at stage 2 (spec §10 rows 10e/10f).
//
//   node scripts/dev-merge-guard.js --pr 1094 \
//     --review-cmd "node apps/life-manager/scripts/dev-adversary-review.js"
//
// Contract, both directions:
//   IN  — the PR diff arrives on stdin. Nothing else. No repo access is assumed, no PR number, no
//         branch: the reviewer judges the diff it was handed and nothing it might have fetched.
//   OUT — one JSON object on stdout, `{"verdict":"pass"|"fail","findings":[...]}`, which is the
//         guard's contract (lowercase). The reviewer MODEL is asked for {"verdict":"PASS"|"FAIL"}
//         because upper case is what a model reliably emits; this script lowercases it.
//
// FAIL CLOSED, every time. Timeout, non-zero exit, prose instead of JSON, a missing verdict, a
// near-miss like "passed" — all of them are FAIL. The asymmetry is deliberate: a wrong FAIL costs
// one day of an unattended loop, a wrong PASS merges unreviewed code into production.
//
// MODEL ROUTING IS THE OPERATOR'S SHELL'S BUSINESS. `claude` here is whatever `claude` resolves to
// in the environment launchd hands this process — the claudexmix/Sol proxy alias, or a direct
// Anthropic session. This file pins NO model and NO provider, so the loop keeps working when
// routing changes and fails loudly (FAIL, not silent pass) when the CLI is missing. Override the
// binary with $LM_DEV_REVIEW_CLI, the budget with $LM_DEV_REVIEW_TIMEOUT_MS.
//
// FRESHNESS is the point of `-p`: one non-interactive process per review, no resumed session, no
// memory of the implementation that produced the diff. A reviewer that helped write the code is not
// a reviewer.
//
// This file is not named dev-merge-guard*, so the guard's STATIC self-deny list does not cover it —
// but the guard resolves `--review-cmd` by realpath at runtime and refuses any PR that touches the
// resolved file, so a PR cannot edit its own judge. See lib/self-build-daily-runtime.test.js.

const os = require("node:os");
const { execFileSync } = require("node:child_process");


const DEFAULT_TIMEOUT_MS = 12 * 60 * 1000;

const REVIEW_PROMPT = [
  "You are a fresh adversarial reviewer for the Life Manager repository. You did not write this",
  "change and you have no context about it beyond the unified diff on stdin.",
  "",
  "Read the diff and decide whether it is safe to merge into production UNATTENDED — no human will",
  "read it before it deploys. FAIL on any of:",
  "  - a new side effect that reaches a third party (mail, call, post, payment, on-chain transfer);",
  "  - a change that weakens a test, a gate, a privacy/PII scrub, or an allowlist;",
  "  - a secret, credential, token or personal datum added in plain text;",
  "  - a change whose blast radius you cannot bound from the diff alone;",
  "  - anything outside apps/life-manager/{lib,test,scripts} or a non-additive package.json edit.",
  "Uncertainty is a FAIL. You are the last reader before production.",
  "",
  'Answer with ONE line of JSON and nothing else: {"verdict":"PASS"|"FAIL","findings":["..."]}',
  "findings must be concrete (file + what is wrong) and must be non-empty when the verdict is FAIL.",
].join("\n");


// Models wrap JSON in prose no matter how firmly they are told not to, so the LAST balanced JSON
// object in the output wins. Scanning from the end also means a prompt echo cannot be mistaken for
// the answer.
function extractJsonObject(text) {
  const value = String(text || "");
  for (let end = value.lastIndexOf("}"); end !== -1; end = value.lastIndexOf("}", end - 1)) {
    for (let start = value.lastIndexOf("{", end); start !== -1; start = value.lastIndexOf("{", start - 1)) {
      try {
        const parsed = JSON.parse(value.slice(start, end + 1));
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
      } catch {
        // keep widening
      }
      if (start === 0) break;
    }
    if (end === 0) break;
  }
  return null;
}


function parseReviewerAnswer(text) {
  const parsed = extractJsonObject(text);
  if (!parsed) {
    return {
      verdict: "fail",
      findings: [`reviewer did not answer with JSON: ${String(text || "").trim().slice(0, 300) || "(empty)"}`],
    };
  }

  const raw = typeof parsed.verdict === "string" ? parsed.verdict.trim() : "";
  const findings = Array.isArray(parsed.findings)
    ? parsed.findings.map((finding) => String(finding)).filter(Boolean)
    : [];

  // Exact match after case folding. "passed", "PASS?", "ok" and true are all FAIL: a reviewer that
  // cannot emit the one required token has not demonstrated it understood the contract.
  if (raw.toLowerCase() === "pass") return { verdict: "pass", findings };
  if (raw.toLowerCase() === "fail") {
    return {
      verdict: "fail",
      findings: findings.length ? findings : ["reviewer returned FAIL without findings"],
    };
  }
  return {
    verdict: "fail",
    findings: findings.length
      ? findings
      : [`reviewer returned no usable verdict (${JSON.stringify(parsed.verdict ?? null)})`],
  };
}


// MEASURED 2026-07-27: `claude` on this machine is `~/.local/bin/claude` (a symlink into
// ~/.local/share/claude/versions/…), and `claudexmix` is a SHELL FUNCTION — it does not exist as a
// binary at all. The parked launchd plist's PATH is
// `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`, which contains neither. A
// reviewer that cannot be spawned fails closed, so nothing unsafe merges — but the loop would then
// burn seven days never merging anything, which is a silent waste, not a safe design. Hence: try
// PATH first, then the known install location, and only then hand over the bare name so the failure
// is an honest ENOENT naming what was missing.
function resolveReviewCli(env = process.env) {
  if (env.LM_DEV_REVIEW_CLI) return env.LM_DEV_REVIEW_CLI;
  const fs = require("node:fs");
  const path = require("node:path");
  const candidates = [
    ...String(env.PATH || "").split(path.delimiter).filter(Boolean).map((dir) => path.join(dir, "claude")),
    path.join(env.HOME || os.homedir(), ".local/bin/claude"),
  ];
  for (const candidate of candidates) {
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      return candidate;
    } catch {
      // keep looking
    }
  }
  return "claude";
}


function runAdversaryReview(input = {}) {
  const env = input.env || process.env;
  const cli = input.cli || resolveReviewCli(env);
  const args = input.args || ["-p", REVIEW_PROMPT];
  const timeoutMs = Number(input.timeoutMs || env.LM_DEV_REVIEW_TIMEOUT_MS || DEFAULT_TIMEOUT_MS);
  const exec = input.exec || execFileSync;

  let output;
  try {
    output = exec(cli, args, {
      input: String(input.diff || ""),
      encoding: "utf8",
      timeout: timeoutMs,
      killSignal: "SIGKILL",
      maxBuffer: 64 * 1024 * 1024,
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });
  } catch (error) {
    // execFileSync throws on timeout AND on non-zero exit. Both are FAIL — a reviewer that crashed
    // after printing a pass has not reviewed anything.
    const detail = error?.killed || error?.code === "ETIMEDOUT"
      ? `review command timed out after ${timeoutMs}ms`
      : `review command failed: ${error?.message || error}`;
    return { verdict: "fail", findings: [detail] };
  }

  return parseReviewerAnswer(output);
}


// Synchronous, whole-of-stdin read. The guard hands over the entire diff and closes the pipe, so
// streaming buys nothing and an async read would race the write below.
function readStdin() {
  try {
    return require("node:fs").readFileSync(process.stdin.fd, "utf8");
  } catch {
    return "";
  }
}


function main() {
  const diff = readStdin();
  if (!diff.trim()) {
    // An empty diff means the guard could not produce one. Reviewing nothing is not a pass.
    process.stdout.write(`${JSON.stringify({
      verdict: "fail",
      findings: ["no diff arrived on stdin; there is nothing to review"],
    })}\n`);
    return;
  }
  process.stdout.write(`${JSON.stringify(runAdversaryReview({ diff }))}\n`);
}


if (require.main === module) {
  try {
    main();
  } catch (error) {
    process.stdout.write(`${JSON.stringify({
      verdict: "fail",
      findings: [`review hook threw: ${error?.message || error}`],
    })}\n`);
    process.exitCode = 1;
  }
}


module.exports = {
  DEFAULT_TIMEOUT_MS,
  REVIEW_PROMPT,
  extractJsonObject,
  parseReviewerAnswer,
  resolveReviewCli,
  runAdversaryReview,
};
