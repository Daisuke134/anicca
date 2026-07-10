// sol-trace.mjs — SOL pre-gate trace-line appends (REQ-011/012, franklin-sol-evolvable-edge).
// Fail-soft: a trace-file write failure (disk full, permissions) MUST NOT crash or exit-nonzero
// the calling pass -- same convention as every other trace append in skills/earn.
import fs from "node:fs";
import path from "node:path";

function now() {
  return new Date().toISOString();
}

function appendLine(tracePath, line) {
  try {
    fs.mkdirSync(path.dirname(tracePath), { recursive: true });
    fs.appendFileSync(tracePath, JSON.stringify(line) + "\n");
  } catch {
    // fail-soft: never crash or exit-nonzero the calling pass on a trace-write failure.
  }
}

/**
 * appendGateTrace(tracePath, fields) — REQ-011: WHEN the SOL pre-gate evaluates a pass (paper or
 * live) append exactly one structured JSONL line recording timestamp, genome_id, the full
 * resolved genome, mode ("paper"|"live"), decision ("engage"|"skip"), wouldEngage, conviction,
 * momentumPct, liquidityUsd, and the mint evaluated -- to state/sol-gate.trace.jsonl (sibling of
 * the existing state/sol-trade.trace.jsonl).
 *
 * @param {string} tracePath
 * @param {{genome_id: string, genome: object, mode: "paper"|"live", decision: "engage"|"skip",
 *          wouldEngage: boolean, conviction: number, momentumPct: number|null,
 *          liquidityUsd: number|null, mint: string|null, reason?: string}} fields
 */
export function appendGateTrace(tracePath, fields) {
  appendLine(tracePath, {
    ts: now(),
    slot: "earn/sol-trade",
    action: "sol-gate",
    ...fields,
  });
}

/**
 * appendGenomeLinkTrace(tracePath, fields) — REQ-012: WHEN the pre-gate's decision is
 * engage===true AND franklin-trading start is subsequently invoked for that pass, record the SAME
 * genome_id (and full genome values) into state/sol-trade.trace.jsonl, timestamped at or before
 * the pass's own live-pass trace line, so a later offline join (attributeGenomeIdSol) can
 * attribute a realized swap's P&L to the genome that was active when this pass ran.
 *
 * @param {string} tracePath
 * @param {{genome_id: string, genome: object}} fields
 */
export function appendGenomeLinkTrace(tracePath, { genome_id, genome }) {
  appendLine(tracePath, {
    ts: now(),
    slot: "earn/sol-trade",
    action: "genome",
    genome_id,
    genome,
  });
}
