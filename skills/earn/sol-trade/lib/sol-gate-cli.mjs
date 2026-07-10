// sol-gate-cli.mjs — run.sh's SOL pre-gate entrypoint (franklin-sol-evolvable-edge). Composes the
// pure/effectful modules above into one pass: load this instance's genome (REQ-006/016), fetch
// the free market signal for each watchlist mint (REQ-007), decide engagement (REQ-008/009),
// ALWAYS record one gate trace line (REQ-011), and -- only if engage===true -- record the
// genome_id linkage line (REQ-012) and print a descriptive-only context line (REQ-010) for run.sh
// to optionally append to franklin-trading's prompt. Fail-soft throughout: never throws to its
// caller, never exits non-zero, always prints valid JSON.
//
// This file itself is Effectful Shell (I/O: genome files, network, trace appends) -- the
// decision logic it calls (decideEngagement) and the data it composes (fetchSolMarketSignal,
// appendGateTrace, appendGenomeLinkTrace) are the tested pure/effectful units (see
// verification-architecture.md's Purity Boundary Map). No new decision logic lives in this file.
//
// FIND-001 fix (2026-07-10 impl-review iteration-1): this is the ONLY entrypoint sol-trade/run.sh
// calls each pass (run.sh:75), so the exploration-cadence trigger this feature's Provenance section
// named but never wired (genome.mjs's `shouldMutateThisPass`, mirrored in sol-genome.mjs) is invoked
// HERE, inline, every pass -- there is no separate SOL analog of genome.mjs's own CLI (that CLI
// exists only because PM's pick.py is a SEPARATE python process needing knobs via shell-eval'd env
// vars; the SOL pre-gate is already one node process that computes+consumes its own genome in
// memory, so folding maybe-mutate into this file's own per-pass main() is the correct copy+TWEAK,
// not a blind copy of PM's two-process shape). On the cadence, mutate() draws a fresh step from the
// CURRENTLY loaded (baseline+override) genome and this pass PERSISTS the mutant as the new
// per-instance override (`sol-gate-genome-override.json`) so it becomes the active "current
// mutant trial" for subsequent passes too (genome.mjs's own doc comment for instanceOverridePath) --
// making genomeId() actually change across passes instead of being frozen at baseline forever.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { loadGenome, mutate, genomeId, instanceOverridePath, shouldMutateThisPass } from "./sol-genome.mjs";
import { fetchSolMarketSignal, decideEngagement, isLiveEnabled, describeSignal } from "./sol-gate.mjs";
import { appendGateTrace, appendGenomeLinkTrace } from "./sol-trace.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// .../sol-trade/lib -> .../sol-trade -> .../earn -> .../earn/state (sibling of the existing
// sol-trade.trace.jsonl, matching run.sh's own STATE_DIR="$SKILL_DIR/../state" convention).
const STATE_DIR = path.join(__dirname, "..", "..", "state");
const GATE_TRACE_PATH = process.env.SOL_GATE_TRACE_PATH || path.join(STATE_DIR, "sol-gate.trace.jsonl");
const SOL_TRADE_TRACE_PATH = process.env.SOL_TRADE_TRACE_PATH || path.join(STATE_DIR, "sol-trade.trace.jsonl");
const CACHE_DIR = process.env.SOL_GATE_CACHE_DIR || path.join(STATE_DIR, "sol-gate-cache");

// FIND-001: cadence knob + per-instance counter file, same naming convention as genome.mjs's own
// EARN_GENOME_MUTATE_EVERY/EARN_GENOME_COUNTER_FILE (SOL_GATE_ prefix for this rail's own knobs).
const GENOME_MUTATE_EVERY = Number(process.env.SOL_GATE_GENOME_MUTATE_EVERY || 5);

function skipResult() {
  return { genome_id: null, mode: "paper", decision: "skip", engage: false, contextLine: "" };
}

/**
 * maybeMutateGenome(genome, { home }) — FIND-001: on the exploration cadence, draw a mutation from
 * the currently-loaded genome and persist it as this instance's new current-generation override so
 * the pre-gate's genome actually evolves across passes. Fail-soft: a persistence failure (disk
 * full, permissions) degrades to "used the mutation for this pass only, not durably" -- it MUST
 * NOT crash or exit-nonzero the calling pass (same convention as every other guard in this file).
 *
 * @param {Record<string, number|string>} genome
 * @param {{home?: string}} opts
 * @returns {{genome: Record<string, number|string>, mutated: boolean}}
 */
function maybeMutateGenome(genome, { home } = {}) {
  const counterFile =
    process.env.SOL_GATE_GENOME_COUNTER_FILE ||
    path.join(home || path.join(process.env.HOME || "", ".anicca"), "skills", "earn", "state", "sol-gate-genome-pass-counter.json");
  if (!shouldMutateThisPass(counterFile, GENOME_MUTATE_EVERY)) {
    return { genome, mutated: false };
  }
  const mutant = mutate(genome);
  try {
    const overridePath = instanceOverridePath(home);
    fs.mkdirSync(path.dirname(overridePath), { recursive: true });
    fs.writeFileSync(overridePath, JSON.stringify(mutant, null, 2) + "\n");
  } catch {
    // fail-soft: persistence failure just means this pass's mutation isn't durable beyond THIS
    // pass -- never crash or exit-nonzero the calling pre-gate pass.
  }
  return { genome: mutant, mutated: true };
}

async function main() {
  const home = process.env.ANICCA_HOME;
  const loaded = loadGenome({ home });
  const { genome } = maybeMutateGenome(loaded, { home });
  const id = genomeId(genome);
  const mints = String(genome.SOL_GATE_WATCHLIST || "")
    .split(",")
    .map((m) => m.trim())
    .filter(Boolean);
  const live = isLiveEnabled(process.env);
  const maxStalenessSec = Number(genome.SOL_GATE_MAX_STALENESS_SEC);

  let best = null;
  for (const mint of mints) {
    let signal;
    try {
      signal = await fetchSolMarketSignal(mint, { cacheDir: CACHE_DIR, maxStalenessSec });
    } catch {
      signal = { ok: false, source: "none", reason: "fetch-threw" };
    }
    if (!signal.ok) continue;
    const outcome = decideEngagement({
      momentumPct: signal.priceChange24h,
      liquidityUsd: signal.liquidity,
      ageSec: signal.ageSec,
      genome,
      liveEnabled: live,
    });
    if (!best || outcome.conviction > best.outcome.conviction) best = { mint, signal, outcome };
  }

  const mode = live ? "live" : "paper";
  const wouldEngage = best ? best.outcome.wouldEngage : false;
  const conviction = best ? best.outcome.conviction : 0;
  const momentumPct = best ? best.signal.priceChange24h : null;
  const liquidityUsd = best ? best.signal.liquidity : null;
  const mint = best ? best.mint : mints[0] || null;
  const engage = best ? best.outcome.engage : false;
  const decision = engage ? "engage" : "skip";
  const reason = best ? undefined : "no-signal";

  appendGateTrace(GATE_TRACE_PATH, {
    genome_id: id,
    genome,
    mode,
    decision,
    ...(reason ? { reason } : {}),
    wouldEngage,
    conviction,
    momentumPct,
    liquidityUsd,
    mint,
  });

  let contextLine = "";
  if (engage) {
    appendGenomeLinkTrace(SOL_TRADE_TRACE_PATH, { genome_id: id, genome });
    contextLine = JSON.stringify(describeSignal({ momentumPct, liquidityUsd, conviction, mint }));
  }

  process.stdout.write(JSON.stringify({ genome_id: id, mode, decision, engage, contextLine }) + "\n");
}

main().catch(() => {
  // Fail-soft (NFR): no failure mode in this feature may crash or exit-nonzero the calling
  // sol-trade/run.sh pass -- every failure degrades to "skip", same as every other guard here.
  process.stdout.write(JSON.stringify(skipResult()) + "\n");
});
