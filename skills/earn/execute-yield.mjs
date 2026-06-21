// execute-yield.mjs — earn_yield as a self-managing TREASURY: keep a liquid compute buffer so the
// loop's survival tier stays funded (= frontier model), deploy the surplus into the best safe stable
// yield, and REFILL the buffer from yield when frontier inference has burned it down. No human, no
// per-instance babysitting: every Anicca on this repo manages its own liquid-vs-yield balance.
//
// Why a buffer: compute is paid in USDC via x402 from LIQUID balance, and the loop picks its model
// by liquid tier (>$1 funded → frontier). If we deploy ALL liquid to yield, the agent starves its
// own brain down to the cheap tier. So the treasury keeps COMPUTE_RESERVE_USDC liquid (sized above
// the funded threshold), parks the rest in yield, and withdraws from yield to top the buffer back up
// when it runs low. Result: frontier while the agent is solvent, automatic step-down to cheaper
// models only when total wealth is genuinely gone.
//
// Honest: own-capital accrual (external:false, kind:"yield"); every action is a real on-chain tx.
import { createPublicClient, createWalletClient, http, fallback } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import fs from "fs";

// EVERY public Base RPC flakes intermittently (mainnet.base.org timeouts, llamarpc 521, drpc 500) —
// that silently dropped deposits (the loop logged "deploy" but no tx landed). Use a viem fallback
// transport across several RPCs so a single one being down never breaks an earn. BASE_RPC_URL (if set)
// is tried FIRST, then the public pool.
const RPC_LIST = [
  ...(process.env.BASE_RPC_URL ? [process.env.BASE_RPC_URL] : []),
  "https://mainnet.base.org",
  "https://base-rpc.publicnode.com",
  "https://base.drpc.org",
  "https://base.llamarpc.com",
  "https://1rpc.io/base",
  "https://base.meowrpc.com",
];
const TRANSPORT = fallback(RPC_LIST.map((u) => http(u, { timeout: 12_000, retryCount: 2 })));
const RPC = RPC_LIST[0]; // kept for any log/back-compat references
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const AAVE_POOL = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5";
const AAVE_APY = 0.032;
// Liquid USDC to keep for compute (x402 inference). Sized well above the funded tier ($1) so the
// loop runs a frontier model and has runway between refills.
const RESERVE = Math.round(parseFloat(process.env.COMPUTE_RESERVE_USDC || "5") * 1e6);
const MIN_DEPLOY = Math.round(parseFloat(process.env.YIELD_MIN_DEPLOY_USDC || "1") * 1e6);
const REFILL_AT = Math.round(RESERVE * 0.6); // refill the buffer once liquid drops below 60% of it

function out(o) { process.stdout.write(JSON.stringify(o) + "\n"); }
function loadKey() {
  // PKVAR names the env var that HOLDS the key (e.g. "BLOCKRUN_WALLET_KEY") — resolve it INDIRECTLY.
  // The old `process.env.PKVAR` used the var NAME as the key string → "invalid private key, got string"
  // and earn silently failed (no yield ever deployed). run.sh always passes PKVAR, so this was fatal.
  const k = (process.env.PKVAR && process.env[process.env.PKVAR]) || process.env.BLOCKRUN_WALLET_KEY;
  if (k) return k.startsWith("0x") ? k : "0x" + k;
  try { const w = JSON.parse(fs.readFileSync(process.env.HOME + "/.automaton/wallet.json", "utf8")); return w.privateKey.startsWith("0x") ? w.privateKey : "0x" + w.privateKey; } catch { return null; }
}
const erc20 = [
  { name: "approve", type: "function", stateMutability: "nonpayable", inputs: [{ type: "address" }, { type: "uint256" }], outputs: [{ type: "bool" }] },
  { name: "allowance", type: "function", stateMutability: "view", inputs: [{ type: "address" }, { type: "address" }], outputs: [{ type: "uint256" }] },
  { name: "balanceOf", type: "function", stateMutability: "view", inputs: [{ type: "address" }], outputs: [{ type: "uint256" }] },
];
const beefy = [
  { name: "deposit", type: "function", stateMutability: "nonpayable", inputs: [{ type: "uint256" }], outputs: [] },
  { name: "withdraw", type: "function", stateMutability: "nonpayable", inputs: [{ type: "uint256" }], outputs: [] },
  { name: "withdrawAll", type: "function", stateMutability: "nonpayable", inputs: [], outputs: [] },
  { name: "getPricePerFullShare", type: "function", stateMutability: "view", inputs: [], outputs: [{ type: "uint256" }] },
  { name: "balanceOf", type: "function", stateMutability: "view", inputs: [{ type: "address" }], outputs: [{ type: "uint256" }] },
];
const aave = [{ name: "supply", type: "function", stateMutability: "nonpayable", inputs: [{ type: "address" }, { type: "uint256" }, { type: "address" }, { type: "uint16" }], outputs: [] }];

// Best ACTIVE single-asset USDC Beefy Base vault (want==USDC → direct deposit/withdraw). null on fail.
async function bestBeefy() {
  try {
    const [vaults, apys] = await Promise.all([
      fetch("https://api.beefy.finance/vaults").then((r) => r.json()),
      fetch("https://api.beefy.finance/apy").then((r) => r.json()),
    ]);
    const cands = vaults
      .filter((v) => v.chain === "base" && v.status === "active" && (v.tokenAddress || "").toLowerCase() === USDC.toLowerCase())
      .map((v) => ({ id: v.id, vault: v.earnedTokenAddress, apy: apys[v.id] || 0 }))
      .filter((v) => v.vault && v.apy > 0)
      .sort((a, b) => b.apy - a.apy);
    return cands[0] || null;
  } catch { return null; }
}

async function main() {
  const pk = loadKey();
  if (!pk) return out({ abort: "no wallet key" });
  const acct = privateKeyToAccount(pk);
  const pub = createPublicClient({ chain: base, transport: TRANSPORT });
  const w = createWalletClient({ account: acct, chain: base, transport: TRANSPORT });
  if ((await pub.getBalance({ address: acct.address })) === 0n) return out({ abort: "no ETH for gas", wallet: acct.address });

  const liquid = await pub.readContract({ address: USDC, abi: erc20, functionName: "balanceOf", args: [acct.address] });
  const bf = await bestBeefy();
  const vault = bf?.vault;

  // ---- DEPLOY: liquid above the buffer goes to the best yield ----
  const surplus = liquid - BigInt(RESERVE);
  if (surplus >= BigInt(MIN_DEPLOY)) {
    const useBeefy = bf && bf.apy > AAVE_APY;
    const venue = useBeefy ? vault : AAVE_POOL;
    const protocol = useBeefy ? `beefy:${bf.id}` : "aave-v3-base";
    let alw = await pub.readContract({ address: USDC, abi: erc20, functionName: "allowance", args: [acct.address, venue] });
    if (alw < surplus) {
      const ah = await w.writeContract({ address: USDC, abi: erc20, functionName: "approve", args: [venue, surplus] });
      await pub.waitForTransactionReceipt({ hash: ah, confirmations: 2 });
    }
    const tx = useBeefy
      ? await w.writeContract({ address: venue, abi: beefy, functionName: "deposit", args: [surplus] })
      : await w.writeContract({ address: venue, abi: aave, functionName: "supply", args: [USDC, surplus, acct.address, 0] });
    const r = await pub.waitForTransactionReceipt({ hash: tx });
    return out({ kind: "yield", action: "deploy", protocol, apy_pct: +((useBeefy ? bf.apy : AAVE_APY) * 100).toFixed(2), tx, status: r.status === "success" ? "0x1" : "0x0", deposited_usdc: Number(surplus) / 1e6, reserve_usdc: RESERVE / 1e6, wallet: acct.address });
  }

  // ---- REFILL: liquid below the trigger → pull the position back to liquid to top up the buffer ----
  // Uses Beefy's withdrawAll() (no args) — NOT a computed partial withdraw(shares). The old partial
  // path mixed 6-dec USDC `need` with 18-dec mooShares, producing a wrong share amount that REVERTED
  // (status 0x0) every wake = a recurring gas bleed. withdrawAll exits the whole position in one robust
  // call; the next wake redeploys the surplus above RESERVE, so the buffer is restored cleanly.
  if (liquid < BigInt(REFILL_AT) && vault) {
    const shares = await pub.readContract({ address: vault, abi: beefy, functionName: "balanceOf", args: [acct.address] });
    if (shares > 0n) {
      const tx = await w.writeContract({ address: vault, abi: beefy, functionName: "withdrawAll", args: [] });
      const r = await pub.waitForTransactionReceipt({ hash: tx });
      const liq2 = await pub.readContract({ address: USDC, abi: erc20, functionName: "balanceOf", args: [acct.address] });
      return out({ kind: "yield", action: "refill", protocol: `beefy:${bf.id}`, tx, status: r.status === "success" ? "0x1" : "0x0", refilled_usdc: Number(liq2 - liquid) / 1e6, reserve_usdc: RESERVE / 1e6, wallet: acct.address });
    }
  }

  // ---- HOLD: buffer is healthy, surplus too small to deploy. Positions keep accruing. ----
  out({ kind: "yield_hold", action: "hold", liquid_usdc: Number(liquid) / 1e6, reserve_usdc: RESERVE / 1e6, note: "buffer healthy" });
}
main().catch((e) => out({ error: String(e?.message || e) }));
