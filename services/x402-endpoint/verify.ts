// USDC tx verification on Base via viem.
// Per spec 09 § 2 T4: read tx hash from x-paid-tx-hash header, fetch tx receipt + block,
// decode ERC20 Transfer log, confirm amount ≥ challenge.amount to receiver, reject if block
// age > 10 min (anti-replay window).
//
// Pattern mirrors ~/.anicca-genesis/agentkit/test-final.mjs (createPublicClient + base chain + mainnet RPC).

import { createPublicClient, http, parseAbiItem, decodeEventLog, getAddress } from "viem";
import { base } from "viem/chains";

const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const TRANSFER_EVENT = parseAbiItem(
  "event Transfer(address indexed from, address indexed to, uint256 value)"
);

// Anti-replay window: a tx hash older than this many seconds is rejected even if otherwise valid.
const MAX_TX_AGE_SECONDS = 10 * 60; // 10 minutes

const publicClient = createPublicClient({
  chain: base,
  transport: http("https://mainnet.base.org"),
});

export type VerifyResult =
  | {
      ok: true;
      from: string;
      to: string;
      valueUsdc: number;
      blockNumber: bigint;
      blockTimestamp: number; // unix seconds
      ageSeconds: number;
      txHash: `0x${string}`;
    }
  | { ok: false; reason: string };

const USDC_DECIMAL_DIVISOR = 1_000_000; // 6 decimals

function isHexHash(s: string): s is `0x${string}` {
  return /^0x[0-9a-fA-F]{64}$/.test(s);
}

/**
 * Verify that the supplied tx hash represents a confirmed USDC transfer of at
 * least `minUsdc` to `expectedReceiver` on Base mainnet, mined within the last 10 minutes.
 */
export async function verifyUsdcPayment(args: {
  txHash: string;
  expectedReceiver: string;
  minUsdc: number;
}): Promise<VerifyResult> {
  const { txHash, expectedReceiver, minUsdc } = args;

  if (!isHexHash(txHash)) {
    return { ok: false, reason: `invalid tx hash format: ${txHash}` };
  }

  let receiverChecksum: string;
  try {
    receiverChecksum = getAddress(expectedReceiver);
  } catch {
    return { ok: false, reason: `invalid receiver address: ${expectedReceiver}` };
  }

  let receipt;
  try {
    receipt = await publicClient.getTransactionReceipt({ hash: txHash });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { ok: false, reason: `tx receipt not found: ${msg}` };
  }

  if (!receipt || receipt.status !== "success") {
    return {
      ok: false,
      reason: `tx not confirmed or reverted (status=${receipt?.status ?? "missing"})`,
    };
  }

  // Pull block to enforce the age window.
  let block;
  try {
    block = await publicClient.getBlock({ blockNumber: receipt.blockNumber });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { ok: false, reason: `block lookup failed for ${receipt.blockNumber}: ${msg}` };
  }

  const blockTimestamp = Number(block.timestamp);
  const ageSeconds = Math.floor(Date.now() / 1000) - blockTimestamp;
  if (ageSeconds > MAX_TX_AGE_SECONDS) {
    return {
      ok: false,
      reason: `tx too old: ${ageSeconds}s > ${MAX_TX_AGE_SECONDS}s replay window`,
    };
  }
  if (ageSeconds < -60) {
    // Clock skew or block from the future — treat as suspicious.
    return { ok: false, reason: `tx block timestamp in the future by ${-ageSeconds}s` };
  }

  // Find a USDC Transfer log matching expected receiver + amount.
  const usdcLogs = receipt.logs.filter(
    (log) => log.address.toLowerCase() === USDC_BASE.toLowerCase()
  );

  for (const log of usdcLogs) {
    let decoded;
    try {
      decoded = decodeEventLog({
        abi: [TRANSFER_EVENT],
        data: log.data,
        topics: log.topics,
      });
    } catch {
      continue;
    }
    if (decoded.eventName !== "Transfer") continue;
    const { from, to, value } = decoded.args as { from: string; to: string; value: bigint };
    if (getAddress(to) !== receiverChecksum) continue;

    const minUnits = BigInt(Math.floor(minUsdc * USDC_DECIMAL_DIVISOR));
    if (value < minUnits) {
      return {
        ok: false,
        reason: `transfer amount ${value} < required ${minUnits} (USDC base units, 6 decimals)`,
      };
    }

    const valueUsdc = Number(value) / USDC_DECIMAL_DIVISOR;
    return {
      ok: true,
      from: getAddress(from),
      to: receiverChecksum,
      valueUsdc,
      blockNumber: receipt.blockNumber,
      blockTimestamp,
      ageSeconds,
      txHash,
    };
  }

  return { ok: false, reason: `no USDC Transfer to ${receiverChecksum} found in tx logs` };
}
