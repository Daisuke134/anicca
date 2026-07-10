// sol-evolve.mjs — SOL rail earnings-gate attribution + promotion wiring
// (franklin-sol-evolvable-edge, REQ-012b/013/014/015/015b).
//
// REQ-014/REQ-015 (HARD, no reimplementation): evaluatePromotion and promote are REUSED VERBATIM
// from evolve.mjs (already rail-agnostic, already tested, already adversary-hardened for the PM
// feature) -- this file imports them UNCHANGED and adds NO new implementation of either.
//
// REQ-012b (CORRECTED join key vs PM's attributeGenomeId): record-swap.mjs:19 hardcodes
// `task = "jupiter swap round-trip"` as a FIXED CONSTANT for every SOL swap this instance ever
// records -- it carries no per-mint/per-pass discriminator, so a market/task-field match (PM's
// approach) would match EVERY genome-linked line or NONE, never the correct one. attributeGenomeIdSol
// therefore uses TIMESTAMP ORDERING ALONE: the most recent genome-linked trace line whose ts is
// <= the ledger row's ts, relying on sol-trade/run.sh's single-slot, non-overlapping pass model
// (Edge Case Catalog, "Concurrent passes") for correctness.
//
// REQ-013 (CORRECTED field names vs PM's tx/status): record-swap.mjs's SOL earn-ledger row has NO
// tx/status fields; it has `sig` (the Solana signature string) and `confirmed: true` (set only
// after on-chain RPC confirmation). Accumulates row.net_usdc (WIN-OR-LOSS, ledger.mjs's
// deriveLine() field), NEVER row.earn_usdc (WIN-ONLY, always 0 for a losing swap).
import path from "node:path";
import { fileURLToPath } from "node:url";
import { evaluatePromotion, promote } from "../../lib/evolve.mjs";

export { evaluatePromotion, promote };

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// SOL rail's own canonical baseline path (REQ-015) -- distinct from PM's, never touches anything
// under skills/earn/polymarket-trade/ (rail isolation).
export const SOL_CANONICAL_BASELINE_PATH = path.join(__dirname, "..", "baseline-genome.json");

export const DEFAULT_MIN_REDEEMS = 3; // K, same rationale as evolve.mjs's DEFAULT_MIN_REDEEMS

// Parse a trace line's ISO-8601 UTC timestamp to epoch seconds. NaN on anything unparseable so
// callers can defensively skip it.
function traceTsSeconds(t) {
  const ms = Date.parse(t.ts);
  return Number.isFinite(ms) ? ms / 1000 : NaN;
}

/**
 * attributeGenomeIdSol(ledgerRow, traceLines) — REQ-012b. PURE function: given a confirmed
 * sol-trade ledger row and the full sol-trade.trace.jsonl array, returns the genome_id of the
 * MOST RECENT genome-linked trace line (action==="genome", genome_id present) whose timestamp is
 * <= the ledger row's timestamp -- TIMESTAMP ORDERING ALONE, NO market/task/mint-field comparison
 * of any kind. Returns null (unattributed) if no such preceding line exists.
 *
 * @param {{ts: number}} ledgerRow
 * @param {Array<object>} traceLines
 * @returns {string|null}
 */
export function attributeGenomeIdSol(ledgerRow, traceLines) {
  const swapTs = Number(ledgerRow.ts) || 0;
  let best = null;
  for (const t of traceLines || []) {
    if (t.action !== "genome" || !t.genome_id) continue;
    const tTs = traceTsSeconds(t);
    if (!Number.isFinite(tTs) || tTs > swapTs) continue;
    if (best === null || tTs > best.ts) best = { ts: tTs, genome_id: t.genome_id };
  }
  return best ? best.genome_id : null;
}

/**
 * summarizeByGenomeSol(ledgerRows, traceLines) — REQ-013. Chain-verified realized P&L + confirmed
 * swap count per genome_id. Counts a ledger row IF AND ONLY IF row.source==="sol-trade",
 * typeof row.sig==="string" && row.sig.length>0, AND row.confirmed===true. Accumulates
 * Number(row.net_usdc || 0) (WIN-OR-LOSS) per attributed genome_id via attributeGenomeIdSol.
 * Unattributed rows count toward NO genome (never silently folded into baseline).
 *
 * @returns {Map<string, {genome_id: string, realized_usdc: number, redeem_count: number}>}
 */
export function summarizeByGenomeSol(ledgerRows, traceLines) {
  const byGenome = new Map();
  for (const row of ledgerRows || []) {
    if (!row || row.source !== "sol-trade") continue;
    if (typeof row.sig !== "string" || row.sig.length === 0) continue;
    if (row.confirmed !== true) continue;
    const gid = attributeGenomeIdSol(row, traceLines);
    if (!gid) continue; // unattributed realized P&L counts toward nobody
    const entry = byGenome.get(gid) || { genome_id: gid, realized_usdc: 0, redeem_count: 0 };
    entry.realized_usdc = Math.round((entry.realized_usdc + Number(row.net_usdc || 0)) * 1e6) / 1e6;
    entry.redeem_count += 1;
    byGenome.set(gid, entry);
  }
  return byGenome;
}
