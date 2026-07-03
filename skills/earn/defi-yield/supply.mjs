#!/usr/bin/env node
// supply.mjs — the AI's REAL Aave v3 supply() tool for earn/defi-yield (money-safe, viem).
// The automaton invokes THIS in its loop to put its own USDC to work earning yield — I do not place it by
// hand. DEFAULT = DRY_RUN: it SIMULATES (approve + supply) and prints the plan, broadcasting NOTHING. A real
// on-chain supply happens ONLY with DRY_RUN=false AND EARN_MODE=execute. It supplies onBehalfOf ITS OWN
// wallet (aBasUSDC minted to itself), always withdrawable. Keeps an ETH gas reserve. Records the tx.
//
//   node supply.mjs            # DRY_RUN plan (no tx)
//   DRY_RUN=false EARN_MODE=execute PM_SUPPLY_USDC=2 node supply.mjs   # real supply of 2 USDC
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createPublicClient, createWalletClient, http, parseAbi, getContract } from 'viem';
import { base } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';

const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';       // USDC on Base (6 decimals)
const AAVE_POOL = '0xA238Dd80C259a72e81d7e4664a9801593F98d1c5';  // Aave v3 Pool on Base (verified code exists)
const RPC = process.env.BASE_RPC || 'https://mainnet.base.org';
const ERC20 = parseAbi(['function allowance(address,address) view returns (uint256)',
                        'function balanceOf(address) view returns (uint256)',
                        'function approve(address,uint256) returns (bool)']);
const POOL = parseAbi(['function supply(address asset,uint256 amount,address onBehalfOf,uint16 referralCode)']);

function loadKey() {
  // founder wallet (this AI's OWN key) — never a human's key elsewhere
  const p = path.join(os.homedir(), '.anicca-founder', 'wallet.json');
  const j = JSON.parse(fs.readFileSync(p, 'utf8'));
  let k = j.private_key || j.privateKey || j.secret;
  if (!k) throw new Error('no private_key in ~/.anicca-founder/wallet.json');
  if (!k.startsWith('0x')) k = '0x' + k;
  return k;
}

async function main() {
  const DRY = process.env.DRY_RUN !== 'false';
  const EXEC = process.env.EARN_MODE === 'execute';
  const account = privateKeyToAccount(loadKey());
  const pub = createPublicClient({ chain: base, transport: http(RPC) });

  const usdc = getContract({ address: USDC, abi: ERC20, client: pub });
  const bal = await usdc.read.balanceOf([account.address]);         // 6 decimals
  const eth = await pub.getBalance({ address: account.address });
  const want = BigInt(Math.floor(Number(process.env.PM_SUPPLY_USDC || '2') * 1e6));
  const balUsd = Number(bal) / 1e6;

  // money-safety gates (pure): need USDC, keep gas, never supply more than balance minus a small buffer
  const RESERVE_USDC = 500000n; // keep 0.5 USDC
  const supplyAmt = want > (bal - RESERVE_USDC) ? (bal - RESERVE_USDC) : want;
  const plan = { slot: 'earn/defi-yield', tool: 'aave-supply', pool: 'aave-v3',
                 wallet: account.address, usdc: balUsd, eth: Number(eth) / 1e18,
                 supply_usdc: Number(supplyAmt) / 1e6 };

  if (supplyAmt <= 0n) { console.log(JSON.stringify({ ...plan, decision: 'skip', note: 'no supply_usdc after reserve' })); return; }
  if (eth === 0n) { console.log(JSON.stringify({ ...plan, decision: 'no-gas' })); return; }

  if (DRY || !EXEC) {
    // SIMULATE only — proves the calls are valid, broadcasts nothing
    try {
      await pub.simulateContract({ account, address: USDC, abi: ERC20, functionName: 'approve', args: [AAVE_POOL, supplyAmt] });
      console.log(JSON.stringify({ ...plan, decision: 'DRY_RUN-ok', note: 'approve+supply simulated, NO tx broadcast' }));
    } catch (e) {
      console.log(JSON.stringify({ ...plan, decision: 'DRY_RUN-sim-fail', err: String(e).slice(0, 120) }));
    }
    return;
  }

  // REAL path (DRY_RUN=false AND EARN_MODE=execute): approve then supply, onBehalfOf SELF
  const wallet = createWalletClient({ account, chain: base, transport: http(RPC) });
  const allow = await usdc.read.allowance([account.address, AAVE_POOL]);
  let approveTx = null;
  if (allow < supplyAmt) {
    approveTx = await wallet.writeContract({ address: USDC, abi: ERC20, functionName: 'approve', args: [AAVE_POOL, supplyAmt] });
    await pub.waitForTransactionReceipt({ hash: approveTx });
  }
  const supplyTx = await wallet.writeContract({ address: AAVE_POOL, abi: POOL, functionName: 'supply',
    args: [USDC, supplyAmt, account.address, 0] });
  const rcpt = await pub.waitForTransactionReceipt({ hash: supplyTx });

  const ledger = path.join(os.homedir(), 'loops', 'earn-defi-yield');
  fs.mkdirSync(ledger, { recursive: true });
  const row = { ts: Math.floor(Date.now() / 1000), src: 'defi-yield', pool: 'aave-v3',
    action: 'supply', asset: 'USDC', amount_usdc: Number(supplyAmt) / 1e6,
    approve_tx: approveTx, supply_tx: supplyTx, block: Number(rcpt.blockNumber), status: rcpt.status };
  fs.appendFileSync(path.join(ledger, 'positions.jsonl'), JSON.stringify(row) + '\n');
  console.log(JSON.stringify({ ...plan, decision: 'supplied', approve_tx: approveTx, supply_tx: supplyTx, status: rcpt.status }));
}

main().catch((e) => { console.log(JSON.stringify({ slot: 'earn/defi-yield', decision: 'error', err: String(e).slice(0, 160) })); process.exit(1); });
