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

// VERIFIED 2026-06-21: eth_getCode on Base mainnet returns 11840 chars of bytecode at this address —
// the GDAv1Forwarder is deployed on Base. (USDCx Super Token address is still resolved at pool-creation
// time: use an existing Base USDC wrapper super token or deploy one via the Super Token Factory.)
export const GDA_FORWARDER = "0x6DA13Bde224A05a288748d857b9e7DDEffd1dE08";

// Max int96 (Superfluid flow rates are int96 wei/sec). A rate at/above this overflows/misencodes —
// reject it (defense-in-depth on a money-moving stream, symmetric to the bridge amount ceiling).
export const MAX_INT96 = (2n ** 95n) - 1n;

// UNVERIFIED: hand-written ("minimal") GDAv1Forwarder ABI — confirm tuple order + types + outputs
// against the live contract before prod (a type/order mismatch reverts on-chain = fail-closed, but
// must be verified, not assumed). Token args below MUST be the USDCx Super Token (the Super-Token
// wrapper of USDC on Base, BASE_USDCX_ADDRESS) — NOT plain USDC; wrap USDC->USDCx before distributing.
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
// token MUST be the USDCx Super Token (UNVERIFIED that the caller passes USDCx not plain USDC — a
// pure builder can't check on-chain; the runtime caller must pass BASE_USDCX_ADDRESS).
export function buildDistributeFlowCall({ token, from, pool, flowRatePerSec }) {
  if (typeof flowRatePerSec !== "bigint" || flowRatePerSec < 0n) throw new Error("gda: flowRatePerSec must be a non-negative bigint (wei/sec)");
  if (flowRatePerSec > MAX_INT96) throw new Error("gda: flowRatePerSec exceeds int96 max (overflow guard)"); // FIND-B02
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

// LIVE UBI POOL (created 2026-06-21 on Base, tx 0xcb161a69061714c9af47f5c730eada1eb5a12e60addaa13fa9faa225f6ca2189):
// token=USDCx 0xD04383398dD2426297da660F9CCA3d439AF9ce1b, admin=anicca 0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21.
// SECURITY NOTE (2026-07-07): automaton's wallet key was rotated to 0xB9dd3B67921B354c656523d6851537988F31DD56
// after the 0xa3CDd4... key leaked, but the pool's on-chain `admin` field is IMMUTABLE state set at
// createPool() time and still reads 0xa3CDd4... (verified via admin() view call, 2026-07-07) --
// `distributionFromAnyAddress:false` means only that (compromised) address can distribute/update member
// units on this pool. Residual risk is LOW today (pool USDCx balance verified = 0 at rotation time, and
// the old address's own funds were already moved out) but NOT zero if this pool is ever refunded before
// the admin role itself is migrated (recreate the pool with the new address as admin, or find/call a
// pool-admin-transfer function if Superfluid's GDAv1 exposes one -- unverified, out of scope here).
export const UBI_GDA_POOL = "0xEF0702A57bd465E77e048DCAFC6F532B761988d0";
export const BASE_USDCX = "0xD04383398dD2426297da660F9CCA3d439AF9ce1b";
