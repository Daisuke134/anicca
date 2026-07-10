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
//
// FIND-002 fix (2026-07-10 impl-review iteration-1): evaluatePromotion/promote were reused
// correctly but NEVER ORCHESTRATED against real ledger/trace data anywhere -- no runEvolveSol()
// equivalent of evolve.mjs's own runEvolve(), no CLI entrypoint, nothing in run.sh ever called this
// file. `runEvolveSol` below mirrors evolve.mjs's `runEvolve` line-for-line (same read -> attribute
// -> gate -> maybe-promote shape), REUSING evolve.mjs's OWN `readTrace`/`buildGenomeIndex` verbatim
// (both are already rail-agnostic: readTrace just parses a JSONL file, buildGenomeIndex just reads
// `action==="genome"` lines -- exactly SOL's own sol-trace.mjs `appendGenomeLinkTrace` shape too) so
// this feature adds NO new implementation of either, mirroring REQ-014/015's identical
// no-reimplementation mandate for evaluatePromotion/promote.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readLedger } from "../../../_shared/lib/ledger.mjs";
import { evaluatePromotion, promote, readTrace, buildGenomeIndex } from "../../lib/evolve.mjs";
import { SAFE_DEFAULT_GENOME, stripForbidden, genomeId as computeGenomeId } from "./sol-genome.mjs";

export { evaluatePromotion, promote, readTrace, buildGenomeIndex };

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// SOL rail's own canonical baseline path (REQ-015) -- distinct from PM's, never touches anything
// under skills/earn/polymarket-trade/ (rail isolation).
export const SOL_CANONICAL_BASELINE_PATH = path.join(__dirname, "..", "baseline-genome.json");

export const DEFAULT_MIN_REDEEMS = 3; // K, same rationale as evolve.mjs's DEFAULT_MIN_REDEEMS

// FIND-002: the SAME shared earn-ledger.jsonl / this rail's OWN sol-trade.trace.jsonl -- both live
// under skills/earn/state (a sibling of sol-trade/, matching sol-gate-cli.mjs's own STATE_DIR
// convention: lib -> sol-trade -> earn -> state).
export const DEFAULT_LEDGER_PATH = path.join(__dirname, "..", "..", "state", "earn-ledger.jsonl");
export const DEFAULT_TRACE_PATH = path.join(__dirname, "..", "..", "state", "sol-trade.trace.jsonl");

function readJsonSafe(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

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

/**
 * runEvolveSol(opts) — FIND-002 fix: full attribution + gate + (maybe) promote pipeline for the SOL
 * rail, mirroring evolve.mjs's own `runEvolve` line-for-line (REQ-012b/013/014/015). Read-only
 * unless a genuine chain-verified promotion happens, in which case it writes the SOL canonical
 * baseline file + commits (via the REUSED, unchanged `promote()`). Never throws on "nothing to
 * promote" (a normal, expected outcome -- cold-start or a losing/below-K mutant is simply
 * discarded, same as evolve.mjs's own contract).
 *
 * @param {{ledgerPath?: string, tracePath?: string, canonicalPath?: string, minRedeems?: number, cwd?: string}} [opts]
 */
export async function runEvolveSol({
  ledgerPath = DEFAULT_LEDGER_PATH,
  tracePath = DEFAULT_TRACE_PATH,
  canonicalPath = SOL_CANONICAL_BASELINE_PATH,
  minRedeems = Number(process.env.SOL_EVOLVE_MIN_REDEEMS || DEFAULT_MIN_REDEEMS),
  cwd,
} = {}) {
  const ledgerRows = await readLedger(ledgerPath);
  const traceLines = await readTrace(tracePath);
  const genomeIndex = buildGenomeIndex(traceLines);

  const baselineGenome = stripForbidden(readJsonSafe(canonicalPath) || SAFE_DEFAULT_GENOME);
  const baselineId = computeGenomeId(baselineGenome);
  const summary = summarizeByGenomeSol(ledgerRows, traceLines);

  const evaluations = {};
  let winner = null;
  for (const gid of summary.keys()) {
    if (gid === baselineId) continue;
    const verdict = evaluatePromotion({ summary, baselineId, mutantId: gid, minRedeems });
    evaluations[gid] = verdict;
    if (verdict.promote) {
      const stats = summary.get(gid);
      if (!winner || stats.realized_usdc > winner.stats.realized_usdc) winner = { genome_id: gid, stats };
    }
  }

  const summaryOut = Object.fromEntries(summary);

  if (!winner) {
    return { promoted: false, baselineId, evaluations, summary: summaryOut };
  }

  const winnerGenome = genomeIndex.get(winner.genome_id);
  if (!winnerGenome) {
    // Never promote a genome whose actual knob VALUES we never captured -- an id with no
    // recoverable values cannot become the new baseline-genome.json.
    return {
      promoted: false,
      baselineId,
      evaluations,
      summary: summaryOut,
      reason: "winner-genome-values-unavailable",
    };
  }

  const result = promote(winnerGenome, { canonicalPath, cwd });
  return {
    promoted: true,
    baselineId,
    newBaselineId: result.genome_id,
    commit: result.commit,
    evaluations,
    summary: summaryOut,
  };
}

// --- CLI entrypoint --------------------------------------------------------------------------
// `node sol-evolve.mjs [ledgerPath] [tracePath]` -- standalone, idempotent gate-check, mirrors
// evolve.mjs's own CLI block exactly. Prints the JSON result. Safe to run repeatedly/periodically
// (e.g. every sol-trade/run.sh pass, right after any swap this pass records); a no-promotion
// outcome is a normal, silent no-op, exactly like every other idle-pass guard in this codebase.
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [ledgerPath, tracePath] = process.argv.slice(2);
  runEvolveSol({
    ledgerPath: ledgerPath || DEFAULT_LEDGER_PATH,
    tracePath: tracePath || DEFAULT_TRACE_PATH,
  })
    .then((result) => {
      console.log(JSON.stringify(result, null, 2));
    })
    .catch((e) => {
      console.error("sol-evolve.mjs error:", e.message);
      process.exitCode = 1;
    });
}
