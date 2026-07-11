// economy/gig/lib/ensure-gas.mjs — franklin-reputation-gasless G1: gas preflight before an on-chain
// write (register()/giveFeedback(), the only two writes in this skill that spend the CALLER'S OWN
// native ETH — payViaFacilitator (lib/escrow.mjs) is already gasless for the payer via EIP-3009, the
// facilitator's own signer pays that gas). See
// docs/superpowers/specs/2026-07-12-franklin-reputation-gasless-design.md §1 G1 / §4 MONEY-SAFETY.
//
// ★MONEY-SAFETY (spec §4, MUST)★:
//   - testnet: below-threshold balance auto-drips from a configured funder, hard-capped at
//     MAX_DRIP_WEI_PER_OP (0.0005 ETH) PER OP regardless of what a caller requests, and rate-limited to
//     `maxDripsPerDay` drips per address (DEFAULT_MAX_DRIPS_PER_DAY) via an on-disk JSONL log — once the
//     cap is hit, ensureGas refuses (fail-closed), it never queues/retries around the cap.
//   - mainnet: NEVER auto-spends. A below-threshold mainnet balance returns a structured
//     {ok:false, action:"needs_gas", requiredWei} error; the caller (gig.mjs) must treat that as a
//     normal, expected outcome (fail-open at the CALLER's layer — see gig.mjs's recordFeedbackBestEffort)
//     and never itself attempt to seed mainnet gas.
//   - decideGasAction/countRecentDrips are pure (no I/O) — unit-tested directly, no network in the loop.
//
// Chain config mirrors lib/identity.mjs's own independent, self-contained GIG_CHAIN read (same
// documented rationale: "kept as an independent, equally-simple env read here rather than a cross-
// import, so this file stays self-contained" — identity.mjs L35-37).
import { createPublicClient, createWalletClient, http, parseEther } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base, baseSepolia } from "viem/chains";
import fs from "node:fs";
import path from "node:path";

export const GIG_CHAIN = process.env.GIG_CHAIN === "base" ? "base" : "base-sepolia";
const CHAIN_PROFILES = {
  "base-sepolia": { chain: baseSepolia, rpcUrl: "https://sepolia.base.org" },
  base: { chain: base, rpcUrl: "https://mainnet.base.org" },
};
const ACTIVE_CHAIN = CHAIN_PROFILES[GIG_CHAIN];
export const DEFAULT_RPC_URL = process.env.GIG_RPC_URL || ACTIVE_CHAIN.rpcUrl;

// Threshold: enough native ETH left over after a drip/existing balance to comfortably cover one
// register() (≈108,899 gas, WITNESS-RUNBOOK.md §3 live measurement) or one giveFeedback() (same order
// of magnitude) at a generous gas-price safety margin. 0.0001 ETH ≈ $0.18 at $1800/ETH — far above any
// single write's real cost (WITNESS-RUNBOOK.md §3: register() ≈ $0.0012 on mainnet; testnet gas is free
// money, so no such margin math applies there, but the same threshold value keeps behavior uniform).
export const DEFAULT_GAS_THRESHOLD_WEI = parseEther("0.0001");
// ★MONEY-SAFETY hard cap (spec §4 MUST: "1 op あたり ≤ 0.0005 ETH")★ — enforced in ensureGas() below
// regardless of what `dripAmountWei` a caller requests; this constant is the ceiling, never negotiable.
export const MAX_DRIP_WEI_PER_OP = parseEther("0.0005");
export const DEFAULT_DRIP_WEI = MAX_DRIP_WEI_PER_OP;
// ★MONEY-SAFETY (spec §4 MUST: "1 日 ≤ N 回")★ — default N, overridable per-call (never per-env, so a
// caller can't quietly raise it via an env var this module doesn't read).
export const DEFAULT_MAX_DRIPS_PER_DAY = 20;
export const DRIP_WINDOW_MS = 24 * 3600 * 1000;

const DEFAULT_DRIP_LOG_PATH = process.env.GIG_GAS_DRIP_LOG_PATH || new URL("../state/gas-drip-log.jsonl", import.meta.url).pathname;

/**
 * decideGasAction — pure threshold decision, zero I/O. `isMainnet:true` NEVER returns "drip" (spec §4
 * MUST) — a below-threshold mainnet balance is always "needs_gas", the caller's job to surface as a
 * structured, non-fatal error.
 */
export function decideGasAction({ balanceWei, thresholdWei = DEFAULT_GAS_THRESHOLD_WEI, isMainnet }) {
  const balance = BigInt(balanceWei);
  const threshold = BigInt(thresholdWei);
  if (balance >= threshold) return { action: "ok" };
  if (isMainnet) {
    return {
      action: "needs_gas",
      reason: "mainnet gas below threshold -- no auto-spend (money-safety MUST, spec §4)",
      requiredWei: (threshold - balance).toString(),
    };
  }
  return { action: "drip", reason: "testnet gas below threshold -- auto-drip eligible" };
}

/**
 * countRecentDrips — pure bookkeeping (deterministic arithmetic over already-known log rows, same
 * category as lending-gate.mjs's sumRecentGojoGiftsUsd) — how many drips `address` has already received
 * within `windowMs` of `nowMs`. Malformed rows are ignored, never thrown on (fail-safe read of an
 * append-only log some other process may also be writing to).
 */
export function countRecentDrips(dripLogRows, address, nowMs, windowMs = DRIP_WINDOW_MS) {
  const addr = typeof address === "string" ? address.toLowerCase() : "";
  if (!addr) return 0;
  let count = 0;
  for (const row of dripLogRows || []) {
    if (!row || typeof row.address !== "string" || row.address.toLowerCase() !== addr) continue;
    const ts = Date.parse(row.ts);
    if (!Number.isFinite(ts)) continue;
    if (nowMs - ts < windowMs) count += 1;
  }
  return count;
}

function readDripLog(file) {
  try {
    return fs
      .readFileSync(file, "utf8")
      .split("\n")
      .filter(Boolean)
      .map((line) => {
        try {
          return JSON.parse(line);
        } catch {
          return null;
        }
      })
      .filter(Boolean);
  } catch {
    return [];
  }
}

function appendDripLog(file, row) {
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.appendFileSync(file, JSON.stringify(row) + "\n");
  } catch {
    // best-effort log -- a failed append must never crash a successful drip (fail-open on bookkeeping,
    // never on the money-moving decision itself, which already happened above this call).
  }
}

/**
 * ensureGas — the impure preflight. Reads `address`'s native balance, decides via decideGasAction, and:
 *   - "ok": returns immediately, no drip attempted.
 *   - testnet "drip": sends a hard-capped (MAX_DRIP_WEI_PER_OP), daily-rate-limited (maxDripsPerDay) top
 *     -up via `sendDripFn` (production default: a real viem sendTransaction from `funderPrivateKey`).
 *   - mainnet "needs_gas": returns {ok:false, action:"needs_gas", requiredWei} — NEVER calls sendDripFn.
 * `publicClient`/`sendDripFn` are dependency-injected (tests pass fakes; production defaults construct
 * real viem clients) — same DI convention as gig.mjs's own `pay`/`verifyIdentityFn` parameters.
 * Never throws: every failure path returns {ok:false, ...}.
 */
export async function ensureGas({
  address,
  isMainnet = GIG_CHAIN === "base",
  rpcUrl = DEFAULT_RPC_URL,
  chain = ACTIVE_CHAIN.chain,
  publicClient,
  thresholdWei = DEFAULT_GAS_THRESHOLD_WEI,
  funderPrivateKey = process.env.GIG_GAS_FUNDER_PRIVATE_KEY,
  dripAmountWei = DEFAULT_DRIP_WEI,
  dripCapWei = MAX_DRIP_WEI_PER_OP,
  maxDripsPerDay = DEFAULT_MAX_DRIPS_PER_DAY,
  dripLogPath = DEFAULT_DRIP_LOG_PATH,
  nowMs = Date.now(),
  sendDripFn,
} = {}) {
  if (!address) return { ok: false, action: "error", reason: "address required" };

  const client = publicClient || createPublicClient({ chain, transport: http(rpcUrl) });
  let balance;
  try {
    balance = await client.getBalance({ address });
  } catch (e) {
    return { ok: false, action: "error", reason: `getBalance failed: ${e.shortMessage || e.message || String(e)}` };
  }

  const decision = decideGasAction({ balanceWei: balance, thresholdWei, isMainnet: !!isMainnet });
  if (decision.action === "ok") return { ok: true, action: "ok", balanceWei: balance.toString() };
  if (decision.action === "needs_gas") {
    return { ok: false, action: "needs_gas", reason: decision.reason, requiredWei: decision.requiredWei, balanceWei: balance.toString() };
  }

  // testnet drip path — hard cap enforced HERE, independent of what dripAmountWei the caller passed.
  const amount = BigInt(dripAmountWei) > BigInt(dripCapWei) ? BigInt(dripCapWei) : BigInt(dripAmountWei);

  const rows = readDripLog(dripLogPath);
  const recentCount = countRecentDrips(rows, address, nowMs, DRIP_WINDOW_MS);
  if (recentCount >= maxDripsPerDay) {
    return {
      ok: false,
      action: "needs_gas",
      reason: `daily drip cap (${maxDripsPerDay}) reached for ${address} -- refusing further auto-drip (fail-closed, spec §4)`,
      balanceWei: balance.toString(),
    };
  }

  const drip =
    sendDripFn ||
    (funderPrivateKey
      ? async ({ to, amountWei }) => {
          const funder = privateKeyToAccount(funderPrivateKey);
          const walletClient = createWalletClient({ account: funder, chain, transport: http(rpcUrl) });
          const hash = await walletClient.sendTransaction({ to, value: amountWei });
          return { hash };
        }
      : null);

  if (!drip) {
    return {
      ok: false,
      action: "needs_gas",
      reason: "testnet gas low but no funder configured (GIG_GAS_FUNDER_PRIVATE_KEY unset) -- refusing, no manual seeding fallback",
      balanceWei: balance.toString(),
    };
  }

  let sent;
  try {
    sent = await drip({ to: address, amountWei: amount });
  } catch (e) {
    return { ok: false, action: "needs_gas", reason: `drip tx failed: ${e.shortMessage || e.message || String(e)}` };
  }

  let receipt;
  try {
    receipt = await client.waitForTransactionReceipt({ hash: sent.hash });
  } catch (e) {
    return { ok: false, action: "needs_gas", reason: `drip tx receipt wait failed: ${e.shortMessage || e.message || String(e)}`, tx: sent.hash };
  }

  appendDripLog(dripLogPath, {
    ts: new Date(nowMs).toISOString(),
    address,
    amountWei: amount.toString(),
    tx: sent.hash,
    status: receipt.status,
  });

  if (receipt.status !== "success") {
    return { ok: false, action: "needs_gas", reason: `drip tx reverted: ${sent.hash}`, tx: sent.hash };
  }
  return { ok: true, action: "dripped", tx: sent.hash, amountWei: amount.toString(), balanceWeiBefore: balance.toString() };
}
