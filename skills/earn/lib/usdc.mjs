// usdc — read a wallet's USDC balance on Base via eth_call balanceOf(address).
// Used for the GATE-0 before/after delta proof (wallet grew => real earn).
// Pure transport: fetch injectable for tests.
const BASE_RPC = process.env.BASE_RPC_URL || "https://mainnet.base.org";
// Native USDC on Base.
const USDC = (process.env.USDC_ADDRESS || "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913").toLowerCase();
const ADDR_RE = /^0x[0-9a-fA-F]{40}$/;
const BALANCE_OF = "0x70a08231"; // balanceOf(address) selector

export async function usdcBalance(wallet, opts = {}) {
  if (typeof wallet !== "string" || !ADDR_RE.test(wallet)) {
    throw new Error(`usdc: not an address: ${wallet}`);
  }
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const rpc = opts.rpc || BASE_RPC;
  const token = (opts.token || USDC).toLowerCase();
  const padded = wallet.toLowerCase().replace(/^0x/, "").padStart(64, "0");
  const data = BALANCE_OF + padded;
  const res = await fetchImpl(rpc, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "eth_call",
      params: [{ to: token, data }, "latest"],
    }),
  });
  if (!res.ok) throw new Error(`usdc: rpc ${res.status}`);
  const j = await res.json();
  const hex = j && j.result ? j.result : "0x0";
  const base = BigInt(hex === "0x" ? "0x0" : hex);
  // 6 decimals; return a JS number (USDC values are well within safe-integer range here).
  return Number(base) / 1e6;
}

export function delta(after, before) {
  return Math.round((Number(after) - Number(before)) * 1e6) / 1e6;
}
