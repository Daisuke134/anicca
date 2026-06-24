// scaffold.test.js — VCSDD RED phase: asserts the 3 thin wrapper scripts exist and delegate
// correctly to scheduler.js pass functions. Run:
//   node --test apps/life-call/skill-life-manager/scripts/scaffold.test.js
"use strict";

const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { execSync } = require("node:child_process");

const SCRIPTS = path.resolve(__dirname);
const SKILL_DIR = path.resolve(__dirname, "..");

// ── 1. Syntax validity — each script must parse as valid JS ─────────────────────────────────────

test("tick.js passes node --check", () => {
  execSync(`node --check "${path.join(SCRIPTS, "tick.js")}"`);
});

test("travel.js passes node --check", () => {
  execSync(`node --check "${path.join(SCRIPTS, "travel.js")}"`);
});

test("ask.js passes node --check", () => {
  execSync(`node --check "${path.join(SCRIPTS, "ask.js")}"`);
});

// ── 2. Module shape — run must be an exported async function ────────────────────────────────────

test("tick.js exports run as a function", () => {
  const m = require("./tick.js");
  assert.strictEqual(typeof m.run, "function", "tick.run must be a function");
});

test("travel.js exports run as a function", () => {
  const m = require("./travel.js");
  assert.strictEqual(typeof m.run, "function", "travel.run must be a function");
});

test("ask.js exports run as a function", () => {
  const m = require("./ask.js");
  assert.strictEqual(typeof m.run, "function", "ask.run must be a function");
});

// ── 3. Delegation — each run(stub) invokes exactly the right scheduler function once ───────────

test("tick.run(stub) calls stub.tick exactly once", async () => {
  let calls = 0;
  const stub = { tick: async () => { calls++; } };
  const { run } = require("./tick.js");
  await run(stub);
  assert.strictEqual(calls, 1, "stub.tick must be called exactly once");
});

test("travel.run(stub) calls stub.travelTick exactly once", async () => {
  let calls = 0;
  const stub = { travelTick: async () => { calls++; } };
  const { run } = require("./travel.js");
  await run(stub);
  assert.strictEqual(calls, 1, "stub.travelTick must be called exactly once");
});

test("ask.run(stub) calls stub.askTickAll exactly once", async () => {
  let calls = 0;
  const stub = { askTickAll: async () => { calls++; } };
  const { run } = require("./ask.js");
  await run(stub);
  assert.strictEqual(calls, 1, "stub.askTickAll must be called exactly once");
});

// ── 4. SKILL.md presence and content ────────────────────────────────────────────────────────────

test("SKILL.md exists", () => {
  const skillMd = path.join(SKILL_DIR, "SKILL.md");
  assert.ok(fs.existsSync(skillMd), "SKILL.md must exist in skill-life-manager/");
});

test("SKILL.md mentions tick entrypoint", () => {
  const skillMd = path.join(SKILL_DIR, "SKILL.md");
  const content = fs.readFileSync(skillMd, "utf8");
  assert.ok(content.includes("tick"), "SKILL.md must reference the tick entrypoint");
});

test("SKILL.md mentions travel entrypoint", () => {
  const skillMd = path.join(SKILL_DIR, "SKILL.md");
  const content = fs.readFileSync(skillMd, "utf8");
  assert.ok(content.includes("travel"), "SKILL.md must reference the travel entrypoint");
});

test("SKILL.md mentions ask entrypoint", () => {
  const skillMd = path.join(SKILL_DIR, "SKILL.md");
  const content = fs.readFileSync(skillMd, "utf8");
  assert.ok(content.includes("ask"), "SKILL.md must reference the ask entrypoint");
});

// ── 5. FIND-001: Explicit no-cross-wiring — each script calls ONLY its own fn, never others ────
// Injects a full 3-function stub exposing tick, travelTick, and askTickAll.
// Each counter must be 1 for the owner and 0 for the others.
// If travel.js accidentally called tick(), travelTick_calls==1 AND tick_calls==1 → test fails.

test("tick.run: calls tick once AND does NOT call travelTick or askTickAll (no-cross-wiring)", async () => {
  const counts = { tick: 0, travelTick: 0, askTickAll: 0 };
  const fullStub = {
    tick:        async () => { counts.tick++; },
    travelTick:  async () => { counts.travelTick++; },
    askTickAll:  async () => { counts.askTickAll++; },
  };
  const { run } = require("./tick.js");
  await run(fullStub);
  assert.strictEqual(counts.tick,       1, "tick must be called exactly once");
  assert.strictEqual(counts.travelTick, 0, "tick.js must NOT call travelTick");
  assert.strictEqual(counts.askTickAll, 0, "tick.js must NOT call askTickAll");
});

test("travel.run: calls travelTick once AND does NOT call tick or askTickAll (no-cross-wiring)", async () => {
  const counts = { tick: 0, travelTick: 0, askTickAll: 0 };
  const fullStub = {
    tick:        async () => { counts.tick++; },
    travelTick:  async () => { counts.travelTick++; },
    askTickAll:  async () => { counts.askTickAll++; },
  };
  const { run } = require("./travel.js");
  await run(fullStub);
  assert.strictEqual(counts.travelTick, 1, "travelTick must be called exactly once");
  assert.strictEqual(counts.tick,       0, "travel.js must NOT call tick");
  assert.strictEqual(counts.askTickAll, 0, "travel.js must NOT call askTickAll");
});

test("ask.run: calls askTickAll once AND does NOT call tick or travelTick (no-cross-wiring)", async () => {
  const counts = { tick: 0, travelTick: 0, askTickAll: 0 };
  const fullStub = {
    tick:        async () => { counts.tick++; },
    travelTick:  async () => { counts.travelTick++; },
    askTickAll:  async () => { counts.askTickAll++; },
  };
  const { run } = require("./ask.js");
  await run(fullStub);
  assert.strictEqual(counts.askTickAll, 1, "askTickAll must be called exactly once");
  assert.strictEqual(counts.tick,       0, "ask.js must NOT call tick");
  assert.strictEqual(counts.travelTick, 0, "ask.js must NOT call travelTick");
});

// ── 6. FIND-002: No-auto-run guard — require() must not invoke any pass ──────────────────────────
// Strategy: write a temp helper script to disk and run it in a fresh child process (cold require,
// empty module cache). The helper patches Module._load so scheduler.js returns a stub that throws
// "AUTO_RUN_DETECTED" if any of its pass-functions are called. Then it requires the wrapper script.
// If the wrapper auto-calls run() at import time, the stub throws and the child exits non-zero.
// The parent asserts exit code == 0 AND stdout contains "NO_AUTO_RUN".
//
// Limitation honestly documented: same-process require() returns a cached module (no re-execution),
// so cold-require proof is done via a child process. The same-process check below still proves the
// export contract (typeof run === "function") and that no extra properties were exported.

const os = require("node:os");
const tmpDir = os.tmpdir();

function coldRequireCheck(scriptPath, passName) {
  const helperPath = path.join(tmpDir, `scaffold-no-auto-run-${passName}-${Date.now()}.cjs`);
  const helperContent = [
    '"use strict";',
    "const Module = require('module');",
    "Module._load = (function(origLoad) {",
    "  return function(req, parent, isMain) {",
    "    if (req.includes('scheduler')) {",
    "      return {",
    "        tick:        function() { throw new Error('AUTO_RUN_DETECTED: tick called on import'); },",
    "        travelTick:  function() { throw new Error('AUTO_RUN_DETECTED: travelTick called on import'); },",
    "        askTickAll:  function() { throw new Error('AUTO_RUN_DETECTED: askTickAll called on import'); }",
    "      };",
    "    }",
    "    return origLoad.apply(this, arguments);",
    "  };",
    "})(Module._load);",
    "var m = require(" + JSON.stringify(scriptPath) + ");",
    "if (typeof m.run !== 'function') { process.stderr.write('EXPORT_SHAPE_FAIL'); process.exit(2); }",
    "process.stdout.write('NO_AUTO_RUN');",
  ].join("\n");

  const fs2 = require("node:fs");
  fs2.writeFileSync(helperPath, helperContent, "utf8");
  try {
    const result = execSync(`node ${JSON.stringify(helperPath)}`, { encoding: "utf8" });
    return result;
  } finally {
    try { fs2.unlinkSync(helperPath); } catch (_) {}
  }
}

test("tick.js: fresh require() returns {run: function} with no side-effects (no-auto-run)", () => {
  // Same-process check: export shape
  const m = require("./tick.js");
  assert.strictEqual(typeof m.run, "function", "tick must export run");
  assert.strictEqual(Object.keys(m).length, 1, "tick must export ONLY run, nothing extra");

  // Cold-require check via child process
  const tickPath = require.resolve("./tick.js");
  const result = coldRequireCheck(tickPath, "tick");
  assert.ok(result.includes("NO_AUTO_RUN"),
    "tick.js must not call run() on require (require.main guard must hold) — got: " + result);
});

test("travel.js: fresh require() returns {run: function} with no side-effects (no-auto-run)", () => {
  const m = require("./travel.js");
  assert.strictEqual(typeof m.run, "function", "travel must export run");
  assert.strictEqual(Object.keys(m).length, 1, "travel must export ONLY run, nothing extra");

  const travelPath = require.resolve("./travel.js");
  const result = coldRequireCheck(travelPath, "travel");
  assert.ok(result.includes("NO_AUTO_RUN"),
    "travel.js must not call run() on require (require.main guard must hold) — got: " + result);
});

test("ask.js: fresh require() returns {run: function} with no side-effects (no-auto-run)", () => {
  const m = require("./ask.js");
  assert.strictEqual(typeof m.run, "function", "ask must export run");
  assert.strictEqual(Object.keys(m).length, 1, "ask must export ONLY run, nothing extra");

  const askPath = require.resolve("./ask.js");
  const result = coldRequireCheck(askPath, "ask");
  assert.ok(result.includes("NO_AUTO_RUN"),
    "ask.js must not call run() on require (require.main guard must hold) — got: " + result);
});
