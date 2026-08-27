// renew.mjs — extend a running Nosana lease before it expires (S15: the 24/7 piece).
//
// Why not the CLI: `nosana job extend` crashes before it does any work —
// dist/src/cli/job/extend/action.js:23 calls `nosana.solana.config.network.includes('devnet')`
// on an undefined config.network, purely to build a display URL (measured 2026-07-26). The SDK's
// own `jobs.extend(job, seconds, instructionOnly, payer)` is fine, so we call that directly.
//
// The lease is what keeps a self-paying agent alive. Renewing costs only the extra runtime
// (the escrow for the added minutes), which is far cheaper than posting a fresh confidential job
// and re-delivering its definition — and it keeps the SAME container, so nothing restarts.
//
// Money-safety: pays from the SAME capped sub-wallet that posted the job, never the canonical key.
//
// There are TWO brakes here, and the second one exists because the first was not enough. A total-
// lease ceiling bounds how long ONE lease may run, and that is all it bounds — a loop under a
// ceiling keeps buying time until the wallet is empty and calls it normal operation. Measured
// 2026-07-27: job AzUFmVa5 rode the ceiling from 600s to 19800s and took the wallet from 0.894 NOS
// to 0.027, which is less than a single 10-minute lease costs. The agent had paid itself homeless.
//
// So the real brake is a floor, and the floor is priced as THE COST OF MOVING OUT: always keep
// enough to post one fresh lease somewhere else. An agent that spends its last token on staying
// where it is has no move left; one that stops early can still relocate. Stopping is survivable,
// running dry is not.

import fs from "node:fs";

export const DEFAULT_RENEW_MARGIN_SEC = 180; // start renewing when this much lease is left
export const DEFAULT_EXTEND_SEC = 600; // add 10 minutes per renewal
export const DEFAULT_MAX_TOTAL_SEC = 6 * 60 * 60; // never let one lease exceed 6h without a human
// Escrow a fresh confidential post demands, measured 2026-07-26 and duration-independent. This is
// the price of the option to move, so it is what we refuse to spend.
export const DEFAULT_NOS_MOVE_OUT_RESERVE = 0.34;
// What one 600s extension costs on the cheapest market (0.0302 quoted; the live run averaged
// ~0.027). Quote the higher number: under-quoting here is what lets the floor be crossed.
export const DEFAULT_NOS_PER_EXTEND = 0.0302;
// The CLI refuses to sign below this, so falling under it means no transaction can be sent at all.
export const DEFAULT_SOL_FEE_FLOOR = 0.005;

/**
 * Pure: should we renew now? Returns {renew, reason, remainingSec}.
 *
 * Balances are REQUIRED. They default to zero rather than to "unknown means fine", because the one
 * way this check fails dangerously is by being skipped: a caller that forgets to pass balances
 * would otherwise get back the old, unaffordable "yes".
 */
export function evaluateRenewal({
  job,
  nowTs,
  marginSec = DEFAULT_RENEW_MARGIN_SEC,
  maxTotalSec = DEFAULT_MAX_TOTAL_SEC,
  nosBalance,
  solBalance,
  nosPerExtend = DEFAULT_NOS_PER_EXTEND,
  nosReserve = DEFAULT_NOS_MOVE_OUT_RESERVE,
  solFeeFloor = DEFAULT_SOL_FEE_FLOOR,
}) {
  if (!job || typeof job !== "object") return { renew: false, reason: "no job", remainingSec: null };
  const state = Number(job.state);
  if (state !== 1) return { renew: false, reason: `job not running (state ${state})`, remainingSec: null };
  const timeStart = Number(job.timeStart || 0);
  const timeout = Number(job.timeout || 0);
  if (!timeStart || !timeout) return { renew: false, reason: "lease bounds unknown", remainingSec: null };
  const remainingSec = timeStart + timeout - nowTs;
  if (timeout >= maxTotalSec) {
    return { renew: false, reason: `lease already ${timeout}s, at/over the ${maxTotalSec}s ceiling`, remainingSec };
  }
  if (remainingSec > marginSec) {
    return { renew: false, reason: `${Math.round(remainingSec)}s left, margin is ${marginSec}s`, remainingSec };
  }
  if (typeof nosBalance !== "number" || typeof solBalance !== "number") {
    return { renew: false, reason: "refusing to renew without knowing the balance", remainingSec };
  }
  if (solBalance < solFeeFloor) {
    return { renew: false, reason: `${solBalance} SOL is under the ${solFeeFloor} needed to sign anything`, remainingSec };
  }
  if (nosBalance - nosPerExtend < nosReserve) {
    return {
      renew: false,
      reason: `stopping at ${nosBalance} NOS — paying for this extension would spend the ${nosReserve} NOS kept to move house`,
      remainingSec,
    };
  }
  return { renew: true, reason: `${Math.round(remainingSec)}s left — renewing`, remainingSec };
}

/** Load a Solana Keypair from a 64-byte JSON-array keypair file. Never logs the bytes. */
async function loadKeypair(keypairPath) {
  const { Keypair } = await import("@solana/web3.js");
  const bytes = Uint8Array.from(JSON.parse(fs.readFileSync(keypairPath, "utf8")));
  if (bytes.length !== 64) throw new Error("renew: keypair file must contain 64 bytes");
  return Keypair.fromSecretKey(bytes);
}

/**
 * Extend a live job via the SDK (CLI-free). Returns the tx signature.
 * sdkPath defaults to the globally-installed CLI's bundled SDK, which is the copy proven to work
 * against mainnet on this machine.
 */
export async function extendLease({
  jobAddress,
  keypairPath,
  extendSec = DEFAULT_EXTEND_SEC,
  network = "mainnet",
  sdkPath = "/opt/homebrew/lib/node_modules/@nosana/cli/node_modules/@nosana/sdk/dist/index.js",
  sdkFactory,
}) {
  if (!jobAddress || !keypairPath) throw new Error("renew: jobAddress and keypairPath are required");
  const payer = await loadKeypair(keypairPath);
  const sdk = sdkFactory
    ? sdkFactory({ payer, network })
    : await (async () => {
        const mod = await import(sdkPath);
        const Client = mod.Client || mod.default;
        const bs58 = (await import("bs58")).default;
        return new Client(network, bs58.encode(payer.secretKey));
      })();
  return sdk.jobs.extend(jobAddress, extendSec, false, payer);
}
