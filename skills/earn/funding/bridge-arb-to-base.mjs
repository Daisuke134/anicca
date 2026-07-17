#!/usr/bin/env node
// bridge-arb-to-base.mjs — RECOVER-1続: move claude-p's recovered Arbitrum USDC (HL withdraw proceeds)
// to Base USDC (its x402/operating wallet), same owner both ends (0x810f), no human in the loop.
// Copy+tweak of the proven relay.link flow in skills/earn/hl-trade/fund-hl.mjs (same quote+steps API).
//
// Key loading: reads ~/.anicca-founder/wallet.json directly (file→memory, never via stdout/env echo).
// Usage:
//   node bridge-arb-to-base.mjs --dry              # quote only
//   node bridge-arb-to-base.mjs [--amount-usd X]   # REAL bridge (default: full USDC balance minus $0.01)
// Prints exactly one JSON line.
import { readFileSync } from 'node:fs';
import { createWalletClient, createPublicClient, http, fallback } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { arbitrum } from 'viem/chains';

const USDC_ARB = '0xaf88d065e77c8cC2239327C5EDb3A432268e5831';
const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const MAX_FEE_PCT = Number(process.env.BRIDGE_MAX_FEE_PCT || 10);
const RPCS = ['https://arb1.arbitrum.io/rpc', 'https://arbitrum-one-rpc.publicnode.com', 'https://1rpc.io/arb'];

const DRY = process.argv.includes('--dry');
const amtArg = process.argv.indexOf('--amount-usd');

function out(o) { console.log(JSON.stringify(o)); return o; }

async function main() {
  const w = JSON.parse(readFileSync(`${process.env.HOME}/.anicca-founder/wallet.json`, 'utf8'));
  const account = privateKeyToAccount(w.private_key.startsWith('0x') ? w.private_key : `0x${w.private_key}`);
  const address = account.address;

  const pub = createPublicClient({ chain: arbitrum, transport: fallback(RPCS.map((u) => http(u, { timeout: 12000 }))) });
  const balUnits = await pub.readContract({
    address: USDC_ARB, abi: [{ name: 'balanceOf', type: 'function', stateMutability: 'view', inputs: [{ name: 'a', type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf', args: [address],
  });
  const balUsdc = Number(balUnits) / 1e6;
  const amountUsdc = amtArg > -1 ? Number(process.argv[amtArg + 1]) : Math.max(0, balUsdc - 0.01);
  if (!(amountUsdc > 0.5)) return out({ bridged: false, reason: 'amount too small', balUsdc });
  const amount = String(Math.floor(amountUsdc * 1e6));

  const q = await (await fetch('https://api.relay.link/quote', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user: address, recipient: address,
      originChainId: 42161, destinationChainId: 8453,
      originCurrency: USDC_ARB, destinationCurrency: USDC_BASE,
      amount, tradeType: 'EXACT_INPUT',
    }),
  })).json();
  if (!q?.details) return out({ bridged: false, reason: 'relay quote failed', detail: JSON.stringify(q).slice(0, 300) });

  const inUsd = Number(q.details.currencyIn?.amountUsd || amountUsdc);
  const outUsd = Number(q.details.currencyOut?.amountUsd || 0);
  const feeUsd = Math.max(0, inUsd - outUsd);
  const feePct = inUsd > 0 ? (feeUsd / inUsd) * 100 : 100;
  if (DRY) return out({ bridged: false, dry: true, address, balUsdc, amountUsdc, inUsd, outUsd, feeUsd: +feeUsd.toFixed(4), feePct: +feePct.toFixed(2), steps: (q.steps || []).map((s) => s.id) });
  if (feePct > MAX_FEE_PCT) return out({ bridged: false, reason: 'uneconomic', feeUsd: +feeUsd.toFixed(4), feePct: +feePct.toFixed(2) });

  const wallet = createWalletClient({ account, chain: arbitrum, transport: fallback(RPCS.map((u) => http(u, { timeout: 12000 }))) });
  const hashes = [];
  for (const step of q.steps || []) {
    for (const item of step.items || []) {
      const tx = item.data;
      if (!tx?.to) continue;
      const hash = await wallet.sendTransaction({ to: tx.to, data: tx.data, value: tx.value ? BigInt(tx.value) : 0n });
      await pub.waitForTransactionReceipt({ hash, timeout: 120000 });
      hashes.push({ step: step.id, hash });
    }
  }
  return out({ bridged: true, amountUsdc, outUsd: +outUsd.toFixed(4), feeUsd: +feeUsd.toFixed(4), hashes });
}

main().catch((e) => out({ bridged: false, reason: 'error', error: String(e?.message || e) }));
