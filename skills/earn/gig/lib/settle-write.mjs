/**
 * settle-write.mjs — write the loop's profitable-shape earn line for a record-earn-VERIFIED inflow.
 * Called ONLY after record-earn printed "VERIFIED +N USDC". Attaches a REAL representative external
 * tx hash (status "0x1") so isProfitable (tx && status==="0x1" && external && net>0) registers it.
 *
 * argv: <earn> <wallet> <wake> <ledgerPath> [founderLedgerPath]
 * Honest: if NO external tx can be found, it records WITHOUT tx (loop under-counts, never fabricates)
 * and flags no_tx so the gap is visible. The amount is ALWAYS record-earn's (passed as <earn>).
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { representativeExternalTx } from './settle-tx.mjs';

// SHARED internal wallets (record-earn.mjs SHARED) — a Transfer FROM these is NOT external.
const SHARED = ['0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21', '0x9b1ee988b1a2931abce467f0a8eaff6c70c93e83'];

const [earnStr, wallet, wake, ledgerPath, founderLedger] = process.argv.slice(2);
const earn = Number(earnStr);
const out = (o) => console.log(JSON.stringify(o));

if (!(earn > 0)) { out({ source: 'gig', task: 'settle', earn_usdc: 0, cost_usdc: 0, wake }); process.exit(0); }

// The exact block range record-earn just processed (its ledger row carries from_block/to_block) →
// scan precisely that window so a real earn is never missed and no unfinalized blocks are read (FIND-003).
function recordEarnRange() {
  const fl = founderLedger || path.join(os.homedir(), '.anicca-founder', 'state', 'earn-ledger.jsonl');
  try {
    const rows = fs.readFileSync(fl, 'utf8').trim().split('\n').filter(Boolean);
    const last = JSON.parse(rows[rows.length - 1]);
    if (Number.isInteger(last.from_block) && Number.isInteger(last.to_block)) return { fromBlock: last.from_block, toBlock: last.to_block };
  } catch {}
  return {};
}

// TEST-ONLY seam (FIND-001): a tx may be injected ONLY under FOUNDER_TEST, exactly like record-earn's
// seams. In prod the tx MUST come from a real on-chain log — never a caller-supplied value.
let tx = (process.env.FOUNDER_TEST === '1' && process.env.GIG_SETTLE_TX) ? process.env.GIG_SETTLE_TX : null;
if (!tx) {
  const range = recordEarnRange();
  const r = await representativeExternalTx(wallet, { myWallets: SHARED, ...range }).catch(() => null);
  tx = r && r.tx ? r.tx : null;
}

const line = { ts: Math.floor(Date.now() / 1000), wallet, source: 'gig', task: 'settle',
  earn_usdc: earn, cost_usdc: 0, net_usdc: earn, external: true, wake };
if (tx) { line.tx = tx; line.status = '0x1'; } else { line.no_tx = true; }

try { fs.mkdirSync(ledgerPath.replace(/\/[^/]+$/, ''), { recursive: true }); fs.appendFileSync(ledgerPath, JSON.stringify(line) + '\n'); } catch {}
out(line);
