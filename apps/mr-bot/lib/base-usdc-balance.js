"use strict";

const { getAddress } = require("viem");

const { BASE_USDC } = require("./base-usdc-payout.js");

const DEFAULT_RPC_URL = "https://mainnet.base.org";

async function readUsdcBalance(walletAddress, opts = {}) {
  const address = getAddress(String(walletAddress || ""));
  const rpcUrl = opts.rpcUrl || DEFAULT_RPC_URL;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") throw new Error("Base balance reader needs fetch");
  const response = await fetchImpl(rpcUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "eth_call",
      params: [{
        to: BASE_USDC,
        data: `0x70a08231${address.slice(2).toLowerCase().padStart(64, "0")}`,
      }, "latest"],
    }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.error || !/^0x[0-9a-f]+$/i.test(String(body.result || ""))) {
    throw new Error(`Base USDC balance read failed (${response.status})`);
  }
  return BigInt(body.result).toString();
}

module.exports = { DEFAULT_RPC_URL, readUsdcBalance };
