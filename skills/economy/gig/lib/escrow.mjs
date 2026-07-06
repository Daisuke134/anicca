// economy/gig/lib/escrow.mjs — pays USDC through the ALREADY-BUILT self-host x402-rs facilitator
// (services/facilitator, P2.1, running at 127.0.0.1:8405) using the exact EIP-3009
// transferWithAuthorization flow proven live in services/facilitator/scripts/settle-test.mjs
// (real tx 0x383e9369... on Base Sepolia). This module does NOT reinvent x402 or the facilitator --
// it is the same signing + /verify + /settle sequence, parameterized for (from,to,amount) so gig.mjs
// can call it twice per completed gig: once poster -> escrow (post), once escrow -> taker (verify_and_pay).
//
// "Escrow" here = a custody keypair the gig-board process holds (GIG_ESCROW_PRIVATE_KEY), not a
// Solidity escrow contract -- documented limitation (see README "Escrow model"), consistent with the
// P2.2 MVP scope (fail-closed release gating is enforced in lib/store.mjs, not by a contract).
//
// CHAIN-SELECTABLE (see WITNESS-RUNBOOK.md): GIG_CHAIN=base-sepolia (default, testnet) or
// GIG_CHAIN=base (mainnet, real USDC) picks which network payViaFacilitator/settleBody settle
// against. Testnet stays the default so nothing here changes behavior unless GIG_CHAIN=base is set.
import { privateKeyToAccount } from "viem/accounts";
import { createPublicClient, http as viemHttp } from "viem";
import { base, baseSepolia } from "viem/chains";
import { randomBytes } from "node:crypto";

export const USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e";
export const CHAIN_ID_BASE_SEPOLIA = 84532;
// Base mainnet USDC (canonical, Circle-issued -- verified live via eth_getCode on
// https://mainnet.base.org 2026-07-07, same 6-decimal token as testnet). See MAINNET.md /
// WITNESS-RUNBOOK.md for the go-live checklist.
export const USDC_BASE_MAINNET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
export const CHAIN_ID_BASE_MAINNET = 8453;

// GIG_CHAIN selects which network payViaFacilitator/settleBody default to when a caller doesn't
// override chainId/usdcAddress/rpcUrl/chain explicitly -- 'base-sepolia' (default, testnet, no real
// money) or 'base' (mainnet, real money). Unset/anything else falls back to testnet, fail-safe.
export const GIG_CHAIN = process.env.GIG_CHAIN === "base" ? "base" : "base-sepolia";

const CHAIN_PROFILES = {
  "base-sepolia": { chain: baseSepolia, chainId: CHAIN_ID_BASE_SEPOLIA, usdcAddress: USDC_BASE_SEPOLIA, rpcUrl: "https://sepolia.base.org" },
  base: { chain: base, chainId: CHAIN_ID_BASE_MAINNET, usdcAddress: USDC_BASE_MAINNET, rpcUrl: "https://mainnet.base.org" },
};
const ACTIVE_CHAIN = CHAIN_PROFILES[GIG_CHAIN];
const DEFAULT_RPC_URL = process.env.GIG_RPC_URL || ACTIVE_CHAIN.rpcUrl;

async function signAuthorization({ privateKey, to, amountBase, chainId, usdcAddress, validitySeconds }) {
  const payer = privateKeyToAccount(privateKey);
  const now = Math.floor(Date.now() / 1000);
  const nonce = "0x" + randomBytes(32).toString("hex");
  const authorization = {
    from: payer.address,
    to,
    value: String(amountBase),
    validAfter: String(now - 60),
    validBefore: String(now + validitySeconds),
    nonce,
  };
  const domain = { name: "USDC", version: "2", chainId, verifyingContract: usdcAddress };
  const types = {
    TransferWithAuthorization: [
      { name: "from", type: "address" },
      { name: "to", type: "address" },
      { name: "value", type: "uint256" },
      { name: "validAfter", type: "uint256" },
      { name: "validBefore", type: "uint256" },
      { name: "nonce", type: "bytes32" },
    ],
  };
  const signature = await payer.signTypedData({ domain, types, primaryType: "TransferWithAuthorization", message: authorization });
  const paymentRequirements = {
    scheme: "exact",
    network: `eip155:${chainId}`,
    amount: String(amountBase),
    payTo: to,
    maxTimeoutSeconds: validitySeconds,
    asset: usdcAddress,
    extra: { name: "USDC", version: "2" },
  };
  const paymentPayload = { x402Version: 2, accepted: paymentRequirements, payload: { signature, authorization } };
  return { payerAddress: payer.address, body: { x402Version: 2, paymentPayload, paymentRequirements } };
}

async function postJson(url, body) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const json = await res.json().catch(() => ({}));
  return { httpOk: res.ok, status: res.status, json };
}

// The facilitator's own /verify does an on-chain balanceOf() preflight through ITS OWN RPC connection --
// a separate process from ours, which can transiently lag behind a just-mined funding tx even after
// OUR publicClient has already confirmed it (same root cause as the ERC-8004 ownerOf() propagation lag
// documented in lib/identity.mjs: sepolia.base.org load-balances across backend nodes without strict
// read-your-writes consistency). Reproduced live during the P2.2 security-fix E2E re-proof: a
// legitimate, already-funded release failed /verify with "insufficient_funds" seconds after its own
// funding tx had a confirmed receipt. Retry with backoff instead of failing a legitimate call outright.
const TRANSIENT_VERIFY_REASONS = new Set(["insufficient_funds"]);
const RETRY_DELAYS_MS = [3000, 5000, 8000];

async function verifyWithRetry(facilitatorUrl, body) {
  for (let attempt = 0; ; attempt++) {
    const verify = await postJson(`${facilitatorUrl}/verify`, body);
    if (verify.httpOk && verify.json.isValid === true) return verify;
    const transient = TRANSIENT_VERIFY_REASONS.has(verify.json.invalidReason) && attempt < RETRY_DELAYS_MS.length;
    if (!transient) return verify;
    await new Promise((r) => setTimeout(r, RETRY_DELAYS_MS[attempt]));
  }
}

/**
 * settleBody — run /verify (with transient-lag retry, see above) then /settle against the facilitator
 * for an already-signed payload, then WAIT for the settle tx to actually be mined before reporting
 * success. Fail-closed, no crash: any failure returns { ok:false, stage, reason, raw } instead of
 * throwing (matches services/x402-endpoint/verify.mjs's structured-error contract).
 * `chain`/`rpcUrl` default to GIG_CHAIN's own profile -- ALWAYS pass the same chain the payload was
 * actually signed/settled against (a caller that overrides payViaFacilitator's chainId/usdcAddress but
 * not this must override rpcUrl/chain here too, or receipt confirmation silently queries the wrong
 * network).
 */
export async function settleBody({ facilitatorUrl, body, rpcUrl = DEFAULT_RPC_URL, chain = ACTIVE_CHAIN.chain }) {
  const verify = await verifyWithRetry(facilitatorUrl, body);
  if (!verify.httpOk || verify.json.isValid !== true) {
    return { ok: false, stage: "verify", reason: verify.json.invalidReason || `http ${verify.status}`, raw: verify.json };
  }
  const settle = await postJson(`${facilitatorUrl}/settle`, body);
  if (!settle.httpOk || settle.json.success !== true) {
    return { ok: false, stage: "settle", reason: settle.json.errorReason || `http ${settle.status}`, raw: settle.json };
  }
  const tx = settle.json.transaction;
  const publicClient = createPublicClient({ chain, transport: viemHttp(rpcUrl) });
  const receipt = await publicClient.waitForTransactionReceipt({ hash: tx });
  if (receipt.status !== "success") {
    return { ok: false, stage: "confirm", reason: `settle tx reverted on-chain: ${tx}`, raw: settle.json };
  }
  return { ok: true, tx, payer: settle.json.payer };
}

/**
 * payViaFacilitator — sign + settle a gasless USDC transfer (from,to,amountBase) through the
 * self-host facilitator. `privateKey` never leaves this process; the facilitator only ever sees the
 * already-signed EIP-3009 payload (the payer's key signs off-chain, the facilitator's OWN key pays L2
 * gas). This is the ONE function gig.mjs calls for both "poster funds escrow" and "escrow pays taker".
 * chainId/usdcAddress/rpcUrl/chain all default to GIG_CHAIN's active profile (testnet unless
 * GIG_CHAIN=base) -- overriding one without the others is the caller's responsibility to keep consistent.
 */
export async function payViaFacilitator({
  privateKey,
  to,
  amountBase,
  facilitatorUrl,
  chainId = ACTIVE_CHAIN.chainId,
  usdcAddress = ACTIVE_CHAIN.usdcAddress,
  rpcUrl = DEFAULT_RPC_URL,
  chain = ACTIVE_CHAIN.chain,
  validitySeconds = 300,
}) {
  const { payerAddress, body } = await signAuthorization({ privateKey, to, amountBase, chainId, usdcAddress, validitySeconds });
  const result = await settleBody({ facilitatorUrl, body, rpcUrl, chain });
  return { ...result, payerAddress, to, amountBase };
}
