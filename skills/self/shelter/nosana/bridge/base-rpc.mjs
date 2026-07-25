// base-rpc.mjs — minimal raw Base (EVM) JSON-RPC reads/writes, matching the existing repo
// convention in ../../../earn/lib/usdc.mjs (hand-rolled JSON-RPC over fetch, no SDK) rather than
// adding a full EVM client's read/write surface on top of viem (which this feature already adds,
// but only for ABI encoding and signing — see cctp.mjs / sign.mjs). fetchImpl is injectable so
// nothing here hits the network in tests. Every function fails closed (throws) on a non-OK HTTP
// response or an RPC-level error — never returns a fabricated/zero value on failure.

export const DEFAULT_BASE_RPC_URL = process.env.BASE_RPC_URL || "https://mainnet.base.org";

async function rpcCall({ fetchImpl = fetch, rpcUrl = DEFAULT_BASE_RPC_URL, method, params }) {
  const res = await fetchImpl(rpcUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  if (!res || !res.ok) {
    throw new Error(`base-rpc: HTTP ${res && res.status} calling ${method} (fail-closed)`);
  }
  const body = await res.json();
  if (body.error) {
    throw new Error(`base-rpc: ${method} returned an RPC error: ${JSON.stringify(body.error)} (fail-closed)`);
  }
  return body.result;
}

export async function getGasPriceWei(opts = {}) {
  const hex = await rpcCall({ ...opts, method: "eth_gasPrice", params: [] });
  return BigInt(hex);
}

export async function getEthBalanceWei({ address, ...opts }) {
  const hex = await rpcCall({ ...opts, method: "eth_getBalance", params: [address, "latest"] });
  return BigInt(hex);
}

export async function getTransactionCount({ address, ...opts }) {
  const hex = await rpcCall({ ...opts, method: "eth_getTransactionCount", params: [address, "pending"] });
  return BigInt(hex);
}

export async function getChainId(opts = {}) {
  const hex = await rpcCall({ ...opts, method: "eth_chainId", params: [] });
  return Number(BigInt(hex));
}

export async function ethCall({ to, data, ...opts }) {
  return rpcCall({ ...opts, method: "eth_call", params: [{ to, data }, "latest"] });
}

export async function sendRawTransaction({ signedTxHex, ...opts }) {
  return rpcCall({ ...opts, method: "eth_sendRawTransaction", params: [signedTxHex] });
}

export async function getTransactionReceipt({ txHash, ...opts }) {
  return rpcCall({ ...opts, method: "eth_getTransactionReceipt", params: [txHash] });
}
