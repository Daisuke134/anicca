"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { startFunderWeeklyReflectionLoop } = require("./funder-weekly-reflection-loop.js");

test("configured scheduler runs immediately and every 15 minutes without a human checkpoint", async () => {
  let runs = 0;
  let interval;
  const started = startFunderWeeklyReflectionLoop({
    env: { LM_RUNTIME_DATABASE_URL: "postgres://runtime", LM_FUNDRAISING_TENANT_ID: "dais-local" },
    runOnce: async () => { runs += 1; },
    setIntervalImpl: (fn, ms) => { interval = { fn, ms, unref() {} }; return interval; },
    logger: { log() {}, error() {} },
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(started.enabled, true);
  assert.equal(interval.ms, 15 * 60 * 1000);
  assert.equal(runs, 1);
  await interval.fn();
  assert.equal(runs, 2);
});

test("missing tenant or database disables the loop instead of guessing identity", () => {
  for (const env of [{}, { DATABASE_URL: "postgres://runtime" }, { LM_FUNDRAISING_TENANT_ID: "dais-local" }]) {
    const result = startFunderWeeklyReflectionLoop({
      env,
      setIntervalImpl: () => { throw new Error("must not schedule"); },
      logger: { log() {}, error() {} },
    });
    assert.equal(result.enabled, false);
  }
});
