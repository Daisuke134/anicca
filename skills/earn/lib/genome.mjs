// genome.mjs — earn EXPLORATION-knob genome: canonical baseline + per-instance override merge,
// safe small mutation, content-hash id (#19 EVOLVE, spec
// docs/superpowers/specs/2026-07-05-evolve-earnings-gated-self-improve-design.md).
//
// HARD #0 (unchanged, non-negotiable): this file NEVER decides which market/side to bet — it
// only tunes pick.py's EXPLORATION knobs (MIN_EDGE/MIN_CONF/RESOLVE_HORIZON_DAYS/MAX_CANDIDATES/
// EARN_CONSENSUS_MODELS, see polymarket-trade/pick.py's own env docstring). That judgment stays
// the model's job inside pick.py, untouched by this module.
//
// Money-safety (spec §3, HARD): MAX_BET_SIZE / MAX_PASS_SPEND / POLY_MIN_ORDER are OUTSIDE the
// genome entirely — never read, never written, never exported by anything in this file. They are
// stripped defensively (stripForbidden) from every genome object this module ever produces, even
// a maliciously/accidentally crafted override file, so a bad file on disk can never smuggle a cap
// override into a shell env via toExportLines()/the CLI below.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Canonical baseline lives IN the OSS repo itself (`__REPO_ROOT__/skills/earn/baseline-genome.json`),
// propagated to every instance body by the EXISTING daemon rsync (`__REPO_ROOT__/skills -> body`,
// spec §2.4) — no new propagation wiring needed here.
export const CANONICAL_BASELINE_PATH = path.join(__dirname, "..", "baseline-genome.json");

// The ONLY knobs EVOLVE ever touches — every one an EXPLORATION knob read by pick.py's env
// (spec §1.1). Money-safety caps are never in this list.
export const KNOB_KEYS = Object.freeze([
  "MIN_EDGE",
  "MIN_CONF",
  "RESOLVE_HORIZON_DAYS",
  "MAX_CANDIDATES",
  "EARN_CONSENSUS_MODELS",
]);

// Safe default = today's pick.py env defaults (spec §2.1: "無ければ安全な default（今の env
// default 値）"). Keep in sync with polymarket-trade/pick.py's _env_float/_env_int defaults and
// the polymarket-agent AIAnalyzer.CONSENSUS_MODELS FREE-MODE default.
export const SAFE_DEFAULT_GENOME = Object.freeze({
  MIN_EDGE: 0.15,
  MIN_CONF: 7,
  RESOLVE_HORIZON_DAYS: 14,
  MAX_CANDIDATES: 5,
  EARN_CONSENSUS_MODELS:
    "nvidia/llama-4-maverick,nvidia/qwen3-next-80b-a3b-instruct,nvidia/mistral-nemotron",
});

// Mutation ranges/steps for NUMERIC knobs only (spec §2.1 example: "MIN_EDGE ±0.03,
// RESOLVE_HORIZON_DAYS ±7, MAX_CANDIDATES ±2、範囲は clamp"). EARN_CONSENSUS_MODELS is a
// categorical (model-roster) knob that the genome carries and exports, but mutate() never
// touches it — swapping the model roster is closer to a judgment call than a knob nudge, so it
// stays pinned to the FREE-MODE default until a future spec explicitly widens mutate()'s scope.
const MUTATION_SPEC = Object.freeze({
  MIN_EDGE: { step: 0.03, min: 0.05, max: 0.4, decimals: 2 },
  MIN_CONF: { step: 1, min: 4, max: 10, decimals: 0 },
  RESOLVE_HORIZON_DAYS: { step: 7, min: 3, max: 30, decimals: 0 },
  MAX_CANDIDATES: { step: 2, min: 2, max: 10, decimals: 0 },
});

// Caps that must NEVER be part of genome (HARD, spec §3). Stripped defensively from every
// genome object this module produces (baseline, override, mutated) so no code path here can ever
// emit them, regardless of what a malformed file on disk contains.
export const FORBIDDEN_CAP_KEYS = Object.freeze(["MAX_BET_SIZE", "MAX_PASS_SPEND", "POLY_MIN_ORDER"]);

function stripForbidden(obj) {
  const out = { ...obj };
  for (const k of FORBIDDEN_CAP_KEYS) delete out[k];
  return out;
}

function readJsonSafe(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

// Per-instance current-generation override path — mirrors the ANICCA_HOME/body-state convention
// used across skills/earn/lib (see cost-basis.mjs's FILE derivation). NOT canonical: this is the
// instance's OWN current mutant trial, distinct from the shared canonical baseline.
export function instanceOverridePath(home) {
  const effectiveHome = home || process.env.ANICCA_HOME || path.join(process.env.HOME || "", ".anicca");
  return path.join(effectiveHome, "skills", "earn", "state", "genome-override.json");
}

/**
 * load_genome(instance_home) — canonical baseline (`CANONICAL_BASELINE_PATH`, or
 * `SAFE_DEFAULT_GENOME` if the canonical file is missing) merged with THIS instance's current
 * override (override wins per-key). Pure read, never throws (fail-closed to safe defaults on any
 * read/parse error).
 *
 * @param {{home?: string, canonicalPath?: string}} [opts]
 * @returns {Record<string, number|string>}
 */
export function loadGenome({ home, canonicalPath = CANONICAL_BASELINE_PATH } = {}) {
  const canonical = readJsonSafe(canonicalPath);
  const baseline = stripForbidden({ ...SAFE_DEFAULT_GENOME, ...(canonical || {}) });
  const override = stripForbidden(readJsonSafe(instanceOverridePath(home)) || {});
  return stripForbidden({ ...baseline, ...override });
}

/**
 * mutate(genome) — clamp a small change to 1-2 NUMERIC knobs (chosen at random from
 * MUTATION_SPEC's keys), each moved by its own fixed step in a random direction then clamped to
 * [min,max]. NEVER touches FORBIDDEN_CAP_KEYS (not even in MUTATION_SPEC) and NEVER touches
 * EARN_CONSENSUS_MODELS (categorical, not in MUTATION_SPEC). Returns a NEW object — never mutates
 * its argument (coding-style.md immutability).
 *
 * @param {Record<string, number|string>} genome
 * @param {{rng?: () => number, count?: number}} [opts] rng is injectable for deterministic tests.
 */
export function mutate(genome, { rng = Math.random, count } = {}) {
  const pool = Object.keys(MUTATION_SPEC);
  const n = Math.max(1, Math.min(2, count ?? (rng() < 0.5 ? 1 : 2)));
  const chosen = [];
  const remaining = [...pool];
  for (let i = 0; i < Math.min(n, remaining.length); i++) {
    const idx = Math.floor(rng() * remaining.length) % remaining.length;
    chosen.push(remaining.splice(idx, 1)[0]);
  }

  const next = stripForbidden({ ...SAFE_DEFAULT_GENOME, ...genome });
  for (const key of chosen) {
    const spec = MUTATION_SPEC[key];
    const current = Number(next[key]);
    const rawBase = Number.isFinite(current) ? current : Number(SAFE_DEFAULT_GENOME[key]);
    // Defense-in-depth #1: clamp the BASE itself before stepping. A genome fed into mutate()
    // might already carry an out-of-range value for this knob (e.g. a malformed override file,
    // or repeated/chained mutation over many exploration passes) — re-anchoring to the safe
    // range FIRST guarantees the result below can never compound outward across generations.
    const base = Math.min(spec.max, Math.max(spec.min, rawBase));
    const direction = rng() < 0.5 ? -1 : 1;
    let value = base + direction * spec.step;
    // Defense-in-depth #2: clamp after stepping (the actual excursion guard for THIS mutation —
    // e.g. MIN_EDGE at its floor 0.05 moving -0.03 must land back at 0.05, never 0.02).
    value = Math.min(spec.max, Math.max(spec.min, value));
    value = spec.decimals === 0 ? Math.round(value) : Number(value.toFixed(spec.decimals));
    // Defense-in-depth #3: re-clamp AFTER rounding too — toFixed()/Number() on a boundary value
    // could in theory introduce a hair of floating-point drift; never trust rounding alone to
    // preserve a hard floor/ceiling.
    value = Math.min(spec.max, Math.max(spec.min, value));
    next[key] = value;
  }
  return next;
}

/**
 * genomeId(genome) — short deterministic content hash for P&L attribution (spec §2.1). Same knob
 * values -> same id regardless of key insertion order (keys sorted before hashing); forbidden cap
 * keys are stripped before hashing so their presence/absence can never change a genome's identity.
 */
export function genomeId(genome) {
  const sanitized = stripForbidden(genome);
  const sortedKeys = Object.keys(sanitized).sort();
  const canonical = JSON.stringify(sortedKeys.map((k) => [k, sanitized[k]]));
  return crypto.createHash("sha256").update(canonical).digest("hex").slice(0, 12);
}

// Shell-safe single-quote wrapping (values here are numbers or a fixed comma-separated model
// list — never user input — but quote defensively regardless).
function shQuote(v) {
  return "'" + String(v).replace(/'/g, "'\\''") + "'";
}

/**
 * toExportLines(genome, id, mutated) — `export KEY='value'` lines for run.sh to `eval`. Only ever
 * emits KNOB_KEYS (+ EARN_GENOME_ID / EARN_GENOME_MUTATED bookkeeping) — money-safety caps are
 * never in KNOB_KEYS so they can never appear here.
 */
export function toExportLines(genome, id, mutated) {
  const lines = [];
  for (const key of KNOB_KEYS) {
    if (genome[key] !== undefined && genome[key] !== null) {
      lines.push(`export ${key}=${shQuote(genome[key])}`);
    }
  }
  lines.push(`export EARN_GENOME_ID=${shQuote(id)}`);
  lines.push(`export EARN_GENOME_MUTATED=${shQuote(mutated ? "1" : "0")}`);
  return lines;
}

/**
 * shouldMutateThisPass(counterFile, cadence) — deterministic exploration cadence: mutate once
 * every `cadence` passes (arithmetic/bookkeeping, not judgment — HARD constraint: deterministic
 * code only for tools+arithmetic+bookkeeping). Increments and persists a simple counter; on any
 * read/parse error the counter restarts at 0 (fail-closed to "count", never crashes the pass).
 */
export function shouldMutateThisPass(counterFile, cadence) {
  const M = Math.max(1, Number(cadence) || 1);
  let n = 0;
  try {
    n = Number(JSON.parse(fs.readFileSync(counterFile, "utf8")).n) || 0;
  } catch {
    n = 0;
  }
  n += 1;
  try {
    fs.mkdirSync(path.dirname(counterFile), { recursive: true });
    fs.writeFileSync(counterFile, JSON.stringify({ n }));
  } catch {
    // best-effort persistence only — a failed write just means cadence resets, never a crash.
  }
  return n % M === 0;
}

// --- CLI entrypoint --------------------------------------------------------------------------
// `node genome.mjs [--maybe-mutate]` prints `export KEY='value'` lines to stdout for run.sh to
// `eval`. With --maybe-mutate, consults EARN_GENOME_MUTATE_EVERY (default 5) + a per-instance
// pass counter to decide whether THIS pass explores a fresh mutation drawn from the current
// baseline+override (never a compounding mutation-of-a-mutation) or runs the unmutated genome.
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const home = process.env.ANICCA_HOME;
  let genome = loadGenome({ home });
  let mutated = false;
  if (process.argv.includes("--maybe-mutate")) {
    const cadence = Number(process.env.EARN_GENOME_MUTATE_EVERY || 5);
    const counterFile =
      process.env.EARN_GENOME_COUNTER_FILE ||
      path.join(
        (home || process.env.HOME + "/.anicca"),
        "skills",
        "earn",
        "state",
        "genome-pass-counter.json",
      );
    if (shouldMutateThisPass(counterFile, cadence)) {
      genome = mutate(genome);
      mutated = true;
    }
  }
  const id = genomeId(genome);
  for (const line of toExportLines(genome, id, mutated)) {
    process.stdout.write(line + "\n");
  }
}
