// Deployment-role single-writer gate. The legacy boolean remains a safe transition switch.
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const { maybeStartLoops, inngestConfigured, inProcessLoopsOn } = require("./maybe-start-loops.js");

function counters() {
  // startWakeLoop is tracked like every other loop: the dial runs on its own timer (spec §3.1
  // method A), so "the scheduler process started its loops" is only true if the dial started too.
  const c = { startScheduler: 0, startWakeLoop: 0, startReminderLoop: 0, startTravelLoop: 0, startAskLoop: 0, startOnboardLoop: 0, startDiscoveryLoop: 0, startInvestmentDryRunLoop: 0 };
  const starters = {
    startScheduler: () => c.startScheduler++,
    startWakeLoop: () => c.startWakeLoop++,
    startReminderLoop: () => c.startReminderLoop++,
    startTravelLoop: () => c.startTravelLoop++,
    startAskLoop: () => c.startAskLoop++,
    startOnboardLoop: () => c.startOnboardLoop++,
    startDiscoveryLoop: () => c.startDiscoveryLoop++,
    startInvestmentDryRunLoop: () => c.startInvestmentDryRunLoop++,
  };
  return { c, starters };
}

test("default standalone process keeps the current Railway behavior during migration", () => {
  const { c, starters } = counters();
  const r = maybeStartLoops({}, starters);
  assert.strictEqual(r.started, true);
  assert.deepStrictEqual(c, { startScheduler: 1, startWakeLoop: 1, startReminderLoop: 1, startTravelLoop: 1, startAskLoop: 1, startOnboardLoop: 1, startDiscoveryLoop: 1, startInvestmentDryRunLoop: 1 });
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
  assert.deepStrictEqual(c, { startScheduler: 1, startWakeLoop: 1, startReminderLoop: 1, startTravelLoop: 1, startAskLoop: 1, startOnboardLoop: 1, startDiscoveryLoop: 1, startInvestmentDryRunLoop: 1 });
});

for (const off of ["false", "FALSE", " False ", "0", "off"]) {
  test(`LIFE_RUN_LOOPS=${JSON.stringify(off)} falls back to one standalone owner without Inngest`, () => {
    const { c, starters } = counters();
    const r = maybeStartLoops({ LIFE_RUN_LOOPS: off }, starters);
    assert.strictEqual(r.started, true);
    assert.strictEqual(r.owner, "standalone-inngest-missing-fallback");
    assert.match(r.reason, /standalone|fallback/i);
    assert.doesNotMatch(r.reason, /openclaw|INNGEST|secret|key/i);
    assert.deepStrictEqual(c, { startScheduler: 1, startWakeLoop: 1, startReminderLoop: 1, startTravelLoop: 1, startAskLoop: 1, startOnboardLoop: 1, startDiscoveryLoop: 1, startInvestmentDryRunLoop: 1 },
      "all eight loops start exactly once");
  });
}

test("off plus an Inngest signing key keeps the in-process owner off", () => {
  const { c, starters } = counters();
  const r = maybeStartLoops({ LIFE_RUN_LOOPS: "off", INNGEST_SIGNING_KEY: "signing-secret" }, starters);
  assert.strictEqual(r.started, false);
  assert.match(r.reason, /disabled|deployment/i);
  assert.deepStrictEqual(c, counters().c);
});

test("off plus Inngest dev mode keeps the in-process owner off", () => {
  const { c, starters } = counters();
  const r = maybeStartLoops({ LIFE_RUN_LOOPS: "0", INNGEST_DEV: " 1 " }, starters);
  assert.strictEqual(r.started, false);
  assert.deepStrictEqual(c, counters().c);
});

for (const role of ["api", "worker", "scheduler"]) {
  test(`off plus explicit ${role} role never starts the standalone fallback`, () => {
    const { c, starters } = counters();
    const r = maybeStartLoops({ LIFE_RUN_LOOPS: "false", LM_DEPLOYMENT_ROLE: role, LM_SCHEDULER_OWNER: "owner" }, starters);
    assert.strictEqual(r.started, false);
    assert.deepStrictEqual(c, counters().c);
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

test("shared Inngest configuration treats trimmed dev/key values consistently", () => {
  assert.equal(inngestConfigured({ INNGEST_DEV: " 1 " }), true);
  assert.equal(inngestConfigured({ INNGEST_SIGNING_KEY: " signing-secret " }), true);
  assert.equal(inngestConfigured({ INNGEST_SIGNING_KEY: " \t\n" }), false);
  assert.equal(inngestConfigured({ INNGEST_SIGNING_KEY: 1 }), false);
});

test("shared in-process predicate matches the standalone fallback and explicit ownership", () => {
  assert.equal(inProcessLoopsOn({ LIFE_RUN_LOOPS: "off" }), true);
  assert.equal(inProcessLoopsOn({ LIFE_RUN_LOOPS: "off", INNGEST_SIGNING_KEY: "key" }), false);
  assert.equal(inProcessLoopsOn({ LIFE_RUN_LOOPS: "off", INNGEST_SIGNING_KEY: " \t\n" }), true);
  assert.equal(inProcessLoopsOn({ LIFE_RUN_LOOPS: "off", INNGEST_DEV: "1" }), false);
  assert.equal(inProcessLoopsOn({ LIFE_RUN_LOOPS: "off", LM_DEPLOYMENT_ROLE: "api" }), false);
  assert.equal(inProcessLoopsOn({ LIFE_RUN_LOOPS: "true", LM_DEPLOYMENT_ROLE: "api" }), true);
});
