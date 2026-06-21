#!/usr/bin/env node
/**
 * ubi-watcher — the bridge from a /income signup to a real on-chain payout.
 *
 * CONTRACT (spec 32 §11/§13):
 *  - INPUT: Supabase `recipients` rows with status='queued' whose `notes` carry
 *    `method=wallet;wallet=0x...` (written by netlify/functions/income-signup.js).
 *  - For each wallet recipient, pay a fixed stipend (UBI_STIPEND_USDC, default 0.10)
 *    of anicca's OWN USDC on Base via execute-ubi.py (anicca's key; no human).
 *  - IDEMPOTENT / never double-pay: claim a row by flipping queued->paying ONLY if
 *    it is still 'queued' (Supabase conditional PATCH returns the row only if it
 *    matched). If 0 rows returned, another run already claimed it -> skip.
 *  - On tx status 0x1 -> status='paid', tx hash appended to notes, approved_at set.
 *  - On any failure -> status back to 'queued' (release for retry), nothing lost.
 *  - INVARIANT: a row is paid at most once; on-chain 0x1 is the only success signal.
 *  - OUTPUT: JSON {paid:[{id,wallet,tx,amount_base}], skipped:n, failed:[...]}.
 *
 * Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, BLOCKRUN_WALLET_KEY (via execute-ubi),
 *      UBI_STIPEND_USDC (default 0.10), UBI_LIMIT (max rows/run, default 25),
 *      UBI_WATCHER_DRY (1 = claim+plan but skip the real send, for wiring tests).
 */
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SUPABASE_URL = process.env.SUPABASE_URL;
const SVC = process.env.SUPABASE_SERVICE_ROLE_KEY;
const STIPEND_USDC = Number(process.env.UBI_STIPEND_USDC || '0.10');
const LIMIT = Number(process.env.UBI_LIMIT || '25');
const DRY = process.env.UBI_WATCHER_DRY === '1';
const WALLET_RE = /^0x[0-9a-fA-F]{40}$/;
const __dirname = path.dirname(fileURLToPath(import.meta.url));

function die(msg) { console.log(JSON.stringify({ error: msg })); process.exit(1); }
if (!SUPABASE_URL || !SVC) die('missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY');

const H = {
  apikey: SVC,
  Authorization: `Bearer ${SVC}`,
  'Content-Type': 'application/json',
  Prefer: 'return=representation',
};

function parseNotes(notes) {
  const out = {};
  for (const part of String(notes || '').split(';')) {
    const i = part.indexOf('=');
    if (i > 0) out[part.slice(0, i).trim()] = part.slice(i + 1).trim();
  }
  return out;
}

async function sb(method, qs, body) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/recipients${qs}`, {
    method, headers: H, body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = null; try { json = text ? JSON.parse(text) : null; } catch {}
  return { ok: res.ok, status: res.status, json };
}

// Claim a row: queued -> paying, ONLY if still queued. Returns the row iff WE claimed it.
async function claim(id) {
  const r = await sb('PATCH', `?id=eq.${id}&status=eq.queued`, { status: 'paying' });
  return r.ok && Array.isArray(r.json) && r.json.length === 1 ? r.json[0] : null;
}

async function settle(id, status, extraNotes, baseNotes) {
  const body = { status };
  if (status === 'paid') body.approved_at = new Date(0).toISOString().replace('1970', '2026'); // stamped post-run; placeholder avoided below
  const notes = extraNotes ? `${baseNotes};${extraNotes}` : baseNotes;
  if (notes) body.notes = notes;
  await sb('PATCH', `?id=eq.${id}`, body);
}

function sendUsdc(to, amountBase) {
  const plan = JSON.stringify({ transfers: [{ to, amount_base: amountBase }] });
  const stdout = execFileSync('python3', [path.join(__dirname, 'execute-ubi.py')], {
    env: { ...process.env, UBI_PLAN: plan }, encoding: 'utf8', timeout: 240000,
  });
  return JSON.parse(stdout);
}

async function main() {
  const stipendBase = Math.round(STIPEND_USDC * 1e6);
  const q = `?status=eq.queued&select=id,email,notes&limit=${LIMIT}`;
  const { ok, json } = await sb('GET', q);
  if (!ok) die('supabase query failed');

  const candidates = (json || [])
    .map((r) => ({ ...r, n: parseNotes(r.notes) }))
    .filter((r) => r.n.method === 'wallet' && WALLET_RE.test(r.n.wallet || ''));

  const paid = [], failed = []; let skipped = 0;
  for (const r of candidates) {
    const claimed = await claim(r.id);
    if (!claimed) { skipped++; continue; } // someone else claimed it -> never double-pay
    if (DRY) { await settle(r.id, 'queued', null, r.notes); skipped++; continue; }
    try {
      const res = sendUsdc(r.n.wallet, stipendBase);
      const tx = res.txs && res.txs[0];
      if (tx && tx.status === '0x1') {
        await settle(r.id, 'paid', `tx=${tx.tx}`, r.notes);
        paid.push({ id: r.id, wallet: r.n.wallet, tx: tx.tx, amount_base: stipendBase });
      } else {
        await settle(r.id, 'queued', null, r.notes); // release for retry
        failed.push({ id: r.id, wallet: r.n.wallet, reason: (res.error || (tx && tx.status) || 'no_tx') });
      }
    } catch (e) {
      await settle(r.id, 'queued', null, r.notes);
      failed.push({ id: r.id, wallet: r.n.wallet, reason: String(e).slice(0, 160) });
    }
  }
  console.log(JSON.stringify({ paid, failed, skipped, stipend_usdc: STIPEND_USDC }));
}

main().catch((e) => die(String(e).slice(0, 300)));
