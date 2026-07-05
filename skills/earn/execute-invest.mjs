// execute-invest.mjs — the INVESTING leg of the earn skill (the 3rd honest way to make money,
// alongside yield and x402 products). NOT gambling: this is risk-managed, no-leverage, blue-chip
// dollar-cost-averaging — the crypto equivalent of buying the S&P 500. Anicca holds a capped target
// allocation in ETH (a blue-chip), buying small steps when under-allocated. Capital compounds with
// the asset over time; a single buy can never blow the treasury because the allocation is capped and
// a liquid compute buffer is always preserved.
//
// Risk rules (hard): never exceed INVEST_TARGET_PCT of investable capital in the blue-chip; never
// spend the compute buffer (COMPUTE_RESERVE_USDC); buy in small INVEST_STEP_USD steps (DCA);
// no leverage, no perps, no memecoins. Higher-risk active strategies (Hyperliquid/AutoHedge) are
// verified separately and only added once proven — this leg is the safe, always-valid investment.
import { createPublicClient, createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { loadEvmKey } from "./lib/resolve-identity.mjs";
import { base } from "viem/chains";
import fs from "fs";

const RPC = process.env.BASE_RPC_URL || "https://mainnet.base.org";
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const WETH = "0x4200000000000000000000000000000000000006";          // blue-chip ETH
const ROUTER = "0x2626664c2603336E57B271c5C0b26F421741e481";        // Uniswap SwapRouter02 (Base)
const RESERVE = parseFloat(process.env.COMPUTE_RESERVE_USDC || "5"); // liquid kept for compute
const TARGET_PCT = parseFloat(process.env.INVEST_TARGET_PCT || "0.30"); // max blue-chip share of investable
const STEP_USD = parseFloat(process.env.INVEST_STEP_USD || "1");     // DCA step size per wake
const FEE = 500;

function out(o) { process.stdout.write(JSON.stringify(o) + "\n"); }
// #28: env-first (PKVAR indirection / BLOCKRUN_WALLET_KEY) then GATED per-instance file resolution.
// Never read the shared $HOME wallet directly (a foreign spawn would sign with another instance's key).
function loadKey() { return loadEvmKey(); }
const erc20 = [
  { name: "approve", type: "function", stateMutability: "nonpayable", inputs: [{ type: "address" }, { type: "uint256" }], outputs: [{ type: "bool" }] },
  { name: "balanceOf", type: "function", stateMutability: "view", inputs: [{ type: "address" }], outputs: [{ type: "uint256" }] },
];
const router = [{ name: "exactInputSingle", type: "function", stateMutability: "payable", inputs: [{ type: "tuple", components: [{ name: "tokenIn", type: "address" }, { name: "tokenOut", type: "address" }, { name: "fee", type: "uint24" }, { name: "recipient", type: "address" }, { name: "amountIn", type: "uint256" }, { name: "amountOutMinimum", type: "uint256" }, { name: "sqrtPriceLimitX96", type: "uint160" }] }], outputs: [{ type: "uint256" }] }];

async function ethPrice() {
  try { const r = await fetch("https://api.coinbase.com/v2/prices/ETH-USD/spot"); return Number((await r.json()).data.amount) || 0; } catch { return 0; }
}

async function main() {
  const pk = loadKey();
  if (!pk) return out({ abort: "no wallet key" });
  const acct = privateKeyToAccount(pk);
  const pub = createPublicClient({ chain: base, transport: http(RPC) });
  const w = createWalletClient({ account: acct, chain: base, transport: http(RPC) });
  if ((await pub.getBalance({ address: acct.address })) === 0n) return out({ abort: "no ETH for gas" });

  const liquid = Number(await pub.readContract({ address: USDC, abi: erc20, functionName: "balanceOf", args: [acct.address] })) / 1e6;
  const wethBal = Number(await pub.readContract({ address: WETH, abi: erc20, functionName: "balanceOf", args: [acct.address] })) / 1e18;
  const ep = await ethPrice();
  if (!ep) return out({ abort: "no ETH price" });

  const bluechipUsd = wethBal * ep;
  const investable = Math.max(0, liquid - RESERVE);          // never touch the compute buffer
  const portfolio = bluechipUsd + investable;                // capital eligible for the blue-chip target
  const targetUsd = portfolio * TARGET_PCT;
  // already at/over target, or no investable headroom → hold
  if (bluechipUsd >= targetUsd - 0.01 || investable < STEP_USD) {
    return out({ kind: "invest_hold", asset: "ETH", bluechip_usd: +bluechipUsd.toFixed(2), target_usd: +targetUsd.toFixed(2), liquid_usd: +liquid.toFixed(2), note: "blue-chip allocation satisfied / no investable headroom" });
  }
  // DCA one capped step toward the target (never more than the step, the gap, or the investable headroom)
  const buyUsd = Math.min(STEP_USD, targetUsd - bluechipUsd, investable);
  const amountIn = BigInt(Math.floor(buyUsd * 1e6));
  const ah = await w.writeContract({ address: USDC, abi: erc20, functionName: "approve", args: [ROUTER, amountIn] });
  await pub.waitForTransactionReceipt({ hash: ah, confirmations: 2 });
  const tx = await w.writeContract({ address: ROUTER, abi: router, functionName: "exactInputSingle", args: [{ tokenIn: USDC, tokenOut: WETH, fee: FEE, recipient: acct.address, amountIn, amountOutMinimum: 0n, sqrtPriceLimitX96: 0n }] });
  const r = await pub.waitForTransactionReceipt({ hash: tx });
  out({ kind: "invest", action: "dca_buy", asset: "ETH", tx, status: r.status === "success" ? "0x1" : "0x0", bought_usd: +buyUsd.toFixed(2), bluechip_usd_before: +bluechipUsd.toFixed(2), target_usd: +targetUsd.toFixed(2), eth_price: ep, wallet: acct.address });
}
main().catch((e) => out({ error: String(e?.message || e) }));
