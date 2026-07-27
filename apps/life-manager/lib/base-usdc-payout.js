"use strict";

const { createHash } = require("node:crypto");
const { getAddress } = require("viem");
const { privateKeyToAccount } = require("viem/accounts");

const BASE_CHAIN_ID = 8453;
const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const DEFAULT_RPC_URL = "https://mainnet.base.org";
const DEFAULT_VALIDITY_SECONDS = 300;

const AUTHORIZATION_TYPES = Object.freeze({
  TransferWithAuthorization: Object.freeze([
    Object.freeze({ name: "from", type: "address" }),
    Object.freeze({ name: "to", type: "address" }),
    Object.freeze({ name: "value", type: "uint256" }),
    Object.freeze({ name: "validAfter", type: "uint256" }),
    Object.freeze({ name: "validBefore", type: "uint256" }),
    Object.freeze({ name: "nonce", type: "bytes32" }),
  ]),
});

function exactPositiveInteger(value, label) {
  const raw = typeof value === "bigint"
    ? value.toString()
    : String(value == null ? "" : value).trim();
  if (!/^\d+$/.test(raw) || BigInt(raw) <= 0n) {
    throw new Error(`${label} must be an exact positive integer`);
  }
  return raw;
}

function privateKeyHex(value) {
  const raw = String(value == null ? "" : value).trim().replace(/^0x/i, "");
  if (!/^[0-9a-fA-F]{64}$/.test(raw)) throw new Error("private key is not a 32-byte scalar");
  return `0x${raw}`;
}

function ethereumAddress(value, label) {
  try {
    return getAddress(String(value == null ? "" : value).trim());
  } catch {
    throw new Error(`${label} is not a valid Ethereum address`);
  }
}

function localFacilitator(value) {
  let url;
  try {
    url = new URL(String(value == null ? "" : value));
  } catch {
    throw new Error("facilitatorUrl is not a URL");
  }
  const loopback = new Set(["127.0.0.1", "localhost", "[::1]"]);
  if (url.protocol !== "http:" || !loopback.has(url.hostname) || url.username || url.password) {
    throw new Error("signed payout payloads may only be sent to the loopback self-hosted facilitator");
  }
  return url.toString().replace(/\/$/, "");
}

function authorizationNonce(payoutId, walletAddress, destination, amountAtomic) {
  const id = String(payoutId == null ? "" : payoutId).trim();
  if (!/^[A-Za-z0-9:._-]{1,200}$/.test(id)) {
    throw new Error("payoutId is required and must be a closed public identifier");
  }
  const material = [
    "life-manager-base-usdc-payout-v1",
    id,
    walletAddress.toLowerCase(),
    destination.toLowerCase(),
    amountAtomic,
  ].join("\n");
  return `0x${createHash("sha256").update(material, "utf8").digest("hex")}`;
}

function normalizedHash(value) {
  const raw = String(value == null ? "" : value).trim().toLowerCase();
  return /^0x[0-9a-f]{64}$/.test(raw) ? raw : null;
}

function topicAddress(address) {
  return `0x${address.slice(2).toLowerCase().padStart(64, "0")}`;
}

function hexInteger(value) {
  const raw = String(value == null ? "" : value);
  if (!/^0x[0-9a-f]+$/i.test(raw)) return null;
  return BigInt(raw);
}

function exactTransferReceipt(receipt, expected) {
  if (!receipt || receipt.status !== "0x1") throw new Error("payout receipt is missing or failed");
  if (normalizedHash(receipt.transactionHash) !== expected.txHash) {
    throw new Error("payout receipt transaction does not match settlement");
  }
  const blockNumber = hexInteger(receipt.blockNumber);
  if (blockNumber == null) throw new Error("payout receipt has no block number");

  const matches = (Array.isArray(receipt.logs) ? receipt.logs : []).filter((log) => {
    if (!log || String(log.address || "").toLowerCase() !== BASE_USDC.toLowerCase()) return false;
    if (normalizedHash(log.transactionHash) !== expected.txHash) return false;
    if (!Array.isArray(log.topics) || log.topics.length < 3) return false;
    if (String(log.topics[0]).toLowerCase() !== TRANSFER_TOPIC) return false;
    if (String(log.topics[1]).toLowerCase() !== topicAddress(expected.from)) return false;
    if (String(log.topics[2]).toLowerCase() !== topicAddress(expected.to)) return false;
    const amount = hexInteger(log.data);
    return amount != null && amount === BigInt(expected.amountAtomic);
  });
  if (matches.length !== 1) {
    throw new Error("payout receipt does not contain exactly one matching USDC Transfer");
  }
  return blockNumber.toString();
}

async function jsonPost(url, body, fetchImpl) {
  const response = await fetchImpl(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await response.json().catch(() => ({}));
  return { ok: Boolean(response.ok), status: response.status, json };
}

function rpcBoundary(rpcUrl, fetchImpl) {
  let id = 0;
  return async (method, params) => {
    const response = await fetchImpl(rpcUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params }),
    });
    const json = await response.json().catch(() => ({}));
    if (!response.ok || json.error) {
      throw new Error(`Base RPC ${method} failed (${response.status})`);
    }
    return json.result;
  };
}

async function waitForReceipt(txHash, rpcCall, deps) {
  const attempts = deps.receiptAttempts == null ? 60 : deps.receiptAttempts;
  const sleep = deps.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const receipt = await rpcCall("eth_getTransactionReceipt", [txHash]);
    if (receipt) return receipt;
    if (attempt + 1 < attempts) await sleep(1_000);
  }
  throw new Error("payout receipt was not mined before the confirmation deadline");
}

async function settleBaseUsdc(request = {}, deps = {}) {
  const amountAtomic = exactPositiveInteger(request.amountAtomic, "amountAtomic");
  const destination = ethereumAddress(request.destination, "destination");
  const walletAddress = ethereumAddress(request.walletAddress, "walletAddress");
  const facilitatorUrl = localFacilitator(request.facilitatorUrl);
  const privateKey = privateKeyHex(request.privateKey);
  const account = privateKeyToAccount(privateKey);
  if (account.address !== walletAddress) {
    throw new Error("private-key signer does not match the stored agent wallet");
  }

  const nonce = authorizationNonce(request.payoutId, walletAddress, destination, amountAtomic);
  const nowSeconds = Math.floor((request.nowMs == null ? Date.now() : request.nowMs) / 1_000);
  const authorization = {
    from: walletAddress,
    to: destination,
    value: amountAtomic,
    validAfter: String(nowSeconds - 60),
    validBefore: String(nowSeconds + DEFAULT_VALIDITY_SECONDS),
    nonce,
  };
  const domain = {
    name: "USD Coin",
    version: "2",
    chainId: BASE_CHAIN_ID,
    verifyingContract: BASE_USDC,
  };
  const signature = await account.signTypedData({
    domain,
    types: AUTHORIZATION_TYPES,
    primaryType: "TransferWithAuthorization",
    message: authorization,
  });
  const paymentRequirements = {
    scheme: "exact",
    network: `eip155:${BASE_CHAIN_ID}`,
    amount: amountAtomic,
    payTo: destination,
    maxTimeoutSeconds: DEFAULT_VALIDITY_SECONDS,
    asset: BASE_USDC,
    extra: { name: "USD Coin", version: "2" },
  };
  const paymentPayload = {
    x402Version: 2,
    accepted: paymentRequirements,
    payload: { signature, authorization },
  };
  const body = { x402Version: 2, paymentPayload, paymentRequirements };

  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") throw new Error("payout settlement needs fetch");
  const verify = await jsonPost(`${facilitatorUrl}/verify`, body, fetchImpl);
  if (!verify.ok || verify.json.isValid !== true) {
    const reason = verify.json.invalidReason || `http ${verify.status}`;
    throw new Error(`payout verify failed: ${reason}`);
  }
  const settle = await jsonPost(`${facilitatorUrl}/settle`, body, fetchImpl);
  if (!settle.ok || settle.json.success !== true) {
    const reason = settle.json.errorReason || `http ${settle.status}`;
    throw new Error(`payout settle failed: ${reason}`);
  }
  const txHash = normalizedHash(settle.json.transaction);
  if (!txHash) throw new Error("payout settle returned no valid transaction hash");
  if (settle.json.payer != null
    && ethereumAddress(settle.json.payer, "settlement payer") !== walletAddress) {
    throw new Error("payout settlement payer does not match the agent wallet");
  }

  const rpcCall = deps.rpcCall || rpcBoundary(request.rpcUrl || DEFAULT_RPC_URL, fetchImpl);
  const chainId = hexInteger(await rpcCall("eth_chainId", []));
  if (chainId !== BigInt(BASE_CHAIN_ID)) {
    throw new Error("payout confirmation RPC is not the Base mainnet chain (8453)");
  }
  const receipt = await waitForReceipt(txHash, rpcCall, deps);
  const blockNumber = exactTransferReceipt(receipt, {
    txHash,
    amountAtomic,
    from: walletAddress,
    to: destination,
  });

  return {
    txHash,
    amountAtomic,
    from: walletAddress,
    to: destination,
    blockNumber,
  };
}

module.exports = {
  BASE_CHAIN_ID,
  BASE_USDC,
  TRANSFER_TOPIC,
  AUTHORIZATION_TYPES,
  authorizationNonce,
  exactTransferReceipt,
  settleBaseUsdc,
};
