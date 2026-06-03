// USDC tx verification on Base via viem.
// Per spec 09 § 2 T4: read tx hash from x-paid-tx-hash header, fetch tx receipt,
// decode ERC20 Transfer log, confirm amount ≥ challenge.amount to receiver.
//
// Pattern mirrors ~/.anicca-genesis/agentkit/test-final.mjs (createPublicClient + base chain + mainnet RPC).

import { createPublicClient, http, parseAbiItem, decodeEventLog, getAddress } from "viem";
import { base } from "viem/chains";

const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const TRANSFER_EVENT = parseAbiItem("event Transfer(address indexed from, address indexed to, uint256 value)");

const publicClient = createPublicClient({
  chain: base,
  transport: http("https://mainnet.base.org"),
});

export type VerifyResult =
  | { ok: true; from: string; to: string; valueUsdc: number; blockNumber: bigint; txHash: `0x${string}` }
  | { ok: false; reason: string };

const USDC_DECIMALS = 6n;
const USDC_DECIMAL_DIVISOR = 1_000_000;

function isHexHash(s: string): s is `0x${string}` {
  return /^0x[0-9a-fA-F]{64}$/.test(s);
}

/**
 * Verify that the supplied tx hash represents a confirmed USDC transfer of at
 * least `minUsdc` to `expectedReceiver` on Base mainnet.
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
    return { ok: false, reason: `tx not confirmed or reverted (status=${receipt?.status ?? "missing"})` };
  }

  // Find a USDC Transfer log matching expected receiver.
  const usdcLogs = receipt.logs.filter(
    (log) => log.address.toLowerCase() === USDC_BASE.toLowerCase()
  );

  for (const log of usdcLogs) {
    try {
      const decoded = decodeEventLog({
        abi: [TRANSFER_EVENT],
        data: log.data,
        topics: log.topics,
      });
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
        txHash,
      };
    } catch {
      // Not a Transfer event we recognise — skip.
    }
  }

  return { ok: false, reason: `no USDC Transfer to ${receiverChecksum} found in tx logs` };
}
