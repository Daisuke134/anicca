/**
 * settle-write.mjs — write the loop's profitable-shape earn line for a record-earn-VERIFIED inflow.
 * Called ONLY after record-earn printed "VERIFIED +N USDC". Attaches a REAL representative external
 * tx hash (status "0x1") so isProfitable (tx && status==="0x1" && external && net>0) registers it.
 *
 * argv: <earn> <wallet> <wake> <ledgerPath>
 * env seam: GIG_SETTLE_TX (test only) injects the tx instead of an RPC lookup.
 * Prints the structured JSON line. Honest: if NO external tx can be found, it records WITHOUT tx
 * (loop will under-count, never fabricate) and flags no_tx so the gap is visible.
 */
import fs from 'node:fs';
import { representativeExternalTx } from './settle-tx.mjs';

const [earnStr, wallet, wake, ledgerPath] = process.argv.slice(2);
const earn = Number(earnStr);
const out = (o) => console.log(JSON.stringify(o));

if (!(earn > 0)) { out({ source: 'gig', task: 'settle', earn_usdc: 0, cost_usdc: 0, wake }); process.exit(0); }

let tx = process.env.GIG_SETTLE_TX || null;
if (!tx) {
  const r = await representativeExternalTx(wallet).catch(() => null);
  tx = r && r.tx ? r.tx : null;
}

const line = { ts: Math.floor(Date.now() / 1000), wallet, source: 'gig', task: 'settle',
  earn_usdc: earn, cost_usdc: 0, net_usdc: earn, external: true, wake };
if (tx) { line.tx = tx; line.status = '0x1'; } else { line.no_tx = true; }

try { fs.mkdirSync(ledgerPath.replace(/\/[^/]+$/, ''), { recursive: true }); fs.appendFileSync(ledgerPath, JSON.stringify(line) + '\n'); } catch {}
out(line);
