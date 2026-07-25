// check.mjs — I/O orchestration for "can Franklin afford to keep its shelter?". Wires together
// every pure module in this directory with REAL reads (mirrors renew/executor.mjs's and
// funding/acquire-nos.mjs's own shape: real identity, real balances, real ledgers, real price —
// every dependency injectable for tests). Never throws for an honestly-computed "insolvent"/
// "unknown" result — DOES throw for unresolvable identity or an unfetchable NOS/USD price (fail-
// closed: a missing price must stop the whole report, not flow a fabricated number through it).
//
// --dry (DEFAULT, matching bin/citizen-up|citizen-fund|citizen-rent|citizen-state's convention):
//   reads everything real, computes the solvency report and the top-up decision, and returns —
//   never calls acquireNos.
// --live: additionally calls acquireNos({live:true}) — reusing that module's OWN full gate
//   (quote/slippage/price-impact/floor checks) unchanged — IF AND ONLY IF the top-up decision says
//   `allowed: true`. Never a second, looser path to a real swap.

import { resolveSolanaSecret } from "../../../../earn/lib/resolve-identity.mjs";
import { deriveAddressFromSecret } from "../keypair.mjs";
import { fetchNosUsdPriceLive } from "../market.mjs";
import { DEFAULT_RPC_URL } from "../deploy.mjs";
import { renewShelter } from "../renew/executor.mjs";
import { acquireNos, LAMPORTS_PER_SOL } from "../funding/acquire-nos.mjs";
import { readShelterCostEntriesResolved } from "../../../spawn/lib/shelter-cost-ledger.js";
import { resolveStateDir } from "../../../spawn/lib/state-path.js";
import { readShelterRevenueEvents, DEFAULT_REVENUE_LEDGER_FILENAME } from "./revenue-events.mjs";
import { buildSelfWalletSet, classifyRevenueRows } from "./self-pay.mjs";
import { defaultLedgerWindow } from "./ledger-window.mjs";
import { buildSolvencyLedger } from "./solvency-ledger.mjs";
import { computeSolvencyReport } from "./solvency-report.mjs";
import { decideShelterTopUp } from "./topup-decision.mjs";
import path from "node:path";

function log(line) {
  // Every call site below passes a static/numeric/public-address string — NEVER secret material.
  process.stdout.write(`[citizen-solvency] ${line}\n`);
}

async function readSolBalanceSol({ connection, address, PublicKeyCtor }) {
  const lamports = await connection.getBalance(new PublicKeyCtor(address));
  return lamports / LAMPORTS_PER_SOL;
}

const NOS_MINT = "nosXBVoaCTtYdLvKY6Csb4AC8JCdQKKAaWYtx2ZMoo7";
async function readNosBalance({ connection, address, PublicKeyCtor }) {
  const resp = await connection.getParsedTokenAccountsByOwner(new PublicKeyCtor(address), { mint: new PublicKeyCtor(NOS_MINT) });
  if (!resp || !Array.isArray(resp.value) || resp.value.length === 0) return 0;
  const amount = resp.value[0].account.data.parsed.info.tokenAmount.uiAmount;
  return typeof amount === "number" ? amount : 0;
}

/**
 * The full solvency check. Every I/O dependency has a real default; tests override them.
 *
 * @param {{
 *   env?: object, live?: boolean, warningHours?: number, criticalHours?: number,
 *   rpcUrl?: string, fetchImpl?: Function, connectionFactory?: Function, publicKeyCtor?: Function,
 *   now?: Function, solanaSelfWallets?: string[], revenueLedgerFile?: string,
 *   fetchNosUsdPriceImpl?: Function, acquireNosImpl?: Function, renewShelterImpl?: Function,
 * }} [opts]
 */
export async function checkShelterSolvency({
  env = process.env,
  live = false,
  warningHours,
  criticalHours,
  rpcUrl = env.NOSANA_RPC_URL || env.SOLANA_RPC_URL || DEFAULT_RPC_URL,
  fetchImpl = fetch,
  connectionFactory,
  publicKeyCtor,
  now = () => Date.now(),
  solanaSelfWallets,
  revenueLedgerFile,
  fetchNosUsdPriceImpl = fetchNosUsdPriceLive,
  acquireNosImpl = acquireNos,
  renewShelterImpl = renewShelter,
} = {}) {
  // Step 1: identity — the SAME secret every earn/spend/renew engine in this repo resolves; never
  // a new wallet; never logs secret material.
  const secret = resolveSolanaSecret({ env });
  if (!secret) {
    throw new Error(
      "checkShelterSolvency: no Solana secret resolved for this instance — ANICCA_HOME must point at Franklin's home (e.g. $HOME/.blockrun)",
    );
  }
  // secretBytes is intentionally not destructured here — this module only ever needs the public
  // address (balance reads, ledger reads), never the secret itself.
  const { address } = deriveAddressFromSecret(secret);
  log(`resolved address ${address}`);

  // Step 2: real balances.
  const web3 = await import("@solana/web3.js");
  const PublicKey = publicKeyCtor || web3.PublicKey;
  const connection = connectionFactory ? connectionFactory(rpcUrl) : new web3.Connection(rpcUrl, "confirmed");
  const solBalance = await readSolBalanceSol({ connection, address, PublicKeyCtor: PublicKey });
  const nosBalance = await readNosBalance({ connection, address, PublicKeyCtor: PublicKey });
  log(`balances: ${solBalance} SOL, ${nosBalance} NOS`);

  // Step 3: real NOS/USD price. Fail closed (throws) on any fetch failure — never flow an
  // optimistic/stale/zero price into the burn-rate math below. Called with no fetchImpl override
  // (mirrors renew/executor.mjs's own `fetchNosUsdPriceImpl({})` call exactly) — fetchNosUsdPriceLive
  // has its OWN default fetchImpl (a Jupiter-specific `{price}` adapter, market.mjs's
  // defaultJupiterNosFetchImpl), a DIFFERENT contract from the plain `fetchImpl(url)` this module's
  // `fetchImpl` param uses elsewhere; forwarding the wrong one here would silently break the price
  // fetch (confirmed live 2026-07-25: it did, until this comment was added).
  const nosUsdPrice = await fetchNosUsdPriceImpl({});
  log(`NOS/USD price: $${nosUsdPrice}`);

  // Step 4: real ledgers. shelter-cost.jsonl via the CORRECTION-AWARE reader (never the raw one —
  // see shelter-burn.mjs's header). shelter-revenue.jsonl honestly reports "no source" when unwired.
  const stateDir = resolveStateDir({ env });
  const shelterCostFile = path.join(stateDir, "shelter-cost.jsonl");
  const costRowsResolved = readShelterCostEntriesResolved(shelterCostFile);
  const revenueFile = revenueLedgerFile || path.join(stateDir, DEFAULT_REVENUE_LEDGER_FILENAME);
  const { rows: revenueRowsRaw, sourceExists: revenueSourceExists } = readShelterRevenueEvents(revenueFile);
  log(
    `ledgers: ${costRowsResolved.length} resolved shelter-cost row(s) from ${shelterCostFile}; ` +
      `${revenueRowsRaw.length} revenue row(s) from ${revenueFile} (source ${revenueSourceExists ? "exists" : "not yet created"})`,
  );

  // Step 5: classify revenue rows (self-pay excluded — INV-7). The wallet's own address is always
  // in the Solana self-wallet set (a self-transfer to itself is never revenue); callers/env may
  // extend this once a real colony-wide Solana self-wallet registry is wired here.
  const extraSelfWallets = (env.NOSANA_TREASURY_SELF_WALLETS || "").split(",").map((s) => s.trim()).filter(Boolean);
  const selfWalletSet = buildSelfWalletSet({ solanaSelfWallets: solanaSelfWallets || [address, ...extraSelfWallets] });
  const revenueRowsClassified = classifyRevenueRows(revenueRowsRaw, selfWalletSet);

  // Step 6: the shared window — anchored to the earliest real event across BOTH ledgers, ending now
  // (see ledger-window.mjs's defaultLedgerWindow for why this beats a fixed "trailing 24h" default).
  const nowTs = now() / 1000;
  const window = defaultLedgerWindow([...costRowsResolved, ...revenueRowsClassified], nowTs);
  const windowStart = window.windowStart ?? nowTs - 1;
  log(`window: ${new Date(windowStart * 1000).toISOString()} .. ${new Date(window.windowEnd * 1000).toISOString()}`);

  // Step 7: the join, the report, the decision — all pure from here.
  const ledger = buildSolvencyLedger({ costRowsResolved, revenueRowsClassified, windowStart, windowEnd: window.windowEnd });
  const solvencyReport = computeSolvencyReport({ ledger, nosBalance, nosUsdPrice, warningHours, criticalHours });
  log(
    `solvency: burn $${ledger.burnUsdPerHour.toFixed(6)}/hr, external revenue $${ledger.revenueUsdPerHour.toFixed(6)}/hr, ` +
      `net $${ledger.netUsdPerHour.toFixed(6)}/hr — ${solvencyReport.survivalSignal.level} (promoteEarning=${solvencyReport.survivalSignal.promoteEarning})`,
  );

  const solBalanceLamports = Math.round(solBalance * LAMPORTS_PER_SOL);
  const topupDecision = decideShelterTopUp({ survivalLevel: solvencyReport.survivalSignal.level, solBalanceLamports });
  log(`top-up decision: ${topupDecision.allowed ? "RECOMMENDED" : "not recommended"} — ${topupDecision.reason}`);

  // Step 8: cross-check against survival-drive.mjs's OWN live number (renewShelter computes it
  // fresh every call, dry or live — this is a second, independent real read, not a re-derivation of
  // the same numbers already computed above; the two burn-rate METHODOLOGIES differ on purpose —
  // see this feature's report for the full comparison).
  let survivalDriveComparison = null;
  try {
    const renewResult = await renewShelterImpl({ env, live: false, rpcUrl, fetchImpl, connectionFactory, publicKeyCtor, now });
    survivalDriveComparison = {
      nosPerHour: renewResult.nosPerHour,
      runwayHours: renewResult.runwayHours,
      runway: renewResult.runway,
      survivalSignal: renewResult.survivalSignal,
      source: "renewShelter (live active-job price, or cheapest-market rate when no active job)",
    };
    log(
      `survival-drive cross-check: ${renewResult.nosPerHour.toFixed(6)} NOS/hr -> runway ${renewResult.runway.days}d ` +
        `${renewResult.runway.hours.toFixed(1)}h (${renewResult.survivalSignal.level})`,
    );
  } catch (err) {
    survivalDriveComparison = { error: (err && err.message) || String(err) };
    log(`survival-drive cross-check failed (non-fatal to this report): ${survivalDriveComparison.error}`);
  }

  const result = {
    address,
    solBalance,
    nosBalance,
    nosUsdPrice,
    ledger,
    solvencyReport,
    topupDecision,
    survivalDriveComparison,
    live,
    topupExecuted: false,
  };

  if (live && topupDecision.allowed) {
    log("--live and top-up recommended: invoking acquireNos (which applies its OWN full spend gate).");
    const topupResult = await acquireNosImpl({ env, live: true, requestedSol: topupDecision.recommendedSpendSol, fetchImpl });
    result.topupExecuted = true;
    result.topupResult = topupResult;
  }

  return result;
}
