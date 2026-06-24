// maybe-start-loops.test.js — B3: the voice-daemon single-writer gate.
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const { maybeStartLoops } = require("./maybe-start-loops.js");

function counters() {
  const c = { startScheduler: 0, startTravelLoop: 0, startAskLoop: 0, startOnboardLoop: 0 };
  const starters = {
    startScheduler: () => c.startScheduler++,
    startTravelLoop: () => c.startTravelLoop++,
    startAskLoop: () => c.startAskLoop++,
    startOnboardLoop: () => c.startOnboardLoop++,
  };
  return { c, starters };
}

test("default (unset) → all 4 loops start once (Railway behaviour unchanged)", () => {
  const { c, starters } = counters();
  const r = maybeStartLoops({}, starters);
  assert.strictEqual(r.started, true);
  assert.deepStrictEqual(c, { startScheduler: 1, startTravelLoop: 1, startAskLoop: 1, startOnboardLoop: 1 });
});

test('LIFE_RUN_LOOPS="true" → all 4 loops start', () => {
  const { c, starters } = counters();
  const r = maybeStartLoops({ LIFE_RUN_LOOPS: "true" }, starters);
  assert.strictEqual(r.started, true);
  assert.deepStrictEqual(c, { startScheduler: 1, startTravelLoop: 1, startAskLoop: 1, startOnboardLoop: 1 });
});

for (const off of ["false", "FALSE", " False ", "0", "off"]) {
  test(`LIFE_RUN_LOOPS=${JSON.stringify(off)} → voice daemon, NO loops start`, () => {
    const { c, starters } = counters();
    const r = maybeStartLoops({ LIFE_RUN_LOOPS: off }, starters);
    assert.strictEqual(r.started, false, "started=false");
    assert.match(r.reason, /single-writer|cron/i, "reason explains cron owns loops");
    assert.deepStrictEqual(c, { startScheduler: 0, startTravelLoop: 0, startAskLoop: 0, startOnboardLoop: 0 },
      "ZERO loops started when off — single writer");
  });
}

test("an unrelated value (e.g. 'yes') is treated as ON (fail-safe to running, not silent-off)", () => {
  const { c, starters } = counters();
  const r = maybeStartLoops({ LIFE_RUN_LOOPS: "yes" }, starters);
  assert.strictEqual(r.started, true, "only explicit false/0/off disables — avoids accidental silent no-wake");
  assert.strictEqual(c.startScheduler, 1);
});
