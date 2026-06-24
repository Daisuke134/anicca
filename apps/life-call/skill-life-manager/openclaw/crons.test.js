// crons.test.js — B2: verify the Life Manager cron-COMMAND registration artifacts are well-formed,
// AND that the command GENERATOR (build-commands.js) actually emits valid round-tripped openclaw
// commands (the double-JSON.stringify is executed + asserted, not just substring-matched).
//
// Live registration + firing = B4 on the product gateway (openclaw>=2026.6.10 has command-cron; the
// local runtime 2026.6.1 lacks it). SINGLE-WRITER migration: only WAKE is race-safe (atomic lm_wake_log
// unique(uid,event_key)); TRAVEL+ASK dedup is in-memory read-then-write (no atomic constraint) so the
// Railway scheduler and these cron jobs must NOT run at the same time — B4 cutover is a switch, not
// coexistence. (Follow-up C-H1: atomic unique constraints on [Travel]+lm_ask_log.)
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { buildRegisterCommands } = require("./build-commands.js");

const HERE = __dirname;
const crons = JSON.parse(fs.readFileSync(path.join(HERE, "crons.json"), "utf8"));
const sh = fs.readFileSync(path.join(HERE, "register-crons.sh"), "utf8");

const EXPECTED = [
  { name: "lm-wake", cron: "*/1 * * * *", script: "tick.js" },
  { name: "lm-travel", cron: "*/30 * * * *", script: "travel.js" },
  { name: "lm-ask", cron: "*/20 * * * *", script: "ask.js" },
];

test("crons.json defines exactly the 3 expected jobs", () => {
  assert.ok(Array.isArray(crons.jobs));
  assert.strictEqual(crons.jobs.length, 3);
  assert.deepStrictEqual(crons.jobs.map((j) => j.name).sort(), ["lm-ask", "lm-travel", "lm-wake"]);
});

for (const exp of EXPECTED) {
  test(`job ${exp.name}: schedule + command-argv + script exists`, () => {
    const job = crons.jobs.find((j) => j.name === exp.name);
    assert.ok(job, `${exp.name} present`);
    assert.strictEqual(job.cron, exp.cron);
    assert.strictEqual(job.commandArgv[0], "node");
    assert.strictEqual(job.commandArgv[1], `skill-life-manager/scripts/${exp.script}`);
    assert.ok(fs.existsSync(path.join(HERE, "..", "scripts", exp.script)), "scaffold script exists");
  });
}

// ── FIND-003: EXECUTE the generator and assert the literal round-tripped output ──────────────────
test("buildRegisterCommands: emits a literal JSON-array --command-argv that bash round-trips", () => {
  const cmds = buildRegisterCommands(crons.jobs, "/srv/app/apps/life-call");
  assert.strictEqual(cmds.length, 3);
  const wake = cmds.find((c) => c.name === "lm-wake");
  // The exact token bash must hand to openclaw: a double-quoted string whose content is the JSON array.
  assert.ok(
    wake.create.includes('--command-argv "[\\"node\\",\\"skill-life-manager/scripts/tick.js\\"]"'),
    "argv round-trips to a literal JSON array token, got: " + wake.create
  );
  assert.ok(wake.create.includes('openclaw cron create "*/1 * * * *"'), "schedule quoted");
  assert.ok(wake.create.includes('--name "lm-wake"'), "name quoted");
  assert.ok(wake.create.includes('--command-cwd "/srv/app/apps/life-call"'), "cwd passed through");
});

test("buildRegisterCommands: idempotent rm precedes create, and NO model-job flags (zero tokens)", () => {
  const cmds = buildRegisterCommands(crons.jobs, "/tmp/x");
  for (const c of cmds) {
    assert.match(c.rm, /^openclaw cron rm .* \|\| true$/, "rm-before-create, failure tolerated");
    assert.ok(!/--message|--model|--agent|--system-event/.test(c.create), "no model-backed flags");
  }
});

test("buildRegisterCommands: cwd from json drives all 3, no crossed scripts", () => {
  const cmds = buildRegisterCommands(crons.jobs, "/d");
  const byName = Object.fromEntries(cmds.map((c) => [c.name, c.create]));
  assert.ok(byName["lm-travel"].includes("travel.js") && !byName["lm-travel"].includes("tick.js"));
  assert.ok(byName["lm-ask"].includes("ask.js") && !byName["lm-ask"].includes("travel.js"));
});

// ── register-crons.sh shape ──────────────────────────────────────────────────────────────────────
test("register-crons.sh drives from build-commands.js under errexit, cwd from env, no hardcoded host", () => {
  assert.match(sh, /build-commands\.js/, "uses the tested generator (no duplicated inline generator)");
  assert.match(sh, /bash -eo pipefail|bash -e\b/, "pipes into bash with errexit (FIND-002)");
  assert.match(sh, /LIFE_CALL_DIR/, "cwd from env");
  assert.match(sh, /set -euo pipefail/, "script-level errexit");
  assert.ok(!/--command-cwd ["']?\/(Users|home|srv)\b/.test(sh), "no hardcoded absolute host path");
});
