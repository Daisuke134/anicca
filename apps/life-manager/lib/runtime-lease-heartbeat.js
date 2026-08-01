"use strict";

function startRuntimeLeaseHeartbeat(input = {}, dependencies = {}) {
  const heartbeatJob = dependencies.heartbeatJob;
  if (typeof heartbeatJob !== "function") {
    throw new Error("runtime heartbeat function is required");
  }
  const leaseSeconds = Number(input.leaseSeconds);
  if (!Number.isInteger(leaseSeconds) || leaseSeconds < 30 || leaseSeconds > 900) {
    throw new Error("runtime heartbeat lease is invalid");
  }
  const setIntervalFn = dependencies.setIntervalFn || setInterval;
  const clearIntervalFn = dependencies.clearIntervalFn || clearInterval;
  const identity = Object.freeze({
    tenantId: input.tenantId,
    jobId: input.jobId,
    attempt: input.attempt,
    workerId: input.workerId,
    leaseSeconds,
  });
  const intervalMs = Math.max(1000, Math.floor((leaseSeconds * 1000) / 3));
  let chain = Promise.resolve();
  let firstError = null;
  let stopped = false;

  function pulse() {
    if (stopped) return Promise.resolve();
    const attempt = chain.then(() => heartbeatJob(
      identity,
      dependencies.storeOptions || {},
    ));
    chain = attempt.catch((error) => {
      if (!firstError) firstError = error;
    });
    return chain;
  }

  const timer = setIntervalFn(pulse, intervalMs);
  return Object.freeze({
    async stop() {
      stopped = true;
      clearIntervalFn(timer);
      await chain;
      if (firstError) throw firstError;
    },
  });
}

module.exports = {
  startRuntimeLeaseHeartbeat,
};
