// sol-genome.mjs — SOL_GATE exploration-knob genome for Franklin's SOL pre-gate: canonical
// baseline + per-instance override merge, safe small mutation, content-hash id
// (franklin-sol-evolvable-edge, REQ-001..006/016). COPY+TWEAK of the proven
// `skills/earn/lib/genome.mjs` (#19 EVOLVE) shape, SOL-specific knob names/ranges.
//
// HARD #0 (unchanged, non-negotiable, mirrors genome.mjs's own header): this file NEVER decides
// which market/side to trade -- it only tunes the pre-gate's EXPLORATION knobs (momentum/
// liquidity/conviction/staleness thresholds + the watchlist). Which market/side/size to trade
// remains franklin-trading's own internal model-debate judgment (REQ-010, REQ-018).
//
// Money-safety (REQ-004, HARD): SOL_TRADE_MAX_SPEND is OUTSIDE the genome entirely -- never read,
// never written, never exported by anything in this file. It is stripped defensively
// (stripForbidden) from every genome object this module ever produces, even a maliciously/
// accidentally crafted override file, so a bad file on disk can never smuggle a cap override into
// the pre-gate's decision or run.sh's invocation.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Canonical SOL baseline lives alongside the sol-trade skill itself (propagated to every instance
// body by the existing daemon rsync, same convention as PM's CANONICAL_BASELINE_PATH).
export const CANONICAL_BASELINE_PATH = path.join(__dirname, "..", "baseline-genome.json");

// The ONLY knobs the SOL pre-gate genome ever touches (REQ-001). Money-safety caps are never in
// this list.
export const KNOB_KEYS = Object.freeze([
  "SOL_GATE_MIN_MOMENTUM_PCT",
  "SOL_GATE_MIN_LIQUIDITY_USD",
  "SOL_GATE_MIN_CONVICTION",
  "SOL_GATE_MAX_STALENESS_SEC",
  "SOL_GATE_WATCHLIST",
]);

// REQ-001 stated defaults -- conservative, genuinely new design choices (no prior in-repo number
// to copy for the SOL rail, per the spec's Open Questions #1), scrutinized in spec-review.
export const SAFE_DEFAULT_GENOME = Object.freeze({
  SOL_GATE_MIN_MOMENTUM_PCT: 2.0,
  SOL_GATE_MIN_LIQUIDITY_USD: 1000000,
  SOL_GATE_MIN_CONVICTION: 6,
  SOL_GATE_MAX_STALENESS_SEC: 300,
  SOL_GATE_WATCHLIST: "So11111111111111111111111111111111111111112", // wrapped-SOL mint
});

// REQ-002 mutation ranges/steps for the 4 NUMERIC knobs only. SOL_GATE_WATCHLIST is a categorical
// knob (REQ-003) the genome carries and exports but mutate() never touches -- swapping the
// watchlist is a judgment/scope call, not a numeric-knob nudge.
const MUTATION_SPEC = Object.freeze({
  SOL_GATE_MIN_MOMENTUM_PCT: { step: 0.5, min: 0.5, max: 8.0, decimals: 1 },
  SOL_GATE_MIN_LIQUIDITY_USD: { step: 250000, min: 100000, max: 5000000, decimals: 0 },
  SOL_GATE_MIN_CONVICTION: { step: 1, min: 3, max: 10, decimals: 0 },
  SOL_GATE_MAX_STALENESS_SEC: { step: 60, min: 60, max: 900, decimals: 0 },
});

// REQ-004 (HARD, money-safety): caps that must NEVER be part of the SOL genome.
export const FORBIDDEN_CAP_KEYS = Object.freeze(["SOL_TRADE_MAX_SPEND"]);

/**
 * stripForbidden(obj) — remove FORBIDDEN_CAP_KEYS from every genome object this module ever
 * produces (canonical read, override read, merged load, every mutated output), even from a
 * maliciously/accidentally crafted on-disk file. Returns a NEW object (immutability, never
 * mutates its argument).
 */
export function stripForbidden(obj) {
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

// base58 mint-address shape (no 0 O I l); comma-separated list, each segment must match.
const MINT_RE = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;

function isValidWatchlist(value) {
  if (typeof value !== "string" || value.trim().length === 0) return false;
  const mints = value.split(",").map((s) => s.trim());
  return mints.length > 0 && mints.every((m) => MINT_RE.test(m));
}

// REQ-006/REQ-016: per-instance current-generation override path, ANICCA_HOME-gated exactly like
// genome.mjs's own instanceOverridePath() -- never falls back to a shared/ambient path.
export function instanceOverridePath(home) {
  const effectiveHome = home || process.env.ANICCA_HOME || path.join(process.env.HOME || "", ".anicca");
  return path.join(effectiveHome, "skills", "earn", "state", "sol-gate-genome-override.json");
}

/**
 * loadGenome(opts) — canonical SOL baseline (or SAFE_DEFAULT_GENOME if the canonical file is
 * missing/malformed) merged with THIS instance's own override (override wins per-key). Pure read,
 * never throws (fails closed to safe defaults on any read/parse error). REQ-003's edge case: a
 * malformed/empty SOL_GATE_WATCHLIST anywhere in the merge fails closed to the SAFE_DEFAULT
 * watchlist (never an empty eligible universe silently treated as "everything").
 *
 * @param {{home?: string, canonicalPath?: string}} [opts]
 * @returns {Record<string, number|string>}
 */
export function loadGenome({ home, canonicalPath = CANONICAL_BASELINE_PATH } = {}) {
  const canonical = readJsonSafe(canonicalPath);
  const baseline = stripForbidden({ ...SAFE_DEFAULT_GENOME, ...(canonical || {}) });
  const override = stripForbidden(readJsonSafe(instanceOverridePath(home)) || {});
  const merged = stripForbidden({ ...baseline, ...override });
  if (!isValidWatchlist(merged.SOL_GATE_WATCHLIST)) {
    merged.SOL_GATE_WATCHLIST = SAFE_DEFAULT_GENOME.SOL_GATE_WATCHLIST;
  }
  return merged;
}

/**
 * mutate(genome, opts) — clamp a small change to 1-2 NUMERIC knobs (chosen at random from
 * MUTATION_SPEC's keys), each moved by its own fixed step in a random direction then clamped to
 * [min,max] BEFORE stepping, AFTER stepping, and AFTER rounding (3-layer defense-in-depth, REQ-002).
 * NEVER touches FORBIDDEN_CAP_KEYS or SOL_GATE_WATCHLIST (categorical, REQ-003, not in
 * MUTATION_SPEC's pool). Returns a NEW object -- never mutates its argument.
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
    // Defense-in-depth #1: re-anchor the BASE into range BEFORE stepping -- a genome fed into
    // mutate() might already carry an out-of-range value (malformed override file, or
    // repeated/chained mutation over many exploration passes).
    const base = Math.min(spec.max, Math.max(spec.min, rawBase));
    const direction = rng() < 0.5 ? -1 : 1;
    let value = base + direction * spec.step;
    // Defense-in-depth #2: clamp after stepping (the actual excursion guard for THIS mutation).
    value = Math.min(spec.max, Math.max(spec.min, value));
    value = spec.decimals === 0 ? Math.round(value) : Number(value.toFixed(spec.decimals));
    // Defense-in-depth #3: re-clamp AFTER rounding too -- toFixed()/Number() on a boundary value
    // could in theory introduce a hair of floating-point drift.
    value = Math.min(spec.max, Math.max(spec.min, value));
    next[key] = value;
  }
  return next;
}

/**
 * genomeId(genome) — short deterministic content hash for P&L attribution (REQ-005). Same knob
 * values -> same id regardless of key insertion order; forbidden cap keys are stripped before
 * hashing so their presence/absence can never change a genome's identity.
 */
export function genomeId(genome) {
  const sanitized = stripForbidden(genome);
  const sortedKeys = Object.keys(sanitized).sort();
  const canonical = JSON.stringify(sortedKeys.map((k) => [k, sanitized[k]]));
  return crypto.createHash("sha256").update(canonical).digest("hex").slice(0, 12);
}
