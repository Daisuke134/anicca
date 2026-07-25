// fund-tenant.mjs (Mac-side ONLY — never fetched into a job) — transfers a deliberately tiny
// amount of SOL + NOS from Franklin's TREASURY wallet to the disposable tenant wallet
// (tenant/keypair.mjs), so the in-job proof-of-life (tenant/entrypoint.mjs) has a real, nonzero
// balance to read and (eventually) spend. This is the ONLY file in tenant/ that ever resolves
// Franklin's treasury secret — it must, since only the treasury can authorize spending its own
// funds — and it must NEVER run anywhere but this Mac (see tenant/README.md's "Trust boundary").
//
// Hard caps (spec: "a fraction of a dollar is plenty — the cheapest market is $0.04796/hr"):
// DEFAULT_TENANT_FUND_SOL/DEFAULT_TENANT_FUND_NOS below are already comfortably above what one
// ~15-minute job costs; MAX_TENANT_FUND_SOL/MAX_TENANT_FUND_NOS are absolute ceilings this module
// refuses to exceed regardless of env overrides — mirrors funding/acquire-nos.mjs's unconditional
// 25%-of-balance clamp (resolveSpendLamports), expressed here as a fixed ceiling instead of a
// balance fraction because the whole point is "the blast radius must be a rounding error", not
// "proportional to whatever the treasury happens to hold".
//
// --dry is the default (matches every other bin/citizen-* entrypoint's convention): every step
// below runs for real — identity, real treasury+tenant balances, the combined gate — then the
// function returns BEFORE building or signing any transaction. Only live:true signs and sends.

import { resolveSolanaSecret } from "../../../../earn/lib/resolve-identity.mjs";
import { deriveAddressFromSecret } from "../keypair.mjs";
import { NOS_MINT } from "../market.mjs";
import { NOS_DECIMALS } from "../funding/acquire-nos.mjs";
import { DEFAULT_RPC_URL } from "../deploy.mjs";
import { appendChild } from "../../../spawn/lib/ledger.js";
import { resolveStateDir } from "../../../spawn/lib/state-path.js";

export const LAMPORTS_PER_SOL = 1_000_000_000;
export const DEFAULT_TENANT_FUND_SOL = 0.003;
export const DEFAULT_TENANT_FUND_NOS = 0.2;
export const MAX_TENANT_FUND_SOL = 0.01;
export const MAX_TENANT_FUND_NOS = 0.5;
export const DEFAULT_TREASURY_SOL_FEE_FLOOR = 0.01;

function log(line) {
  // Every call site below passes a static/numeric/public-address string — this module NEVER logs
  // secretBytes, the base58 secret, or anything decoded from it.
  process.stdout.write(`[citizen-tenant-fund] ${line}\n`);
}

/**
 * Pure: the single combined preflight gate fundTenant consults before any spend — absolute hard
 * ceilings (never exceeded regardless of config) AND treasury balance sufficiency (never leaves
 * the treasury below its own fee floor). Fails closed on missing/non-finite numbers.
 *
 * @returns {{allowed: boolean, reason: string}}
 */
export function evaluateTenantFundingGate({
  solToSend,
  nosToSend,
  treasurySolBalance,
  treasuryNosBalance,
  solFeeFloor = DEFAULT_TREASURY_SOL_FEE_FLOOR,
  maxSol = MAX_TENANT_FUND_SOL,
  maxNos = MAX_TENANT_FUND_NOS,
}) {
  for (const [key, value] of Object.entries({ solToSend, nosToSend })) {
    if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
      return { allowed: false, reason: `${key} must be a positive number (fail-closed)` };
    }
  }
  if (solToSend > maxSol) {
    return { allowed: false, reason: `solToSend ${solToSend} exceeds the absolute ceiling ${maxSol} SOL` };
  }
  if (nosToSend > maxNos) {
    return { allowed: false, reason: `nosToSend ${nosToSend} exceeds the absolute ceiling ${maxNos} NOS` };
  }
  if (typeof treasurySolBalance !== "number" || !Number.isFinite(treasurySolBalance)) {
    return { allowed: false, reason: "treasurySolBalance is unavailable (fail-closed)" };
  }
  if (typeof treasuryNosBalance !== "number" || !Number.isFinite(treasuryNosBalance)) {
    return { allowed: false, reason: "treasuryNosBalance is unavailable (fail-closed)" };
  }
  if (treasuryNosBalance < nosToSend) {
    return { allowed: false, reason: `treasury NOS balance ${treasuryNosBalance} is below the ${nosToSend} NOS requested to send` };
  }
  const postSendSol = treasurySolBalance - solToSend;
  if (postSendSol < solFeeFloor) {
    return {
      allowed: false,
      reason: `post-send treasury SOL balance ${postSendSol} would fall below the fee floor ${solFeeFloor}`,
    };
  }
  return { allowed: true, reason: "within absolute ceilings and treasury balance floors" };
}

async function readTreasuryBalances({ connection, address, PublicKeyCtor }) {
  const lamports = await connection.getBalance(new PublicKeyCtor(address));
  const resp = await connection.getParsedTokenAccountsByOwner(new PublicKeyCtor(address), {
    mint: new PublicKeyCtor(NOS_MINT),
  });
  const nos =
    resp && Array.isArray(resp.value) && resp.value.length > 0
      ? resp.value[0].account.data.parsed.info.tokenAmount.uiAmount || 0
      : 0;
  return { solBalance: lamports / LAMPORTS_PER_SOL, nosBalance: nos, lamports };
}

/**
 * The full fund-the-tenant orchestration. Every I/O dependency has a real default; tests override
 * them. Never throws for a REFUSED gate or dry mode (expected, successful "decided not to spend
 * yet" outcomes) — DOES throw for an unresolvable treasury identity or a missing tenantAddress.
 *
 * @param {{env?: object, live?: boolean, tenantAddress: string, solAmount?: number,
 *          nosAmount?: number, rpcUrl?: string, fetchImpl?: Function, connectionFactory?: Function,
 *          publicKeyCtor?: Function, keypairCtor?: Function, splToken?: object,
 *          systemProgramCtor?: Function, transactionCtor?: Function, sendAndConfirmImpl?: Function,
 *          now?: Function}} opts
 */
export async function fundTenant({
  env = process.env,
  live = false,
  tenantAddress,
  solAmount = Number(env.NOSANA_TENANT_FUND_SOL || DEFAULT_TENANT_FUND_SOL),
  nosAmount = Number(env.NOSANA_TENANT_FUND_NOS || DEFAULT_TENANT_FUND_NOS),
  rpcUrl = env.NOSANA_RPC_URL || env.SOLANA_RPC_URL || DEFAULT_RPC_URL,
  connectionFactory,
  publicKeyCtor,
  keypairCtor,
  splToken,
  systemProgramCtor,
  transactionCtor,
  sendAndConfirmImpl,
  now = () => Date.now(),
} = {}) {
  if (typeof tenantAddress !== "string" || tenantAddress.length === 0) {
    throw new Error("fundTenant: tenantAddress is required — run ensureLocalTenantKeypair first");
  }

  // Step 1: identity — the ONLY place in tenant/ that resolves the treasury secret.
  const secret = resolveSolanaSecret({ env });
  if (!secret) {
    throw new Error(
      "fundTenant: no Solana secret resolved for this instance — ANICCA_HOME must point at Franklin's home (e.g. $HOME/.blockrun)",
    );
  }
  const { address: treasuryAddress, secretBytes } = deriveAddressFromSecret(secret);
  log(`treasury address ${treasuryAddress} -> tenant address ${tenantAddress}`);

  const web3 = await import("@solana/web3.js");
  const PublicKey = publicKeyCtor || web3.PublicKey;
  const Keypair = keypairCtor || web3.Keypair;
  const connection = connectionFactory ? connectionFactory(rpcUrl) : new web3.Connection(rpcUrl, "confirmed");

  // Step 2: real balances.
  const { solBalance, nosBalance } = await readTreasuryBalances({ connection, address: treasuryAddress, PublicKeyCtor: PublicKey });
  log(`treasury balances: ${solBalance} SOL, ${nosBalance} NOS`);

  // Step 3: the combined gate.
  const gate = evaluateTenantFundingGate({
    solToSend: solAmount,
    nosToSend: nosAmount,
    treasurySolBalance: solBalance,
    treasuryNosBalance: nosBalance,
  });
  log(`funding gate: ${gate.allowed ? "ALLOWED" : "REFUSED"} — ${gate.reason}`);

  const result = { treasuryAddress, tenantAddress, solAmount, nosAmount, treasurySolBalance: solBalance, treasuryNosBalance: nosBalance, gate, sent: false };

  if (!live) {
    log(
      gate.allowed
        ? `gate ALLOWED — would send ${solAmount} SOL + ${nosAmount} NOS to ${tenantAddress}. Stopping before signing/sending (dry).`
        : `gate REFUSED — would NOT send even outside dry mode. Stopping before signing/sending (dry).`,
    );
    return result;
  }
  if (!gate.allowed) {
    log("refusing to send: funding gate denied it.");
    return result;
  }

  // ---- Everything below this line only runs with --live. ----
  const spl = splToken || (await import("@solana/spl-token"));
  const SystemProgram = systemProgramCtor || web3.SystemProgram;
  const Transaction = transactionCtor || web3.Transaction;
  const sendAndConfirm = sendAndConfirmImpl || web3.sendAndConfirmTransaction;

  const treasuryKeypair = Keypair.fromSecretKey(secretBytes);
  const tenantPubkey = new PublicKey(tenantAddress);
  const treasuryPubkey = new PublicKey(treasuryAddress);
  const nosMintPubkey = new PublicKey(NOS_MINT);

  const treasuryAta = spl.getAssociatedTokenAddressSync(nosMintPubkey, treasuryPubkey);
  const tenantAta = spl.getAssociatedTokenAddressSync(nosMintPubkey, tenantPubkey);
  const tenantAtaInfo = await connection.getAccountInfo(tenantAta);

  const tx = new Transaction();
  tx.add(SystemProgram.transfer({ fromPubkey: treasuryPubkey, toPubkey: tenantPubkey, lamports: Math.floor(solAmount * LAMPORTS_PER_SOL) }));
  if (!tenantAtaInfo) {
    tx.add(spl.createAssociatedTokenAccountInstruction(treasuryPubkey, tenantAta, tenantPubkey, nosMintPubkey));
  }
  const nosRawAmount = BigInt(Math.floor(nosAmount * 10 ** NOS_DECIMALS));
  tx.add(spl.createTransferInstruction(treasuryAta, tenantAta, treasuryPubkey, nosRawAmount));

  const nowTs = now() / 1000;
  const stateDir = resolveStateDir({ env });
  const ledgerFile = `${stateDir}/nosana-tenant-funding.jsonl`;
  appendChild(ledgerFile, { ts: nowTs, status: "intent", treasuryAddress, tenantAddress, solAmount, nosAmount });

  const signature = await sendAndConfirm(connection, tx, [treasuryKeypair]);

  appendChild(ledgerFile, { ts: now() / 1000, status: "settled", treasuryAddress, tenantAddress, solAmount, nosAmount, signature });
  log(`sent ${solAmount} SOL + ${nosAmount} NOS to ${tenantAddress} — signature ${signature}, recorded to ${ledgerFile}`);

  result.sent = true;
  result.signature = signature;
  return result;
}
