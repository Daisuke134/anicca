"use strict";
// spec 2026-08-01-lm-daily-organ-design.md §3 row 1c: the done receipt is "organ 毎の経過ms がログに
// 出る". Today every organ logs only its outcome, so when `tenant timeout 90000ms` fires there is no
// way to tell which organ ate the budget. This wrapper is that measurement.
//
// Run: node --test lib/organ-run.test.js
const { test } = require("node:test");
const assert = require("node:assert");

const { runOrgan } = require("./organ-run.js");

test("runOrgan returns the organ's value and logs how long it took", async () => {
  const lines = [];
  let clock = 1000;
  const result = await runOrgan({
    label: "care", uid: "lm_abcdefghijklmnop",
    run: async () => { clock += 250; return { status: "scanned" }; },
    log: (line) => lines.push(line),
    now: () => clock,
  });
  assert.deepEqual(result, { status: "scanned" });
  assert.equal(lines.length, 1);
  // Full-line equality, not a substring match: the uid is truncated to 12 chars like every other
  // organ log line in scheduler.js, and a substring assertion would still pass an UNtruncated uid.
  assert.equal(
    lines[0],
    "[care] uid=lm_abcdefghi ms=250",
    "expected the label, the 12-char-truncated uid, and the elapsed ms",
  );
});

test("a throwing organ is logged with its error and does NOT propagate", async () => {
  const lines = [];
  const errors = [];
  const result = await runOrgan({
    label: "diet", uid: "u1",
    run: async () => { throw new Error("places api down"); },
    log: (line) => lines.push(line),
    logError: (line) => errors.push(line),
    now: () => 0,
  });
  assert.equal(result, null, "the caller continues with no value rather than dying");
  assert.match(errors[0], /err places api down/);
  assert.match(errors[0], /ms=/, "a failure is still timed — a slow failure is the interesting case");
});

// Before this wrapper existed, every organ's catch block used console.error. Routing both outcomes
// through one `log` demoted organ failures to stdout, so anything watching stderr — the thing an
// operator actually greps, and the channel Railway/launchd separate out — saw NOTHING when an organ
// broke. Measuring how long an organ took must not cost the ability to notice it died.
test("a failure goes to the ERROR channel and a success does not", async () => {
  const lines = [];
  const errors = [];
  const channels = { log: (line) => lines.push(line), logError: (line) => errors.push(line), now: () => 0 };

  await runOrgan({ label: "care", uid: "u1", run: async () => "ok", ...channels });
  assert.equal(lines.length, 1, "the success receipt stays on the normal channel");
  assert.deepEqual(errors, [], "a healthy organ must never cry wolf on stderr");

  await runOrgan({ label: "care", uid: "u1", run: async () => { throw new Error("boom"); }, ...channels });
  assert.equal(errors.length, 1, "the failure is on stderr where a watcher is looking");
  assert.match(errors[0], /\[care\] uid=u1 ms=0 err boom/);
  assert.equal(lines.length, 1, "and it is NOT also duplicated onto stdout");
});

test("with no channels passed, runOrgan still returns a value and still swallows a throw", async () => {
  // The wrapper's whole job is to never take down its caller. If `log` were required, a caller that
  // omitted it would throw from inside the catch block and propagate — the exact failure this
  // module exists to prevent. So the default logger is part of the contract, not a convenience —
  // and that goes for the error channel too, which is reached only from inside that catch block.
  const originalLog = console.log;
  const originalError = console.error;
  const lines = [];
  const errors = [];
  console.log = (line) => lines.push(line);
  console.error = (line) => errors.push(line);
  try {
    const ok = await runOrgan({ label: "care", uid: "u1", run: async () => "value", now: () => 0 });
    assert.equal(ok, "value");

    const failed = await runOrgan({
      label: "diet", uid: "u1",
      run: async () => { throw new Error("no logger here"); },
      now: () => 0,
    });
    assert.equal(failed, null, "a throw is still swallowed when no logger was supplied");
  } finally {
    console.log = originalLog;
    console.error = originalError;
  }
  assert.equal(lines.length, 1, "the success fell back to console.log");
  assert.equal(errors.length, 1, "and the failure fell back to console.error, not console.log");
  assert.match(errors[0], /err no logger here/);
});

test("runOrgan times the failure path too, so a slow throw is visible", async () => {
  const errors = [];
  let clock = 0;
  await runOrgan({
    label: "mental", uid: "u1",
    run: async () => { clock += 4000; throw new Error("boom"); },
    logError: (line) => errors.push(line),
    now: () => clock,
  });
  assert.match(errors[0], /ms=4000/);
});
