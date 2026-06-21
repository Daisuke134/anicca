#!/usr/bin/env node
// net-positive.mjs — the single honest question: is anicca earning more than it spends?
// Reads the earn ledger (realised earn_usdc + cost_usdc per wake) and the live on-chain balances, and
// prints a net-positive verdict. Compute is $0 (free glm-4.7), so "spend" = gas + bridge/swap fees +
// realised trading losses; "earn" = realised yield interest + closed HL PnL + x402 sales + token fees.
//
// This is for MONITORING (the article's 6-3 numbers + an alert when net goes negative), not a decision.
// Usage: node net-positive.mjs [earn-ledger.jsonl]
import fs from 'node:fs';

const LEDGER = process.argv[2] || `${process.env.HOME}/.anicca/skills/earn/state/earn-ledger.jsonl`;

function readLedger() {
  try {
    return fs.readFileSync(LEDGER, 'utf8').trim().split('\n').filter(Boolean).map((l) => {
      try { return JSON.parse(l); } catch { return null; }
    }).filter(Boolean);
  } catch { return []; }
}

const rows = readLedger();
let earn = 0, cost = 0;
const bySource = {};
for (const r of rows) {
  const e = Number(r.earn_usdc || 0), c = Number(r.cost_usdc || 0);
  earn += e; cost += c;
  const s = r.source || 'unknown';
  bySource[s] = bySource[s] || { earn: 0, cost: 0, n: 0 };
  bySource[s].earn += e; bySource[s].cost += c; bySource[s].n += 1;
}
const net = earn - cost;

const out = {
  ledger: LEDGER,
  wakes: rows.length,
  realised_earn_usdc: Number(earn.toFixed(6)),
  realised_cost_usdc: Number(cost.toFixed(6)),
  net_usdc: Number(net.toFixed(6)),
  net_positive: net > 0,
  by_source: Object.fromEntries(
    Object.entries(bySource).map(([k, v]) => [k, { earn: Number(v.earn.toFixed(6)), cost: Number(v.cost.toFixed(6)), wakes: v.n }]),
  ),
  note: net > 0
    ? 'NET POSITIVE — anicca earns more than it spends (realised).'
    : 'not yet net-positive (realised). Open positions (HL/yield) accrue unrealised; close/accrue to realise.',
};
console.log(JSON.stringify(out, null, 2));
process.exit(net > 0 ? 0 : 1);
