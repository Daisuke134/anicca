// steward.mjs — the S9 常駐化 loop: attach to an already-posted Nosana job and stay alive for
// the WHOLE lease, doing three things every cycle:
//   1. re-read the job from Nosana's public jobs API (so a lease extension made mid-lease is
//      picked up — leaseEnd is recomputed from scratch every cycle, never cached),
//   2. sign a heartbeat over a fresh Solana blockhash+slot (heartbeat.mjs) — the third-party-
//      verifiable "I was alive at this moment" evidence,
//   3. append it to the durable heartbeat ledger (nosana-heartbeats.jsonl under the same
//      fail-closed state dir the deploy ledgers use).
//
// Same dependency-injection style as deploy.mjs: every I/O boundary (fetch, RPC connection,
// clock, sleep, ledger append, log) is a parameter with a real default, so the loop's decision
// logic is fully testable without network or timers.
//
// Fail-closed reads: a single API blip is tolerated (the loop keeps beating — aliveness evidence
// must not depend on the indexer's uptime), but maxConsecutiveFailures in a row throws, because
// at that point the steward can no longer honestly claim to know the lease state.

import path from "node:path";

import { ensureNosanaKeypair } from "./keypair.mjs";
import { makeHeartbeatEntry } from "./heartbeat.mjs";
import { NOSANA_JOBS_API_BASE_URL, DEFAULT_RPC_URL } from "./deploy.mjs";
import { appendChild } from "../../spawn/lib/ledger.js";
import { resolveStateDir } from "../../spawn/lib/state-path.js";

export const HEARTBEAT_LEDGER_BASENAME = "nosana-heartbeats.jsonl";
export const DEFAULT_INTERVAL_MS = 60_000;
export const DEFAULT_GRACE_SECONDS = 120;

// Nosana job state integers (observed live 2026-07-26: a finished job carries state 2 +
// jobStatus "success"): 0=queued, 1=running, >=2 terminal (done/stopped).
const TERMINAL_JOB_STATUSES = new Set(["success", "failed", "stopped"]);

function defaultLog(line) {
  process.stdout.write(`[citizen-steward] ${line}\n`);
}

/**
 * GET {base}/{jobAddress} from Nosana's public jobs API. Same authority + same fail-closed
 * contract as deploy.mjs's reconcileNosanaJobViaApi: any HTTP/parse/shape failure returns null,
 * never throws — the caller decides how many nulls in a row it can tolerate.
 */
export async function fetchJobViaApi({ fetchImpl = fetch, jobAddress, apiBaseUrl = NOSANA_JOBS_API_BASE_URL } = {}) {
  try {
    const res = await fetchImpl(`${apiBaseUrl}/${jobAddress}`);
    if (!res || !res.ok) return null;
    const job = await res.json();
    if (!job || typeof job !== "object") return null;
    return job;
  } catch {
    return null;
  }
}

/**
 * Pure: the lease end as of THIS read. timeStart+timeout is the live-lease truth (timeout grows
 * when the lease is extended); timeEnd is only a fallback for already-ended jobs. Null when the
 * API gave neither — caller treats lease length as unknown, not infinite.
 */
export function computeLeaseEnd(job) {
  if (!job || typeof job !== "object") return null;
  const timeStart = Number(job.timeStart || 0);
  const timeout = Number(job.timeout || 0);
  if (timeStart > 0 && timeout > 0) return timeStart + timeout;
  const timeEnd = Number(job.timeEnd || 0);
  return timeEnd > 0 ? timeEnd : null;
}

/**
 * Pure: has this job stopped being a live lease? True on a terminal state int, a terminal
 * jobStatus string, or nowTs past leaseEnd+grace (grace absorbs indexer lag around the boundary).
 */
export function isTerminal(job, nowTs, graceSeconds = DEFAULT_GRACE_SECONDS) {
  if (!job || typeof job !== "object") return false;
  if (Number(job.state) >= 2) return true;
  if (TERMINAL_JOB_STATUSES.has(job.jobStatus)) return true;
  const leaseEnd = computeLeaseEnd(job);
  return leaseEnd != null && nowTs > leaseEnd + graceSeconds;
}

/**
 * The lease-long steward loop. Resolves Franklin's keypair ONCE up front (tests inject a
 * throwaway `keypair` instead), then beats until the job is terminal.
 *
 * @returns {Promise<{cycles: number, heartbeats: number, terminal: {state: number|null, jobStatus: string|null, reason: string}}>}
 */
export async function stewardLoop({
  jobAddress,
  env = process.env,
  keypair,
  fetchImpl = fetch,
  connectionFactory,
  rpcUrl = (env && (env.NOSANA_RPC_URL || env.SOLANA_RPC_URL)) || DEFAULT_RPC_URL,
  intervalMs = DEFAULT_INTERVAL_MS,
  graceSeconds = DEFAULT_GRACE_SECONDS,
  maxConsecutiveFailures = 5,
  maxCycles = Infinity,
  now = () => Date.now(),
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  appendImpl,
  log = defaultLog,
} = {}) {
  if (typeof jobAddress !== "string" || jobAddress.length === 0) {
    throw new Error("stewardLoop: jobAddress is required");
  }

  const identity = keypair || ensureNosanaKeypair({ env });
  const payer = identity.address;
  const secretBytes = identity.secretBytes || (await importSecretBytes({ env }));

  const connection = connectionFactory
    ? connectionFactory(rpcUrl)
    : new (await import("@solana/web3.js")).Connection(rpcUrl, "confirmed");

  const append =
    appendImpl ||
    ((entry) => appendChild(path.join(resolveStateDir({ env }), HEARTBEAT_LEDGER_BASENAME), entry));

  log(`steward attached to job ${jobAddress} as ${payer} (interval ${intervalMs}ms)`);

  let cycles = 0;
  let heartbeats = 0;
  let consecutiveFailures = 0;
  let lastLeaseEnd = null;
  let lastJob = null;

  for (;;) {
    cycles += 1;

    const job = await fetchJobViaApi({ fetchImpl, jobAddress });
    if (job === null) {
      consecutiveFailures += 1;
      log(`jobs API read failed (${consecutiveFailures}/${maxConsecutiveFailures} consecutive)`);
      if (consecutiveFailures >= maxConsecutiveFailures) {
        throw new Error(
          `stewardLoop: ${consecutiveFailures} consecutive jobs-API failures for ${jobAddress} — lease state unknown, stopping (fail-closed)`,
        );
      }
    } else {
      consecutiveFailures = 0;
      lastJob = job;
      const leaseEnd = computeLeaseEnd(job);
      if (leaseEnd != null && lastLeaseEnd != null && leaseEnd > lastLeaseEnd) {
        log(`lease extended: leaseEnd ${lastLeaseEnd} -> ${leaseEnd} (timeout re-read mid-lease)`);
      }
      if (leaseEnd != null) lastLeaseEnd = leaseEnd;
    }

    // Beat even when this cycle's API read failed — aliveness evidence must not depend on the
    // indexer's uptime; only the RPC (blockhash source) is a hard dependency of a beat.
    //
    // slot + blockhash MUST come from ONE atomic RPC response: a real S8 E2E run produced 2/16
    // entries whose getBlock(slot).blockhash mismatched, because getSlot() and
    // getLatestBlockhash() are separate calls that can evaluate at different slots. The
    // *AndContext variant returns {context:{slot}, value:{blockhash}} from a single evaluation,
    // so the verifier's getBlock(slot) cross-check holds. Plain pair kept as fallback for
    // injected fakes/older RPCs (their entries verify sig-only).
    let slot;
    let blockhash;
    if (typeof connection.getLatestBlockhashAndContext === "function") {
      const resp = await connection.getLatestBlockhashAndContext();
      slot = resp.context.slot;
      blockhash = resp.value.blockhash;
    } else {
      slot = await connection.getSlot();
      ({ blockhash } = await connection.getLatestBlockhash());
    }
    const entry = makeHeartbeatEntry({
      jobAddress,
      payer,
      blockhash,
      slot,
      ts: now() / 1000,
      cycle: cycles,
      secretBytes,
    });
    append(entry);
    heartbeats += 1;
    log(`heartbeat ${cycles}: slot ${slot}, blockhash ${blockhash.slice(0, 8)}…, signed + appended`);

    const nowTs = now() / 1000;
    if (lastJob && isTerminal(lastJob, nowTs, graceSeconds)) {
      const terminal = { state: Number(lastJob.state), jobStatus: lastJob.jobStatus ?? null, reason: "job-terminal" };
      log(`job is terminal (state=${terminal.state}, jobStatus=${terminal.jobStatus}) after ${cycles} cycles — steward done`);
      return { cycles, heartbeats, terminal };
    }
    if (cycles >= maxCycles) {
      log(`maxCycles (${maxCycles}) reached — stopping steward (safety valve)`);
      return { cycles, heartbeats, terminal: { state: lastJob ? Number(lastJob.state) : null, jobStatus: lastJob ? (lastJob.jobStatus ?? null) : null, reason: "max-cycles" } };
    }

    await sleep(intervalMs);
  }
}

// The live path resolves secretBytes through the same canonical identity module the keypair
// materializer uses — kept out of stewardLoop's hot path and NEVER logged (constraint 6).
async function importSecretBytes({ env }) {
  const { resolveSolanaSecret } = await import("../../../earn/lib/resolve-identity.mjs");
  const { deriveAddressFromSecret } = await import("./keypair.mjs");
  const secret = resolveSolanaSecret({ env });
  if (!secret) throw new Error("stewardLoop: no Solana secret resolved — cannot sign heartbeats");
  return deriveAddressFromSecret(secret).secretBytes;
}
