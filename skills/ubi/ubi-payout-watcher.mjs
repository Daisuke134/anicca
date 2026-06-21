#!/usr/bin/env node
// UBI payout watcher (LOCAL — runs where anicca's wallet key lives).
// Polls Supabase `recipients` for status='queued' and pays a real USDC stipend:
//   - method=wallet : send straight to their Base address
//   - method=email  : create (or get) their Crossmint email-owned wallet, send there
// On success: status->'paid', tx + payout address written into notes. Idempotent.
//
// Env (from ~/.openclaw/.env): SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
//   BLOCKRUN_WALLET_KEY (execute-ubi), CROSSMINT_API_KEY (email wallets),
//   UBI_STIPEND_BASE (default 100000 = $0.10).
// Usage:
//   node ubi-payout-watcher.mjs          one pass
//   node ubi-payout-watcher.mjs --loop   poll forever (demo mode, every 8s)

import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const CROSSMINT_KEY = process.env.CROSSMINT_API_KEY;
const STIPEND_BASE = parseInt(process.env.UBI_STIPEND_BASE || '100000', 10); // $0.10
const WALLET_RE = /wallet=(0x[0-9a-fA-F]{40})/;
const METHOD_RE = /method=(\w+)/;
const __dirname = dirname(fileURLToPath(import.meta.url));

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.error('missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY');
  process.exit(1);
}

const sb = (path, init = {}) =>
  fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    ...init,
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  });

// Create (or get) a Crossmint smart wallet OWNED by an email; returns its Base address.
async function crossmintEmailWallet(email) {
  if (!CROSSMINT_KEY) throw new Error('no CROSSMINT_API_KEY');
  const res = await fetch('https://www.crossmint.com/api/2025-06-09/wallets', {
    method: 'POST',
    headers: { 'X-API-KEY': CROSSMINT_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chainType: 'evm',
      owner: `email:${email}`,
      config: { adminSigner: { type: 'email', email } },
    }),
  });
  const j = await res.json();
  if (!j.address) throw new Error('crossmint wallet: ' + JSON.stringify(j).slice(0, 160));
  return j.address; // deterministic per email; safe to call repeatedly
}

function payWallet(to, amountBase) {
  const plan = JSON.stringify({ transfers: [{ to, amount_base: amountBase }] });
  const out = execFileSync('python3', [join(__dirname, 'execute-ubi.py')], {
    env: { ...process.env, UBI_PLAN: plan },
    encoding: 'utf8',
  });
  const tx = JSON.parse(out.trim()).txs?.[0];
  if (!tx || tx.status !== '0x1') throw new Error('send not confirmed: ' + out.trim());
  return tx;
}

const RESERVE_BASE = parseInt(process.env.UBI_RESERVE_BASE || '1000000', 10); // keep $1 runway
const ANICCA_BASE_ADDR = 'a3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21';
const USDC_BASE_ADDR = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913';

async function aniccaUsdcBase() {
  const r = await fetch('https://mainnet.base.org', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_call', params: [{ to: USDC_BASE_ADDR, data: '0x70a08231000000000000000000000000' + ANICCA_BASE_ADDR }, 'latest'] }),
  });
  const j = await r.json();
  return j.result && j.result !== '0x' ? parseInt(j.result, 16) : 0;
}

function yourTurnEmail(email, method, usd) {
  // "your turn" email — best-effort, never blocks payout.
  try {
    execFileSync('gog', ['gmail', 'send', '--account', 'redacted@example.invalid', '--to', email,
      '--subject', "Your basic income arrived",
      '--body', `Anicca just sent you $${usd} (USDC on Base). ${method === 'email'
        ? 'Sign in at https://aniccaai.com/income/wallet with this email to see and use it.'
        : 'Check your wallet or basescan.org.'} More comes as Anicca earns more.`],
      { stdio: 'ignore', timeout: 30000 });
  } catch (e) { /* email is best-effort */ }
}

async function pass() {
  // FIFO: oldest signups first (a queue/right, not a lottery).
  const res = await sb('recipients?status=eq.queued&select=id,email,notes,applied_at&order=applied_at.asc.nullslast');
  if (!res.ok) throw new Error('supabase read ' + res.status);
  const rows = await res.json();
  // DEDUP GUARD (anti-drain): never pay an email or wallet that was already paid.
  const paidRes = await sb('recipients?status=eq.paid&select=email,notes');
  const paidRows = paidRes.ok ? await paidRes.json() : [];
  const paidEmails = new Set(paidRows.map((p) => (p.email || '').toLowerCase()).filter(Boolean));
  const paidWallets = new Set(paidRows.map((p) => ((p.notes || '').match(WALLET_RE) || [])[1]).filter(Boolean));
  let paid = 0;
  let bal = await aniccaUsdcBase(); // reserve floor: stop before draining below runway
  for (const r of rows) {
    const notes = r.notes || '';
    const method = (notes.match(METHOD_RE) || [])[1];
    if (method !== 'wallet' && method !== 'email') continue; // bank/card handled elsewhere
    const wAddr = (notes.match(WALLET_RE) || [])[1];
    if (paidEmails.has((r.email || '').toLowerCase()) || (wAddr && paidWallets.has(wAddr))) {
      await sb(`recipients?id=eq.${r.id}`, { method: 'PATCH', headers: { Prefer: 'return=minimal' }, body: JSON.stringify({ status: 'duplicate' }) });
      console.log(`SKIP duplicate ${method} ${r.email}`);
      continue;
    }
    try {
      let to;
      if (method === 'wallet') {
        to = (notes.match(WALLET_RE) || [])[1];
        if (!to) continue;
      } else {
        to = await crossmintEmailWallet(r.email); // email → their Crossmint wallet
      }
      if (bal - STIPEND_BASE < RESERVE_BASE) {
        console.log(`RESERVE floor reached (bal $${bal / 1e6}); ${r.email} stays queued (their turn comes when funds grow)`);
        break; // FIFO: leave the rest queued, pay them next cycle when topped up
      }
      const tx = payWallet(to, STIPEND_BASE);
      bal -= tx.amount_base;
      await sb(`recipients?id=eq.${r.id}`, {
        method: 'PATCH',
        headers: { Prefer: 'return=minimal' },
        body: JSON.stringify({ status: 'paid', notes: `${notes};payout_addr=${to};paid_tx=${tx.tx};paid_base=${tx.amount_base}` }),
      });
      paid++;
      console.log(`PAID ${method} ${r.email} -> ${to} $${tx.amount_base / 1e6} tx=${tx.tx}`);
      if (r.email) yourTurnEmail(r.email, method, tx.amount_base / 1e6);
    } catch (e) {
      console.error(`FAIL ${method} ${r.email}: ${e.message}`);
    }
  }
  return { queued: rows.length, paid };
}

async function main() {
  const loop = process.argv.includes('--loop');
  if (!loop) {
    const r = await pass();
    console.log(`done queued=${r.queued} paid=${r.paid}`);
    return;
  }
  console.log('watcher loop started (every 8s). Ctrl-C to stop.');
  // eslint-disable-next-line no-constant-condition
  while (true) {
    try {
      const r = await pass();
      if (r.paid) console.log(`[tick] paid ${r.paid}`);
    } catch (e) {
      console.error('[tick] err', e.message);
    }
    await new Promise((res) => setTimeout(res, 8000));
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
