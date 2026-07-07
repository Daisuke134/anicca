#!/usr/bin/env node
// fund-hl.mjs — let Anicca fund its OWN Hyperliquid perps account from its OWN Base USDC, with NO human
// and NO other AI in the loop. One step: relay.link bridges Base USDC → Hyperliquid (chain 1337), the
// deposit credits Anicca's HL trading balance. Then hl.py can open a real perp.
//
// ECONOMIC GUARD (corrected): the Base→HL deposit has a ~fixed ~$1.2 relay cost, but this is a ONE-TIME
// ENTRY fee — once funded, Anicca trades on HL repeatedly with NO further bridge cost, so the fee
// AMORTIZES over every future trade. The earlier "30-40% per trade" framing was wrong (it's a one-time
// deposit, not recurring). So the guard only blocks ABSURDLY tiny deposits where even a one-time $1.2 is
// silly (e.g. funding $2). Default HL_MAX_FEE_PCT=20 → allows ~$6+ deposits; below that it records
// "needs more capital". This keeps "don't waste money" without giving up on HL when real capital exists.
//
// Env: FUND_HL_USDC (amount to bridge, default from caller), PKVAR (env var NAME holding the key),
//      HL_MAX_FEE_PCT (default 5). Prints JSON result; never throws uncaught (fails closed).
import { createWalletClient, createPublicClient, http, fallback, encodeFunctionData } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';

const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const HL_USDC = '0x00000000000000000000000000000000'; // relay's "USDC (Perps)" on chain 1337
const MAX_FEE_PCT = Number(process.env.HL_MAX_FEE_PCT || 20); // one-time entry fee; amortizes over trades
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
  // Derive address from THIS instance's actual signing key (never a separate hardcoded/env fallback --
  // that used to be able to drift from the real signer, so a quote/recipient could silently point at a
  // DIFFERENT address than the one that actually signs+pays for the bridge tx; rotated 2026-07-07).
  const account = privateKeyToAccount(loadKey());
  const address = account.address;

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

  // 3) economic — execute the relay steps (approve + deposit) with the SAME key/address used for the quote above.
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
