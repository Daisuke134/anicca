"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  startRuntimeLeaseHeartbeat,
} = require("./runtime-lease-heartbeat.js");

function controlledTimer() {
  const state = { scheduled: null, intervalMs: null, cleared: null };
  return {
    state,
    setIntervalFn(callback, intervalMs) {
      state.scheduled = callback;
      state.intervalMs = intervalMs;
      return "lease-timer";
    },
    clearIntervalFn(timer) {
      state.cleared = timer;
    },
  };
}

test("lease heartbeat renews the exact claimed attempt and stops its timer", async () => {
  const timer = controlledTimer();
  const calls = [];
  const heartbeat = startRuntimeLeaseHeartbeat({
    tenantId: "dais",
    jobId: `outbound-event:${"a".repeat(64)}`,
    attempt: 2,
    workerId: "connector-local",
    leaseSeconds: 60,
  }, {
    heartbeatJob: async (identity, storeOptions) => {
      calls.push({ identity, storeOptions });
    },
    storeOptions: { query: "fixture-query" },
    setIntervalFn: timer.setIntervalFn,
    clearIntervalFn: timer.clearIntervalFn,
  });

  assert.equal(timer.state.intervalMs, 20_000);
  await timer.state.scheduled();
  await heartbeat.stop();

  assert.deepEqual(calls, [{
    identity: {
      tenantId: "dais",
      jobId: `outbound-event:${"a".repeat(64)}`,
      attempt: 2,
      workerId: "connector-local",
      leaseSeconds: 60,
    },
    storeOptions: { query: "fixture-query" },
  }]);
  assert.equal(timer.state.cleared, "lease-timer");
});

test("overlapping timer pulses are serialized before stop resolves", async () => {
  const timer = controlledTimer();
  const releases = [];
  const started = [];
  const heartbeat = startRuntimeLeaseHeartbeat({
    tenantId: "dais",
    jobId: `outbound-event:${"b".repeat(64)}`,
    attempt: 1,
    workerId: "connector-local",
    leaseSeconds: 90,
  }, {
    heartbeatJob: async () => {
      started.push(started.length + 1);
      await new Promise((resolve) => releases.push(resolve));
    },
    setIntervalFn: timer.setIntervalFn,
    clearIntervalFn: timer.clearIntervalFn,
  });

  const first = timer.state.scheduled();
  const second = timer.state.scheduled();
  await Promise.resolve();
  assert.deepEqual(started, [1]);

  releases.shift()();
  await first;
  await Promise.resolve();
  assert.deepEqual(started, [1, 2]);
  releases.shift()();
  await second;
  await heartbeat.stop();
});

test("stop reports the first heartbeat failure after clearing the timer", async () => {
  const timer = controlledTimer();
  const heartbeat = startRuntimeLeaseHeartbeat({
    tenantId: "dais",
    jobId: `outbound-event:${"c".repeat(64)}`,
    attempt: 1,
    workerId: "connector-local",
    leaseSeconds: 60,
  }, {
    heartbeatJob: async () => {
      throw new Error("runtime heartbeat lost lease");
    },
    setIntervalFn: timer.setIntervalFn,
    clearIntervalFn: timer.clearIntervalFn,
  });

  await timer.state.scheduled();
  await assert.rejects(heartbeat.stop(), /lost lease/i);
  assert.equal(timer.state.cleared, "lease-timer");
});
