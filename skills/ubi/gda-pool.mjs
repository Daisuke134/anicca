// gda-pool.mjs — Superfluid GDA (General Distribution Agreement) continuous-distribution rail for UBI
// (phase 2). Instead of per-cycle batch sends, anicca opens ONE pool of Super-USDC (USDCx) on Base;
// each verified human is a pool member with 1 unit; anicca distributes the earned USDCx to the pool
// and every member's balance streams pro-rata, in a single tx, forever. On-chain cohort only (bank/
// email/mobile rails cover the rest).
//
// Contracts (Superfluid GDAv1Forwarder — same address across networks):
//   forwarder: 0x6DA13Bde224A05a288748d857b9e7DDEffd1dE08
//   createPool(token, admin, config) / updateMemberUnits(pool, member, units, "0x") / distribute(...)
// Docs: https://docs.superfluid.org/docs/technical-reference/GDAv1Forwarder
//
// GATE (like the other rails' account/key): needs anicca's wallet key (sends the tx) + BASE_USDCX_ADDRESS
// (the Super Token wrapper of USDC on Base — wrap plain USDC -> USDCx before distributing). Pure
// calldata builders are unit-tested; the on-chain send is injectable. Sending is real money movement —
// it runs only from anicca's own wallet (own-funds), never a user key.
import { encodeFunctionData, isAddress, getAddress } from "viem";

export const GDA_FORWARDER = "0x6DA13Bde224A05a288748d857b9e7DDEffd1dE08";

// minimal GDAv1Forwarder ABI (the three calls we use).
export const GDA_FORWARDER_ABI = [
  { type: "function", name: "createPool", stateMutability: "nonpayable",
    inputs: [
      { name: "token", type: "address" },
      { name: "admin", type: "address" },
      { name: "config", type: "tuple", components: [
        { name: "transferabilityForUnitsOwner", type: "bool" },
        { name: "distributionFromAnyAddress", type: "bool" },
      ] },
    ], outputs: [{ name: "success", type: "bool" }, { name: "pool", type: "address" }] },
  { type: "function", name: "updateMemberUnits", stateMutability: "nonpayable",
    inputs: [
      { name: "pool", type: "address" }, { name: "member", type: "address" },
      { name: "newUnits", type: "uint128" }, { name: "userData", type: "bytes" },
    ], outputs: [{ name: "success", type: "bool" }] },
  { type: "function", name: "distributeFlow", stateMutability: "nonpayable",
    inputs: [
      { name: "token", type: "address" }, { name: "from", type: "address" },
      { name: "pool", type: "address" }, { name: "requestedFlowRate", type: "int96" },
      { name: "userData", type: "bytes" },
    ], outputs: [{ name: "success", type: "bool" }] },
];

function requireAddr(a, label) {
  if (!a || !isAddress(a)) throw new Error(`gda: ${label} must be a valid address`);
  return getAddress(a);
}

// Pure: calldata to create the UBI pool (USDCx, anicca as admin). Non-transferable units (a member
// can't sell their UBI seat), distribution from the admin only.
export function buildCreatePoolCall({ token, admin }) {
  return encodeFunctionData({
    abi: GDA_FORWARDER_ABI, functionName: "createPool",
    args: [requireAddr(token, "token(USDCx)"), requireAddr(admin, "admin"),
      { transferabilityForUnitsOwner: false, distributionFromAnyAddress: false }],
  });
}

// Pure: calldata to set a verified human's units. 1 unit = one equal share; 0 = remove. Units are
// integers (>=0); a fractional or negative unit is rejected (no malformed on-chain write).
export function buildUpdateMemberUnitsCall({ pool, member, units }) {
  if (!Number.isInteger(units) || units < 0) throw new Error("gda: units must be a non-negative integer");
  return encodeFunctionData({
    abi: GDA_FORWARDER_ABI, functionName: "updateMemberUnits",
    args: [requireAddr(pool, "pool"), requireAddr(member, "member"), BigInt(units), "0x"],
  });
}

// Pure: calldata to stream USDCx to the pool at requestedFlowRate (wei/sec, int96). flowRate>0; 0 stops.
export function buildDistributeFlowCall({ token, from, pool, flowRatePerSec }) {
  if (typeof flowRatePerSec !== "bigint" || flowRatePerSec < 0n) throw new Error("gda: flowRatePerSec must be a non-negative bigint (wei/sec)");
  return encodeFunctionData({
    abi: GDA_FORWARDER_ABI, functionName: "distributeFlow",
    args: [requireAddr(token, "token(USDCx)"), requireAddr(from, "from"), requireAddr(pool, "pool"), flowRatePerSec, "0x"],
  });
}

// Live: send one of the above calls to the forwarder. sendTx is injectable ({to, data}) -> hash.
// Real money movement — own wallet only. Never throws silently; surfaces the send error.
export async function sendGdaCall(calldata, { sendTx } = {}) {
  if (typeof calldata !== "string" || !calldata.startsWith("0x")) throw new Error("gda: calldata required");
  if (typeof sendTx !== "function") throw new Error("gda: sendTx (own-wallet sender) required");
  return sendTx({ to: GDA_FORWARDER, data: calldata });
}
