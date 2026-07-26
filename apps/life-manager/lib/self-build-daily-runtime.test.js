"use strict";

// Runtime wiring for the daily self-build pass (spec §10 row 10f):
// the fresh-adversary review hook, the launchd entrypoint, and the enable script.
//
// The review hook tests include REAL child processes (a real timeout, a real non-JSON answer),
// because "fails closed" is a claim about process behaviour, not about a string.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const {
  REVIEW_PROMPT,
  parseReviewerAnswer,
  resolveReviewCli,
  runAdversaryReview,
} = require("../scripts/dev-adversary-review.js");
const {
  classifyChangedPath,
  createReviewCommandHook,
  resolveReviewCommandPaths,
} = require("./dev-merge-guard.js");
const { SELF_BUILD_PROTECTED_PATHS } = require("./self-build-daily.js");

const APP_DIR = path.join(__dirname, "..");
const REPO_DIR = path.resolve(APP_DIR, "../..");
const REVIEW_CLI = path.join(APP_DIR, "scripts/dev-adversary-review.js");
const DAILY_CLI = path.join(APP_DIR, "scripts/self-build-daily.js");
const ENABLE_SCRIPT = path.join(APP_DIR, "scripts/enable-self-build-launchd.sh");
const ENTRYPOINT = path.join(REPO_DIR, "skills/life-manager/self-build-daily.sh");


test("the review hook, the daily CLI and the enable script are executable", () => {
  for (const file of [REVIEW_CLI, DAILY_CLI, ENABLE_SCRIPT, ENTRYPOINT]) {
    assert.ok(fs.statSync(file).mode & 0o100, `${file} must be executable`);
  }
});


test("the reviewer is spawned FRESH via claude -p and reads the diff from stdin", () => {
  const source = fs.readFileSync(REVIEW_CLI, "utf8");
  assert.match(source, /LM_DEV_REVIEW_CLI/);
  assert.match(source, /"-p"/);
  assert.match(source, /process\.stdin/);
  // Model routing is the operator's shell's business (claudexmix/Sol or direct); the loop must not
  // hardcode a model, or it breaks the moment routing changes.
  assert.doesNotMatch(source, /claude-[a-z0-9.-]*-20\d{6}/);
});


// A launchd PATH is not a login shell's PATH. On this machine `claude` is ~/.local/bin/claude and
// `claudexmix` is a shell function with no binary at all, so a reviewer resolved from the parked
// plist's PATH would never spawn — safe (fail closed) but useless (nothing ever merges).
test("the reviewer CLI is found even when it is not on the launchd PATH", () => {
  const home = "/home/tester";
  const resolved = resolveReviewCli({
    HOME: home,
    PATH: "/opt/homebrew/bin:/usr/bin:/bin",
  });
  assert.ok(
    resolved === `${home}/.local/bin/claude` || resolved === "claude" || resolved.endsWith("/claude"),
    `unexpected reviewer resolution: ${resolved}`,
  );
});


test("an explicit $LM_DEV_REVIEW_CLI always wins, so routing stays the operator's decision", () => {
  assert.equal(
    resolveReviewCli({ LM_DEV_REVIEW_CLI: "/opt/sol/bin/reviewer", PATH: "/bin" }),
    "/opt/sol/bin/reviewer",
  );
});


test("on THIS machine the reviewer resolves to a real executable", () => {
  const resolved = resolveReviewCli({ HOME: process.env.HOME, PATH: process.env.PATH });
  assert.notEqual(resolved, "claude", "bare 'claude' means nothing executable was found");
  assert.ok(fs.statSync(resolved).mode & 0o100, `${resolved} must be executable`);
});


test("the enable script puts ~/.local/bin on the job's PATH", () => {
  const source = fs.readFileSync(ENABLE_SCRIPT, "utf8");
  assert.match(source, /\$HOME\/\.local\/bin:/);
});


test("a PASS verdict is normalised to the guard's lowercase contract", () => {
  assert.deepEqual(
    parseReviewerAnswer('{"verdict":"PASS","findings":[]}'),
    { verdict: "pass", findings: [] },
  );
  assert.equal(parseReviewerAnswer('{"verdict":"pass","findings":[]}').verdict, "pass");
});


test("a FAIL verdict keeps its findings", () => {
  const answer = parseReviewerAnswer('{"verdict":"FAIL","findings":["adds an outreach call"]}');
  assert.equal(answer.verdict, "fail");
  assert.deepEqual(answer.findings, ["adds an outreach call"]);
});


test("the reviewer's JSON is read out of surrounding prose rather than refused for it", () => {
  const answer = parseReviewerAnswer(
    'Here is my review.\n{"verdict":"FAIL","findings":["touches billing"]}\nDone.',
  );
  assert.equal(answer.verdict, "fail");
  assert.deepEqual(answer.findings, ["touches billing"]);
});


test("non-JSON, empty and missing-verdict answers all FAIL closed", () => {
  for (const text of ["", "looks fine to me", "{}", "null", '{"findings":[]}', "{verdict: pass}"]) {
    const answer = parseReviewerAnswer(text);
    assert.equal(answer.verdict, "fail", `"${text}" must fail closed`);
    assert.ok(answer.findings.length > 0, "a failure must always carry a reason");
  }
});


test("anything other than an explicit PASS fails closed, including near-misses", () => {
  for (const text of ['{"verdict":"passed"}', '{"verdict":"ok"}', '{"verdict":true}', '{"verdict":"PASS?"}']) {
    assert.equal(parseReviewerAnswer(text).verdict, "fail");
  }
});


test("a reviewer that runs past its bounded timeout FAILS — with a real child process", () => {
  const answer = runAdversaryReview({
    diff: "diff --git a/x b/x\n+console.log(1)\n",
    cli: "/bin/sh",
    args: ["-c", "sleep 30"],
    timeoutMs: 300,
  });
  assert.equal(answer.verdict, "fail");
  assert.match(answer.findings.join(" "), /review command|timed out|ETIMEDOUT|SIGTERM/i);
});


test("a reviewer that prints prose instead of JSON FAILS — with a real child process", () => {
  const answer = runAdversaryReview({
    diff: "diff --git a/x b/x\n",
    cli: "/bin/sh",
    args: ["-c", "printf 'looks good to me'"],
    timeoutMs: 5_000,
  });
  assert.equal(answer.verdict, "fail");
});


test("a reviewer that exits non-zero FAILS even if it printed a pass", () => {
  const answer = runAdversaryReview({
    diff: "diff --git a/x b/x\n",
    cli: "/bin/sh",
    args: ["-c", "printf '{\"verdict\":\"PASS\",\"findings\":[]}'; exit 7"],
    timeoutMs: 5_000,
  });
  assert.equal(answer.verdict, "fail");
});


test("a real PASS from a real child process is honoured end to end", () => {
  const answer = runAdversaryReview({
    diff: "diff --git a/x b/x\n",
    cli: "/bin/sh",
    args: ["-c", "cat >/dev/null; printf '{\"verdict\":\"PASS\",\"findings\":[]}'"],
    timeoutMs: 5_000,
  });
  assert.deepEqual(answer, { verdict: "pass", findings: [] });
});


test("the diff really reaches the reviewer on stdin", () => {
  const answer = runAdversaryReview({
    diff: "MARKER-8f3a",
    cli: "/bin/sh",
    args: ["-c", 'grep -q MARKER-8f3a && printf \'{"verdict":"PASS","findings":[]}\''],
    timeoutMs: 5_000,
  });
  assert.equal(answer.verdict, "pass");
});


// ---------------------------------------------------------------------------------------------
// The review script lives under scripts/, which the guard's path allowlist ALLOWS. It is not a
// `dev-merge-guard*` file, so GUARD_SELF_PATHS does not name it. It is protected anyway, at
// runtime, because it is what `--review-cmd` resolves to — a PR that edits its own judge dies at
// eligibility.
// ---------------------------------------------------------------------------------------------
test("the review script does NOT collide with the guard's static self-deny", () => {
  const rel = "apps/life-manager/scripts/dev-adversary-review.js";
  assert.deepEqual(classifyChangedPath(rel), { allowed: true, rule: "allow:scripts" });
});


test("but the guard auto-protects it via resolveReviewCommandPaths once it is the --review-cmd", () => {
  const command = `node ${REVIEW_CLI}`;
  const protectedPaths = resolveReviewCommandPaths(command);
  assert.ok(
    protectedPaths.includes("apps/life-manager/scripts/dev-adversary-review.js"),
    "the resolved review command must be handed to eligibility as a protected path",
  );
  assert.deepEqual(
    classifyChangedPath("apps/life-manager/scripts/dev-adversary-review.js", { protectedPaths }),
    { allowed: false, rule: "deny:guard-self" },
    "a PR that edits its own reviewer must be refused at stage one",
  );
});


test("the self-build orchestrator's own sources are protected the same way", () => {
  for (const file of SELF_BUILD_PROTECTED_PATHS) {
    assert.deepEqual(
      classifyChangedPath(file, { protectedPaths: [...SELF_BUILD_PROTECTED_PATHS] }),
      { allowed: false, rule: "deny:guard-self" },
    );
  }
  assert.ok(SELF_BUILD_PROTECTED_PATHS.includes("apps/life-manager/lib/self-build-daily.js"));
  assert.ok(SELF_BUILD_PROTECTED_PATHS.includes("apps/life-manager/scripts/self-build-daily.js"));
  assert.ok(SELF_BUILD_PROTECTED_PATHS.includes("apps/life-manager/scripts/dev-adversary-review.js"));
});


test("the review hook satisfies the guard's own review-command contract", () => {
  const hook = createReviewCommandHook(
    `printf '{"verdict":"pass","findings":[]}'`,
    { exec: require("node:child_process").execFileSync },
  );
  return hook("diff").then((answer) => {
    assert.equal(answer.verdict, "pass");
  });
});


test("the review prompt demands the exact JSON contract and a fresh adversarial read", () => {
  assert.match(REVIEW_PROMPT, /verdict/);
  assert.match(REVIEW_PROMPT, /PASS/);
  assert.match(REVIEW_PROMPT, /FAIL/);
  assert.match(REVIEW_PROMPT, /findings/);
  assert.match(REVIEW_PROMPT, /stdin|diff/i);
});


// ---------------------------------------------------------------------------------------------
// launchd. This atomic SHIPS the enabling script and does NOT run it.
// ---------------------------------------------------------------------------------------------
test("the launchd entrypoint sources env, logs, and reports the day to Dais's Telegram", () => {
  const source = fs.readFileSync(ENTRYPOINT, "utf8");
  assert.match(source, /openclaw message send/);
  assert.match(source, /8547730585/);
  assert.match(source, /\.openclaw\/\.env/);
  assert.match(source, /self-build-daily\.js/);
  assert.match(source, /LOG=/);
});


test("the entrypoint never loads a schedule itself — enabling is a separate, explicit operator step", () => {
  const entrypoint = fs.readFileSync(ENTRYPOINT, "utf8");
  const library = fs.readFileSync(path.join(APP_DIR, "lib/self-build-daily.js"), "utf8");
  const cli = fs.readFileSync(DAILY_CLI, "utf8");
  for (const text of [entrypoint, library, cli]) {
    assert.doesNotMatch(text, /launchctl/);
    assert.doesNotMatch(text, /crontab/);
  }
});


test("the enable script targets the parked plist at 04:10 JST and is the only place launchctl appears", () => {
  const source = fs.readFileSync(ENABLE_SCRIPT, "utf8");
  assert.match(source, /ai\.anicca\.life-manager-dev\.plist\.disabled/);
  assert.match(source, /launchctl/);
  assert.match(source, /bootstrap|load/);
  assert.match(source, /<integer>4<\/integer>/);
  assert.match(source, /<integer>10<\/integer>/);
  assert.match(source, /Asia\/Tokyo|JST/);
  assert.match(source, /self-build-daily\.sh/);
});


test("nothing in this atomic has actually loaded the job: the parked plist keeps its .disabled suffix", () => {
  const home = process.env.HOME || "";
  const active = path.join(home, "Library/LaunchAgents/ai.anicca.life-manager-dev.plist");
  assert.equal(
    fs.existsSync(active),
    false,
    "10f builds the enabling script; the operator runs it after merge",
  );
});


test("the new suites are reachable from npm test", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(APP_DIR, "package.json"), "utf8"));
  assert.match(manifest.scripts.test, /self-build-daily\.test\.js/);
  assert.match(manifest.scripts.test, /self-build-daily-runtime\.test\.js/);
});
