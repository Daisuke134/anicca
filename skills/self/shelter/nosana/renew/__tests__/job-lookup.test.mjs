// node:test — job-lookup: real-shaped jobs-API fetch (fetchImpl injected, no network) + pure
// aliveness/selection logic, verified against the real job fixture.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  NOSANA_JOBS_API_BASE_URL,
  JOB_STATE_QUEUED,
  JOB_STATE_RUNNING,
  JOB_STATE_COMPLETED,
  fetchJobsForPayer,
  isJobAlive,
  selectActiveJob,
  selectMostRecentJob,
} from "../job-lookup.mjs";

const PAYER = "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T";
// The real fixture job (verified live 2026-07-25): ran its full 900s timeout and completed.
const REAL_EXPIRED_JOB = {
  id: 48185994,
  address: "FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC",
  market: "7AtiXMSH6R1jjBxrcYjehCkkSF7zvYWte63gwEDBcGHq",
  payer: PAYER,
  price: 48,
  state: JOB_STATE_COMPLETED,
  timeStart: 1784956456,
  timeout: 900,
  usdRewardPerHour: 0.043702677,
};

function fetchImplReturning(body, { ok = true, status = 200 } = {}) {
  return async () => ({ ok, status, json: async () => body });
}

test("fetchJobsForPayer requests the documented payer-filtered endpoint", async () => {
  let requestedUrl = null;
  await fetchJobsForPayer({
    fetchImpl: async (url) => {
      requestedUrl = url;
      return { ok: true, status: 200, json: async () => ({ jobs: [], totalJobs: 0 }) };
    },
    posterAddress: PAYER,
  });
  assert.equal(requestedUrl, `${NOSANA_JOBS_API_BASE_URL}?payer=${PAYER}`);
});

test("fetchJobsForPayer returns the real response shape's jobs array", async () => {
  const jobs = await fetchJobsForPayer({
    fetchImpl: fetchImplReturning({ jobs: [REAL_EXPIRED_JOB], totalJobs: 1 }),
    posterAddress: PAYER,
  });
  assert.deepEqual(jobs, [REAL_EXPIRED_JOB]);
});

test("fetchJobsForPayer fails closed (throws) on a non-ok HTTP response — never treats it as 'no jobs'", async () => {
  await assert.rejects(
    () => fetchJobsForPayer({ fetchImpl: fetchImplReturning({}, { ok: false, status: 500 }), posterAddress: PAYER }),
    /HTTP 500/,
  );
});

test("fetchJobsForPayer fails closed on a missing jobs array", async () => {
  await assert.rejects(
    () => fetchJobsForPayer({ fetchImpl: fetchImplReturning({}), posterAddress: PAYER }),
    /no jobs array/,
  );
});

test("fetchJobsForPayer fails closed when fetchImpl itself throws", async () => {
  await assert.rejects(
    () =>
      fetchJobsForPayer({
        fetchImpl: async () => {
          throw new Error("network down");
        },
        posterAddress: PAYER,
      }),
    /network down/,
  );
});

test("isJobAlive: the real fixture job is NOT alive (state COMPLETED, and long past its own expiry)", () => {
  assert.equal(isJobAlive(REAL_EXPIRED_JOB, { nowTs: REAL_EXPIRED_JOB.timeStart + 10000 }), false);
});

test("isJobAlive: a RUNNING job before its expiry is alive", () => {
  const job = { ...REAL_EXPIRED_JOB, state: JOB_STATE_RUNNING };
  assert.equal(isJobAlive(job, { nowTs: job.timeStart + 100 }), true);
});

test("isJobAlive: a QUEUED job counts as alive too", () => {
  const job = { ...REAL_EXPIRED_JOB, state: JOB_STATE_QUEUED };
  assert.equal(isJobAlive(job, { nowTs: job.timeStart + 100 }), true);
});

test("isJobAlive: state RUNNING but past its own timeStart+timeout is NOT alive (indexer-lag guard)", () => {
  const job = { ...REAL_EXPIRED_JOB, state: JOB_STATE_RUNNING };
  assert.equal(isJobAlive(job, { nowTs: job.timeStart + job.timeout + 1 }), false);
});

test("isJobAlive returns false (never throws) on null/malformed input", () => {
  assert.equal(isJobAlive(null, { nowTs: 1 }), false);
  assert.equal(isJobAlive({ state: JOB_STATE_RUNNING, timeStart: "x", timeout: 900 }, { nowTs: 1 }), false);
});

test("selectActiveJob returns null when nothing is alive", () => {
  assert.equal(selectActiveJob([REAL_EXPIRED_JOB], { nowTs: REAL_EXPIRED_JOB.timeStart + 100000 }), null);
});

test("selectActiveJob picks the alive job with the highest timeStart among several", () => {
  const older = { ...REAL_EXPIRED_JOB, address: "OLDER", state: JOB_STATE_RUNNING, timeStart: 1000, timeout: 900 };
  const newer = { ...REAL_EXPIRED_JOB, address: "NEWER", state: JOB_STATE_RUNNING, timeStart: 2000, timeout: 900 };
  const result = selectActiveJob([older, newer], { nowTs: 2100 });
  assert.equal(result.address, "NEWER");
});

test("selectMostRecentJob picks the highest timeStart regardless of aliveness, and null on empty input", () => {
  const a = { address: "A", timeStart: 100 };
  const b = { address: "B", timeStart: 200 };
  assert.equal(selectMostRecentJob([a, b]).address, "B");
  assert.equal(selectMostRecentJob([]), null);
  assert.equal(selectMostRecentJob(undefined), null);
});
