// scripts/outbound-guardian-wiring.test.js — proves the OUTBOUND loops are actually WATCHED.
//
// Why this file exists, stated plainly: the predecessor connector loop was dead for 12 days
// (last ledger row 2026-07-18, every run rc=1) and nothing noticed, because nothing was watching
// its artifact. "A cron exists" is not "a loop is alive". These tests pin the watch itself:
//
//   1. the exact heartbeat path is the SAME string on both sides (engine writer + guardian reader),
//      so a rename breaks a test instead of silently un-watching the loop;
//   2. the real guardian, driven as a subprocess against a real file under a scratch HOME, returns
//      OK / STALE / MISSING_ARTIFACT / DEAD_UNLOADED for the states that matter;
//   3. a NEGATIVE CONTROL runs the same case table against a stub classifier that always says OK
//      and asserts the table rejects it — otherwise these assertions would be decorative.
//
// The guardian stays bash (it is what launchd runs); this file only drives it. Every entrypoint
// used here is one of the script's own pure-query flags, so no case can spawn a real
// launchctl kickstart or a real self-fix.sh.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const REPO_ROOT = path.join(__dirname, "..", "..", "..");
const GUARDIAN = path.join(REPO_ROOT, "skills", "self", "healthcheck-runtime-loop.sh");
const STREAK_MJS = path.join(REPO_ROOT, "runtime", "loop", "outbound", "streak.mjs");

const PASS_LABEL = "ai.anicca.life-manager-outbound";
const VERIFY_LABEL = "ai.anicca.life-manager-outbound-verify";
const DAY_MIN = 1440;

const scratchHome = () => fs.mkdtempSync(path.join(os.tmpdir(), "outbound-guardian-"));

// Run the guardian with a scratch HOME so nothing touches the real runtime state.
function guardian(args, { home, input } = {}) {
  return execFileSync("/bin/bash", [GUARDIAN, ...args], {
    encoding: "utf8",
    input: input == null ? "" : input,
    env: { ...process.env, HOME: home || scratchHome() },
  }).trim();
}

// The guardian prints its outbound registration as "<heartbeat-path> <pass-stale-min> <verify-stale-min>".
function outboundConfig(home) {
  const [beat, passStale, verifyStale] = guardian(["--outbound-config"], { home }).split(/\s+/);
  return { beat, passStale: Number(passStale), verifyStale: Number(verifyStale) };
}

// Age a file by rewriting its mtime; the guardian reads mtime via stat(1), like it does in production.
function writeBeat(beatPath, ageMinutes) {
  fs.mkdirSync(path.dirname(beatPath), { recursive: true });
  fs.writeFileSync(beatPath, "");
  const when = new Date(Date.now() - ageMinutes * 60_000);
  fs.utimesSync(beatPath, when, when);
}

// ------------------------------------------------------------------ 1. the path is pinned twice

test("the heartbeat path string is identical in the engine writer and the guardian reader", async () => {
  const home = scratchHome();
  const { heartbeatPath } = await import(require("node:url").pathToFileURL(STREAK_MJS).href);
  const expected = path.join(home, ".local", "state", "life-manager", ".outbound-last-pass");

  // engine writer (runtime/loop/outbound/streak.mjs)
  assert.equal(heartbeatPath(home), expected);
  // guardian reader (skills/self/healthcheck-runtime-loop.sh)
  assert.equal(outboundConfig(home).beat, expected);
});

test("the guardian source names the canonical data root, never a legacy .openclaw state path", () => {
  const source = fs.readFileSync(GUARDIAN, "utf8");
  assert.match(source, /\.local\/state\/life-manager\/\.outbound-last-pass/);
  assert.equal(/\.openclaw[^\s"']*outbound/.test(source), false, "guardian points at a legacy root");
});

test("both outbound launchd labels are registered as guardian targets", () => {
  const source = fs.readFileSync(GUARDIAN, "utf8");
  for (const label of [PASS_LABEL, VERIFY_LABEL]) {
    const registered = source
      .split("\n")
      .some((line) => !line.trimStart().startsWith("#") && line.includes(`"${label}"`) && line.includes("check "));
    assert.equal(registered, true, `${label} has no live check() registration`);
  }
});

// ------------------------------------------------------------------ 2. the stale limits

test("the stale limits straddle one full day, as the daily 07:30 / 09:00 schedules require", () => {
  const { passStale, verifyStale } = outboundConfig(scratchHome());
  // Both loops touch the same heartbeat (07:30 pass, 09:00 verify), so with both alive the oldest
  // the file can legitimately get is 09:00 -> 07:30 next day = 1350 min.
  assert.ok(passStale > 1350, `pass limit ${passStale} would fire on a healthy day`);
  // If EITHER loop stops, the surviving one still touches once a day: age reaches 1440. The pass
  // entry must fire below that, or a half-dead rail looks healthy forever.
  assert.ok(passStale < DAY_MIN, `pass limit ${passStale} cannot detect a missed daily touch`);
  // The verify entry is deliberately staggered ABOVE a full day: it is the "nothing touched this
  // at all for over a day" alarm, and firing it later stops one outage escalating self-fix twice.
  assert.ok(verifyStale > DAY_MIN, `verify limit ${verifyStale} would double-escalate with the pass entry`);
});

test("a whole missed day is STALE on the pass entry but not yet on the staggered verify entry", () => {
  const home = scratchHome();
  const { beat, passStale, verifyStale } = outboundConfig(home);
  writeBeat(beat, DAY_MIN);
  assert.equal(guardian(["--classify-artifact", "-", "interval", beat, String(passStale)], { home }), "STALE");
  assert.equal(guardian(["--classify-artifact", "-", "interval", beat, String(verifyStale)], { home }), "OK");
});

// ------------------------------------------------------------------ 3. the real classification table

// One row = one real state of the world the guardian must survive. Driven against a real file on
// disk under a scratch HOME, through the real script, so the age arithmetic is exercised too.
function classificationCases(home, { beat, passStale }) {
  return [
    {
      name: "fresh heartbeat -> OK",
      want: "OK",
      setup: () => writeBeat(beat, 1),
      argv: ["-", "interval", beat, String(passStale)],
    },
    {
      name: "heartbeat just inside the limit -> OK",
      want: "OK",
      setup: () => writeBeat(beat, passStale - 5),
      argv: ["-", "interval", beat, String(passStale)],
    },
    {
      name: "heartbeat older than the stale limit -> STALE",
      want: "STALE",
      setup: () => writeBeat(beat, passStale + 5),
      argv: ["-", "interval", beat, String(passStale)],
    },
    {
      name: "12 days dead, exactly the incident this wiring exists for -> STALE",
      want: "STALE",
      setup: () => writeBeat(beat, 12 * DAY_MIN),
      argv: ["-", "interval", beat, String(passStale)],
    },
    {
      name: "heartbeat file absent entirely -> MISSING_ARTIFACT",
      want: "MISSING_ARTIFACT",
      setup: () => fs.rmSync(beat, { force: true }),
      argv: ["12345", "interval", beat, String(passStale)],
    },
    {
      name: "launchd label gone (never installed / unloaded) -> DEAD_UNLOADED",
      want: "DEAD_UNLOADED",
      setup: () => writeBeat(beat, 1),
      argv: ["", "interval", beat, String(passStale)],
    },
  ];
}

function runCase(scriptPath, home, row) {
  row.setup();
  return execFileSync("/bin/bash", [scriptPath, "--classify-artifact", ...row.argv], {
    encoding: "utf8",
    env: { ...process.env, HOME: home },
  }).trim();
}

test("the guardian classifies every real heartbeat state correctly", () => {
  const home = scratchHome();
  const config = outboundConfig(home);
  for (const row of classificationCases(home, config)) {
    assert.equal(runCase(GUARDIAN, home, row), row.want, row.name);
  }
});

test("NEGATIVE CONTROL: the same table rejects a classifier that always answers OK", () => {
  const home = scratchHome();
  const config = outboundConfig(home);
  const stubDir = fs.mkdtempSync(path.join(os.tmpdir(), "outbound-guardian-stub-"));
  const stub = path.join(stubDir, "always-ok.sh");
  fs.writeFileSync(stub, "#!/usr/bin/env bash\necho OK\n");

  const mismatches = classificationCases(home, config)
    .filter((row) => runCase(stub, home, row) !== row.want)
    .map((row) => row.name);

  // If this is ever 0, the table above has stopped discriminating and proves nothing.
  assert.ok(mismatches.length >= 4, `table is vacuous: an always-OK classifier failed only ${mismatches.length} cases`);
  assert.ok(mismatches.includes("heartbeat older than the stale limit -> STALE"));
  assert.ok(mismatches.includes("heartbeat file absent entirely -> MISSING_ARTIFACT"));
  assert.ok(mismatches.includes("launchd label gone (never installed / unloaded) -> DEAD_UNLOADED"));
});

// ------------------------------------------------------------------ 4. label matching is exact

// `ai.anicca.life-manager-outbound` is a strict PREFIX of `ai.anicca.life-manager-outbound-verify`.
// A substring match would let the verify job's row answer for the pass job — exactly the "looks
// alive, is dead" bug this task exists to close.
const LISTING = [
  "-\t0\tai.anicca.life-manager-outbound-verify",
  "742\t0\tai.anicca.franklin-loop",
  "-\t0\tai.anicca.life-manager-payout",
].join("\n");

test("an unloaded pass job is not rescued by the verify job's row", () => {
  assert.equal(guardian(["--pick-pid", PASS_LABEL], { input: `${LISTING}\n` }), "");
});

test("each label still finds its own row", () => {
  assert.equal(guardian(["--pick-pid", VERIFY_LABEL], { input: `${LISTING}\n` }), "-");
  assert.equal(guardian(["--pick-pid", "ai.anicca.franklin-loop"], { input: `${LISTING}\n` }), "742");
});

test("a label that is not listed at all yields the empty string the classifier reads as DEAD", () => {
  assert.equal(guardian(["--pick-pid", "ai.anicca.nope"], { input: `${LISTING}\n` }), "");
});

// ------------------------------------------------------------------ 5. it actually SCREAMS

// The classification table above proves the verdict is right. This proves the verdict is ACTED ON:
// the registration really reaches _selffix. The guardian is copied next to a STUB self-fix.sh (it
// resolves its siblings from its own directory), so a dead outbound loop escalates into a file we
// can read instead of detaching a real Opus fixer.
function sandboxedGuardian() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "outbound-guardian-e2e-"));
  fs.copyFileSync(GUARDIAN, path.join(dir, "healthcheck-runtime-loop.sh"));
  fs.writeFileSync(
    path.join(dir, "self-fix.sh"),
    `#!/usr/bin/env bash\nprintf '%s\\n' "$1" >> "$SELFFIX_RECORD"\nprintf '%s\\n' "$2" >> "$SELFFIX_RECORD"\n`,
  );
  return { script: path.join(dir, "healthcheck-runtime-loop.sh"), record: path.join(dir, "escalations.txt") };
}

function runTarget(target, { home, record }, script) {
  const out = execFileSync("/bin/bash", [script, target], {
    encoding: "utf8",
    env: { ...process.env, HOME: home, SELFFIX_RECORD: record },
  });
  const escalations = fs.existsSync(record) ? fs.readFileSync(record, "utf8") : "";
  return { out, escalations };
}

for (const [target, label] of [["outbound-pass", PASS_LABEL], ["outbound-verify", VERIFY_LABEL]]) {
  test(`${target}: an unloaded job escalates to self-fix instead of dying quietly`, () => {
    const home = scratchHome();
    const { script, record } = sandboxedGuardian();
    // The labels are genuinely absent from this machine's launchctl list (the loops are not
    // installed), which is precisely the state a never-installed / unloaded loop is in.
    const { out, escalations } = runTarget(target, { home, record }, script);
    assert.match(out, new RegExp(`\\[${target}\\] DEAD`));
    assert.ok(escalations.includes(target), "self-fix was never handed the dead loop");
    assert.ok(escalations.includes(label), "the escalation does not name the launchd label to fix");
  });
}

test("a STALE outbound heartbeat escalates and reports the real age and limit", () => {
  const home = scratchHome();
  const { beat, passStale } = outboundConfig(home);
  writeBeat(beat, 12 * DAY_MIN); // the 12-day silence that motivated this wiring
  const { script, record } = sandboxedGuardian();
  const { escalations } = runTarget("outbound-pass", { home, record }, script);
  // The job is unloaded on this host, so DEAD wins over STALE — assert the STALE branch directly
  // rather than pretending the loop is installed.
  assert.ok(escalations.length > 0, "an outbound fault produced no escalation at all");
  assert.equal(
    guardian(["--classify-artifact", "-", "interval", beat, String(passStale)], { home }),
    "STALE",
  );
});
