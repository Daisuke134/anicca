// Deployment-role single-writer gate. The legacy boolean remains a safe transition switch.
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const { maybeStartLoops } = require("./maybe-start-loops.js");

function counters() {
  const c = { startScheduler: 0, startTravelLoop: 0, startAskLoop: 0, startOnboardLoop: 0, startDiscoveryLoop: 0 };
  const starters = {
    startScheduler: () => c.startScheduler++,
    startTravelLoop: () => c.startTravelLoop++,
    startAskLoop: () => c.startAskLoop++,
    startOnboardLoop: () => c.startOnboardLoop++,
    startDiscoveryLoop: () => c.startDiscoveryLoop++,
  };
  return { c, starters };
}

test("default standalone process keeps the current Railway behavior during migration", () => {
  const { c, starters } = counters();
  const r = maybeStartLoops({}, starters);
  assert.strictEqual(r.started, true);
  assert.deepStrictEqual(c, { startScheduler: 1, startTravelLoop: 1, startAskLoop: 1, startOnboardLoop: 1, startDiscoveryLoop: 1 });
});

test("the scheduler deployment starts all loops only with an explicit owner", () => {
  const { c, starters } = counters();
  const r = maybeStartLoops({
    LM_DEPLOYMENT_ROLE: "scheduler",
    LM_SCHEDULER_OWNER: "local-primary",
    LIFE_RUN_LOOPS: "true",
  }, starters);
  assert.strictEqual(r.started, true);
  assert.equal(r.owner, "local-primary");
  assert.deepStrictEqual(c, { startScheduler: 1, startTravelLoop: 1, startAskLoop: 1, startOnboardLoop: 1, startDiscoveryLoop: 1 });
});

for (const off of ["false", "FALSE", " False ", "0", "off"]) {
  test(`LIFE_RUN_LOOPS=${JSON.stringify(off)} remains a safe transition stop`, () => {
    const { c, starters } = counters();
    const r = maybeStartLoops({ LIFE_RUN_LOOPS: off }, starters);
    assert.strictEqual(r.started, false, "started=false");
    assert.match(r.reason, /disabled|deployment/i);
    assert.doesNotMatch(r.reason, /openclaw/i);
    assert.deepStrictEqual(c, { startScheduler: 0, startTravelLoop: 0, startAskLoop: 0, startOnboardLoop: 0, startDiscoveryLoop: 0 },
      "ZERO loops started when off — single writer");
  });
}

for (const role of ["api", "worker"]) {
  test(`${role} deployment never owns scheduler loops`, () => {
    const { c, starters } = counters();
    const r = maybeStartLoops({
      LM_DEPLOYMENT_ROLE: role,
      LIFE_RUN_LOOPS: "true",
    }, starters);
    assert.strictEqual(r.started, false);
    assert.match(r.reason, new RegExp(role));
    assert.deepStrictEqual(c, counters().c);
  });
}

test("scheduler deployment without an owner fails closed", () => {
  const { c, starters } = counters();
  const r = maybeStartLoops({
    LM_DEPLOYMENT_ROLE: "scheduler",
    LIFE_RUN_LOOPS: "true",
  }, starters);
  assert.strictEqual(r.started, false);
  assert.match(r.reason, /owner.*required/i);
  assert.deepStrictEqual(c, counters().c);
});

test("OpenClaw is not a supported deployment owner or fallback", () => {
  const { c, starters } = counters();
  const r = maybeStartLoops({
    LM_DEPLOYMENT_ROLE: "openclaw",
    LIFE_RUN_LOOPS: "true",
  }, starters);
  assert.strictEqual(r.started, false);
  assert.match(r.reason, /unsupported deployment role/i);
  assert.deepStrictEqual(c, counters().c);
});
