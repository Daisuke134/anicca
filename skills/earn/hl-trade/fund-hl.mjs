#!/usr/bin/env node
// fund-hl.mjs — let Anicca fund its OWN Hyperliquid perps account from its OWN Base USDC, with NO human
// and NO other AI in the loop. One step: relay.link bridges Base USDC → Hyperliquid (chain 1337), the
// deposit credits Anicca's HL trading balance. Then hl.py can open a real perp.
//
// ECONOMIC GUARD (the honest part): the Base→HL deposit has a ~fixed ~$1.2 relay/bridge cost, so small
// amounts bleed 30-40% (verified: $3 in → $1.78 out, fee $1.22 = 40%). Bridging tiny capital would just
// burn money. So fund-hl REFUSES to bridge unless the fee is under MAX_FEE_PCT of the amount — i.e. it
// only funds HL once Anicca has enough capital for it to make sense (~$40+ → fee <3%). Below that it
// records why and does nothing. This is "don't fake / don't waste real money", enforced in code.
//
// Env: FUND_HL_USDC (amount to bridge, default from caller), PKVAR (env var NAME holding the key),
//      HL_MAX_FEE_PCT (default 5). Prints JSON result; never throws uncaught (fails closed).
import { createWalletClient, createPublicClient, http, fallback, encodeFunctionData } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';

const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const HL_USDC = '0x00000000000000000000000000000000'; // relay's "USDC (Perps)" on chain 1337
const MAX_FEE_PCT = Number(process.env.HL_MAX_FEE_PCT || 5);
const RPCS = ['https://base.llamarpc.com', 'https://base-rpc.publicnode.com', 'https://base.drpc.org', 'https://1rpc.io/base', 'https://mainnet.base.org'];

function loadKey() {
  const k = (process.env.PKVAR && process.env[process.env.PKVAR]) || process.env.BLOCKRUN_WALLET_KEY;
  if (!k) throw new Error('no key (PKVAR/BLOCKRUN_WALLET_KEY)');
  return k.startsWith('0x') ? k : `0x${k}`;
}

async function main() {
  const amountUsdc = Number(process.env.FUND_HL_USDC || 0);
  if (!(amountUsdc > 0)) return out({ funded: false, reason: 'no amount' });

  const amount = String(Math.floor(amountUsdc * 1e6));
  // address only (no key) — needed for the quote + the economic guard, which run BEFORE any signing.
  const address = process.env.ANICCA_WALLET_ADDRESS || '0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21';

  // 1) quote relay Base USDC -> Hyperliquid
  const q = await (await fetch('https://api.relay.link/quote', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user: address, recipient: address,
      originChainId: 8453, destinationChainId: 1337,
      originCurrency: USDC_BASE, destinationCurrency: HL_USDC,
      amount, tradeType: 'EXACT_INPUT',
    }),
  })).json();
  if (!q?.details) return out({ funded: false, reason: 'relay quote failed', detail: JSON.stringify(q).slice(0, 200) });

  const inUsd = Number(q.details.currencyIn?.amountUsd || amountUsdc);
  const outUsd = Number(q.details.currencyOut?.amountUsd || 0);
  const feeUsd = Math.max(0, inUsd - outUsd);
  const feePct = inUsd > 0 ? (feeUsd / inUsd) * 100 : 100;

  // 2) ECONOMIC GUARD — refuse uneconomic bridges instead of burning real money.
  if (feePct > MAX_FEE_PCT) {
    return out({
      funded: false, reason: 'uneconomic',
      note: `Base→HL fee ${feePct.toFixed(1)}% (>${MAX_FEE_PCT}%) on $${amountUsdc}. HL needs more capital ` +
            `(fee is ~fixed ~$${feeUsd.toFixed(2)}); bridge bigger or earn more first.`,
      feeUsd: Number(feeUsd.toFixed(4)), outUsd: Number(outUsd.toFixed(4)),
    });
  }

  // 3) economic — now load the key and execute the relay steps (approve + deposit) with Anicca's own key.
  const account = privateKeyToAccount(loadKey());
  const wallet = createWalletClient({ account, chain: base, transport: fallback(RPCS.map((u) => http(u, { timeout: 12000 }))) });
  const pub = createPublicClient({ chain: base, transport: fallback(RPCS.map((u) => http(u, { timeout: 12000 }))) });
  const hashes = [];
  for (const step of q.steps || []) {
    for (const item of step.items || []) {
      const tx = item.data;
      if (!tx?.to) continue;
      const hash = await wallet.sendTransaction({
        to: tx.to, data: tx.data, value: tx.value ? BigInt(tx.value) : 0n,
      });
      await pub.waitForTransactionReceipt({ hash, timeout: 120000 });
      hashes.push({ step: step.id, hash });
    }
  }
  return out({ funded: true, amountUsdc, outUsd: Number(outUsd.toFixed(4)), feeUsd: Number(feeUsd.toFixed(4)), hashes });
}

function out(o) { console.log(JSON.stringify(o)); return o; }

main().catch((e) => out({ funded: false, reason: 'error', error: String(e?.message || e) }));
