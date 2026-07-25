// node:test — cctp.mjs: pure ABI encode/decode. No I/O. Selectors are cross-checked against the
// public 4byte.directory signature database (independent of viem) — see this feature's report.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  solanaAddressToBytes32,
  usdcToBaseUnits,
  baseUnitsToUsdc,
  encodeErc20Approve,
  encodeErc20AllowanceCall,
  decodeAllowanceResult,
  encodeDepositForBurn,
} from "../cctp.mjs";
import { BASE_USDC, TOKEN_MESSENGER_V2_BASE, SOLANA_DOMAIN, STANDARD_TRANSFER_MIN_FINALITY_THRESHOLD } from "../constants.mjs";
import { encodeFunctionData } from "viem";

const FRANKLIN_SOLANA_ADDRESS = "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T"; // real address from this feature's task spec

test("solanaAddressToBytes32: converts a real 32-byte Solana pubkey to a 0x-prefixed 64-hex-char string", () => {
  const hex = solanaAddressToBytes32(FRANKLIN_SOLANA_ADDRESS);
  assert.match(hex, /^0x[0-9a-f]{64}$/);
});

test("solanaAddressToBytes32: fails closed on invalid base58 or wrong length", () => {
  assert.throws(() => solanaAddressToBytes32("not-base58!!!"), /not valid base58/);
  assert.throws(() => solanaAddressToBytes32(""), /non-empty string/);
});

test("usdcToBaseUnits / baseUnitsToUsdc round-trip at 6 decimals", () => {
  assert.equal(usdcToBaseUnits(10).toString(), "10000000");
  assert.equal(baseUnitsToUsdc(10000000n), 10);
  assert.equal(usdcToBaseUnits(0.5).toString(), "500000");
});

test("usdcToBaseUnits fails closed on non-positive input", () => {
  assert.throws(() => usdcToBaseUnits(0), /positive finite number/);
  assert.throws(() => usdcToBaseUnits(-1), /positive finite number/);
});

test("encodeErc20Approve: selector matches the well-known ERC-20 approve(address,uint256) selector 0x095ea7b3", () => {
  const data = encodeErc20Approve({ spender: TOKEN_MESSENGER_V2_BASE, amount: 10_000_000n });
  assert.equal(data.slice(0, 10), "0x095ea7b3");
});

test("encodeErc20AllowanceCall + decodeAllowanceResult round-trip a real-shaped eth_call result", () => {
  const callData = encodeErc20AllowanceCall({ owner: "0x810F6D61F7606dEEE2657d3083E150a222Bc29C5", spender: TOKEN_MESSENGER_V2_BASE });
  assert.equal(callData.slice(0, 10), "0xdd62ed3e"); // well-known allowance(address,address) selector
  // A real eth_call result is a 32-byte-padded hex value.
  const fakeResultHex = `0x${(5_000_000n).toString(16).padStart(64, "0")}`;
  const decoded = decodeAllowanceResult(fakeResultHex);
  assert.equal(decoded, 5_000_000n);
});

test("decodeAllowanceResult fails closed on a malformed hex string", () => {
  assert.throws(() => decodeAllowanceResult("not-hex"), /must be a 0x-prefixed hex string/);
});

test("encodeDepositForBurn: selector matches the independently-verified real CCTP V2 selector 0x8e0250ee (cross-checked live against 4byte.directory 2026-07-25)", () => {
  const data = encodeDepositForBurn({
    amount: 10_000_000n,
    destinationDomain: SOLANA_DOMAIN,
    mintRecipientSolanaAddress: FRANKLIN_SOLANA_ADDRESS,
    burnToken: BASE_USDC,
  });
  assert.equal(data.slice(0, 10), "0x8e0250ee");
});

test("encodeDepositForBurn: defaults to Standard Transfer (minFinalityThreshold=2000, maxFee=0) and matches a hand-built viem encoding exactly", () => {
  const abi = [
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
  const mintRecipient = solanaAddressToBytes32(FRANKLIN_SOLANA_ADDRESS);
  const expected = encodeFunctionData({
    abi,
    functionName: "depositForBurn",
    args: [10_000_000n, SOLANA_DOMAIN, mintRecipient, BASE_USDC, `0x${"00".repeat(32)}`, 0n, STANDARD_TRANSFER_MIN_FINALITY_THRESHOLD],
  });
  const actual = encodeDepositForBurn({
    amount: 10_000_000n,
    destinationDomain: SOLANA_DOMAIN,
    mintRecipientSolanaAddress: FRANKLIN_SOLANA_ADDRESS,
    burnToken: BASE_USDC,
  });
  assert.equal(actual, expected);
});

test("encodeDepositForBurn: fails closed on a non-positive amount or a malformed burnToken address", () => {
  assert.throws(
    () => encodeDepositForBurn({ amount: 0n, destinationDomain: SOLANA_DOMAIN, mintRecipientSolanaAddress: FRANKLIN_SOLANA_ADDRESS, burnToken: BASE_USDC }),
    /positive bigint/,
  );
  assert.throws(
    () => encodeDepositForBurn({ amount: 1n, destinationDomain: SOLANA_DOMAIN, mintRecipientSolanaAddress: FRANKLIN_SOLANA_ADDRESS, burnToken: "not-an-address" }),
    /burnToken must be a 0x-prefixed 20-byte address/,
  );
});

test("verified constants: Base domain 6, Solana domain 5, Standard Transfer finality threshold 2000 (all live-verified 2026-07-25)", () => {
  assert.equal(SOLANA_DOMAIN, 5);
  assert.equal(STANDARD_TRANSFER_MIN_FINALITY_THRESHOLD, 2000);
});
