// deploy.mjs — orchestrates a real Nosana job deploy paid for by Franklin's own Solana wallet
// (wallet rail only; spec hard constraint 1). `deployNosanaJob` is the importable/testable
// business-logic core: every I/O boundary (network fetch, RPC connection, CLI shell-out, clock)
// is an injected parameter with a real default, so the decision logic can be exercised without
// hitting the network or spawning a process. `bin/citizen-up` is the thin CLI entrypoint that
// calls this with the real defaults.
//
// `--dry` is the default (spec hard constraint 4): every step below runs — identity, market
// pricing, job-definition build+validate, the spend gate, keypair materialization — and the
// function returns BEFORE the on-chain post. Only `live: true` posts for real.

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { ensureNosanaKeypair } from "./keypair.mjs";
import { fetchMarkets, selectCheapestMarket, estimateJobCost, fetchNosUsdPriceLive, NOS_MINT } from "./market.mjs";
import { buildServiceJobDefinition, validateJobDefinition } from "./job-definition.mjs";
import { evaluateSpendGate, DEFAULT_MAX_SPEND_USD, DEFAULT_SOL_FEE_FLOOR } from "./spend-gate.mjs";
import { readShelterCostEntriesResolved, appendShelterCostEntry } from "../../spawn/lib/shelter-cost-ledger.js";
import { appendChild } from "../../spawn/lib/ledger.js";
import { resolveStateDir } from "../../spawn/lib/state-path.js";

export const DEFAULT_IMAGE = "docker.io/library/nginx:alpine";
export const DEFAULT_EXPOSE_PORT = 80;
export const DEFAULT_DURATION_MINUTES = 15;
export const DEFAULT_RPC_URL = "https://api.mainnet-beta.solana.com";
// Nosana's own public jobs API — no auth, same indexer backend the CLI itself reads. Verified live
// 2026-07-25: GET {base}/<address> returns one job object; GET {base}?payer=<wallet> returns
// {jobs: [...], totalJobs} filtered to that wallet's jobs. See reconcileNosanaJobViaApi below —
// this is the authoritative source that replaced CLI-stdout parsing after a real incident.
export const NOSANA_JOBS_API_BASE_URL = "https://dashboard.k8s.prd.nos.ci/api/jobs";

// Credits/API-key auth is a FORBIDDEN rail here (spec hard constraint 1): Nosana credits are
// Stripe/human-funded, which defeats the entire point of Franklin paying with its own wallet.
// If present, this executor must refuse to use it and log that it is deliberately ignoring it —
// never silently pass it through to the CLI's own `--api` flag.
const CREDITS_ENV_VARS = ["NOSANA_API_KEY", "NOS_API_KEY"];

function log(line) {
  // Every call site below passes a static or numeric-only string — never secret-derived data.
  process.stdout.write(`[citizen-up] ${line}\n`);
}

function refuseCreditsRailIfPresent(env) {
  for (const name of CREDITS_ENV_VARS) {
    if (env[name]) {
      log(`refusing the Nosana credits rail: ${name} is set but this executor pays ONLY from Franklin's own Solana wallet (constraint 1) — deliberately ignoring ${name}, never passing it as --api.`);
    }
  }
}

async function readSolBalanceSol({ connection, address, PublicKeyCtor }) {
  const lamports = await connection.getBalance(new PublicKeyCtor(address));
  return lamports / 1_000_000_000;
}

async function readNosBalance({ connection, address, PublicKeyCtor }) {
  const resp = await connection.getParsedTokenAccountsByOwner(new PublicKeyCtor(address), {
    mint: new PublicKeyCtor(NOS_MINT),
  });
  if (!resp || !Array.isArray(resp.value) || resp.value.length === 0) return 0;
  const amount = resp.value[0].account.data.parsed.info.tokenAmount.uiAmount;
  return typeof amount === "number" ? amount : 0;
}

/**
 * Best-effort, non-authoritative extraction of a job address from `nosana job post`'s stdout.
 * The exact --format json shape for the posted job's address was NOT verified against a real
 * post in this session (spec forbids running --live) — deploy.mjs never trusts this alone; it
 * always cross-checks via `reconcileNosanaJob` (real `job list` read) before finalizing a
 * ledger record. Pure/testable given a stdout string.
 */
export function parseJobAddressFromPostOutput(stdout) {
  if (typeof stdout !== "string" || stdout.length === 0) return null;
  try {
    const parsed = JSON.parse(stdout);
    const candidate = parsed && (parsed.job || parsed.jobAddress || parsed.address || (parsed.job_posting && parsed.job_posting.job));
    if (typeof candidate === "string" && candidate.length > 0) return candidate;
  } catch {
    // stdout wasn't (pure) JSON — fall through to the base58-pubkey-shaped regex heuristic below.
  }
  const match = stdout.match(/\b[1-9A-HJ-NP-Za-km-z]{32,44}\b/);
  return match ? match[0] : null;
}

/**
 * SUPERSEDED for the live path by reconcileNosanaJobViaApi below — kept defined (not deleted) as a
 * documented record of what was tried and exactly why it is unreliable for headless execFileSync
 * invocation. Two real bugs were found here via a real --live run + a live repro (2026-07-25):
 *
 *   Bug 1: `nosana job get` (and `job post`'s own post-post display step, which calls the same
 *   internal `getJob()`) crashes non-interactively: `TypeError: process.stdout.moveCursor is not
 *   a function` at `@nosana/cli/dist/src/generic/utils.js:44` (`clearLine`) — it calls a
 *   TTY-spinner API that does not exist on piped stdout. `job list` (used here) does NOT hit this
 *   specific crash (confirmed live: exit 0), but:
 *
 *   Bug 2: `job list --format json`'s stdout is NOT clean JSON even on success. A real invocation
 *   printed an "Using default solana RPC..." warning banner BEFORE the JSON array, and a
 *   `{"keypair_path":...,"wallet":"<address>","balances":{...}}` summary object AFTER it — so
 *   `JSON.parse(stdout)` below throws (SyntaxError) on the real compound output, silently
 *   returning null every time. That silent null is what let a live run fall through to the
 *   regex-guessed address from `job post`'s own (also-unreliable) stdout, which is how a payer
 *   wallet address once ended up recorded as a `jobAddress` in the settled-cost ledger.
 *
 * Neither bug is something this executor can fix upstream in @nosana/cli — reconcileNosanaJobViaApi
 * sidesteps both by never parsing CLI stdout for this at all.
 */
export function reconcileNosanaJob({
  execFileImpl = execFileSync,
  keypairPath,
  posterAddress,
  marketAddress,
  afterTs,
  network = "mainnet",
}) {
  const args = [
    "job", "list",
    "--poster", posterAddress,
    "--wallet", keypairPath,
    "--network", network,
    "--format", "json",
  ];
  if (marketAddress) args.push("--market", marketAddress);
  if (afterTs != null) args.push("--time-start", String(Math.floor(afterTs)));
  let stdout;
  try {
    stdout = execFileImpl("nosana", args, { encoding: "utf8" });
  } catch {
    return null; // reconciliation itself failed — caller must treat as "still unknown", never retry-post.
  }
  let jobs;
  try {
    jobs = JSON.parse(stdout);
  } catch {
    return null;
  }
  if (!Array.isArray(jobs) || jobs.length === 0) return null;
  return jobs.reduce((newest, j) => (!newest || Number(j.timeStart || 0) > Number(newest.timeStart || 0) ? j : newest), null);
}

/**
 * At-most-once reconciliation (spec hard constraint 5), AUTHORITATIVE version — the one actually
 * used by deployNosanaJob's live path. Reads Nosana's own public jobs API instead of parsing any
 * CLI stdout (see reconcileNosanaJob's doc comment for the two real bugs this replaces). Verified
 * live 2026-07-25 against a real posted job: `GET {NOSANA_JOBS_API_BASE_URL}?payer=<address>`
 * returns `{jobs: [...], totalJobs}`, each job carrying `address`/`market`/`payer`/`project`/
 * `state`/`timeStart` — exactly the CLI's own field names, same indexer backend, no auth needed.
 * Picks the eligible job (matching marketAddress/afterTs, when given) with the highest `timeStart`.
 * Never throws — any fetch/parse/shape failure returns null so the caller treats the outcome as
 * still-unknown rather than ever blind-retrying (constraint 5).
 */
export async function reconcileNosanaJobViaApi({
  fetchImpl = fetch,
  posterAddress,
  marketAddress,
  afterTs,
  apiBaseUrl = NOSANA_JOBS_API_BASE_URL,
}) {
  try {
    const res = await fetchImpl(`${apiBaseUrl}?payer=${posterAddress}`);
    if (!res || !res.ok) return null;
    const data = await res.json();
    const jobs = data && Array.isArray(data.jobs) ? data.jobs : null;
    if (!jobs || jobs.length === 0) return null;
    const eligible = jobs.filter(
      (j) =>
        j &&
        typeof j.address === "string" &&
        j.address.length > 0 &&
        (!marketAddress || j.market === marketAddress) &&
        (afterTs == null || Number(j.timeStart || 0) >= Math.floor(afterTs)),
    );
    if (eligible.length === 0) return null;
    return eligible.reduce(
      (newest, j) => (!newest || Number(j.timeStart || 0) > Number(newest.timeStart || 0) ? j : newest),
      null,
    );
  } catch {
    return null; // fetch/parse failure — still-unknown, never blind-retry (constraint 5).
  }
}

/**
 * Pure: the payer-wallet/job-address confusion caught in a real incident (see
 * reconcileNosanaJob's doc comment) must be structurally impossible to write again. Refuses
 * whenever the candidate jobAddress equals the payer wallet address, regardless of which source
 * produced it — a cheap, source-independent invariant kept as defense in depth even though
 * reconcileNosanaJobViaApi should never produce this in the first place.
 */
export function validateJobAddressIsNotPayer({ jobAddress, payerAddress }) {
  if (typeof jobAddress !== "string" || jobAddress.length === 0) {
    return { valid: false, reason: "jobAddress is missing" };
  }
  if (jobAddress === payerAddress) {
    return {
      valid: false,
      reason: `jobAddress equals the payer wallet address (${payerAddress}) — refusing to record a wallet address as a job address`,
    };
  }
  return { valid: true, reason: "jobAddress is distinct from the payer wallet" };
}

/**
 * The full deploy orchestration. Every I/O dependency has a real default; tests override them.
 *
 * @returns {Promise<object>} a result object describing every decision made, always populated
 *   even when the run stops early (gate refusal or dry mode) — never throws for a REFUSED gate
 *   (that is an expected, successful "decided not to spend" outcome), but DOES throw for
 *   unresolvable identity, no eligible market, an invalid job definition, or a price fetch
 *   failure (all fail-closed per spec hard constraint 3).
 */
export async function deployNosanaJob({
  env = process.env,
  live = false,
  image = env.NOSANA_JOB_IMAGE || DEFAULT_IMAGE,
  exposePort = Number(env.NOSANA_JOB_EXPOSE_PORT || DEFAULT_EXPOSE_PORT),
  durationMinutes = Number(env.NOSANA_JOB_DURATION_MINUTES || DEFAULT_DURATION_MINUTES),
  maxSpendUsd = Number(env.NOSANA_MAX_SPEND_USD || DEFAULT_MAX_SPEND_USD),
  rpcUrl = env.NOSANA_RPC_URL || env.SOLANA_RPC_URL || DEFAULT_RPC_URL,
  network = env.NOSANA_NETWORK || "mainnet",
  fetchImpl = fetch,
  connectionFactory,
  publicKeyCtor,
  execFileImpl = execFileSync,
  now = () => Date.now(),
} = {}) {
  refuseCreditsRailIfPresent(env);

  // Step 1: identity — resolve Franklin's own secret, derive address, materialize keypair file.
  // Never a new wallet (constraint 2); never logs secret material (constraint 6).
  const { address, keypairPath } = ensureNosanaKeypair({ env });
  log(`resolved address ${address}`);
  log(`keypair materialized at ${keypairPath}`);

  // Step 2: live market discovery + selection.
  const markets = await fetchMarkets({ fetchImpl });
  const market = selectCheapestMarket(markets, { requireGpu: true });
  if (!market) {
    throw new Error("deployNosanaJob: no eligible GPU market found — refusing to post (fail-closed)");
  }
  log(`selected market: ${market.name} (${market.address}) @ $${market.usdPerHour}/hr`);

  // Step 3: live NOS/USD price + cost estimate. Throws (fail-closed) on any price-fetch
  // failure — never treats an unknown price as free (constraint 3).
  const nosUsdPrice = await fetchNosUsdPriceLive({});
  const hours = durationMinutes / 60;
  const { usd: costUsd, nos: costNos } = estimateJobCost({ usdPerHour: market.usdPerHour, hours, nosUsdPrice });
  log(`NOS/USD price: $${nosUsdPrice}`);
  log(`estimated cost for ${durationMinutes}min: $${costUsd.toFixed(4)} USD (~${costNos.toFixed(6)} NOS)`);

  // Step 4: build + validate the job definition (pure builder, then our own structural check).
  const jobDefinition = buildServiceJobDefinition({ image, exposePort, gpu: true });
  const structuralValidation = validateJobDefinition(jobDefinition);
  if (!structuralValidation.valid) {
    throw new Error(`deployNosanaJob: built an invalid job definition: ${structuralValidation.errors.join("; ")}`);
  }
  log(`job definition built + structurally valid (image=${image}, expose=${exposePort})`);

  // Step 5: live balances + the combined spend gate (caps + balance sufficiency).
  const Connection = connectionFactory ? null : (await import("@solana/web3.js")).Connection;
  const PublicKey = publicKeyCtor || (await import("@solana/web3.js")).PublicKey;
  const connection = connectionFactory ? connectionFactory(rpcUrl) : new Connection(rpcUrl, "confirmed");
  const solBalance = await readSolBalanceSol({ connection, address, PublicKeyCtor: PublicKey });
  const nosBalance = await readNosBalance({ connection, address, PublicKeyCtor: PublicKey });
  log(`balances: ${solBalance} SOL, ${nosBalance} NOS`);

  const stateDir = resolveStateDir({ env });
  const shelterCostFile = path.join(stateDir, "shelter-cost.jsonl");
  // Resolved (correction-aware) view — a real incident once wrote a wrong jobAddress into this
  // ledger; readShelterCostEntriesResolved is what applies any later correction row before this
  // history feeds the cap-checking gate (see shelter-cost-ledger.js's doc comment).
  const priorEntries = readShelterCostEntriesResolved(shelterCostFile);
  const history = priorEntries.map((r) => ({
    ts: r.ts,
    amountUsd: r.settledLeaseCostUsd,
    status: "sent",
    txHash: r.jobAddress || `no-address-${r.ts}`,
  }));
  const nowTs = now() / 1000;
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

  const result = {
    address,
    keypairPath,
    market,
    nosUsdPrice,
    costUsd,
    costNos,
    durationMinutes,
    jobDefinition,
    solBalance,
    nosBalance,
    gate,
    posted: false,
  };

  // Dry mode ALWAYS stops here, before any on-chain action — but the wording must stay honest
  // to the real gate verdict computed above from real balances. It would be dishonest to print
  // "would post" when the real gate just refused (e.g. insufficient real NOS balance); this
  // still satisfies constraint 4 ("stop before posting, printing exactly what it would spend")
  // by always emitting a "(dry)" line, whichever branch is true.
  if (!live) {
    if (gate.allowed) {
      log(`gate ALLOWED — would post now, spending ~${costNos.toFixed(6)} NOS (~$${costUsd.toFixed(4)}) on market ${market.address}. Stopping before on-chain post (dry).`);
    } else {
      log(`gate REFUSED (${gate.reason}) — would NOT post even outside dry mode. Stopping before on-chain post (dry).`);
    }
    return result;
  }

  if (!gate.allowed) {
    log("refusing to post: spend gate denied the job.");
    return result;
  }

  // ---- Everything below this line only runs with --live. ----

  // Step 6: at-most-once — write the intent record BEFORE posting (constraint 5).
  const intentFile = path.join(stateDir, "nosana-deploy-intents.jsonl");
  const intentId = `${Math.floor(nowTs)}-${market.address}`;
  appendChild(intentFile, {
    ts: nowTs,
    intentId,
    status: "intent",
    address,
    market: market.address,
    costUsd,
    costNos,
    durationMinutes,
  });

  const jobDefFile = path.join(stateDir, `nosana-job-${intentId}.json`);
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(jobDefFile, JSON.stringify(jobDefinition, null, 2));

  // Step 7: authoritative CLI validation as a second, non-unit-testable check before spending.
  try {
    execFileImpl("nosana", ["job", "validate", jobDefFile], { encoding: "utf8" });
  } catch (err) {
    appendChild(intentFile, { ts: now() / 1000, intentId, status: "validate-failed", errorMessage: String((err && err.message) || err) });
    throw new Error(`deployNosanaJob: nosana job validate rejected the built job definition for intent ${intentId} — refusing to post`);
  }

  // Step 8: shell out to the real nosana CLI to post. NEVER pass --api (constraint 1).
  let stdout = null;
  let postError = null;
  try {
    stdout = execFileImpl(
      "nosana",
      [
        "job", "post",
        "--market", market.address,
        "--wallet", keypairPath,
        "--file", jobDefFile,
        "--timeout", String(durationMinutes),
        "--network", network,
        "--format", "json",
      ],
      { encoding: "utf8" },
    );
  } catch (err) {
    postError = err;
  }

  // Step 9: at-most-once reconciliation — the outcome of the post above (success OR failure) is
  // never fully trusted from stdout/exit-code alone; always cross-check real job state before
  // deciding what happened (constraint 5: never blind-retry on an unknown outcome).
  //
  // A real incident (see reconcileNosanaJob's doc comment) showed the CLI's own stdout — both
  // `job post`'s and `job list`'s — is unreliable for this: `job post`'s regex-guessed address is
  // NEVER trusted as the final recorded jobAddress any more (logged only, as a debugging hint).
  // The authoritative source is Nosana's own public jobs API (reconcileNosanaJobViaApi).
  const guessedAddress = stdout ? parseJobAddressFromPostOutput(stdout) : null;
  if (guessedAddress) {
    log(`post-output parse produced a candidate address ${guessedAddress} (NEVER trusted alone — known-fragile CLI stdout); cross-checking via the authoritative jobs API.`);
  }
  const reconciled = await reconcileNosanaJobViaApi({
    fetchImpl,
    posterAddress: address,
    marketAddress: market.address,
    afterTs: Math.floor(nowTs) - 5,
  });
  const candidateAddress = (reconciled && reconciled.address) || null;
  const addressValidation = candidateAddress
    ? validateJobAddressIsNotPayer({ jobAddress: candidateAddress, payerAddress: address })
    : { valid: false, reason: "no address confirmed via the authoritative jobs API" };

  if (!addressValidation.valid) {
    appendChild(intentFile, {
      ts: now() / 1000,
      intentId,
      status: "post-unknown",
      guessedAddress,
      errorMessage: postError ? String(postError.message || postError) : addressValidation.reason,
    });
    throw new Error(
      `deployNosanaJob: outcome of intent ${intentId} is UNKNOWN (${addressValidation.reason}) — reconcile manually via ` +
        `${NOSANA_JOBS_API_BASE_URL}?payer=${address} before any retry. Never blind-retrying.` +
        (guessedAddress ? ` (stdout parsing suggested ${guessedAddress}, but that is never trusted alone.)` : ""),
    );
  }
  const jobAddress = candidateAddress;

  appendChild(intentFile, { ts: now() / 1000, intentId, status: "posted", jobAddress });
  appendShelterCostEntry(shelterCostFile, { ts: now() / 1000, settledLeaseCostUsd: costUsd, jobAddress });
  log(`posted job ${jobAddress} — settled cost $${costUsd.toFixed(4)} recorded to ${shelterCostFile}`);

  result.posted = true;
  result.jobAddress = jobAddress;
  result.intentId = intentId;
  return result;
}
