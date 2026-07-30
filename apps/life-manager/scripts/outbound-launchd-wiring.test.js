// scripts/outbound-launchd-wiring.test.js — the schedule and the guardian contract are pinned.
//
// "The cron exists" is not evidence that anything runs. These assertions pin the two facts that
// actually decide whether the loop is alive: the plists point at real boot scripts, and the
// heartbeat path the engine writes is the exact path skills/self/healthcheck-runtime-loop.sh
// is pointed at. A rename on either side breaks a test instead of silently dying for 12 days.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const APP_DIR = path.join(__dirname, "..");
const LAUNCHD_DIR = path.join(APP_DIR, "launchd");

const AGENTS = Object.freeze([
  { label: "ai.anicca.life-manager-outbound", script: "outbound-boot.sh", hour: 7, minute: 30 },
  { label: "ai.anicca.life-manager-outbound-verify", script: "outbound-verify-boot.sh", hour: 9, minute: 0 },
]);

for (const agent of AGENTS) {
  const templatePath = path.join(LAUNCHD_DIR, `${agent.label}.plist.template`);

  test(`${agent.label}: the template is valid plist once its placeholders are filled`, () => {
    const filled = fs.readFileSync(templatePath, "utf8")
      .replace(/__HOME__/g, "/Users/test")
      .replace(/__APP_DIR__/g, APP_DIR);
    const temp = path.join(
      fs.mkdtempSync(path.join(require("node:os").tmpdir(), "outbound-plist-")),
      "agent.plist",
    );
    fs.writeFileSync(temp, filled, "utf8");
    const out = execFileSync("/usr/bin/plutil", ["-lint", temp], { encoding: "utf8" });
    assert.match(out, /OK/);
  });

  test(`${agent.label}: runs at ${agent.hour}:${String(agent.minute).padStart(2, "0")} local (JST on this host)`, () => {
    const raw = fs.readFileSync(templatePath, "utf8");
    assert.match(raw, /<key>StartCalendarInterval<\/key>/);
    assert.match(raw, new RegExp(`<key>Hour</key>\\s*<integer>${agent.hour}</integer>`));
    assert.match(raw, new RegExp(`<key>Minute</key>\\s*<integer>${agent.minute}</integer>`));
    assert.match(raw, /<key>RunAtLoad<\/key>\s*<false\/>/);
  });

  test(`${agent.label}: points at a boot script that exists and is executable`, () => {
    const raw = fs.readFileSync(templatePath, "utf8");
    assert.ok(raw.includes(`__APP_DIR__/scripts/${agent.script}`), `template does not call ${agent.script}`);
    const script = path.join(APP_DIR, "scripts", agent.script);
    assert.equal(fs.existsSync(script), true);
    assert.equal((fs.statSync(script).mode & 0o111) !== 0, true, `${agent.script} is not executable`);
  });
}

test("the installer installs both agents", () => {
  const installer = fs.readFileSync(path.join(APP_DIR, "scripts", "install-outbound-launchd.sh"), "utf8");
  for (const agent of AGENTS) assert.ok(installer.includes(agent.label), `installer omits ${agent.label}`);
  assert.match(installer, /plutil -lint/);
  assert.match(installer, /launchctl bootstrap/);
});

test("the boot scripts stay thin wrappers, like financial-report-boot.sh", () => {
  for (const agent of AGENTS) {
    const body = fs.readFileSync(path.join(APP_DIR, "scripts", agent.script), "utf8");
    const code = body.split("\n").filter((line) => line.trim() && !line.trim().startsWith("#"));
    assert.ok(code.length <= 8, `${agent.script} has ${code.length} code lines; keep it a wrapper`);
    assert.match(body, /set -euo pipefail/);
    assert.match(body, /exec /);
  }
});

test("the heartbeat path the engine writes is the one the guardian watches", async () => {
  const { heartbeatPath } = await import(require("node:url").pathToFileURL(
    path.join(APP_DIR, "..", "..", "runtime", "loop", "outbound", "streak.mjs"),
  ).href);
  assert.equal(heartbeatPath("/Users/test"), "/Users/test/.local/state/life-manager/.outbound-last-pass");
  const guardian = path.join(APP_DIR, "..", "..", "skills", "self", "healthcheck-runtime-loop.sh");
  assert.equal(fs.existsSync(guardian), true, "the guardian script moved; rewire before trusting the heartbeat");
});

test("no outbound scratch state is committed into the repo", () => {
  const repoRoot = path.join(APP_DIR, "..", "..");
  const tracked = execFileSync("git", ["ls-files", "--", "*outbound*"], { cwd: repoRoot, encoding: "utf8" })
    .split("\n").filter(Boolean);
  for (const file of tracked) {
    assert.equal(/\.jsonl$/.test(file), false, `${file} looks like committed state`);
    assert.equal(/streak\.json$/.test(file), false, `${file} looks like committed state`);
  }
});
