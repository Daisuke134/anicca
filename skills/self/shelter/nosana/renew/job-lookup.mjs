// job-lookup.mjs — real job-state reads for the renewal executor, over the SAME authoritative,
// auth-free Nosana jobs API deploy.mjs already established as ground truth (never CLI stdout —
// `nosana job get`/`job list` are the commands proven to crash or emit unparseable stdout
// non-interactively; see deploy.mjs's reconcileNosanaJobViaApi doc comment). This module adds one
// thing deploy.mjs's own reconciler does not need: picking which of a payer's jobs, if any, is
// currently ALIVE (state QUEUED/RUNNING and not yet past its own timeStart+timeout) — that is
// "the job to renew". Selection is pure and separated from the fetch so the rule is unit-testable
// without the network.

import { NOSANA_JOBS_API_BASE_URL } from "../deploy.mjs";

export { NOSANA_JOBS_API_BASE_URL };

// JobState enum verified against @nosana/kit's JobsProgram.ts (packages/kit/src/services/
// programs/jobs/JobsProgram.ts, nosana-ci/nosana-kit) and cross-checked live 2026-07-25: job
// FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC (which ran its full 900s timeout and stopped)
// reports state 2 via the dashboard API, matching COMPLETED below.
export const JOB_STATE_QUEUED = 0;
export const JOB_STATE_RUNNING = 1;
export const JOB_STATE_COMPLETED = 2;
export const JOB_STATE_STOPPED = 3;

/**
 * I/O: fetch every job the given wallet has ever posted, via the same payer-filtered endpoint
 * deploy.mjs's reconcileNosanaJobViaApi uses (`?payer=<address>` — verified live 2026-07-25 to
 * filter correctly; `project`/`owner`/`wallet` do NOT). Fails closed (throws) on any HTTP/shape
 * problem — an executor that cannot read real job state must never guess that "no jobs" means
 * "nothing to renew" when the real answer is "the read itself failed".
 */
export async function fetchJobsForPayer({ fetchImpl = fetch, posterAddress, apiBaseUrl = NOSANA_JOBS_API_BASE_URL }) {
  if (typeof posterAddress !== "string" || posterAddress.length === 0) {
    throw new Error("fetchJobsForPayer: posterAddress is required");
  }
  const res = await fetchImpl(`${apiBaseUrl}?payer=${posterAddress}`);
  if (!res || !res.ok) {
    throw new Error(`fetchJobsForPayer: HTTP ${res && res.status} from ${apiBaseUrl} (fail-closed)`);
  }
  const data = await res.json();
  const jobs = data && Array.isArray(data.jobs) ? data.jobs : null;
  if (!jobs) {
    throw new Error("fetchJobsForPayer: response has no jobs array (fail-closed — refusing to treat as 'no jobs')");
  }
  return jobs;
}

/**
 * Pure: whether `job` is currently alive — queued or running, AND its own real
 * timeStart+timeout has not already passed `nowTs`. Both checks matter independently: the
 * indexer's `state` field can lag a few seconds behind the on-chain clock right at expiry, so
 * relying on `state` alone could treat an effectively-dead job as renewable.
 */
export function isJobAlive(job, { nowTs }) {
  if (!job || typeof job !== "object") return false;
  if (job.state !== JOB_STATE_QUEUED && job.state !== JOB_STATE_RUNNING) return false;
  const timeStart = Number(job.timeStart);
  const timeout = Number(job.timeout);
  if (!Number.isFinite(timeStart) || !Number.isFinite(timeout)) return false;
  return timeStart + timeout > nowTs;
}

/**
 * Pure: pick the single job to renew — the alive job with the highest timeStart. Returns null
 * (never throws) when none of `jobs` is alive — the caller (executor.mjs) treats null as "nothing
 * to extend, consider posting a successor instead", not as an error.
 */
export function selectActiveJob(jobs, { nowTs }) {
  const alive = (jobs || []).filter((j) => isJobAlive(j, { nowTs }));
  if (alive.length === 0) return null;
  return alive.reduce((newest, j) => (!newest || Number(j.timeStart) > Number(newest.timeStart) ? j : newest), null);
}

/**
 * Pure: the most recent job overall regardless of aliveness — used only to anchor a rent-clock
 * window id (rent-clock.mjs's computeRenewalWindowId) when there is no ALIVE job left, i.e. a
 * lapse already happened and a successor must be posted. Returns null when `jobs` is empty.
 */
export function selectMostRecentJob(jobs) {
  return (jobs || []).reduce(
    (newest, j) => (!newest || Number(j && j.timeStart) > Number(newest.timeStart) ? j : newest),
    null,
  );
}
