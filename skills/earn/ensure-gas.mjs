// ensure-gas.mjs — keep a minimum native-gas (ETH) floor so an Anicca never gas-stalls.
// The recurring failure mode: a wallet funded only in USDC (or drained by a bridge) has no native
// ETH, so it cannot send ANY transaction (deposit yield, buy blue-chip, trade) — value is stranded.
// This runs before any tx-doing earn strategy: if native ETH < MIN_GAS_ETH, it restores gas with the
// cheapest source available — unwrap a little WETH (the blue-chip leg already holds some), or, if no
// WETH, swap a small USDC amount to WETH then unwrap. No human, no bridge, no external help.
import { createPublicClient, createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import fs from "fs";
import { loadEvmKey } from "./lib/resolve-identity.mjs";

const RPC = process.env.BASE_RPC_URL || "https://mainnet.base.org";
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const WETH = "0x4200000000000000000000000000000000000006";
const ROUTER = "0x2626664c2603336E57B271c5C0b26F421741e481";
const MIN_GAS_ETH = parseFloat(process.env.MIN_GAS_ETH || "0.0003");   // floor (~$0.5)
const TOPUP_ETH = parseFloat(process.env.GAS_TOPUP_ETH || "0.0006");   // restore target
const SWAP_USD = parseFloat(process.env.GAS_SWAP_USD || "2");          // if no WETH, swap this much USDC->WETH first

function out(o) { process.stdout.write(JSON.stringify(o) + "\n"); }
// #28: env-first (PKVAR indirection / BLOCKRUN_WALLET_KEY) then GATED per-instance file resolution.
// Never read the shared $HOME/.automaton/wallet.json directly (that let a foreign spawn sign with
// another instance's key). null → main() aborts ("no wallet key").
function loadKey() { return loadEvmKey(); }
const erc20 = [
  { name: "approve", type: "function", stateMutability: "nonpayable", inputs: [{ type: "address" }, { type: "uint256" }], outputs: [{ type: "bool" }] },
  { name: "balanceOf", type: "function", stateMutability: "view", inputs: [{ type: "address" }], outputs: [{ type: "uint256" }] },
  { name: "withdraw", type: "function", stateMutability: "nonpayable", inputs: [{ type: "uint256" }], outputs: [] }, // WETH unwrap -> native ETH
];
const router = [{ name: "exactInputSingle", type: "function", stateMutability: "payable", inputs: [{ type: "tuple", components: [{ name: "tokenIn", type: "address" }, { name: "tokenOut", type: "address" }, { name: "fee", type: "uint24" }, { name: "recipient", type: "address" }, { name: "amountIn", type: "uint256" }, { name: "amountOutMinimum", type: "uint256" }, { name: "sqrtPriceLimitX96", type: "uint160" }] }], outputs: [{ type: "uint256" }] }];

async function main() {
  const pk = loadKey();
  if (!pk) return out({ abort: "no wallet key" });
  const acct = privateKeyToAccount(pk);
  const pub = createPublicClient({ chain: base, transport: http(RPC) });
  const w = createWalletClient({ account: acct, chain: base, transport: http(RPC) });

  const ethBal = Number(await pub.getBalance({ address: acct.address })) / 1e18;
  if (ethBal >= MIN_GAS_ETH) return out({ kind: "gas_ok", eth: +ethBal.toFixed(6), floor: MIN_GAS_ETH });
  if (ethBal === 0) return out({ abort: "zero gas — cannot self-restore (need a one-time external gas seed)" });

  const need = TOPUP_ETH - ethBal;                 // ETH to restore
  let wethBal = Number(await pub.readContract({ address: WETH, abi: erc20, functionName: "balanceOf", args: [acct.address] })) / 1e18;

  // if not enough WETH to unwrap, swap a little USDC -> WETH first (uses the 1-2 txs of gas we still have)
  if (wethBal < need) {
    const usdc = Number(await pub.readContract({ address: USDC, abi: erc20, functionName: "balanceOf", args: [acct.address] })) / 1e6;
    if (usdc < SWAP_USD) return out({ abort: `gas low (${ethBal.toFixed(6)} ETH) but no WETH and < $${SWAP_USD} USDC to source it` });
    const amountIn = BigInt(Math.floor(SWAP_USD * 1e6));
    const ah = await w.writeContract({ address: USDC, abi: erc20, functionName: "approve", args: [ROUTER, amountIn] });
    await pub.waitForTransactionReceipt({ hash: ah, confirmations: 2 });
    const sx = await w.writeContract({ address: ROUTER, abi: router, functionName: "exactInputSingle", args: [{ tokenIn: USDC, tokenOut: WETH, fee: 500, recipient: acct.address, amountIn, amountOutMinimum: 0n, sqrtPriceLimitX96: 0n }] });
    await pub.waitForTransactionReceipt({ hash: sx });
    wethBal = Number(await pub.readContract({ address: WETH, abi: erc20, functionName: "balanceOf", args: [acct.address] })) / 1e18;
  }

  const unwrap = Math.min(need, wethBal);
  if (unwrap <= 0) return out({ abort: "no WETH to unwrap" });
  const tx = await w.writeContract({ address: WETH, abi: erc20, functionName: "withdraw", args: [BigInt(Math.floor(unwrap * 1e18))] });
  const r = await pub.waitForTransactionReceipt({ hash: tx });
  const after = Number(await pub.getBalance({ address: acct.address })) / 1e18;
  out({ kind: "gas_restored", tx, status: r.status, eth_before: +ethBal.toFixed(6), eth_after: +after.toFixed(6), unwrapped_eth: +unwrap.toFixed(6) });
}
main().catch((e) => out({ error: String(e?.message || e) }));
