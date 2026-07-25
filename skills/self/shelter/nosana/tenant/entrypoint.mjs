// entrypoint.mjs — THE script that runs INSIDE a Nosana job container (S7, zero-secret redesign).
// tenant/build-bundle.mjs bundles this file (via esbuild, at build time on this Mac, where the
// whole monorepo exists) together with its real imports — ./proof.mjs, ./public-job-state.mjs,
// the literal, unmodified ../renew/survival-drive.mjs, and ../market.mjs — into ONE
// dependency-free .mjs artifact (tenant/entrypoint.bundle.mjs), so the container needs
// nothing but `node` itself: no npm install (this repo has never verified npm-registry egress
// from a Nosana node — see tenant/README.md), no multi-file fetch, no directory structure.
//
// NO SECRET OF ANY KIND is present in this file, in its env, or anywhere in the job definition
// that carries it (see tenant/README.md's "A finding that changes the design" section): a
// previous version of this feature put a funded tenant key + a GitHub token in the job's env —
// both were then discovered to be published PERMANENTLY to public IPFS the moment such a job
// posts (verified live against a real job's `ipfsJob` hash, fetched unauthenticated from
// ipfs.io). This version carries zero secrets, so there is nothing to leak.
//
// Four things happen here, in order:
//   1. Boots and identifies itself — generates a fresh, EPHEMERAL keypair at runtime (never
//      funded, so leaking it is meaningless) and prints its own public address. This proves code
//      executed in the container; it is not, and was never meant to be, a claim of custody over
//      any funded identity.
//   2. Restores state — reads Franklin's own REAL job history from the public, unauthenticated
//      Nosana jobs API, filtered by Franklin's TREASURY ADDRESS (a public key, passed as a plain
//      env var — publishing an address leaks nothing; only a private key would). No credential.
//   3. Does something economically real and verifiable — reads Franklin's REAL treasury balance
//      from public chain state, recomputes NOS/hour burn rate + runway using the EXACT SAME
//      reused code (../renew/survival-drive.mjs, literally the same file, not a copy) that
//      ../renew/executor.mjs runs on the Mac — a match between the two is strong evidence the
//      same logic ran on the same real data inside the job. Signs a challenge over all of it,
//      bound to a blockhash fetched at runtime (unfakeable from outside the job — see proof.mjs).
//   4. Reports — logs every step to stdout plus a final TENANT_REPORT_JSON line, which is read
//      back via the jobs API's `jobResult.opStates[0]` diagnostics (verified live 2026-07-25 as
//      the reliable evidence channel) — not the exposed HTTP endpoint (never once returned 200 in
//      four attempts across two nodes) and not the dead `-o/--output` artifact flag. There is no
//      step 5 (snapshot-back): a previous version wrote history to a private store using a
//      GitHub token; this version carries no credential to write with, so it does not attempt to
//      — an accepted, disclosed loss of "does this container remember ITS OWN run count", not of
//      the economic-proof claim itself (see tenant/README.md).
//
// Every I/O boundary is an injected parameter with a real default, matching every other
// orchestration function in this skill — __tests__/entrypoint.test.mjs exercises the full flow
// with zero real network calls.

import { buildChallengeMessage, signChallenge } from "./proof.mjs";
import {
  fetchJobsForPayer,
  selectActiveJob,
  selectMostRecentJob,
  computeNosPerHourFromJob,
} from "./public-job-state.mjs";
import { computeRunwayHours, formatRunway } from "../renew/survival-drive.mjs";
import { fetchMarkets, selectCheapestMarket, estimateJobCost, fetchNosUsdPriceLive, NOS_MINT } from "../market.mjs";

const DEFAULT_RPC_URL = "https://api.mainnet-beta.solana.com";

function log(line) {
  // Every call site below passes a static/numeric/public-address/public-signature string — this
  // file has no secret to log in the first place (constraint: zero secrets in this container).
  process.stdout.write(`[tenant] ${line}\n`);
}

async function readNosBalance({ connection, address, PublicKeyCtor }) {
  try {
    const resp = await connection.getParsedTokenAccountsByOwner(new PublicKeyCtor(address), {
      mint: new PublicKeyCtor(NOS_MINT),
    });
    if (!resp || !Array.isArray(resp.value) || resp.value.length === 0) return 0;
    const amount = resp.value[0].account.data.parsed.info.tokenAmount.uiAmount;
    return typeof amount === "number" ? amount : 0;
  } catch (err) {
    log(`NOS balance read failed, treating as 0 (non-fatal): ${err && err.message}`);
    return 0;
  }
}

/**
 * Resolve a real NOS/hour burn rate + its source, mirroring ../renew/executor.mjs's own
 * survival-drive branch (lines ~258-272) EXACTLY: an active job's own locked-in price when one
 * exists, otherwise a live cheapest-GPU-market estimate — the same two-branch logic, so a
 * Mac-side run of `bin/citizen-rent --dry` at roughly the same time computes the identical number
 * for the identical real inputs. Never fabricates a rate: only returns null when BOTH the
 * active-job path and the market-fallback path are unavailable (no job history AND no eligible
 * market) — an exceedingly unlikely real-world state, at which point "no rate" is reported
 * honestly rather than a fabricated one.
 *
 * REGRESSION (found live 2026-07-25 running the real bundled artifact end-to-end against real
 * balances with no active job): `fetchMarkets({fetchImpl})` and `fetchNosUsdPriceLive({fetchImpl})`
 * do NOT share the same fetchImpl calling convention — `fetchMarkets` calls `fetchImpl(url)`
 * (standard), but `fetchNosUsdPriceLive` (via ../../spawn/lib/cloud-target.mjs's
 * `fetchSpotPriceUsd`) calls `fetchImpl()` with ZERO arguments and expects a Response-like object
 * whose `.json()` resolves to `{price}` directly — a completely different shape than the standard
 * `fetch(url)` this file's own `fetchImpl` parameter is. Passing the standard one straight through
 * made the real global `fetch` get called with no URL, throw, get silently swallowed by
 * `fetchSpotPriceUsd`'s own try/catch-to-0, and surface as a confusing
 * "could not obtain a valid NOS/USD price" failure — a REAL bug this file's own hermetic tests
 * did not catch (their fake fetchImpl happened to handle both calling conventions). `fetchNosUsdPriceLive({})`
 * with NO override — deploy.mjs's own real-usage convention — is what actually works in production;
 * `nosUsdPriceFetchImpl` below is a SEPARATE, distinctly-shaped injection point used only by
 * __tests__/entrypoint.test.mjs to exercise this branch hermetically.
 */
async function resolveNosPerHour({ activeJob, mostRecentJob, fetchImpl, nosUsdPriceFetchImpl }) {
  if (activeJob) {
    return { nosPerHour: computeNosPerHourFromJob(activeJob), rateSource: `active-job:${activeJob.address}` };
  }
  // No currently-alive job — fall back to a live market estimate, exactly like executor.mjs does.
  const markets = await fetchMarkets({ fetchImpl });
  const market = selectCheapestMarket(markets, { requireGpu: true });
  if (!market) {
    return { nosPerHour: null, rateSource: "unavailable: no active job and no eligible market" };
  }
  const nosUsdPrice = await fetchNosUsdPriceLive(nosUsdPriceFetchImpl ? { fetchImpl: nosUsdPriceFetchImpl } : {});
  const nosPerHour = estimateJobCost({ usdPerHour: market.usdPerHour, hours: 1, nosUsdPrice }).nos;
  const label = mostRecentJob
    ? `market-fallback:${market.address} (most recent job ${mostRecentJob.address} is no longer alive)`
    : `market-fallback:${market.address} (no job history at all for this wallet)`;
  return { nosPerHour, rateSource: label };
}

/**
 * The full in-job flow. Every I/O dependency has a real default; tests override them. Throws
 * (fail-closed) when NOSANA_TREASURY_ADDRESS is missing — that is "this job cannot do its one
 * job", not a soft failure. Never fabricates a balance, blockhash, rate, or signature.
 *
 * @returns {Promise<object>} the full report — also printed to stdout as TENANT_REPORT_JSON.
 */
export async function runTenantIncarnation({
  env = process.env,
  now = () => Date.now(),
  fetchImpl = fetch,
  // Distinctly-shaped injection point for ../market.mjs's fetchNosUsdPriceLive — see
  // resolveNosPerHour's doc comment for why this must NOT be the same value as `fetchImpl` above.
  // Left undefined by default so production always uses fetchNosUsdPriceLive's own real adapter.
  nosUsdPriceFetchImpl,
  connectionFactory,
  publicKeyCtor,
  keypairCtor,
  signImpl,
  rpcUrl = env.NOSANA_RPC_URL || env.SOLANA_RPC_URL || DEFAULT_RPC_URL,
} = {}) {
  const treasuryAddress = env.NOSANA_TREASURY_ADDRESS;
  if (typeof treasuryAddress !== "string" || treasuryAddress.length === 0) {
    throw new Error("runTenantIncarnation: NOSANA_TREASURY_ADDRESS is not set — this job has nothing to report on");
  }

  // Step 1: boot + identify — a fresh, unfunded, ephemeral identity. Never resolved from any
  // secret, env var, or file: generated fresh, right here, every run.
  const web3 = await import("@solana/web3.js");
  const PublicKey = publicKeyCtor || web3.PublicKey;
  const Keypair = keypairCtor || web3.Keypair;
  const ephemeral = Keypair.generate();
  const ephemeralAddress = ephemeral.publicKey.toBase58();
  log(`booted with a fresh ephemeral identity ${ephemeralAddress} (never funded, generated this run)`);
  log(`reporting on treasury ${treasuryAddress} (public address — not a secret)`);

  // Step 2: restore state — Franklin's REAL public job history, no credential.
  const jobs = await fetchJobsForPayer({ fetchImpl, posterAddress: treasuryAddress });
  const nowTs = now() / 1000;
  const activeJob = selectActiveJob(jobs, { nowTs });
  const mostRecentJob = selectMostRecentJob(jobs);
  if (activeJob) {
    log(`restored state: active job ${activeJob.address} (price ${activeJob.price} raw NOS/sec)`);
  } else if (mostRecentJob) {
    log(`restored state: no alive job — most recent on record is ${mostRecentJob.address} (state ${mostRecentJob.state})`);
  } else {
    log("restored state: no job on record for this wallet at all");
  }

  // Step 3: the economic proof — real balances + a runway recomputation using the SAME code
  // ../renew/executor.mjs runs on the Mac, then a signature bound to a live blockhash.
  const connection = connectionFactory ? connectionFactory(rpcUrl) : new web3.Connection(rpcUrl, "confirmed");
  const treasurySolLamports = await connection.getBalance(new PublicKey(treasuryAddress));
  const treasuryNosBalance = await readNosBalance({ connection, address: treasuryAddress, PublicKeyCtor: PublicKey });
  const { blockhash } = await connection.getLatestBlockhash();
  log(`treasury balances: ${(treasurySolLamports / 1_000_000_000).toFixed(9)} SOL, ${treasuryNosBalance} NOS`);

  const { nosPerHour, rateSource } = await resolveNosPerHour({ activeJob, mostRecentJob, fetchImpl, nosUsdPriceFetchImpl });
  let runwayHours = null;
  if (nosPerHour !== null) {
    runwayHours = computeRunwayHours({ nosBalance: treasuryNosBalance, nosPerHour });
    const runway = formatRunway(runwayHours);
    log(
      `survival drive (reusing the literal ../renew/survival-drive.mjs): runway ${runway.days}d ${runway.hours.toFixed(1)}h ` +
        `at ${nosPerHour.toFixed(6)} NOS/hr — rate source: ${rateSource}`,
    );
  } else {
    log(`survival drive: rate unavailable (${rateSource}) — runway not computed, reported honestly as null`);
  }

  const ts = now() / 1000;
  const message = buildChallengeMessage({
    ephemeralAddress,
    blockhash,
    treasuryAddress,
    treasurySolLamports,
    treasuryNosBalance,
    nosPerHour,
    runwayHours,
    rateSource,
    ts,
  });
  const signatureBytes = await signChallenge({ message, secretKeyBytes: ephemeral.secretKey, signImpl });
  const bs58 = (await import("bs58")).default;
  const signatureBase58 = bs58.encode(signatureBytes);
  log(`signed proof-of-life challenge over live blockhash ${blockhash} with the ephemeral key`);
  log(`signature: ${signatureBase58}`);

  // Step 4: report. No step 5 — nothing is written anywhere; this container carries no credential
  // to write with, by design (see this file's header).
  const report = {
    ephemeralAddress,
    treasuryAddress,
    blockhash,
    treasurySolLamports,
    treasuryNosBalance,
    activeJobAddress: activeJob ? activeJob.address : null,
    mostRecentJobAddress: mostRecentJob ? mostRecentJob.address : null,
    nosPerHour,
    runwayHours,
    rateSource,
    message,
    signature: signatureBase58,
    ts,
  };
  process.stdout.write(`TENANT_REPORT_JSON=${JSON.stringify(report)}\n`);
  return report;
}

// --- CLI entrypoint: when run directly (`node entrypoint.bundle.mjs` inside the job), execute
// the real flow with real defaults and set a real exit code. Guarded so this file (and its
// bundled form) is also plainly importable by tests without side effects.
//
// REGRESSION (found live 2026-07-25 while testing the bundled artifact standalone): a plain
// `path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)` comparison silently NEVER
// matches when the invoking path passes through a symlink Node's own module loader resolves but
// `path.resolve` does not — e.g. macOS's `/var` -> `/private/var` (and `/tmp` -> `/private/tmp`):
// `process.argv[1]` stayed `/var/folders/.../entrypoint.bundle.mjs` while `import.meta.url` was
// `file:///private/var/folders/.../entrypoint.bundle.mjs`. The guard's `if` block then never runs
// at all — the script loads, defines everything, and exits 0 with NO output and NO error,
// which would have looked exactly like a silently-broken job if it had first been discovered
// inside an actual Nosana container rather than in a standalone dry test. Fixed by realpath'ing
// argv[1] the same way Node's loader resolves the entry module, with a fallback to the original
// plain comparison if realpath itself fails for any reason (never let a resolution error alone
// suppress the CLI path).
if (process.argv[1]) {
  const { fileURLToPath } = await import("node:url");
  const path = await import("node:path");
  const fs = await import("node:fs");
  const thisFile = fileURLToPath(import.meta.url);
  let isEntry = path.resolve(process.argv[1]) === thisFile;
  if (!isEntry) {
    try {
      isEntry = fs.realpathSync(process.argv[1]) === thisFile;
    } catch {
      // argv[1] doesn't exist on disk (unusual) — fall back to the plain comparison's result above.
    }
  }
  if (isEntry) {
    try {
      await runTenantIncarnation();
      process.exit(0);
    } catch (err) {
      process.stderr.write(`tenant-entrypoint: ${(err && err.message) || err}\n`);
      process.exit(1);
    }
  }
}
