"use strict";

// Unattended merge guard for the DEV self-build loop (spec §10 row 10e, §9.3).
//
// The loop already produces fix PRs (lib/daily-dev-loop.js -> scripts/life-manager-dev-d0.sh,
// fed by lib/error-intake.js and lib/feedback-to-issue.js). This module is the gate that stands
// between such a PR and production. It is deliberately paranoid: every stage must sign off, in
// order, and the FIRST failure is a hard stop with an honest verdict. Nothing merges on a maybe.
//
// This file contains no schedule wiring on purpose — re-enabling launchd is 10f's job.

const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");


const REPO = "Daisuke134/life-manager";
const RAILWAY_PROJECT = "f9c524cb-ba4a-43bb-9639-ff736afd9ec1";
const RAILWAY_SERVICE = "life-call";
const RAILWAY_ENVIRONMENT = "production";
const HEALTH_URL = "https://life-call-production.up.railway.app/health";
const APP_DIR = path.resolve(__dirname, "..");
const REPO_DIR = path.resolve(APP_DIR, "../..");

// Verified against railway CLI 5.28.0 and the live public GraphQL schema on 2026-07-27:
//   * `railway redeploy` accepts only -s/-e/-p/-y/--json/--from-source. There is NO way to point
//     it at an older deployment id, so "redeploy the previous deployment" is not a CLI feature.
//   * `railway deployment` exposes only list/up/redeploy — again no rollback subcommand.
//   * `Mutation.deploymentRollback(id: String!): Boolean!` ("Rolls back to a deployment.") and
//     `Deployment.canRollback: Boolean!` DO exist, reachable through `railway api`.
// So: rollback runs through `railway api`, gated on canRollback, and falls back to an automatic
// revert PR + alert when Railway says the old deployment is no longer rollback-able.
const ROLLBACK_MUTATION = "mutation($id:String!){deploymentRollback(id:$id)}";
const DEPLOYMENT_DETAIL_QUERY =
  "query($id:String!){deployment(id:$id){id status createdAt canRollback meta}}";

const GUARD_STAGES = Object.freeze([
  "eligibility",
  "tests",
  "review",
  "blocked_actions",
  "merge",
  "deploy_health",
]);

const DEFAULT_AUTHORS = Object.freeze(["Daisuke134"]);

// The loop names its branches `feature/lm-dev-<issue>` (real: PR #1094 -> feature/lm-dev-1090,
// PR #1095 -> feature/lm-dev-1089). `fix/...` is accepted for hand-shaped error fixes.
const BRANCH_PATTERNS = Object.freeze([
  /^feature\/lm-dev-[1-9][0-9]*$/,
  /^fix\/[A-Za-z0-9][A-Za-z0-9._/-]*$/,
]);

const ALLOWED_DIRECTORIES = Object.freeze([
  ["apps/life-manager/lib/", "allow:lib"],
  ["apps/life-manager/test/", "allow:test"],
  ["apps/life-manager/scripts/", "allow:scripts"],
]);

const CONDITIONAL_MANIFEST = "apps/life-manager/package.json";

// package.json script keys the loop may touch: it must be able to register a new regression test.
const MUTABLE_SCRIPTS = Object.freeze(["test", "pretest"]);

// Named function shapes that must never enter production through an unattended merge.
// Grep-based on purpose: this is a last-resort tripwire, not a type system. It runs over ADDED
// diff lines only, so pre-existing calls elsewhere in the repo are not the guard's business.
const BLOCKED_ACTIONS = Object.freeze([
  Object.freeze({
    action: "outreach_send",
    // §9.5: the agent contacts third parties on Dais's behalf. A bad unattended merge that gains
    // an outreach call can mail or ring strangers before anyone reads the diff — irreversible
    // reputational damage, and the one class of side effect Dais cannot undo.
    rationale: "New third-party outreach (mail/call/post) must never ship without a human read.",
    pattern: /\b(?:outreach_send|sendOutreach|sendOutreachEmail|sendMail|sendEmail|makeCall|placeCall|dialOut|postToSocial|telegramSend)\s*\(/,
  }),
  Object.freeze({
    action: "payment",
    // Money leaving or entering a real card/account is irreversible and legally consequential;
    // the billing surface (lib/billing.js) changes only under review.
    rationale: "New charge/refund/payout calls move real money and are irreversible once sent.",
    pattern: /\b(?:paymentIntents|charges|payouts|subscriptions)\.(?:create|update|cancel|del)\s*\(|\b(?:chargeCard|capturePayment|createCharge|issueRefund)\s*\(/,
  }),
  Object.freeze({
    action: "wallet_transfer",
    // §9.8: the agent wallet is the FINANCIAL organ's identity. An on-chain transfer cannot be
    // rolled back by any deploy, so it can never be introduced by machinery that self-merges.
    rationale: "On-chain transfers cannot be reverted by a redeploy, so they never self-merge.",
    pattern: /\b(?:wallet\.transfer|sendTransaction|sendRawTransaction|eth_sendRawTransaction|signTransaction|transferFrom|sendUserOperation)\s*\(/,
  }),
]);

// The guard must be able to fix itself. Its own blocklist declaration lines mention the very
// names it hunts for, so those exact declaration lines (and only those) are exempt.
const GUARD_SOURCE_SUFFIX = "lib/dev-merge-guard.js";
const GUARD_DECLARATION_LINE = /^\s*pattern:\s*\//;


function stableStringify(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value) ?? "null";
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  const keys = Object.keys(value).sort();
  return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
}


function sha256(text) {
  return crypto.createHash("sha256").update(text).digest("hex");
}


function classifyChangedPath(file) {
  const value = String(file || "");
  const basename = value.split("/").pop() || "";
  if (/^\.github\//.test(value)) return { allowed: false, rule: "deny:workflow" };
  if (/(^|\/)migrations?(\/|$)/i.test(value)) return { allowed: false, rule: "deny:migration" };
  if (/^\.env($|\.)/.test(basename)) return { allowed: false, rule: "deny:env" };
  if (/^docs\/superpowers\/specs\//.test(value)) return { allowed: false, rule: "deny:spec" };
  if (/^skills\//.test(value)) return { allowed: false, rule: "deny:skill" };
  if (value === CONDITIONAL_MANIFEST) {
    return { allowed: false, conditional: true, rule: "conditional:package-json" };
  }
  for (const [prefix, rule] of ALLOWED_DIRECTORIES) {
    if (value.startsWith(prefix)) return { allowed: true, rule };
  }
  return { allowed: false, rule: "deny:not-allowlisted" };
}


function isAdditiveOnly(before = {}, after = {}) {
  for (const [name, version] of Object.entries(before)) {
    if (after[name] !== version) return false;
  }
  return true;
}


// A dependency change ships new third-party code straight into production, so it is refused
// outright. Adding a devDependency, or appending a test file to the `test`/`pretest` line, is the
// one manifest edit the loop legitimately needs to register a regression test.
function evaluatePackageJsonChange(before, after) {
  const reasons = [];
  const left = before && typeof before === "object" ? before : {};
  const right = after && typeof after === "object" ? after : {};

  if (stableStringify(left.dependencies ?? {}) !== stableStringify(right.dependencies ?? {})) {
    reasons.push("dependencies_changed");
  }
  if (!isAdditiveOnly(left.devDependencies ?? {}, right.devDependencies ?? {})) {
    reasons.push("devdependencies_not_additive");
  }

  const leftScripts = { ...(left.scripts ?? {}) };
  const rightScripts = { ...(right.scripts ?? {}) };
  for (const key of MUTABLE_SCRIPTS) {
    delete leftScripts[key];
    delete rightScripts[key];
  }
  if (stableStringify(leftScripts) !== stableStringify(rightScripts)) {
    reasons.push("scripts_changed_outside_test");
  }

  const ignored = new Set(["dependencies", "devDependencies", "scripts"]);
  const otherKeys = [...new Set([...Object.keys(left), ...Object.keys(right)])]
    .filter((key) => !ignored.has(key));
  for (const key of otherKeys) {
    if (stableStringify(left[key]) !== stableStringify(right[key])) {
      reasons.push("other_fields_changed");
      break;
    }
  }
  return { allowed: reasons.length === 0, reasons };
}


function evaluateEligibility(pr, options = {}) {
  const authors = options.allowedAuthors || DEFAULT_AUTHORS;
  const reasons = [];
  const value = pr || {};

  if (value.state !== "OPEN") reasons.push("pr_not_open");
  if (value.baseRefName !== "main") reasons.push("base_branch");
  if (!BRANCH_PATTERNS.some((pattern) => pattern.test(String(value.headRefName || "")))) {
    reasons.push("branch_name");
  }
  if (!authors.includes(String(value.author?.login || ""))) reasons.push("author_not_allowlisted");
  if (!/^[a-f0-9]{40}$/.test(String(value.headRefOid || ""))) reasons.push("head_oid_missing");
  if (value.mergeable !== "MERGEABLE") reasons.push("not_mergeable");

  const files = Array.isArray(value.files) ? value.files.map((entry) => entry.path) : [];
  if (files.length === 0) reasons.push("no_changed_files");

  const deniedPaths = [];
  const conditionalPaths = [];
  for (const file of files) {
    const verdict = classifyChangedPath(file);
    if (verdict.allowed) continue;
    if (verdict.conditional) conditionalPaths.push(file);
    else deniedPaths.push({ path: file, rule: verdict.rule });
  }
  if (deniedPaths.length > 0) reasons.push("path_allowlist");

  return {
    ok: reasons.length === 0,
    reasons,
    changedPaths: files,
    deniedPaths,
    conditionalPaths,
  };
}


function parseAddedLines(diff) {
  const added = [];
  let current = "";
  for (const line of String(diff || "").split("\n")) {
    const header = line.match(/^diff --git a\/(.+?) b\/(.+)$/);
    if (header) {
      current = header[2];
      continue;
    }
    const target = line.match(/^\+\+\+ b\/(.+)$/);
    if (target) {
      current = target[1];
      continue;
    }
    if (line.startsWith("+++") || line.startsWith("---")) continue;
    if (line.startsWith("+")) added.push({ path: current, line: line.slice(1) });
  }
  return added;
}


function detectBlockedActions(addedLines) {
  const hits = [];
  for (const entry of Array.isArray(addedLines) ? addedLines : []) {
    const file = String(entry?.path || "");
    const line = String(entry?.line || "");
    if (file.endsWith(GUARD_SOURCE_SUFFIX) && GUARD_DECLARATION_LINE.test(line)) continue;
    for (const blocked of BLOCKED_ACTIONS) {
      if (blocked.pattern.test(line)) {
        hits.push({ action: blocked.action, path: file, line, rationale: blocked.rationale });
      }
    }
  }
  return hits;
}


function chainSeed(runId) {
  return sha256(`dev-merge-guard:v1:${runId}`);
}


function signStageChain(runId, records) {
  let prev = chainSeed(runId);
  return records.map((record) => {
    const body = { ...record, prev };
    const signature = sha256(stableStringify(body));
    prev = signature;
    return { ...body, signature };
  });
}


function verifyStageChain(runId, records) {
  let prev = chainSeed(runId);
  for (const record of Array.isArray(records) ? records : []) {
    if (!record || record.prev !== prev) return false;
    const { signature, ...body } = record;
    if (sha256(stableStringify(body)) !== signature) return false;
    prev = signature;
  }
  return true;
}


function guardLedgerPath(env = process.env) {
  if (env.LM_DEV_GUARD_LEDGER) return env.LM_DEV_GUARD_LEDGER;
  const home = env.HOME || os.homedir();
  return path.join(home, ".life-manager/state/dev-guard-runs.jsonl");
}


function appendGuardRun(ledgerPath, row) {
  fs.mkdirSync(path.dirname(ledgerPath), { recursive: true, mode: 0o700 });
  fs.appendFileSync(ledgerPath, `${JSON.stringify(row)}\n`, { mode: 0o600 });
  fs.chmodSync(ledgerPath, 0o600);
  return row;
}


function tail(text, limit = 4000) {
  const value = String(text || "");
  return value.length <= limit ? value : value.slice(-limit);
}


function normalizeReview(answer) {
  const verdict = answer && typeof answer === "object" ? String(answer.verdict || "") : "";
  const findings = answer && Array.isArray(answer.findings)
    ? answer.findings.map((finding) => String(finding))
    : [];
  if (verdict !== "pass" && verdict !== "fail") {
    return {
      ok: false,
      verdict: verdict || null,
      findings: findings.length ? findings : ["reviewer returned no usable verdict"],
    };
  }
  return { ok: verdict === "pass", verdict, findings };
}


function createReviewCommandHook(command, options = {}) {
  const exec = options.exec;
  if (typeof exec !== "function") throw new Error("dev_merge_guard_review_exec_required");
  return async (diff) => {
    try {
      const output = exec("/bin/sh", ["-c", String(command)], {
        input: String(diff || ""),
        encoding: "utf8",
        timeout: options.timeoutMs || 30 * 60 * 1000,
        maxBuffer: 64 * 1024 * 1024,
      });
      const parsed = JSON.parse(String(output || ""));
      const verdict = parsed && parsed.verdict === "pass" ? "pass" : "fail";
      const findings = Array.isArray(parsed?.findings) ? parsed.findings.map(String) : [];
      if (verdict === "fail" && findings.length === 0) {
        findings.push("reviewer returned a non-pass verdict without findings");
      }
      return { verdict, findings };
    } catch (error) {
      return {
        verdict: "fail",
        findings: [`review command did not return JSON: ${error.message}`],
      };
    }
  };
}


async function pollUntil(probe, { now, sleep, timeoutMs, intervalMs }) {
  const deadline = now().getTime() + timeoutMs;
  for (;;) {
    const value = await probe();
    if (value) return value;
    if (now().getTime() >= deadline) return null;
    await sleep(intervalMs);
  }
}


function createGuardDeps(io = {}) {
  const execImpl = io.exec;
  if (typeof execImpl !== "function") throw new Error("dev_merge_guard_exec_required");
  const fetchImpl = io.fetch || globalThis.fetch;
  const ghImpl = io.gh || ((args, options) => execImpl("gh", args, options));
  const config = io.config || {};
  const repo = config.repo || REPO;
  const repoDir = config.repoDir || REPO_DIR;
  const appSubdir = config.appSubdir || "apps/life-manager";
  const healthUrl = config.healthUrl || HEALTH_URL;
  const railwayArgs = [
    "-p", config.project || RAILWAY_PROJECT,
    "-s", config.service || RAILWAY_SERVICE,
    "-e", config.environment || RAILWAY_ENVIRONMENT,
  ];

  const gh = (args) => String(ghImpl([...args], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }) || "");
  const ghJson = (args) => JSON.parse(gh(args) || "null");
  const railway = (args, options) => String(execImpl("railway", args, {
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
    ...options,
  }) || "");

  const sleep = io.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  // GitHub computes mergeability lazily: the first read of a PR that has not been checked since
  // its last push answers UNKNOWN, and asking is what schedules the computation. Measured on real
  // PR #1094 on 2026-07-27 — the guard refused a perfectly mergeable PR on the first query and saw
  // MERGEABLE on the next. Retry rather than turn GitHub's laziness into a false refusal.
  const mergeabilityAttempts = config.mergeabilityAttempts ?? 6;
  const mergeabilityIntervalMs = config.mergeabilityIntervalMs ?? 3000;

  return {
    now: io.now || (() => new Date()),
    sleep,
    ledgerPath: io.ledgerPath || guardLedgerPath(),

    async getPullRequest(prNumber) {
      let pr = null;
      for (let attempt = 0; attempt < mergeabilityAttempts; attempt += 1) {
        if (attempt > 0) await sleep(mergeabilityIntervalMs);
        pr = ghJson([
          "pr", "view", String(prNumber), "-R", repo,
          "--json", "number,state,baseRefName,headRefName,headRefOid,author,mergeable,files,url,body",
        ]);
        if (pr?.mergeable !== "UNKNOWN") return pr;
      }
      return pr;
    },

    async getDiff(prNumber) {
      return gh(["pr", "diff", String(prNumber), "-R", repo, "--patch"]);
    },

    async readFileAtRef({ ref, path: filePath }) {
      try {
        const encoded = gh([
          "api", `repos/${repo}/contents/${filePath}?ref=${encodeURIComponent(ref)}`,
          "--jq", ".content",
        ]).trim();
        return Buffer.from(encoded, "base64").toString("utf8");
      } catch {
        return null;
      }
    },

    // Full suite + evals against a throwaway checkout of the PR head, so nothing in the
    // operator's working tree can make a red PR look green.
    async runTests({ headOid, headRefName }) {
      const worktree = fs.mkdtempSync(path.join(os.tmpdir(), "lm-guard-worktree-"));
      const appDir = path.join(worktree, appSubdir);
      const output = [];
      const run = (file, args, cwd) => {
        output.push(`$ ${file} ${args.join(" ")}`);
        output.push(String(execImpl(file, args, {
          cwd,
          encoding: "utf8",
          maxBuffer: 64 * 1024 * 1024,
          timeout: 60 * 60 * 1000,
        }) || ""));
      };
      try {
        run("git", ["fetch", "origin", String(headRefName)], repoDir);
        run("git", ["worktree", "add", "--detach", worktree, String(headOid)], repoDir);
        run("npm", ["ci", "--silent"], appDir);
        run("npm", ["test"], appDir);
        run("npm", ["run", "eval"], appDir);
        return { ok: true, exitCode: 0, output: output.join("\n") };
      } catch (error) {
        output.push(String(error.stdout || ""));
        output.push(String(error.stderr || error.message || ""));
        return { ok: false, exitCode: Number.isInteger(error.status) ? error.status : 1, output: output.join("\n") };
      } finally {
        try { execImpl("git", ["worktree", "remove", "--force", worktree], { cwd: repoDir, encoding: "utf8" }); } catch {}
        try { fs.rmSync(worktree, { recursive: true, force: true }); } catch {}
      }
    },

    async merge({ prNumber, headOid }) {
      try {
        gh([
          "pr", "merge", String(prNumber), "-R", repo,
          "--squash", "--delete-branch", "--match-head-commit", String(headOid),
        ]);
      } catch (error) {
        return { ok: false, reason: `merge_command_failed: ${error.message}` };
      }
      const readback = ghJson(["pr", "view", String(prNumber), "-R", repo, "--json", "state,mergeCommit"]);
      const mergeSha = readback?.mergeCommit?.oid || null;
      if (readback?.state !== "MERGED" || !/^[a-f0-9]{40}$/.test(String(mergeSha))) {
        return { ok: false, reason: "merge_readback_failed" };
      }
      return { ok: true, mergeSha };
    },

    async listDeployments() {
      const raw = railway(["deployment", "list", ...railwayArgs, "--limit", "20", "--json"]);
      const parsed = JSON.parse(raw || "[]");
      return Array.isArray(parsed) ? parsed : [];
    },

    async getPreviousSuccessfulDeployment() {
      const raw = railway(["deployment", "list", ...railwayArgs, "--limit", "20", "--json"]);
      const list = JSON.parse(raw || "[]");
      for (const item of Array.isArray(list) ? list : []) {
        if (item.status !== "SUCCESS" || !item.meta?.commitHash) continue;
        const detail = JSON.parse(railway([
          "api", DEPLOYMENT_DETAIL_QUERY, "--variables", JSON.stringify({ id: item.id }),
        ]) || "null");
        const deployment = detail?.data?.deployment;
        if (!deployment) continue;
        return {
          id: deployment.id,
          status: deployment.status,
          canRollback: deployment.canRollback === true,
          commitHash: deployment.meta?.commitHash || item.meta.commitHash,
        };
      }
      return null;
    },

    async triggerRedeploy() {
      try {
        return { ok: true, raw: railway(["redeploy", ...railwayArgs, "--yes", "--json"]) };
      } catch (error) {
        return { ok: false, raw: String(error.message || "") };
      }
    },

    async checkHealth() {
      try {
        const response = await fetchImpl(healthUrl, {
          headers: { "user-agent": "life-manager-dev-merge-guard/1" },
          signal: AbortSignal.timeout(15000),
        });
        if (!response.ok) return false;
        const body = await response.json();
        return body?.ok === true;
      } catch {
        return false;
      }
    },

    // `railway redeploy` cannot target a deployment id (verified above), so rollback is the
    // GraphQL mutation the CLI proxies through `railway api`.
    async rollback({ deploymentId }) {
      try {
        const raw = railway([
          "api", ROLLBACK_MUTATION, "--variables", JSON.stringify({ id: String(deploymentId) }),
        ]);
        const parsed = JSON.parse(raw || "null");
        return { ok: parsed?.data?.deploymentRollback === true, raw };
      } catch (error) {
        return { ok: false, raw: String(error.message || "") };
      }
    },

    async openRevertPr({ mergeSha, prNumber }) {
      const branch = `revert/lm-dev-${prNumber}-${String(mergeSha).slice(0, 12)}`;
      const worktree = fs.mkdtempSync(path.join(os.tmpdir(), "lm-guard-revert-"));
      try {
        execImpl("git", ["fetch", "origin", "main"], { cwd: repoDir, encoding: "utf8" });
        execImpl("git", ["worktree", "add", "-b", branch, worktree, "origin/main"], { cwd: repoDir, encoding: "utf8" });
        execImpl("git", ["revert", "--no-edit", "-m", "1", String(mergeSha)], { cwd: worktree, encoding: "utf8" });
        execImpl("git", ["push", "-u", "origin", branch], { cwd: worktree, encoding: "utf8" });
        const url = gh([
          "pr", "create", "-R", repo, "--base", "main", "--head", branch,
          "--title", `revert: roll back PR #${prNumber} after a red production health check`,
          "--body", [
            `Automatic revert of \`${mergeSha}\` (merged from #${prNumber}).`,
            "",
            "Production health did not come back after the deploy and the previous Railway",
            "deployment reported `canRollback: false`, so the guard could not roll the platform",
            "back. This PR is the rollback. Production is still on the merged commit until it lands.",
          ].join("\n"),
        ]).trim();
        return { url };
      } catch (error) {
        return { url: null, error: String(error.message || "") };
      } finally {
        try { execImpl("git", ["worktree", "remove", "--force", worktree], { cwd: repoDir, encoding: "utf8" }); } catch {}
        try { fs.rmSync(worktree, { recursive: true, force: true }); } catch {}
      }
    },

    async alert(message) {
      process.stderr.write(`dev-merge-guard ALERT: ${message}\n`);
    },
  };
}


async function runMergeGuard({ prNumber, deps, options = {} }) {
  if (!deps || typeof deps.getPullRequest !== "function") {
    throw new Error("dev_merge_guard_deps_required");
  }
  const now = deps.now || (() => new Date());
  const sleep = deps.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  const healthTimeoutMs = options.healthTimeoutMs ?? 10 * 60 * 1000;
  const healthIntervalMs = options.healthIntervalMs ?? 10_000;
  const freshTimeoutMs = options.freshTimeoutMs ?? 15 * 60 * 1000;
  const freshIntervalMs = options.freshIntervalMs ?? 10_000;

  const started = now();
  const runId = `${started.toISOString().replace(/\D/g, "").slice(0, 14)}-pr${prNumber}-${crypto.randomBytes(4).toString("hex")}`;

  const records = [];
  const state = {
    stoppedAtStage: null,
    stopReason: null,
    mergeSha: null,
    deployId: null,
    health: "skipped",
    rollback: null,
  };

  const record = (stage, ok, reason, evidence) => {
    // A reason only ever describes a failure; a passing stage carries none.
    records.push({ stage, ok, reason: ok ? null : (reason || stage), evidence: evidence || {} });
    if (!ok && GUARD_STAGES.includes(stage) && state.stoppedAtStage === null) {
      state.stoppedAtStage = stage;
      state.stopReason = reason || stage;
    }
    return ok;
  };

  let diff = null;
  const loadDiff = async () => {
    if (diff === null) diff = String(await deps.getDiff(prNumber) || "");
    return diff;
  };

  let verdict = "stopped";

  run: {
    // 1. Eligibility.
    const pr = await deps.getPullRequest(prNumber);
    const eligibility = evaluateEligibility(pr, { allowedAuthors: options.allowedAuthors });
    const reasons = [...eligibility.reasons];
    const manifest = {};
    if (eligibility.conditionalPaths.includes(CONDITIONAL_MANIFEST)) {
      const before = await deps.readFileAtRef({ ref: pr.baseRefName, path: CONDITIONAL_MANIFEST });
      const after = await deps.readFileAtRef({ ref: pr.headRefOid, path: CONDITIONAL_MANIFEST });
      let evaluated;
      try {
        evaluated = evaluatePackageJsonChange(JSON.parse(before), JSON.parse(after));
      } catch {
        evaluated = { allowed: false, reasons: ["unreadable"] };
      }
      manifest.package_json = evaluated;
      for (const reason of evaluated.reasons) reasons.push(`package_json:${reason}`);
    }
    if (!record("eligibility", reasons.length === 0, reasons.join(","), {
      pr: pr?.number ?? prNumber,
      branch: pr?.headRefName ?? null,
      author: pr?.author?.login ?? null,
      head_oid: pr?.headRefOid ?? null,
      changed_paths: eligibility.changedPaths,
      denied_paths: eligibility.deniedPaths,
      conditional_paths: eligibility.conditionalPaths,
      ...manifest,
    })) break run;

    // 2. Tests + evals, in an isolated worktree of the PR branch.
    const tests = await deps.runTests({ headOid: pr.headRefOid, headRefName: pr.headRefName });
    if (!record("tests", tests?.ok === true && tests.exitCode === 0, "test_suite_red", {
      exit_code: tests?.exitCode ?? null,
      output_tail: tail(tests?.output),
    })) break run;

    // 3. Fresh adversary.
    const review = normalizeReview(await deps.review(await loadDiff(), {
      prNumber,
      headOid: pr.headRefOid,
    }));
    if (!record("review", review.ok, "adversary_fail", {
      verdict: review.verdict,
      findings: review.findings,
    })) break run;

    // 4. BlockedActions tripwire.
    const hits = detectBlockedActions(parseAddedLines(await loadDiff()));
    if (!record("blocked_actions", hits.length === 0, "blocked_actions_present", { hits })) break run;

    // 5. Merge. The rollback target is read BEFORE the merge, while it is still the live one.
    const previous = await deps.getPreviousSuccessfulDeployment();
    const merged = await deps.merge({ prNumber, headOid: pr.headRefOid });
    const mergeOk = merged?.ok === true && /^[a-f0-9]{40}$/.test(String(merged.mergeSha || ""));
    if (mergeOk) state.mergeSha = merged.mergeSha;
    if (!record("merge", mergeOk, merged?.reason || "merge_failed", {
      merge_sha: state.mergeSha,
      previous_deployment_id: previous?.id ?? null,
      previous_deployment_can_rollback: previous?.canRollback ?? null,
    })) break run;

    // 6. Deploy + health + deploy freshness.
    const redeploy = await deps.triggerRedeploy();
    const healthy = await pollUntil(() => deps.checkHealth(), {
      now, sleep, timeoutMs: healthTimeoutMs, intervalMs: healthIntervalMs,
    });
    if (!healthy) {
      state.health = "failed";
      record("deploy_health", false, "health_red_after_merge", {
        redeploy_ok: redeploy?.ok ?? null,
        health: "failed",
      });
      verdict = "rolled_back";
      state.rollback = await performRollback({
        deps, previous, mergeSha: state.mergeSha, prNumber, records,
        now, sleep, healthTimeoutMs, healthIntervalMs,
      });
      break run;
    }
    state.health = "ok";

    const fresh = await pollUntil(async () => {
      const deployments = await deps.listDeployments();
      return (Array.isArray(deployments) ? deployments : []).find((deployment) =>
        deployment
        && deployment.id !== previous?.id
        && deployment.status === "SUCCESS"
        && deployment.meta?.commitHash === state.mergeSha) || null;
    }, { now, sleep, timeoutMs: freshTimeoutMs, intervalMs: freshIntervalMs });

    if (!fresh) {
      record("deploy_health", false, "deploy_freshness_unverified", {
        redeploy_ok: redeploy?.ok ?? null,
        health: "ok",
        merge_sha: state.mergeSha,
      });
      await deps.alert(
        `PR #${prNumber} merged as ${state.mergeSha} and /health is ok, but no Railway deployment`
        + " reported that exact commit. Production may still be serving the old build.",
      );
      break run;
    }
    state.deployId = fresh.id;
    record("deploy_health", true, null, {
      redeploy_ok: redeploy?.ok ?? null,
      health: "ok",
      deploy_id: fresh.id,
      deploy_commit: fresh.meta?.commitHash ?? null,
    });
    verdict = "merged_deployed";
  }

  const finished = now();
  const stages = signStageChain(runId, records);
  const gateRecords = stages.filter((entry) => GUARD_STAGES.includes(entry.stage));
  const row = {
    schema_version: 1,
    run_id: runId,
    pr: Number(prNumber),
    started_at: started.toISOString(),
    finished_at: finished.toISOString(),
    duration_ms: Math.max(0, finished.getTime() - started.getTime()),
    verdict,
    stopped_at_stage: state.stoppedAtStage,
    stop_reason: state.stopReason,
    stages_passed: gateRecords.filter((entry) => entry.ok).map((entry) => entry.stage),
    stages_failed: gateRecords.filter((entry) => !entry.ok).map((entry) => entry.stage),
    stages,
    merge_sha: state.mergeSha,
    deploy_id: state.deployId,
    health: state.health,
    rollback: state.rollback,
  };
  appendGuardRun(deps.ledgerPath || guardLedgerPath(), row);

  return {
    runId,
    verdict,
    stoppedAtStage: state.stoppedAtStage,
    stopReason: state.stopReason,
    mergeSha: state.mergeSha,
    deployId: state.deployId,
    health: state.health,
    rollback: state.rollback,
    stages,
    stagesPassed: row.stages_passed,
    stagesFailed: row.stages_failed,
    ledgerRow: row,
  };
}


async function performRollback({
  deps, previous, mergeSha, prNumber, records, now, sleep, healthTimeoutMs, healthIntervalMs,
}) {
  if (previous && previous.canRollback === true) {
    const result = await deps.rollback({ deploymentId: previous.id });
    const healthAfter = await pollUntil(() => deps.checkHealth(), {
      now, sleep, timeoutMs: healthTimeoutMs, intervalMs: healthIntervalMs,
    });
    const rollback = {
      attempted: true,
      method: "railway_api_deployment_rollback",
      target_deployment_id: previous.id,
      ok: result?.ok === true,
      revert_pr_url: null,
      health_after: healthAfter ? "ok" : "failed",
    };
    records.push({
      stage: "rollback",
      ok: rollback.ok,
      reason: rollback.ok ? null : "rollback_mutation_failed",
      evidence: rollback,
    });
    await deps.alert(
      `PR #${prNumber} merged as ${mergeSha} but production health stayed red. Rolled back to`
      + ` deployment ${previous.id} (ok=${rollback.ok}, health_after=${rollback.health_after}).`,
    );
    return rollback;
  }

  const revert = await deps.openRevertPr({ mergeSha, prNumber });
  const rollback = {
    attempted: true,
    // Railway offers no rollback for this deployment, so the only honest remedy is a revert PR.
    method: "revert_pr",
    target_deployment_id: previous?.id ?? null,
    ok: Boolean(revert?.url),
    revert_pr_url: revert?.url ?? null,
    health_after: "failed",
  };
  records.push({
    stage: "rollback",
    ok: rollback.ok,
    reason: rollback.ok ? null : "revert_pr_failed",
    evidence: rollback,
  });
  await deps.alert(
    `PR #${prNumber} merged as ${mergeSha}, production health is red, and Railway cannot roll the`
    + ` previous deployment back. Opened revert PR ${rollback.revert_pr_url || "(failed)"}.`
    + " Production stays on the bad commit until that revert lands.",
  );
  return rollback;
}


module.exports = {
  REPO,
  HEALTH_URL,
  GUARD_STAGES,
  BLOCKED_ACTIONS,
  BRANCH_PATTERNS,
  ROLLBACK_MUTATION,
  classifyChangedPath,
  evaluatePackageJsonChange,
  evaluateEligibility,
  parseAddedLines,
  detectBlockedActions,
  signStageChain,
  verifyStageChain,
  guardLedgerPath,
  appendGuardRun,
  createReviewCommandHook,
  createGuardDeps,
  runMergeGuard,
};
