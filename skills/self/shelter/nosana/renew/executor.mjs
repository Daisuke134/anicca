// executor.mjs — S3 "self-renewal path" (agent financial independence): keep Franklin's Nosana
// compute alive with zero human in the loop, by EXTENDING the currently-alive job before it
// expires on the verified wallet-only rail (see renew/README.md for the full rail comparison and
// the quoted evidence), falling back to POSTING A SUCCESSOR job — reusing deploy.mjs's already-
// tested `deployNosanaJob` UNCHANGED — only when there is no alive job left to extend. Also
// computes the survival-drive signal (survival-drive.mjs) on every run, dry or live.
//
// --dry is the DEFAULT (matches deploy.mjs/acquire-nos.mjs's constraint): every step below runs
// for real — identity, real balances, real job-state read, the rent-clock decision, the real cost
// estimate, the spend gate — then the function returns BEFORE any on-chain action, and (matching
// deploy.mjs's own convention) never touches the intent ledger at all in dry mode. Only live:true
// extends or posts for real.
//
// At-most-once ("impossible to pay twice for the same window"): every renewal is anchored to a
// windowId (rent-clock.mjs's computeRenewalWindowId) derived from REAL on-chain state — the job
// address plus the exact expiry timestamp being extended past. Before ever spending in live mode,
// the intent ledger (nosana-renewal-intents.jsonl) is checked for an existing row for that exact
// windowId:
//   - a "posted"/"settled" row => refuse outright (defense in depth: once a renewal lands, a
//     fresh job-state read naturally derives a DIFFERENT windowId anyway, since the real timeout
//     has moved — this ledger check exists specifically to catch the narrow gap between "we sent
//     the tx" and "the indexer reflects it", where a fresh read would still show the OLD timeout).
//   - an unresolved "intent" row => RECONCILE from the authoritative job state (does the job's
//     real on-chain timeout, or a newly-alive successor job, already reflect the attempt?) instead
//     of ever retrying blind.
//   - no row (or only refused/failed rows, which spent nothing) => free to attempt.
//
// Honest death: if the spend gate refuses (insufficient balance, cap exceeded, etc.) this returns
// decision:"refused" loudly (never silently returns as if nothing needed doing), and the
// survival-drive signal is computed and logged on EVERY run regardless of whether a renewal is
// due, so insolvency is visible even before it would block a renewal outright.

import path from "node:path";

import { resolveSolanaSecret } from "../../../../earn/lib/resolve-identity.mjs";
import { deriveAddressFromSecret } from "../keypair.mjs";
import { fetchMarkets, selectCheapestMarket, estimateJobCost, fetchNosUsdPriceLive } from "../market.mjs";
import { evaluateSpendGate, DEFAULT_MAX_SPEND_USD, DEFAULT_SOL_FEE_FLOOR } from "../spend-gate.mjs";
import { deployNosanaJob, DEFAULT_RPC_URL, DEFAULT_DURATION_MINUTES } from "../deploy.mjs";
import { readShelterCostEntriesResolved, appendShelterCostEntry } from "../../../spawn/lib/shelter-cost-ledger.js";
import { appendChild, readChildren } from "../../../spawn/lib/ledger.js";
import { resolveStateDir } from "../../../spawn/lib/state-path.js";
import { NOSANA_JOBS_API_BASE_URL, fetchJobsForPayer, selectActiveJob, selectMostRecentJob } from "./job-lookup.mjs";
import {
  evaluateRentClock,
  computeExpiresAtTs,
  computeRenewalWindowId,
  computeBootstrapWindowId,
  DEFAULT_RENEWAL_LEAD_SECONDS,
} from "./rent-clock.mjs";
import { estimateExtendCostNos, estimateExtendCostUsd } from "./cost.mjs";
import {
  computeRunwayHours,
  evaluateSurvivalSignal,
  formatRunway,
  DEFAULT_RUNWAY_WARNING_HOURS,
  DEFAULT_RUNWAY_CRITICAL_HOURS,
} from "./survival-drive.mjs";

export const DEFAULT_EXTEND_MINUTES = DEFAULT_DURATION_MINUTES; // 15 — same length as the original job.
const NOS_MINT = "nosXBVoaCTtYdLvKY6Csb4AC8JCdQKKAaWYtx2ZMoo7"; // same mint market.mjs/deploy.mjs use.

function log(line) {
  // Every call site below passes a static/numeric/public-address string — NEVER secret material.
  process.stdout.write(`[citizen-rent] ${line}\n`);
}

async function readSolBalanceSol({ connection, address, PublicKeyCtor }) {
  const lamports = await connection.getBalance(new PublicKeyCtor(address));
  return lamports / 1_000_000_000;
}

async function readNosBalance({ connection, address, PublicKeyCtor }) {
  const resp = await connection.getParsedTokenAccountsByOwner(new PublicKeyCtor(address), { mint: new PublicKeyCtor(NOS_MINT) });
  if (!resp || !Array.isArray(resp.value) || resp.value.length === 0) return 0;
  const amount = resp.value[0].account.data.parsed.info.tokenAmount.uiAmount;
  return typeof amount === "number" ? amount : 0;
}

/**
 * Real (--live) default: build + sign an on-chain extend instruction via the verified wallet-only
 * rail — `@nosana/kit`'s `client.jobs.extend({job, timeout})` (the ON-CHAIN JobsProgram instruction
 * builder, backed by `@nosana/jobs-program`'s `getExtendInstruction` — NOT `client.api.jobs.extend`,
 * which is the credits/API rail this repo forbids; see renew/README.md for the quoted evidence).
 * `client.wallet` is a `KeyPairSigner` derived from Franklin's OWN already-resolved secretBytes
 * via `@solana/kit`'s `createKeyPairSignerFromBytes` — never a new/second wallet, never a keyfile
 * on disk. Mirrors acquire-nos.mjs's "sign first, extract the deterministic signature, THEN send"
 * shape: the signature is known here, BEFORE anything is broadcast, which is what lets the caller
 * write an at-most-once intent record before the side effect.
 *
 * NOT exercised against a real transaction in this session (spec forbids --live) — this is the
 * same kind of documented, best-effort-but-unverified-live gap deploy.mjs's own README carries for
 * `nosana job post`'s JSON shape. Verified instead by reading @nosana/kit's own README/source and
 * by resolving every function used here for real in this environment (see this feature's report).
 */
async function defaultBuildAndSignExtend({ jobAddress, additionalSeconds, secretBytes, rpcUrl }) {
  const [{ createNosanaClient }, solanaKit] = await Promise.all([import("@nosana/kit"), import("@solana/kit")]);
  const wallet = await solanaKit.createKeyPairSignerFromBytes(secretBytes);
  const client = createNosanaClient(undefined, rpcUrl ? { solana: { rpcEndpoint: rpcUrl } } : undefined);
  client.wallet = wallet;
  const instruction = await client.jobs.extend({ job: jobAddress, timeout: additionalSeconds });
  const txMessage = await client.solana.buildTransaction(instruction);
  const signedTx = await client.solana.signTransaction(txMessage);
  const signature = solanaKit.getSignatureFromTransaction(signedTx);
  return { signature, sendable: { client, signedTx } };
}

/** Real (--live) default: send the already-signed transaction and wait for confirmation. */
async function defaultSendSignedExtend({ sendable }) {
  await sendable.client.solana.sendTransaction(sendable.signedTx);
}

/**
 * Pure: current classification of a renewal window against the intent ledger's rows.
 *  - "done": a posted/settled row exists — refuse outright, never pay twice.
 *  - "pending-reconciliation": an unresolved "intent" row exists — must reconcile, never retry blind.
 *  - "none": no row, or only refused/failed rows (which spent nothing) — free to attempt.
 */
export function findWindowRecord(intentRows, windowId) {
  const rowsForWindow = (intentRows || []).filter((r) => r && r.windowId === windowId);
  if (rowsForWindow.some((r) => r.status === "posted" || r.status === "settled")) {
    return { state: "done", rows: rowsForWindow };
  }
  if (rowsForWindow.some((r) => r.status === "intent")) {
    return { state: "pending-reconciliation", rows: rowsForWindow };
  }
  return { state: "none", rows: rowsForWindow };
}

/**
 * Pure: given a fresh read of real jobs, decide whether a previously-unresolved EXTEND intent
 * actually landed on-chain. Ground truth is the job's own CURRENT timeout being at least
 * `minTimeout` (the timeout the intent was trying to reach). Never retries; only classifies.
 */
export function reconcileExtendFromJobs(jobs, { jobAddress, minTimeout }) {
  const job = (jobs || []).find((j) => j && j.address === jobAddress);
  if (!job) {
    return {
      outcome: "unknown",
      reason: `job ${jobAddress} not found in a fresh read — cannot confirm the extend landed`,
    };
  }
  const currentTimeout = Number(job.timeout);
  if (Number.isFinite(currentTimeout) && currentTimeout >= minTimeout) {
    return {
      outcome: "settled",
      reason: `job ${jobAddress}'s real on-chain timeout (${currentTimeout}s) already reflects the extension (>= ${minTimeout}s)`,
    };
  }
  return {
    outcome: "unknown",
    reason: `job ${jobAddress}'s real on-chain timeout (${currentTimeout}) does not yet reflect the intended extension (>= ${minTimeout})`,
  };
}

/**
 * Pure: given a fresh read of real jobs, decide whether a previously-unresolved REPOST intent
 * actually landed. Ground truth is an alive job whose timeStart is at/after the attempt timestamp
 * — mirrors deploy.mjs's own reconcileNosanaJobViaApi `afterTs` semantics.
 */
export function reconcileRepostFromJobs(jobs, { attemptTs, nowTs }) {
  const eligible = (jobs || []).filter((j) => Number(j && j.timeStart) >= Math.floor(attemptTs) - 5);
  const candidate = selectActiveJob(eligible, { nowTs });
  if (candidate) {
    return {
      outcome: "settled",
      jobAddress: candidate.address,
      reason: `an alive job ${candidate.address} started at/after the repost attempt`,
    };
  }
  return { outcome: "unknown", reason: "no alive job found starting at/after the repost attempt — cannot confirm the repost landed" };
}

/**
 * The full renewal orchestration. Every I/O dependency has a real default; tests override them.
 * Never throws for a REFUSED gate, a not-yet-due clock, or dry mode (expected, successful
 * "decided not to spend yet" outcomes) — DOES throw for unresolvable identity, a failed real-state
 * read, an invalid job price, or an outcome that remains UNKNOWN after reconciliation (all
 * fail-closed, matching deploy.mjs/acquire-nos.mjs).
 */
export async function renewShelter({
  env = process.env,
  live = false,
  extendMinutes = Number(env.NOSANA_RENEW_EXTEND_MINUTES || DEFAULT_EXTEND_MINUTES),
  leadSeconds = Number(env.NOSANA_RENEW_LEAD_SECONDS || DEFAULT_RENEWAL_LEAD_SECONDS),
  maxSpendUsd = Number(env.NOSANA_MAX_SPEND_USD || DEFAULT_MAX_SPEND_USD),
  runwayWarningHours = Number(env.NOSANA_RUNWAY_WARNING_HOURS || DEFAULT_RUNWAY_WARNING_HOURS),
  runwayCriticalHours = Number(env.NOSANA_RUNWAY_CRITICAL_HOURS || DEFAULT_RUNWAY_CRITICAL_HOURS),
  rpcUrl = env.NOSANA_RPC_URL || env.SOLANA_RPC_URL || DEFAULT_RPC_URL,
  network = env.NOSANA_NETWORK || "mainnet",
  fetchImpl = fetch,
  connectionFactory,
  publicKeyCtor,
  now = () => Date.now(),
  buildAndSignExtend = defaultBuildAndSignExtend,
  sendSignedExtend = defaultSendSignedExtend,
  deployNosanaJobImpl = deployNosanaJob,
  // Whole-function injection (not a raw fetchImpl) because fetchNosUsdPriceLive's own fetchImpl
  // contract is a no-arg `() => {json}` shape (see market.mjs), different from the `fetchImpl(url)`
  // contract fetchJobsForPayer/fetchMarkets use above — tests substitute this directly rather than
  // trying to unify two incompatible fetch conventions.
  fetchNosUsdPriceImpl = fetchNosUsdPriceLive,
} = {}) {
  // Step 1: identity — SAME secret every earn/spend engine in this repo resolves; never a new
  // wallet (constraint 2 of S1, carried forward); never logs secret material (constraint 6).
  const secret = resolveSolanaSecret({ env });
  if (!secret) {
    throw new Error(
      "renewShelter: no Solana secret resolved for this instance — ANICCA_HOME must point at Franklin's home (e.g. $HOME/.blockrun)",
    );
  }
  const { address, secretBytes } = deriveAddressFromSecret(secret);
  log(`resolved address ${address}`);

  // Step 2: real balances. Always resolve web3.js (mirrors acquire-nos.mjs's pattern, not
  // deploy.mjs's — deploy.mjs re-imports a SECOND time just for PublicKey when connectionFactory
  // is given, which would throw if a caller supplied connectionFactory without publicKeyCtor too;
  // importing once unconditionally here avoids that trap entirely).
  const web3 = await import("@solana/web3.js");
  const PublicKey = publicKeyCtor || web3.PublicKey;
  const connection = connectionFactory ? connectionFactory(rpcUrl) : new web3.Connection(rpcUrl, "confirmed");
  const solBalance = await readSolBalanceSol({ connection, address, PublicKeyCtor: PublicKey });
  const nosBalance = await readNosBalance({ connection, address, PublicKeyCtor: PublicKey });
  log(`balances: ${solBalance} SOL, ${nosBalance} NOS`);

  // Step 3: real job state — the authoritative jobs API (never CLI stdout; see job-lookup.mjs).
  const nowTs = now() / 1000;
  const jobs = await fetchJobsForPayer({ fetchImpl, posterAddress: address });
  const activeJob = selectActiveJob(jobs, { nowTs });
  const mostRecentJob = selectMostRecentJob(jobs);
  if (activeJob) {
    log(`active job: ${activeJob.address} (market ${activeJob.market}, price ${activeJob.price} raw NOS/sec)`);
  } else if (mostRecentJob) {
    log(`no alive job — most recent job on record is ${mostRecentJob.address} (state ${mostRecentJob.state})`);
  } else {
    log("no job on record for this wallet at all — this would be the very first post");
  }

  // Step 4: the rent clock. Anchor to the active job's real expiry when one exists; otherwise to
  // the most recent (dead) job's real expiry (correctly reports alreadyExpired/dueForRenewal true
  // with a meaningful "how long has it been dead" figure); otherwise (never posted) anchor to now
  // — trivially due, since there is nothing running to protect.
  let expiresAtTs;
  if (activeJob) {
    expiresAtTs = computeExpiresAtTs({ timeStart: activeJob.timeStart, timeout: activeJob.timeout });
  } else if (mostRecentJob && Number.isFinite(Number(mostRecentJob.timeStart)) && Number.isFinite(Number(mostRecentJob.timeout))) {
    expiresAtTs = computeExpiresAtTs({ timeStart: Number(mostRecentJob.timeStart), timeout: Number(mostRecentJob.timeout) });
  } else {
    expiresAtTs = nowTs;
  }
  const rentClock = evaluateRentClock({ nowTs, expiresAtTs, leadSeconds });
  log(
    `rent clock: ${rentClock.secondsUntilExpiry.toFixed(0)}s until expiry, dueForRenewal=${rentClock.dueForRenewal}, alreadyExpired=${rentClock.alreadyExpired}`,
  );

  // Step 5: the survival-drive signal — ALWAYS computed and logged, regardless of whether a
  // renewal is due, so insolvency is visible even before it would block a renewal outright.
  let nosPerHour;
  if (activeJob) {
    const price = Number(activeJob.price);
    if (!Number.isFinite(price) || price <= 0) {
      throw new Error("renewShelter: active job has no valid price — refusing to treat rent as free (fail-closed)");
    }
    nosPerHour = (price * 3600) / 10 ** 6;
  } else {
    const markets = await fetchMarkets({ fetchImpl });
    const market = selectCheapestMarket(markets, { requireGpu: true });
    if (!market) {
      throw new Error("renewShelter: no eligible GPU market found — refusing to treat rent as free (fail-closed)");
    }
    const nosUsdPriceForRate = await fetchNosUsdPriceImpl({});
    nosPerHour = estimateJobCost({ usdPerHour: market.usdPerHour, hours: 1, nosUsdPrice: nosUsdPriceForRate }).nos;
  }
  const runwayHours = computeRunwayHours({ nosBalance, nosPerHour });
  const runway = formatRunway(runwayHours);
  const survivalSignal = evaluateSurvivalSignal({ runwayHours, warningHours: runwayWarningHours, criticalHours: runwayCriticalHours });
  log(
    `survival drive: runway ${runway.days}d ${runway.hours.toFixed(1)}h at ${nosPerHour.toFixed(6)} NOS/hr — ` +
      `${survivalSignal.level} (promoteEarning=${survivalSignal.promoteEarning}: ${survivalSignal.reason})`,
  );

  const windowId = activeJob
    ? computeRenewalWindowId({ jobAddress: activeJob.address, referenceExpiresAtTs: expiresAtTs })
    : mostRecentJob
      ? computeRenewalWindowId({ jobAddress: mostRecentJob.address, referenceExpiresAtTs: expiresAtTs })
      : computeBootstrapWindowId({ nowTs, bucketSeconds: leadSeconds * 2 });

  const baseResult = {
    address,
    solBalance,
    nosBalance,
    activeJob,
    mostRecentJob,
    rentClock,
    windowId,
    nosPerHour,
    runwayHours,
    runway,
    survivalSignal,
    action: activeJob ? "extend" : "repost",
    posted: false,
  };

  if (!rentClock.dueForRenewal) {
    log(`not due for renewal yet (${rentClock.secondsUntilExpiry.toFixed(0)}s until expiry, lead is ${leadSeconds}s) — nothing to do.`);
    return { ...baseResult, decision: "not-due" };
  }

  // ---- Renewal IS due from here on. Every branch below is loud: it either renews, or it
  // explicitly reports WHY it did not (refused / already-done / unknown-pending) — spec:
  // "never silently skip a window".

  const stateDir = resolveStateDir({ env });
  const intentFile = path.join(stateDir, "nosana-renewal-intents.jsonl");
  // Dry mode never touches the intent ledger at all, matching deploy.mjs's own convention — the
  // ledger only exists to protect real spends.
  const intentRows = live ? readChildren(intentFile) : [];
  const windowRecord = live ? findWindowRecord(intentRows, windowId) : { state: "none", rows: [] };

  if (windowRecord.state === "done") {
    log(`window ${windowId} was already renewed (found a posted/settled intent row) — refusing to pay twice.`);
    return { ...baseResult, decision: "already-done" };
  }

  if (windowRecord.state === "pending-reconciliation") {
    log(`window ${windowId} has an unresolved prior attempt — reconciling from real state instead of retrying blind.`);
    const pendingRow = windowRecord.rows.filter((r) => r.status === "intent").slice(-1)[0];
    const freshJobs = await fetchJobsForPayer({ fetchImpl, posterAddress: address });
    const reconciled =
      pendingRow.action === "extend"
        ? reconcileExtendFromJobs(freshJobs, { jobAddress: pendingRow.jobAddress, minTimeout: pendingRow.targetTimeout })
        : reconcileRepostFromJobs(freshJobs, { attemptTs: pendingRow.ts, nowTs });
    if (reconciled.outcome === "settled") {
      appendChild(intentFile, { ts: now() / 1000, windowId, intentId: pendingRow.intentId, status: "settled", ...reconciled });
      log(`reconciled window ${windowId} as SETTLED: ${reconciled.reason}`);
      return { ...baseResult, decision: "reconciled-settled", reconciliation: reconciled };
    }
    throw new Error(
      `renewShelter: window ${windowId}'s outcome is still UNKNOWN after reconciliation (${reconciled.reason}) — ` +
        `refusing to retry automatically; reconcile manually via ${NOSANA_JOBS_API_BASE_URL}?payer=${address} before any further action.`,
    );
  }

  // windowRecord.state === "none" (or dry mode): free to attempt — never previously paid for.

  if (activeJob) {
    // ---- EXTEND path: the verified wallet-only rail (renew/README.md). ----
    const additionalSeconds = Math.round(extendMinutes * 60);
    const price = Number(activeJob.price);
    const costNos = estimateExtendCostNos({ pricePerSecond: price, additionalSeconds });
    const nosUsdPrice = await fetchNosUsdPriceImpl({});
    const costUsd = estimateExtendCostUsd({ costNos, nosUsdPrice });
    log(`extend estimate: +${extendMinutes}min (+${additionalSeconds}s) costs ~${costNos.toFixed(6)} NOS (~$${costUsd.toFixed(4)})`);

    const shelterCostFile = path.join(stateDir, "shelter-cost.jsonl");
    const priorEntries = readShelterCostEntriesResolved(shelterCostFile);
    const history = priorEntries.map((r) => ({
      ts: r.ts,
      amountUsd: r.settledLeaseCostUsd,
      status: "sent",
      txHash: r.jobAddress || `no-address-${r.ts}`,
    }));
    const gate = evaluateSpendGate({
      costUsd,
      costNos,
      solBalance,
      nosBalance,
      history,
      config: { perJobUsdCap: maxSpendUsd, solFeeFloor: DEFAULT_SOL_FEE_FLOOR },
      nowTs,
    });
    log(`spend gate: ${gate.allowed ? "ALLOWED" : "REFUSED"} — ${gate.reason}`);

    const result = { ...baseResult, costUsd, costNos, additionalSeconds, gate };

    if (!live) {
      if (gate.allowed) {
        log(
          `gate ALLOWED — would extend job ${activeJob.address} by ${extendMinutes}min, spending ~${costNos.toFixed(6)} NOS ` +
            `(~$${costUsd.toFixed(4)}). Stopping before on-chain action (dry).`,
        );
      } else {
        log(`gate REFUSED (${gate.reason}) — would NOT extend even outside dry mode. Stopping before on-chain action (dry).`);
      }
      return { ...result, decision: gate.allowed ? "would-extend" : "refused" };
    }

    if (!gate.allowed) {
      log("refusing to extend: spend gate denied it.");
      return { ...result, decision: "refused" };
    }

    // ---- Everything below this line only runs with --live. ----
    const targetTimeout = Number(activeJob.timeout) + additionalSeconds;
    const { signature, sendable } = await buildAndSignExtend({ jobAddress: activeJob.address, additionalSeconds, secretBytes, rpcUrl });
    const intentId = `${Math.floor(nowTs)}-${activeJob.address}`;
    appendChild(intentFile, {
      ts: nowTs,
      windowId,
      intentId,
      status: "intent",
      action: "extend",
      jobAddress: activeJob.address,
      targetTimeout,
      signature,
      costUsd,
      costNos,
    });

    let sendError = null;
    try {
      await sendSignedExtend({ sendable, signature });
    } catch (err) {
      sendError = err;
    }

    if (!sendError) {
      appendChild(intentFile, { ts: now() / 1000, windowId, intentId, status: "settled", signature });
      appendShelterCostEntry(shelterCostFile, { ts: now() / 1000, settledLeaseCostUsd: costUsd, jobAddress: activeJob.address });
      log(`extended job ${activeJob.address} by ${extendMinutes}min — signature ${signature}, settled cost $${costUsd.toFixed(4)} recorded to ${shelterCostFile}`);
      return { ...result, decision: "extended", signature, posted: true };
    }

    // send threw — outcome UNKNOWN. Reconcile from real state, never blind-retry (spec constraint).
    log(`sendSignedExtend threw — outcome unknown, reconciling from real state (never blind-retrying): ${sendError.message}`);
    const freshJobs = await fetchJobsForPayer({ fetchImpl, posterAddress: address });
    const reconciled = reconcileExtendFromJobs(freshJobs, { jobAddress: activeJob.address, minTimeout: targetTimeout });
    if (reconciled.outcome === "settled") {
      appendChild(intentFile, { ts: now() / 1000, windowId, intentId, status: "settled", signature, ...reconciled });
      appendShelterCostEntry(shelterCostFile, { ts: now() / 1000, settledLeaseCostUsd: costUsd, jobAddress: activeJob.address });
      log(`reconciled: the extend actually landed despite the send error — ${reconciled.reason}`);
      return { ...result, decision: "extended", signature, posted: true, reconciliation: reconciled };
    }
    throw new Error(
      `renewShelter: extend intent ${intentId} (window ${windowId}, signature ${signature}) is UNKNOWN after reconciliation ` +
        `(${reconciled.reason}) — check the signature and job ${activeJob.address} manually before any retry. Never blind-retrying.`,
    );
  }

  // ---- REPOST fallback path (no alive job to extend): reuse deployNosanaJob UNCHANGED. ----
  log("no alive job to extend — falling back to posting a successor job (reusing deployNosanaJob).");
  const intentId = `${Math.floor(nowTs)}-repost`;
  if (live) {
    appendChild(intentFile, { ts: nowTs, windowId, intentId, status: "intent", action: "repost" });
  }
  const deployResult = await deployNosanaJobImpl({
    env,
    live,
    durationMinutes: extendMinutes,
    maxSpendUsd,
    rpcUrl,
    network,
    fetchImpl,
    connectionFactory,
    publicKeyCtor,
    now,
  });
  if (!live) {
    return {
      ...baseResult,
      decision: deployResult.gate && deployResult.gate.allowed ? "would-repost" : "refused",
      deployResult,
    };
  }
  if (deployResult.posted) {
    appendChild(intentFile, { ts: now() / 1000, windowId, intentId, status: "settled", jobAddress: deployResult.jobAddress });
    return { ...baseResult, decision: "reposted", posted: true, jobAddress: deployResult.jobAddress, deployResult };
  }
  appendChild(intentFile, { ts: now() / 1000, windowId, intentId, status: "refused", reason: deployResult.gate && deployResult.gate.reason });
  return { ...baseResult, decision: "refused", deployResult };
}
