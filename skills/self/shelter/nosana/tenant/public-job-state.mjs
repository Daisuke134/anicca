// public-job-state.mjs — reads Franklin's OWN public job history via the same unauthenticated
// Nosana jobs API this whole skill already trusts as ground truth (../deploy.mjs's
// reconcileNosanaJobViaApi, ../renew/job-lookup.mjs's fetchJobsForPayer), filtered by Franklin's
// TREASURY ADDRESS — a plain job env var (NOSANA_TREASURY_ADDRESS), because a Solana ADDRESS is
// public knowledge; only the matching PRIVATE key is a secret, and this file never touches one.
//
// This is the state-restore mechanism for the zero-secret redesign (S7, second pass — see
// tenant/README.md's "State restore" section for the full reasoning + the alternatives
// considered and rejected). It needs no credential because reading ANY wallet's job history and
// ANY wallet's on-chain balance requires no permission on a public blockchain — only SPENDING
// requires a private key, and nothing here spends.
//
// Deliberately a small, disclosed, from-scratch re-expression of ../renew/job-lookup.mjs's
// isJobAlive/selectActiveJob/selectMostRecentJob/fetchJobsForPayer, NOT an import: that file
// imports NOSANA_JOBS_API_BASE_URL from ../deploy.mjs, which itself pulls in keypair.mjs (which
// resolves Franklin's TREASURY secret), market.mjs, job-definition.mjs, spend-gate.mjs, and two
// ledger modules. This file has zero imports beyond the global `fetch` — auditable at a glance as
// structurally incapable of touching any secret, which matters because this exact file is bundled
// into the container (see tenant/build-bundle.mjs).

export const NOSANA_JOBS_API_BASE_URL = "https://dashboard.k8s.prd.nos.ci/api/jobs";
export const NOS_DECIMALS = 6;

export const JOB_STATE_QUEUED = 0;
export const JOB_STATE_RUNNING = 1;

/**
 * I/O: every job `posterAddress` has ever posted, via the public, unauthenticated jobs API.
 * Fails closed (throws) on any HTTP/shape problem — never treats a failed read as "no jobs".
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

/** Pure: is `job` currently alive — queued/running AND its own timeStart+timeout hasn't passed. */
export function isJobAlive(job, { nowTs }) {
  if (!job || typeof job !== "object") return false;
  if (job.state !== JOB_STATE_QUEUED && job.state !== JOB_STATE_RUNNING) return false;
  const timeStart = Number(job.timeStart);
  const timeout = Number(job.timeout);
  if (!Number.isFinite(timeStart) || !Number.isFinite(timeout)) return false;
  return timeStart + timeout > nowTs;
}

/** Pure: the alive job with the highest timeStart, or null when none is alive. */
export function selectActiveJob(jobs, { nowTs }) {
  const alive = (jobs || []).filter((j) => isJobAlive(j, { nowTs }));
  if (alive.length === 0) return null;
  return alive.reduce((newest, j) => (!newest || Number(j.timeStart) > Number(newest.timeStart) ? j : newest), null);
}

/** Pure: the most recent job overall (alive or not), or null when `jobs` is empty. */
export function selectMostRecentJob(jobs) {
  return (jobs || []).reduce(
    (newest, j) => (!newest || Number(j && j.timeStart) > Number(newest && newest.timeStart) ? j : newest),
    null,
  );
}

/**
 * Pure: NOS-per-hour burn rate from a job's own locked-in `price` (raw NOS units per second — see
 * ../renew/cost.mjs's header for the live verification of this field's meaning, and
 * ../renew/executor.mjs:264 for the identical inline formula this mirrors). Fails closed on a
 * missing/non-positive price rather than treating an unknown rate as free.
 */
export function computeNosPerHourFromJob(job) {
  const price = Number(job && job.price);
  if (!Number.isFinite(price) || price <= 0) {
    throw new Error(`computeNosPerHourFromJob: job.price must be a positive finite number, got ${price}`);
  }
  return (price * 3600) / 10 ** NOS_DECIMALS;
}
