// cctp.mjs — pure CCTP V2 calldata encode/decode for the Base(EVM) side of the bridge. No I/O:
// every function here takes plain values and returns plain values (hex strings / bigints). Uses
// viem's `encodeFunctionData`/`decodeFunctionResult` (a new dependency added by this feature — see
// README) instead of hand-rolling ABI padding/selectors: viem computes the correct 4-byte selector
// via a real, audited keccak256 implementation, which is exactly the kind of "don't hand-roll
// crypto" discipline the rest of this repo already follows (bs58/tweetnacl for Solana, not a
// bespoke base58/ed25519 implementation).
//
// The `depositForBurn(uint256,uint32,bytes32,address,bytes32,uint256,uint32)` selector this
// produces (0x8e0250ee) was cross-checked live 2026-07-25 against the public 4byte.directory
// signature database (independent of viem) — see this feature's report.

import { encodeFunctionData, decodeFunctionResult } from "viem";
import bs58 from "bs58";
import { STANDARD_TRANSFER_MIN_FINALITY_THRESHOLD, ZERO_BYTES32 } from "./constants.mjs";

const SOLANA_PUBKEY_BYTE_LENGTH = 32;

const ERC20_APPROVE_ABI = [
  {
    type: "function",
    name: "approve",
    stateMutability: "nonpayable",
    inputs: [
      { name: "spender", type: "address" },
      { name: "amount", type: "uint256" },
    ],
    outputs: [{ type: "bool" }],
  },
];

const ERC20_ALLOWANCE_ABI = [
  {
    type: "function",
    name: "allowance",
    stateMutability: "view",
    inputs: [
      { name: "owner", type: "address" },
      { name: "spender", type: "address" },
    ],
    outputs: [{ type: "uint256" }],
  },
];

// TokenMessengerV2#depositForBurn — developers.circle.com/cctp/references/technical-guide.
const DEPOSIT_FOR_BURN_ABI = [
  {
    type: "function",
    name: "depositForBurn",
    stateMutability: "nonpayable",
    inputs: [
      { name: "amount", type: "uint256" },
      { name: "destinationDomain", type: "uint32" },
      { name: "mintRecipient", type: "bytes32" },
      { name: "burnToken", type: "address" },
      { name: "destinationCaller", type: "bytes32" },
      { name: "maxFee", type: "uint256" },
      { name: "minFinalityThreshold", type: "uint32" },
    ],
    outputs: [],
  },
];

/**
 * Pure: convert a Solana base58 address into the bytes32 form CCTP's `mintRecipient` field
 * requires. A Solana ed25519 public key is exactly 32 bytes, so this is a direct hex encoding —
 * no padding, no truncation. Never throws with the raw input echoed back (bs58 errors can echo
 * the offending string).
 *
 * @param {string} address
 * @returns {`0x${string}`}
 */
export function solanaAddressToBytes32(address) {
  if (typeof address !== "string" || address.length === 0) {
    throw new Error("solanaAddressToBytes32: address must be a non-empty string");
  }
  let decoded;
  try {
    decoded = bs58.decode(address);
  } catch {
    throw new Error("solanaAddressToBytes32: address is not valid base58");
  }
  if (decoded.length !== SOLANA_PUBKEY_BYTE_LENGTH) {
    throw new Error(
      `solanaAddressToBytes32: expected a ${SOLANA_PUBKEY_BYTE_LENGTH}-byte Solana public key, got ${decoded.length} bytes`,
    );
  }
  return `0x${Buffer.from(decoded).toString("hex")}`;
}

/** Pure: USDC (6-decimal) amount -> base units (bigint). Fails closed on non-positive input. */
export function usdcToBaseUnits(usdcAmount) {
  if (typeof usdcAmount !== "number" || !Number.isFinite(usdcAmount) || usdcAmount <= 0) {
    throw new Error("usdcToBaseUnits: usdcAmount must be a positive finite number");
  }
  return BigInt(Math.round(usdcAmount * 1e6));
}

/** Pure: base units (bigint) -> USDC (6-decimal) amount, as a Number. */
export function baseUnitsToUsdc(baseUnits) {
  if (typeof baseUnits !== "bigint" || baseUnits < 0n) {
    throw new Error("baseUnitsToUsdc: baseUnits must be a non-negative bigint");
  }
  return Number(baseUnits) / 1e6;
}

/** Pure: encode ERC-20 `approve(spender, amount)` calldata. */
export function encodeErc20Approve({ spender, amount }) {
  if (typeof amount !== "bigint" || amount < 0n) {
    throw new Error("encodeErc20Approve: amount must be a non-negative bigint");
  }
  return encodeFunctionData({ abi: ERC20_APPROVE_ABI, functionName: "approve", args: [spender, amount] });
}

/** Pure: encode ERC-20 `allowance(owner, spender)` calldata (for an eth_call read). */
export function encodeErc20AllowanceCall({ owner, spender }) {
  return encodeFunctionData({ abi: ERC20_ALLOWANCE_ABI, functionName: "allowance", args: [owner, spender] });
}

/** Pure: decode the `allowance(...)` eth_call result hex into a bigint. */
export function decodeAllowanceResult(hexResult) {
  if (typeof hexResult !== "string" || !/^0x[0-9a-fA-F]*$/.test(hexResult)) {
    throw new Error("decodeAllowanceResult: hexResult must be a 0x-prefixed hex string");
  }
  return decodeFunctionResult({ abi: ERC20_ALLOWANCE_ABI, functionName: "allowance", data: hexResult });
}

/**
 * Pure: encode `TokenMessengerV2#depositForBurn` calldata for a CCTP Standard Transfer
 * (minFinalityThreshold=2000, the free rail — see constants.mjs) with maxFee=0 (Standard Transfer
 * charges no protocol fee, so there is nothing to bound) and destinationCaller=bytes32(0) (any
 * address may submit the destination-side finalize call — see README's "known gap": this build
 * does not submit that call itself).
 */
export function encodeDepositForBurn({
  amount,
  destinationDomain,
  mintRecipientSolanaAddress,
  burnToken,
  maxFee = 0n,
  minFinalityThreshold = STANDARD_TRANSFER_MIN_FINALITY_THRESHOLD,
}) {
  if (typeof amount !== "bigint" || amount <= 0n) {
    throw new Error("encodeDepositForBurn: amount must be a positive bigint");
  }
  if (typeof destinationDomain !== "number" || !Number.isInteger(destinationDomain) || destinationDomain < 0) {
    throw new Error("encodeDepositForBurn: destinationDomain must be a non-negative integer");
  }
  if (typeof burnToken !== "string" || !/^0x[0-9a-fA-F]{40}$/.test(burnToken)) {
    throw new Error("encodeDepositForBurn: burnToken must be a 0x-prefixed 20-byte address");
  }
  const mintRecipient = solanaAddressToBytes32(mintRecipientSolanaAddress);
  return encodeFunctionData({
    abi: DEPOSIT_FOR_BURN_ABI,
    functionName: "depositForBurn",
    args: [amount, destinationDomain, mintRecipient, burnToken, ZERO_BYTES32, maxFee, minFinalityThreshold],
  });
}
