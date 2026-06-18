// execute-yield.mjs — earn_yield (the GOAT earner): deploy idle USDC into DeFi yield.
//
// Anicca's reliable, always-available earner. Supplies idle USDC into Aave v3 on Base
// (the agent's own capital earns the market lending rate — net worth grows via accrual,
// withdrawable any time). This is NOT external revenue (external:false) — it is yield on
// own capital — so it is recorded honestly as kind:"yield" and never faked as a GATE-0
// external payout. The earning shows up as the aToken (aUSDC) balance growing over time.
//
// Idempotent + safe: keeps a small USDC reserve, aborts cleanly if nothing to deploy or
// no ETH for gas. Prints a single JSON line for run.sh to record.
//
// Env: PKVAR | BLOCKRUN_WALLET_KEY (wallet key), BASE_RPC_URL, YIELD_RESERVE_USDC (default 0.5),
//      YIELD_MIN_DEPLOY_USDC (default 0.5).
import { createPublicClient, createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import fs from "fs";

const RPC = process.env.BASE_RPC_URL || "https://mainnet.base.org";
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const AAVE_POOL = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5"; // Aave v3 Pool, Base
const AUSDC = "0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB";     // aBasUSDC
// Reserve must keep enough LIQUID USDC for compute: ClawRouter `auto` pays per-inference x402
// from liquid USDC, so a frontier model is only affordable while liquid stays funded. Only the
// SURPLUS above this runway buffer is deployed into yield. (Earlier $0.5 starved compute → the
// loop fell back to a free model despite a funded wallet.)
const RESERVE = Math.round(parseFloat(process.env.YIELD_RESERVE_USDC || "5") * 1e6);
const MIN_DEPLOY = Math.round(parseFloat(process.env.YIELD_MIN_DEPLOY_USDC || "1") * 1e6);

function out(o) { process.stdout.write(JSON.stringify(o) + "\n"); }

function loadKey() {
  const k = process.env.PKVAR || process.env.BLOCKRUN_WALLET_KEY;
  if (k) return k.startsWith("0x") ? k : "0x" + k;
  try {
    const w = JSON.parse(fs.readFileSync(process.env.HOME + "/.automaton/wallet.json", "utf8"));
    return w.privateKey.startsWith("0x") ? w.privateKey : "0x" + w.privateKey;
  } catch { return null; }
}

const erc20 = [
  { name: "approve", type: "function", stateMutability: "nonpayable", inputs: [{ type: "address" }, { type: "uint256" }], outputs: [{ type: "bool" }] },
  { name: "allowance", type: "function", stateMutability: "view", inputs: [{ type: "address" }, { type: "address" }], outputs: [{ type: "uint256" }] },
  { name: "balanceOf", type: "function", stateMutability: "view", inputs: [{ type: "address" }], outputs: [{ type: "uint256" }] },
];
const pool = [{ name: "supply", type: "function", stateMutability: "nonpayable", inputs: [{ type: "address" }, { type: "uint256" }, { type: "address" }, { type: "uint16" }], outputs: [] }];

async function main() {
  const pk = loadKey();
  if (!pk) return out({ abort: "no wallet key" });
  const acct = privateKeyToAccount(pk);
  const pub = createPublicClient({ chain: base, transport: http(RPC) });
  const w = createWalletClient({ account: acct, chain: base, transport: http(RPC) });

  const eth = await pub.getBalance({ address: acct.address });
  if (eth === 0n) return out({ abort: "no ETH for gas", wallet: acct.address });

  const bal = await pub.readContract({ address: USDC, abi: erc20, functionName: "balanceOf", args: [acct.address] });
  const deployable = bal - BigInt(RESERVE);
  if (deployable < BigInt(MIN_DEPLOY)) {
    return out({ abort: "no idle USDC to deploy", wallet: acct.address, usdc: Number(bal) / 1e6, reserve_usdc: RESERVE / 1e6 });
  }

  const aBefore = await pub.readContract({ address: AUSDC, abi: erc20, functionName: "balanceOf", args: [acct.address] });

  // approve (idempotent: only if allowance < deployable)
  let alw = await pub.readContract({ address: USDC, abi: erc20, functionName: "allowance", args: [acct.address, AAVE_POOL] });
  if (alw < deployable) {
    const ah = await w.writeContract({ address: USDC, abi: erc20, functionName: "approve", args: [AAVE_POOL, deployable] });
    await pub.waitForTransactionReceipt({ hash: ah, confirmations: 2 });
    alw = await pub.readContract({ address: USDC, abi: erc20, functionName: "allowance", args: [acct.address, AAVE_POOL] });
    if (alw < deployable) return out({ error: "approve did not stick", wallet: acct.address });
  }

  const th = await w.writeContract({ address: AAVE_POOL, abi: pool, functionName: "supply", args: [USDC, deployable, acct.address, 0] });
  const r = await pub.waitForTransactionReceipt({ hash: th });
  const aAfter = await pub.readContract({ address: AUSDC, abi: erc20, functionName: "balanceOf", args: [acct.address] });

  out({
    kind: "yield",
    protocol: "aave-v3-base",
    tx: th,
    status: r.status === "success" ? "0x1" : "0x0",
    deposited_usdc: Number(deployable) / 1e6,
    ausdc_before: Number(aBefore) / 1e6,
    ausdc_after: Number(aAfter) / 1e6,
    wallet: acct.address,
  });
}
main().catch((e) => out({ error: String(e?.message || e) }));
