#!/usr/bin/env node
// UBI payout watcher (LOCAL — runs where anicca's wallet key lives).
// Reads queued signups from Supabase `recipients`, pays the WALLET ones a real
// USDC stipend via execute-ubi.py (anicca's key), marks them paid. Idempotent:
// only rows with status='queued' are touched; on success status->'paid' + tx in notes.
//
// Env (from ~/.openclaw/.env): SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
//   BLOCKRUN_WALLET_KEY (execute-ubi reads it), UBI_STIPEND_BASE (default 100000 = $0.10).
// Usage: node ubi-payout-watcher.mjs            (one pass; pay all queued wallet rows)

import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const STIPEND_BASE = parseInt(process.env.UBI_STIPEND_BASE || '100000', 10); // $0.10
const WALLET_RE = /wallet=(0x[0-9a-fA-F]{40})/;
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

function payWallet(to, amountBase) {
  // execute-ubi.py reads UBI_PLAN, signs with anicca's key, sends on Base, prints {"txs":[...]}.
  const plan = JSON.stringify({ transfers: [{ to, amount_base: amountBase }] });
  const out = execFileSync('python3', [join(__dirname, 'execute-ubi.py')], {
    env: { ...process.env, UBI_PLAN: plan },
    encoding: 'utf8',
  });
  const parsed = JSON.parse(out.trim());
  const tx = parsed.txs?.[0];
  if (!tx || tx.status !== '0x1') throw new Error(`send not confirmed: ${out.trim()}`);
  return tx; // {to, tx, amount_base, status}
}

async function main() {
  const res = await sb('recipients?status=eq.queued&select=id,email,notes');
  if (!res.ok) throw new Error(`supabase read ${res.status}`);
  const rows = await res.json();
  const walletRows = rows.filter((r) => (r.notes || '').includes('method=wallet') && WALLET_RE.test(r.notes || ''));
  console.log(`queued=${rows.length} wallet-payable=${walletRows.length}`);

  for (const r of walletRows) {
    const to = (r.notes.match(WALLET_RE) || [])[1];
    try {
      const tx = payWallet(to, STIPEND_BASE);
      const upd = await sb(`recipients?id=eq.${r.id}`, {
        method: 'PATCH',
        headers: { Prefer: 'return=minimal' },
        body: JSON.stringify({
          status: 'paid',
          notes: `${r.notes};paid_tx=${tx.tx};paid_base=${tx.amount_base}`,
        }),
      });
      console.log(`PAID ${r.email} ${to} amount_base=${tx.amount_base} tx=${tx.tx} (mark ${upd.status})`);
    } catch (e) {
      console.error(`FAIL ${r.email} ${to}: ${e.message}`);
    }
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
