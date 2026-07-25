// node:test — public-job-state.mjs: the credential-free "restore Franklin's public job history"
// mechanism (S7, zero-secret redesign). Mirrors ../renew/job-lookup.mjs's own tested behavior —
// this file is a deliberate, disclosed re-expression (see its header for why it isn't an import).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  fetchJobsForPayer,
  isJobAlive,
  selectActiveJob,
  selectMostRecentJob,
  computeNosPerHourFromJob,
  NOSANA_JOBS_API_BASE_URL,
} from "../public-job-state.mjs";

function fetchImplReturning(body, { ok = true, status = 200 } = {}) {
  return async () => ({ ok, status, json: async () => body });
}

test("fetchJobsForPayer: requires posterAddress", async () => {
  await assert.rejects(() => fetchJobsForPayer({ fetchImpl: fetchImplReturning({ jobs: [] }) }), /posterAddress is required/);
});

test("fetchJobsForPayer: real endpoint shape — GET {base}?payer=<address> returns {jobs:[...]}, verified against the public jobs API", async () => {
  let calledUrl = null;
  const fetchImpl = async (url) => {
    calledUrl = url;
    return { ok: true, status: 200, json: async () => ({ jobs: [{ address: "J1" }], totalJobs: 1 }) };
  };
  const jobs = await fetchJobsForPayer({ fetchImpl, posterAddress: "PAYER" });
  assert.equal(calledUrl, `${NOSANA_JOBS_API_BASE_URL}?payer=PAYER`);
  assert.deepEqual(jobs, [{ address: "J1" }]);
});

test("fetchJobsForPayer: fails closed on a non-ok HTTP response", async () => {
  await assert.rejects(
    () => fetchJobsForPayer({ fetchImpl: fetchImplReturning({}, { ok: false, status: 500 }), posterAddress: "P" }),
    /HTTP 500/,
  );
});

test("fetchJobsForPayer: fails closed when the response has no jobs array (never treats as 'no jobs')", async () => {
  await assert.rejects(
    () => fetchJobsForPayer({ fetchImpl: fetchImplReturning({ notJobs: true }), posterAddress: "P" }),
    /no jobs array/,
  );
});

test("isJobAlive: queued/running AND not yet past timeStart+timeout is alive", () => {
  assert.equal(isJobAlive({ state: 0, timeStart: 100, timeout: 50 }, { nowTs: 140 }), true);
  assert.equal(isJobAlive({ state: 1, timeStart: 100, timeout: 50 }, { nowTs: 140 }), true);
});

test("isJobAlive: completed/stopped state, or past expiry, or malformed fields, is never alive", () => {
  assert.equal(isJobAlive({ state: 2, timeStart: 100, timeout: 50 }, { nowTs: 110 }), false);
  assert.equal(isJobAlive({ state: 0, timeStart: 100, timeout: 50 }, { nowTs: 200 }), false);
  assert.equal(isJobAlive(null, { nowTs: 1 }), false);
  assert.equal(isJobAlive({ state: 0, timeStart: "nope", timeout: 50 }, { nowTs: 1 }), false);
});

test("selectActiveJob: picks the alive job with the highest timeStart; null when none alive", () => {
  const jobs = [
    { address: "A", state: 2, timeStart: 100, timeout: 50 }, // dead
    { address: "B", state: 1, timeStart: 200, timeout: 50 }, // alive
    { address: "C", state: 0, timeStart: 150, timeout: 50 }, // alive but older
  ];
  const picked = selectActiveJob(jobs, { nowTs: 210 });
  assert.equal(picked.address, "B");
  assert.equal(selectActiveJob([], { nowTs: 1 }), null);
  assert.equal(selectActiveJob([{ address: "A", state: 2, timeStart: 1, timeout: 1 }], { nowTs: 100 }), null);
});

test("selectMostRecentJob: the highest-timeStart job regardless of aliveness; null on empty", () => {
  const jobs = [
    { address: "A", timeStart: 100 },
    { address: "B", timeStart: 300 },
    { address: "C", timeStart: 200 },
  ];
  assert.equal(selectMostRecentJob(jobs).address, "B");
  assert.equal(selectMostRecentJob([]), null);
});

test("computeNosPerHourFromJob: matches ../renew/executor.mjs's own inline formula (price*3600/1e6) — verified against a real observed job (price=47 -> 0.1692 NOS/hr)", () => {
  const rate = computeNosPerHourFromJob({ price: 47 });
  assert.ok(Math.abs(rate - 0.1692) < 1e-9);
});

test("computeNosPerHourFromJob: fails closed on a missing/non-positive price — never treats rent as free", () => {
  assert.throws(() => computeNosPerHourFromJob({ price: 0 }), /positive finite number/);
  assert.throws(() => computeNosPerHourFromJob({}), /positive finite number/);
  assert.throws(() => computeNosPerHourFromJob(null), /positive finite number/);
});
