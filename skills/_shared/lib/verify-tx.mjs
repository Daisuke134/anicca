// verify-tx — read a Base (or any EVM) tx receipt status over JSON-RPC.
// Pure transport: fetch is injectable so tests never touch the network.
// Returns "0x1" (success) / "0x0" (reverted) / null (receipt not yet available).
const BASE_RPC = process.env.BASE_RPC_URL || "https://mainnet.base.org";
const TX_RE = /^0x[0-9a-fA-F]{64}$/;

export async function receiptStatus(txHash, opts = {}) {
  if (typeof txHash !== "string" || !TX_RE.test(txHash)) {
    throw new Error(`verify-tx: not a tx hash: ${txHash}`);
  }
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const rpc = opts.rpc || BASE_RPC;
  const res = await fetchImpl(rpc, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_getTransactionReceipt", params: [txHash] }),
  });
  if (!res.ok) throw new Error(`verify-tx: rpc ${res.status}`);
  const j = await res.json();
  const receipt = j && j.result;
  if (!receipt || typeof receipt.status !== "string") return null;
  return receipt.status; // "0x1" | "0x0"
}
