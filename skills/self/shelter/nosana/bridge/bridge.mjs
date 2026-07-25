// bridge.mjs — S10: move the colony's idle USDC from Base to Solana via CCTP V2 Standard
// Transfer, so the shelter wallet's runway stops being measured in hours. Orchestrates every pure
// module in this directory with REAL reads (mirrors ../funding/acquire-nos.mjs's and
// ../treasury/check.mjs's own shape: real identity, real balances, real gas price, real ETH/USD
// price — every I/O dependency injectable for tests).
//
// SCOPE / KNOWN GAP (read before assuming this completes a transfer end-to-end): CCTP requires an
// explicit destination-side "finalize" call (fetch Circle's attestation for the burn, then submit
// it to Solana's CCTP program to mint) — this call is PUBLIC/permissionless (anyone holding the
// attestation may submit it) but is NOT automatically performed by anyone unless something submits
// it. This build does NOT submit that call: implementing it correctly requires hand-deriving
// several Anchor PDAs against Circle's Solana CCTP program, which could not be verified live in
// this session (this repo's own convention, per ../deploy.mjs's README "Known gap" section, is to
// ship the value-additive, fully-testable part and flag the single highest-risk gap honestly
// rather than ship unverifiable guesswork). What this build DOES do, safely and completely:
//   1. Burns real USDC on Base via TokenMessengerV2#depositForBurn (the irreversible spend this
//      colony's own founder wallet controls), with full at-most-once discipline.
//   2. Polls the real Solana USDC balance at the destination for the credit (spec: "poll for the
//      destination-side credit... never re-send").
// A `--live` run will very likely end in `awaiting-credit` (the burn succeeded on Base; the mint
// has not happened yet because nothing has submitted the finalize call) — this is reported
// honestly, not silently treated as failure or success. The follow-up (a future S11) is to
// automate the finalize call, or to complete it once manually via the attestation this burn's tx
// hash makes available at https://iris-api.circle.com/v2/messages/6?transactionHash=<burnTxHash>.
//
// --dry (DEFAULT): resolves identity, reads real balances/gas price/prices, computes the
// worth-it verdict and the spend gate, then stops before any signing. --live additionally signs
// and sends IF AND ONLY IF both the worth-it verdict and the spend gate allow it.

import path from "node:path";
import { resolveBridgeIdentity } from "./identity.mjs";
import { evaluateBridgeQuote, DEFAULT_MAX_COST_FRACTION } from "./quote.mjs";
import { evaluateBridgeGate, DEFAULT_MAX_BRIDGE_USD } from "./spend-gate.mjs";
import {
  encodeErc20Approve,
  encodeErc20AllowanceCall,
  decodeAllowanceResult,
  encodeDepositForBurn,
  usdcToBaseUnits,
} from "./cctp.mjs";
import { BASE_USDC, TOKEN_MESSENGER_V2_BASE, SOLANA_DOMAIN } from "./constants.mjs";
import {
  DEFAULT_BASE_RPC_URL,
  getGasPriceWei,
  getEthBalanceWei,
  getTransactionCount,
  getChainId,
  ethCall,
  sendRawTransaction,
  getTransactionReceipt,
} from "./base-rpc.mjs";
import { fetchEthUsdPrice } from "./eth-price.mjs";
import { getSolanaUsdcBalance } from "./solana-balance.mjs";
import { signBaseTransaction } from "./sign.mjs";
import { pollForBaseReceipt, reconcileUnknownBurnOutcome, pollForDestinationCredit } from "./reconcile.mjs";
import { usdcBalance } from "../../../../earn/lib/usdc.mjs";
import { appendChild, readChildren } from "../../../spawn/lib/ledger.js";
import { resolveStateDir } from "../../../spawn/lib/state-path.js";

export const DEFAULT_BRIDGE_AMOUNT_USDC = 10;

// Real measured 2026-07-25 via eth_estimateGas against Base mainnet for a standard ERC-20
// approve(spender, 10 USDC) call from the founder wallet: result 0xdbb0 = 56,240 gas. +~20% margin.
export const DEFAULT_APPROVE_GAS_UNITS = 68000n;

// depositForBurn could not be measured with a clean, unwrapped eth_estimateGas call in this
// session: every real recent Base depositForBurn-emitting transaction found via eth_getLogs (383
// real events scanned) was routed through a third-party router/aggregator/ERC-4337 EntryPoint,
// which inflates gas beyond a raw direct call — see this feature's report. Bounded instead by a
// REAL measured comparable: a receiveMessage-shaped call (the destination-side leg, which
// ADDITIONALLY verifies a Circle attestation signature and mints — strictly more work than a plain
// burn) used 171,252 gas in a real Base transaction (0xd68b069a7c98481e07c190c0edabe4e624195e0d873cae3d879c577f34938fa2).
// depositForBurn does less work, so is expected to cost less; 220,000 is a deliberately
// conservative round-up. Overridable via NOSANA_BRIDGE_BURN_GAS_UNITS.
export const DEFAULT_BURN_GAS_UNITS = 220000n;

// This build submits no Solana-side transaction (see the file header's known gap) — the poll for
// the destination credit is a read, not a paid action, so the real Solana-side cost is $0 here.
export const DEFAULT_SOLANA_GAS_USD = 0;

function log(line) {
  // Every call site below passes a static/numeric/public-address string — NEVER secret material.
  process.stdout.write(`[citizen-bridge] ${line}\n`);
}

/**
 * Pure: resolve how much USDC to actually bridge — the smaller of the requested amount, the real
 * available balance, and the explicit cap. Never returns a negative amount even with a zero
 * balance. Mirrors ../funding/acquire-nos.mjs's resolveSpendLamports clamp-not-refuse shape.
 */
export function resolveBridgeAmount({ requestedUsdc, availableUsdc, capUsdc }) {
  if (typeof requestedUsdc !== "number" || !Number.isFinite(requestedUsdc) || requestedUsdc <= 0) {
    throw new Error("resolveBridgeAmount: requestedUsdc must be a positive finite number");
  }
  if (typeof availableUsdc !== "number" || !Number.isFinite(availableUsdc) || availableUsdc < 0) {
    throw new Error("resolveBridgeAmount: availableUsdc must be a non-negative finite number");
  }
  if (typeof capUsdc !== "number" || !Number.isFinite(capUsdc) || capUsdc <= 0) {
    throw new Error("resolveBridgeAmount: capUsdc must be a positive finite number");
  }
  const amountUsdc = Math.max(Math.min(requestedUsdc, availableUsdc, capUsdc), 0);
  return { amountUsdc, hardCapApplied: amountUsdc < requestedUsdc };
}

// ---------------------------------------------------------------------------------------------
// Pure: ledger record shaping — kept out of inline object literals so a test can assert no record
// ever contains secret material, mirrors ../funding/acquire-nos.mjs's
// buildFundingIntentRecord/buildFundingSettledRecord convention exactly.
// ---------------------------------------------------------------------------------------------

export function buildBridgeIntentRecord({ ts, intentId, kind, address, txHash, amountUsdc, destination }) {
  return { ts, intentId, status: "intent", kind, address, txHash, amountUsdc, destination };
}

export function buildBridgeSettledRecord({ ts, intentId, evmAddress, solanaAddress, burnTxHash, amountUsdc, outcome }) {
  return { ts, intentId, status: "settled", evmAddress, solanaAddress, burnTxHash, amountUsdc, outcome };
}

/**
 * The full bridge orchestration. Every I/O dependency has a real default; tests override them.
 * Never throws for a REFUSED verdict/gate or dry mode (expected, successful "decided not to
 * bridge yet" outcomes) — DOES throw for unresolvable identity, an unfetchable gas/ETH price, or
 * an unresolved-after-reconciliation burn outcome (fail-closed).
 *
 * @returns {Promise<object>}
 */
export async function bridgeToSolana({
  env = process.env,
  live = false,
  amountUsdc = Number(env.NOSANA_BRIDGE_AMOUNT_USDC || DEFAULT_BRIDGE_AMOUNT_USDC),
  evmHome = env.NOSANA_BRIDGE_EVM_HOME || env.ANICCA_HOME,
  solanaHome = env.NOSANA_BRIDGE_SOLANA_HOME,
  maxBridgeUsd = Number(env.NOSANA_BRIDGE_MAX_USD || DEFAULT_MAX_BRIDGE_USD),
  maxCostFraction = Number(env.NOSANA_BRIDGE_MAX_COST_FRACTION || DEFAULT_MAX_COST_FRACTION),
  rpcUrl = env.BASE_RPC_URL || DEFAULT_BASE_RPC_URL,
  solanaRpcUrl = env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com",
  fetchImpl = fetch,
  connectionFactory,
  publicKeyCtor,
  now = () => Date.now(),
  sleepImpl = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  approveGasUnits = BigInt(env.NOSANA_BRIDGE_APPROVE_GAS_UNITS || DEFAULT_APPROVE_GAS_UNITS),
  burnGasUnits = BigInt(env.NOSANA_BRIDGE_BURN_GAS_UNITS || DEFAULT_BURN_GAS_UNITS),
  destinationPollTimeoutMs,
} = {}) {
  // Step 1: identity. Never a new wallet; never logs secret material.
  const { evmAddress, evmPrivateKey, solanaAddress } = resolveBridgeIdentity({ env, evmHome, solanaHome });
  log(`Base source: ${evmAddress}`);
  log(`Solana destination: ${solanaAddress}`);

  // Step 2: real balances + real gas price + real ETH/USD price. Fail closed on any of these —
  // never flow a fabricated number into the worth-it verdict or the spend gate.
  const usdcAvailable = await usdcBalance(evmAddress, { fetchImpl, rpc: rpcUrl });
  const ethBalanceWei = await getEthBalanceWei({ address: evmAddress, fetchImpl, rpcUrl });
  const gasPriceWei = await getGasPriceWei({ fetchImpl, rpcUrl });
  const ethUsdPrice = await fetchEthUsdPrice({ fetchImpl });
  log(
    `Base balances: ${usdcAvailable} USDC, ${ethBalanceWei} wei ETH; gas price ${gasPriceWei} wei/gas; ETH/USD $${ethUsdPrice}`,
  );

  // Step 3: resolve the real amount to bridge (clamp to available balance and the explicit cap).
  const { amountUsdc: resolvedAmountUsdc, hardCapApplied } = resolveBridgeAmount({
    requestedUsdc: amountUsdc,
    availableUsdc: usdcAvailable,
    capUsdc: maxBridgeUsd,
  });
  log(`bridge amount resolved: $${resolvedAmountUsdc}${hardCapApplied ? " (clamped below the requested amount)" : ""}`);

  let quote = null;
  let gate = null;
  let needsApprove = false;
  let amountBaseUnits = 0n;
  let gasCostWeiEstimate = 0n;

  if (resolvedAmountUsdc <= 0) {
    quote = { worthIt: false, netReceivedUsdc: null, costUsd: null, costFraction: null, reason: "resolved bridge amount is $0 — nothing to bridge (balance/cap clamp)" };
    gate = { allowed: false, reason: "resolved bridge amount is $0 — nothing to bridge" };
  } else {
    // Step 4: allowance check — only include the approve tx if the current allowance is insufficient.
    const allowanceHex = await ethCall({
      to: BASE_USDC,
      data: encodeErc20AllowanceCall({ owner: evmAddress, spender: TOKEN_MESSENGER_V2_BASE }),
      fetchImpl,
      rpcUrl,
    });
    const currentAllowance = decodeAllowanceResult(allowanceHex);
    amountBaseUnits = usdcToBaseUnits(resolvedAmountUsdc);
    needsApprove = currentAllowance < amountBaseUnits;
    log(`current TokenMessengerV2 allowance: ${currentAllowance} base units — ${needsApprove ? "approve needed" : "sufficient, will skip approve"}`);

    const effectiveApproveGasUnits = needsApprove ? approveGasUnits : 0n;
    gasCostWeiEstimate = (effectiveApproveGasUnits + burnGasUnits) * gasPriceWei;

    // Step 5: pure cost/worth-it verdict, using REAL numbers throughout.
    quote = evaluateBridgeQuote({
      amountUsdc: resolvedAmountUsdc,
      gasUnitsApprove: effectiveApproveGasUnits,
      gasUnitsBurn: burnGasUnits,
      baseGasPriceWei: Number(gasPriceWei),
      ethUsdPrice,
      bridgeFeeBps: 0, // CCTP Standard Transfer — verified live 2026-07-25, 0 bps on Base and Solana
      solanaGasUsd: DEFAULT_SOLANA_GAS_USD,
      maxCostFraction,
    });
    log(`worth-it verdict: ${quote.worthIt ? "WORTH IT" : "NOT WORTH IT"} — ${quote.reason}`);

    // Step 6: spend gate (caps + ETH-for-future-gas floor).
    const stateDirForHistory = resolveStateDir({ env });
    const ledgerFileForHistory = path.join(stateDirForHistory, "nosana-bridge.jsonl");
    const priorEntries = readChildren(ledgerFileForHistory);
    const history = priorEntries
      .filter((r) => r && r.status === "settled")
      .map((r) => ({ ts: r.ts, amountUsd: r.amountUsdc, status: "sent", txHash: r.burnTxHash || `no-hash-${r.ts}` }));
    const nowTsForGate = now() / 1000;
    gate = evaluateBridgeGate({
      amountUsdc: resolvedAmountUsdc,
      ethBalanceWei,
      gasCostWeiEstimate,
      config: { perBridgeUsdCap: maxBridgeUsd },
      history,
      nowTs: nowTsForGate,
    });
    log(`spend gate: ${gate.allowed ? "ALLOWED" : "REFUSED"} — ${gate.reason}`);
  }

  const result = {
    evmAddress,
    solanaAddress,
    amountUsdc: resolvedAmountUsdc,
    usdcAvailable,
    gasPriceWei: gasPriceWei.toString(),
    ethBalanceWei: ethBalanceWei.toString(),
    ethUsdPrice,
    needsApprove,
    quote,
    gate,
    posted: false,
  };

  // Dry mode ALWAYS stops here, before any signing — but stays honest to the real verdict/gate
  // computed above from real balances/prices.
  if (!live) {
    log(
      quote.worthIt && gate.allowed
        ? `would bridge $${resolvedAmountUsdc} now — stopping before any signing/sending (dry).`
        : "would NOT bridge (see worth-it verdict / spend gate above) — stopping before any signing/sending (dry).",
    );
    return result;
  }
  if (!quote.worthIt) {
    log("refusing to bridge: worth-it verdict says no.");
    return result;
  }
  if (!gate.allowed) {
    log("refusing to bridge: spend gate denied it.");
    return result;
  }

  // ---- Everything below this line only runs with --live. ----

  const web3 = await import("@solana/web3.js");
  const PublicKey = publicKeyCtor || web3.PublicKey;
  const solanaConnection = connectionFactory ? connectionFactory(solanaRpcUrl) : new web3.Connection(solanaRpcUrl, "confirmed");

  const stateDir = resolveStateDir({ env });
  const intentFile = path.join(stateDir, "nosana-bridge-intents.jsonl");
  const ledgerFile = path.join(stateDir, "nosana-bridge.jsonl");
  const nowTs = now() / 1000;

  const chainId = await getChainId({ fetchImpl, rpcUrl });
  let currentNonce = await getTransactionCount({ address: evmAddress, fetchImpl, rpcUrl });
  const maxPriorityFeePerGas = gasPriceWei / 10n > 0n ? gasPriceWei / 10n : 1n;
  const maxFeePerGas = gasPriceWei * 2n + maxPriorityFeePerGas;

  const preSolanaBalance = await getSolanaUsdcBalance({ connection: solanaConnection, address: solanaAddress, PublicKeyCtor: PublicKey });

  const getReceiptImpl = (h) => getTransactionReceipt({ txHash: h, fetchImpl, rpcUrl });

  if (needsApprove) {
    const approveData = encodeErc20Approve({ spender: TOKEN_MESSENGER_V2_BASE, amount: amountBaseUnits });
    const { signedTxHex, txHash: approveTxHash } = await signBaseTransaction({
      privateKey: evmPrivateKey,
      chainId,
      nonce: currentNonce,
      to: BASE_USDC,
      data: approveData,
      gas: approveGasUnits,
      maxFeePerGas,
      maxPriorityFeePerGas,
    });
    const approveIntentId = `${Math.floor(nowTs)}-approve`;
    // At-most-once: write the intent BEFORE sending (the hash is already known — deterministic
    // signing, see sign.mjs's doc comment).
    appendChild(intentFile, buildBridgeIntentRecord({ ts: nowTs, intentId: approveIntentId, kind: "approve", address: evmAddress, txHash: approveTxHash, amountUsdc: resolvedAmountUsdc, destination: null }));
    try {
      await sendRawTransaction({ signedTxHex, fetchImpl, rpcUrl });
    } catch (err) {
      log(`approve send threw — outcome unknown, reconciling via receipt (never blind-retrying): ${err && err.message}`);
    }
    let approveOutcome = await pollForBaseReceipt({ txHash: approveTxHash, getReceiptImpl, sleepImpl, now });
    if (approveOutcome.outcome !== "confirmed" && approveOutcome.outcome !== "failed-onchain") {
      approveOutcome = await reconcileUnknownBurnOutcome({ txHash: approveTxHash, getReceiptImpl });
    }
    if (approveOutcome.outcome !== "confirmed") {
      appendChild(intentFile, { ts: now() / 1000, intentId: approveIntentId, status: "unknown", ...approveOutcome });
      throw new Error(
        `bridgeToSolana: approve tx ${approveTxHash} outcome is ${approveOutcome.outcome} — refusing to proceed to the burn. Never blind-retrying.`,
      );
    }
    appendChild(intentFile, { ts: now() / 1000, intentId: approveIntentId, status: "settled", txHash: approveTxHash });
    log(`approve confirmed: ${approveTxHash}`);
    currentNonce = currentNonce + 1n;
  }

  const burnData = encodeDepositForBurn({
    amount: amountBaseUnits,
    destinationDomain: SOLANA_DOMAIN,
    mintRecipientSolanaAddress: solanaAddress,
    burnToken: BASE_USDC,
  });
  const { signedTxHex: burnSignedHex, txHash: burnTxHash } = await signBaseTransaction({
    privateKey: evmPrivateKey,
    chainId,
    nonce: currentNonce,
    to: TOKEN_MESSENGER_V2_BASE,
    data: burnData,
    gas: burnGasUnits,
    maxFeePerGas,
    maxPriorityFeePerGas,
  });

  const burnIntentId = `${Math.floor(nowTs)}-burn`;
  appendChild(
    intentFile,
    buildBridgeIntentRecord({ ts: nowTs, intentId: burnIntentId, kind: "burn", address: evmAddress, txHash: burnTxHash, amountUsdc: resolvedAmountUsdc, destination: solanaAddress }),
  );

  try {
    await sendRawTransaction({ signedTxHex: burnSignedHex, fetchImpl, rpcUrl });
  } catch (err) {
    log(`burn send threw — outcome unknown, reconciling via receipt (never blind-retrying): ${err && err.message}`);
  }

  let burnOutcome = await pollForBaseReceipt({ txHash: burnTxHash, getReceiptImpl, sleepImpl, now });
  if (burnOutcome.outcome !== "confirmed" && burnOutcome.outcome !== "failed-onchain") {
    burnOutcome = await reconcileUnknownBurnOutcome({ txHash: burnTxHash, getReceiptImpl });
  }

  if (burnOutcome.outcome === "failed-onchain") {
    appendChild(intentFile, { ts: now() / 1000, intentId: burnIntentId, status: "failed-onchain" });
    result.burnTxHash = burnTxHash;
    result.burnOutcome = burnOutcome;
    throw new Error(`bridgeToSolana: burn tx ${burnTxHash} failed on-chain — refusing to retry automatically; inspect and decide manually`);
  }
  if (burnOutcome.outcome !== "confirmed") {
    appendChild(intentFile, { ts: now() / 1000, intentId: burnIntentId, status: "unknown", ...burnOutcome });
    result.burnTxHash = burnTxHash;
    result.burnOutcome = burnOutcome;
    throw new Error(
      `bridgeToSolana: outcome of burn intent ${burnIntentId} (tx ${burnTxHash}) is UNKNOWN — check https://basescan.org/tx/${burnTxHash} manually before any retry. Never blind-retrying.`,
    );
  }

  appendChild(intentFile, { ts: now() / 1000, intentId: burnIntentId, status: "burned", txHash: burnTxHash });
  log(`burn confirmed on Base: ${burnTxHash} — polling Solana for the destination-side credit (this is the normal slow path here, not an error — see the known-gap note in this file's header)`);

  // Poll for the destination-side credit — NEVER re-sends the burn regardless of the outcome here.
  const creditResult = await pollForDestinationCredit({
    getSolanaUsdcBalanceImpl: () => getSolanaUsdcBalance({ connection: solanaConnection, address: solanaAddress, PublicKeyCtor: PublicKey }),
    preBalance: preSolanaBalance,
    minExpectedDelta: resolvedAmountUsdc * 0.99, // Standard Transfer is fee-free; 1% slack for float/rounding
    sleepImpl,
    now,
    ...(destinationPollTimeoutMs != null ? { timeoutMs: destinationPollTimeoutMs } : {}),
  });

  appendChild(
    ledgerFile,
    buildBridgeSettledRecord({ ts: now() / 1000, intentId: burnIntentId, evmAddress, solanaAddress, burnTxHash, amountUsdc: resolvedAmountUsdc, outcome: creditResult.outcome }),
  );

  result.burnTxHash = burnTxHash;
  result.creditResult = creditResult;
  result.posted = true;
  log(
    creditResult.outcome === "credited"
      ? `destination credited: +${creditResult.delta} USDC on Solana`
      : `burn done (${burnTxHash}); destination credit not yet observed — ${creditResult.reason}`,
  );
  return result;
}
