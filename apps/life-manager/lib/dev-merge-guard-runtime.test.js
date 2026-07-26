"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const CLI = path.join(root, "scripts/dev-merge-guard.js");


test("the merge guard CLI exists and is executable", () => {
  const stats = fs.statSync(CLI);
  assert.ok(stats.mode & 0o100, "scripts/dev-merge-guard.js must be executable");
});


test("the CLI wires the real gh/exec/fetch deps into the library pipeline", () => {
  const source = fs.readFileSync(CLI, "utf8");
  assert.match(source, /require\("\.\.\/lib\/dev-merge-guard\.js"\)/);
  assert.match(source, /createGuardDeps/);
  assert.match(source, /runMergeGuard/);
  assert.match(source, /execFileSync/);
  assert.match(source, /--review-cmd/);
  assert.match(source, /createReviewCommandHook/);
});


test("the CLI refuses to run without an explicit fresh-reviewer hook", () => {
  const source = fs.readFileSync(CLI, "utf8");
  assert.match(source, /dev_merge_guard_review_required/);
});


test("this atomic does not enable any cron or launchd schedule", () => {
  const source = fs.readFileSync(CLI, "utf8");
  const library = fs.readFileSync(path.join(root, "lib/dev-merge-guard.js"), "utf8");
  for (const text of [source, library]) {
    assert.doesNotMatch(text, /launchctl/);
    assert.doesNotMatch(text, /crontab/);
  }
  assert.equal(
    fs.existsSync(path.join(root, "launchd/ai.anicca.life-manager-dev.plist")),
    false,
    "10f owns re-enabling the schedule",
  );
});


test("the guard's own package.json entry keeps the suite reachable", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
  assert.match(manifest.scripts.test, /dev-merge-guard\.test\.js/);
  assert.match(manifest.scripts.test, /dev-merge-guard-runtime\.test\.js/);
});
