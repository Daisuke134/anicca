// entrypoint.mjs — THE script that actually runs INSIDE a Nosana job container (S7: "the agent
// lives on compute it bought"). job.mjs's bootstrap script fetches this file (and its four
// self-contained siblings: derive-address.mjs, github-contents-store.mjs, report-ledger.mjs,
// proof.mjs) from a pinned commit on the public life-manager repo, `npm install`s the two real npm
// deps it needs (@solana/web3.js, bs58 — tweetnacl comes along as @solana/web3.js's own
// dependency), then runs `node tenant/entrypoint.mjs` with no arguments.
//
// Five things happen here, in order, matching the S7 spec:
//   1. Boots and identifies itself — resolves the tenant keypair FROM ITS OWN ENV (never generates
//      one; never touches Franklin's treasury key, which is never present in this container at
//      all — see tenant/README.md's "Trust boundary").
//   2. Restores state — reads its own prior-incarnation history from the SAME remote store S4
//      already proved works, via a token scoped ONLY to that one repo's contents.
//   3. Does something economically real and verifiable from inside the job — reads its own live
//      on-chain balance, then signs a challenge bound to a blockhash fetched at runtime (see
//      proof.mjs's header for why that is unfakeable from outside the job).
//   4. Snapshots state back — appends this run to the same remote history before exiting.
//   5. Reports — every step above is logged to stdout, which IS readable after the job ends via
//      the jobs API's `jobResult.opStates[0]` diagnostics (verified live 2026-07-25 during the
//      health-check incident investigation — this is the evidence channel this feature relies on,
//      not the exposed HTTP endpoint, which has never once returned 200).
//
// Every I/O boundary is an injected parameter with a real default, matching every other
// orchestration function in this skill (deploy.mjs, acquire-nos.mjs, executor.mjs) — so
// __tests__/entrypoint.test.mjs can exercise the full five-step flow with zero real network calls.

import { resolveTenantSecretForJob } from "./derive-address.mjs";
import { createGithubContentsStore, DEFAULT_STATE_REPO } from "./github-contents-store.mjs";
import { restoreTenantRuns, appendTenantRun, buildTenantRunRecord, TENANT_RUNS_REMOTE_KEY } from "./report-ledger.mjs";
import { buildChallengeMessage, signChallenge } from "./proof.mjs";

// Duplicated from ../market.mjs (a single string constant, not logic) rather than imported, for
// the same self-containment reason documented in derive-address.mjs's header.
const NOS_MINT = "nosXBVoaCTtYdLvKY6Csb4AC8JCdQKKAaWYtx2ZMoo7";
const DEFAULT_RPC_URL = "https://api.mainnet-beta.solana.com";

function log(line) {
  // Every call site below passes a static/numeric/public-address/public-signature string — this
  // file never logs a secret key or anything decoded from one.
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
 * The full in-job incarnation flow. Every I/O dependency has a real default; tests override them.
 * Throws (fail-closed) on an unresolvable identity or a missing state-store token — both are
 * "this job cannot do its one job" conditions, not soft failures. Never fabricates a balance,
 * blockhash, or signature.
 *
 * @returns {Promise<object>} the exact record snapshotted to the remote store, plus context about
 *   what was restored — this same object is also the report printed to stdout.
 */
export async function runTenantIncarnation({
  env = process.env,
  now = () => Date.now(),
  fetchImpl = fetch,
  connectionFactory,
  publicKeyCtor,
  signImpl,
  rpcUrl = env.NOSANA_RPC_URL || env.SOLANA_RPC_URL || DEFAULT_RPC_URL,
  stateRepo = env.NOSANA_STATE_REPO || DEFAULT_STATE_REPO,
  githubApiBaseUrl,
  jobAddress = env.NOSANA_JOB_ADDRESS || null,
} = {}) {
  // Step 1: boot + identify.
  const { address, secretBytes } = resolveTenantSecretForJob({ env });
  log(`booted as tenant address ${address}`);

  // Step 2: restore state from the external store.
  const token = env.NOSANA_STATE_GITHUB_TOKEN;
  if (typeof token !== "string" || token.length === 0) {
    throw new Error("runTenantIncarnation: NOSANA_STATE_GITHUB_TOKEN is not set — cannot reach the state store");
  }
  const store = createGithubContentsStore({
    repo: stateRepo,
    token,
    fetchImpl,
    ...(githubApiBaseUrl ? { apiBaseUrl: githubApiBaseUrl } : {}),
  });
  const restored = await restoreTenantRuns({ store });
  log(`restored state: ${restored.priorRunCount} previous run(s) found at ${TENANT_RUNS_REMOTE_KEY}`);
  if (restored.lastRun) {
    log(
      `previous life: run #${restored.lastRun.runNumber} at ts ${restored.lastRun.ts}, ` +
        `balance was ${restored.lastRun.solLamports} lamports / ${restored.lastRun.nosBalance} NOS`,
    );
  } else {
    log("previous life: none — this is the tenant's first recorded incarnation");
  }

  // Step 3: the economic proof — real balance reads + a signature bound to a blockhash fetched
  // right now (see proof.mjs's header for why that is unfakeable from outside the job).
  const web3 = await import("@solana/web3.js");
  const PublicKey = publicKeyCtor || web3.PublicKey;
  const connection = connectionFactory ? connectionFactory(rpcUrl) : new web3.Connection(rpcUrl, "confirmed");
  const solLamports = await connection.getBalance(new PublicKey(address));
  const nosBalance = await readNosBalance({ connection, address, PublicKeyCtor: PublicKey });
  const { blockhash } = await connection.getLatestBlockhash();
  const ts = now() / 1000;
  const runNumber = restored.priorRunCount + 1;
  log(`balances: ${(solLamports / 1_000_000_000).toFixed(9)} SOL, ${nosBalance} NOS`);

  const message = buildChallengeMessage({ address, blockhash, solLamports, nosBalance, runNumber, ts });
  const signatureBytes = await signChallenge({ message, secretKeyBytes: secretBytes, signImpl });
  const bs58 = (await import("bs58")).default;
  const signatureBase58 = bs58.encode(signatureBytes);
  log(`signed proof-of-custody challenge over live blockhash ${blockhash}`);
  log(`signature: ${signatureBase58}`);

  const x402Attempted = false;
  const x402Reason =
    "not attempted this pass: the tenant wallet was not funded by this executor before this job was posted " +
    "(see tenant/README.md's trust-boundary + 'what was NOT executed' sections) — an x402 payment needs a " +
    "real nonzero balance this run may not have.";
  log(`x402 paid-inference step: SKIPPED — ${x402Reason}`);

  // Step 4: snapshot state back, BEFORE exiting.
  const record = buildTenantRunRecord({
    ts,
    runNumber,
    tenantAddress: address,
    solLamports,
    nosBalance,
    blockhash,
    message,
    signature: signatureBase58,
    x402Attempted,
    x402Reason,
    jobAddress,
  });
  await appendTenantRun({ store, record });
  log(`snapshotted run #${runNumber} back to ${TENANT_RUNS_REMOTE_KEY}`);
  await store.close();

  // Step 5: report. This stdout line is the artifact the outside world reads after the job ends
  // (via jobResult.opStates[0].diagnostics's stdout capture — the exposed HTTP endpoint is NOT
  // relied on, see this file's header).
  const report = { ...record, priorRunCount: restored.priorRunCount, lastRun: restored.lastRun };
  process.stdout.write(`TENANT_REPORT_JSON=${JSON.stringify(report)}\n`);
  return report;
}

// --- CLI entrypoint: when fetched into a job and run directly (`node tenant/entrypoint.mjs`),
// execute the real flow with real defaults and set a real exit code. Guarded (matches
// skills/earn/lib/resolve-identity.mjs's own convention) so this file is also plainly importable
// by tests without side effects.
if (process.argv[1]) {
  const { fileURLToPath } = await import("node:url");
  const path = await import("node:path");
  if (path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
    try {
      await runTenantIncarnation();
      process.exit(0);
    } catch (err) {
      process.stderr.write(`tenant-entrypoint: ${(err && err.message) || err}\n`);
      process.exit(1);
    }
  }
}
