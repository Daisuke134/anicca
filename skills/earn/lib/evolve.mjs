// evolve.mjs — chain-verified realized-P&L attribution + earnings-gated genome promotion (#19
// EVOLVE, spec docs/superpowers/specs/2026-07-05-evolve-earnings-gated-self-improve-design.md).
//
// WHY THIS FILE DOES A JOIN, NOT A DIRECT READ: redeem.py (spec §5, "変更しない") builds its
// earn-ledger line from data-api positions and does NOT itself know which genome was active when
// the ORIGINAL bet was placed (bets and redeems can be days apart). pick.py's genome_id IS
// recorded at bet time in run.sh's structured trace (`state/pm-trade.trace.jsonl`, "trade"
// action). So attribution here is a pure, read-only, offline JOIN: for each on-chain-verified
// REDEEM ledger row, find the most recent preceding "trade" trace line for the same market and
// take ITS genome_id. This keeps redeem.py untouched while still answering "which genome earned
// this realized dollar" (spec §2.3 "genome id を bet 時に記録し、resolve/redeem 時に紐付ける").
//
// HARD 0.24 (money-safety, non-negotiable): promotion counts ONLY earn-ledger rows that are
// on-chain-verified realized (source "polymarket-redeem", a `tx` present, `status==="0x1"`).
// Paper/simulated rows (no tx) are NEVER counted toward any genome's P&L, and NEVER promote.
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { readLedger } from "../../_shared/lib/ledger.mjs";
import { CANONICAL_BASELINE_PATH, SAFE_DEFAULT_GENOME, genomeId as computeGenomeId } from "./genome.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const DEFAULT_LEDGER_PATH = path.join(__dirname, "..", "state", "earn-ledger.jsonl");
export const DEFAULT_TRACE_PATH = path.join(__dirname, "..", "state", "pm-trade.trace.jsonl");
export const DEFAULT_MIN_REDEEMS = 3; // K, spec §2.3 ("統計的に無意味な1発を除く"); overridable via env

function readJsonSafe(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

// Read the pm-trade structured trace (JSONL). Missing file -> [] (fail-closed, never throws).
export async function readTrace(tracePath) {
  let raw;
  try {
    raw = await fs.promises.readFile(tracePath, "utf8");
  } catch (e) {
    if (e && e.code === "ENOENT") return [];
    throw e;
  }
  return raw
    .split("\n")
    .filter((l) => l.trim().length > 0)
    .map((l) => {
      try {
        return JSON.parse(l);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

// Build a genome_id -> genome-values map from "genome" trace lines (run.sh records the full
// resolved knob values alongside the id each pass, see polymarket-trade/run.sh). Needed so a
// PROMOTED mutant's actual knob VALUES (not just its id) can be written as the new baseline.
export function buildGenomeIndex(traceLines) {
  const index = new Map();
  for (const t of traceLines) {
    if (t.action !== "genome" || !t.genome_id || !t.genome) continue;
    if (!index.has(t.genome_id)) index.set(t.genome_id, t.genome);
  }
  return index;
}

// Parse a trace line's timestamp (ISO 8601 UTC, e.g. "2026-07-05T12:00:00Z") to epoch seconds.
// Returns NaN on anything unparseable so callers can defensively skip it.
function traceTsSeconds(t) {
  const ms = Date.parse(t.ts);
  return Number.isFinite(ms) ? ms / 1000 : NaN;
}

/**
 * attributeGenomeId(ledgerRow, traceLines) — which genome_id was active when the ORIGINAL bet
 * behind this REDEEM ledger row was placed. Matches the most recent "trade" trace line whose
 * `market` equals the ledger row's `task` (redeem.py's build_ledger_line sets task=row.title,
 * which IS the market question — the same string pick.py put in its own "market" trace field)
 * and whose timestamp is at or before the redeem. Returns null on no match — an unattributed
 * realized row counts toward NO genome (never silently folded into baseline).
 */
export function attributeGenomeId(ledgerRow, traceLines) {
  const redeemTs = Number(ledgerRow.ts) || 0;
  let best = null;
  for (const t of traceLines) {
    if (t.action !== "trade" || !t.genome_id || !t.market) continue;
    if (t.market !== ledgerRow.task) continue;
    const tTs = traceTsSeconds(t);
    if (!Number.isFinite(tTs) || tTs > redeemTs) continue;
    if (best === null || tTs > best.ts) best = { ts: tTs, genome_id: t.genome_id };
  }
  return best ? best.genome_id : null;
}

/**
 * summarizeByGenome(ledgerRows, traceLines) — chain-verified realized P&L + redeem count per
 * genome_id. ONLY on-chain-confirmed redeem rows count (tx present AND status==="0x1"); every
 * counted row's net_usdc (win OR loss) is summed so a genome cannot cherry-pick only its wins.
 * Paper/simulated/unattributed rows never enter this map (HARD 0.24).
 *
 * @returns {Map<string, {genome_id: string, realized_usdc: number, redeem_count: number}>}
 */
export function summarizeByGenome(ledgerRows, traceLines) {
  const byGenome = new Map();
  for (const row of ledgerRows || []) {
    if (!row || row.source !== "polymarket-redeem") continue;
    if (!row.tx || row.status !== "0x1") continue; // on-chain-verified ONLY — no paper/simulated
    const gid = attributeGenomeId(row, traceLines);
    if (!gid) continue; // unattributed realized P&L counts toward nobody
    const entry = byGenome.get(gid) || { genome_id: gid, realized_usdc: 0, redeem_count: 0 };
    entry.realized_usdc = Math.round((entry.realized_usdc + Number(row.net_usdc || 0)) * 1e6) / 1e6;
    entry.redeem_count += 1;
    byGenome.set(gid, entry);
  }
  return byGenome;
}

/**
 * evaluatePromotion({summary, baselineId, mutantId, minRedeems}) — the GATE (spec §2.3): a
 * mutant genome is promotion-eligible ONLY when (a) it has >= minRedeems on-chain-verified
 * redeems (K, kills a statistically-meaningless single lucky bet), (b) it is itself NET-POSITIVE
 * (realized_usdc > 0 — an absolute floor, spec §3/HARD 0.24: a genome that merely loses LESS
 * money than baseline is still a net-losing strategy and must NEVER be auto-adopted), AND
 * (c) its chain-verified realized P&L beats baseline's (baseline's floor is itself clamped at 0,
 * so a baseline that is currently losing money can't be "beaten" by another loser). Pure decision
 * function (no I/O) so it's directly unit-testable.
 */
export function evaluatePromotion({ summary, baselineId, mutantId, minRedeems = DEFAULT_MIN_REDEEMS }) {
  const baseline = summary.get(baselineId) || { realized_usdc: 0, redeem_count: 0 };
  const mutant = summary.get(mutantId);
  if (!mutant) return { promote: false, reason: "no-onchain-realized-data-for-mutant" };
  if (mutant.redeem_count < minRedeems) {
    return { promote: false, reason: `below-K-redeems (${mutant.redeem_count}<${minRedeems})` };
  }
  // HARD 0.24 (money-safety): "less-negative" is NOT a promotion — the challenger must clear an
  // absolute net-positive floor, not just outperform a baseline that may itself be losing money.
  if (!(mutant.realized_usdc > 0)) {
    return { promote: false, reason: `challenger-not-net-positive (${mutant.realized_usdc}<=0)` };
  }
  const baselineFloor = Math.max(baseline.realized_usdc, 0);
  if (!(mutant.realized_usdc > baselineFloor)) {
    return {
      promote: false,
      reason: `does-not-beat-baseline (${mutant.realized_usdc}<=${baselineFloor})`,
    };
  }
  return { promote: true, reason: "beats-baseline-chain-verified-net-positive" };
}

function git(args, cwd) {
  return execFileSync("git", args, { cwd, encoding: "utf8" });
}

/**
 * promote(genome, opts) — write the new canonical baseline-genome.json and `git commit` it
 * (spec §2.3, "自動、no human"). NEVER called on paper/simulated data (enforced by the caller,
 * runEvolve, which only reaches here after evaluatePromotion returns promote:true from
 * on-chain-verified summarizeByGenome data). Throws on any git failure — a promotion that isn't
 * actually committed must surface as an error, never a silent false-success.
 *
 * @param {Record<string, number|string>} genome the WINNING genome's actual knob values
 * @param {{canonicalPath?: string, cwd?: string}} [opts]
 * @returns {{genome_id: string, commit: string}}
 */
export function promote(genome, { canonicalPath = CANONICAL_BASELINE_PATH, cwd } = {}) {
  const repoRoot = cwd || path.resolve(path.dirname(canonicalPath), "..", "..");
  const id = computeGenomeId(genome);
  fs.writeFileSync(canonicalPath, JSON.stringify(genome, null, 2) + "\n");
  git(["add", "--", canonicalPath], repoRoot);
  // Path-scoped commit (repo-safety): `the canonical checkout` is a shared checkout other processes may also be
  // touching concurrently (observed live — unrelated healthcheck scripts sitting modified in the
  // working tree). `git commit -- <path>` commits ONLY changes to that pathspec regardless of
  // what else happens to be staged, so a promotion can never sweep unrelated changes into its
  // commit.
  git(
    [
      "-c",
      "user.name=Anicca Evolve",
      "-c",
      "user.email=evolve@anicca.local",
      "commit",
      "-m",
      `feat(evolve): promote genome ${id} — chain-verified realized P&L beats baseline`,
      "--",
      canonicalPath,
    ],
    repoRoot,
  );
  const commit = git(["rev-parse", "HEAD"], repoRoot).trim();
  return { genome_id: id, commit };
}

/**
 * runEvolve(opts) — full attribution + gate + (maybe) promote pipeline. Read-only unless a
 * genuine chain-verified promotion happens, in which case it writes the canonical baseline file
 * + commits. Never throws on "nothing to promote" (a normal, expected outcome — losing mutants
 * are simply discarded, spec §1.4 "負けは破棄").
 */
export async function runEvolve({
  ledgerPath = DEFAULT_LEDGER_PATH,
  tracePath = DEFAULT_TRACE_PATH,
  canonicalPath = CANONICAL_BASELINE_PATH,
  minRedeems = Number(process.env.EVOLVE_MIN_REDEEMS || DEFAULT_MIN_REDEEMS),
  cwd,
} = {}) {
  const ledgerRows = await readLedger(ledgerPath);
  const traceLines = await readTrace(tracePath);
  const genomeIndex = buildGenomeIndex(traceLines);

  const baselineGenome = stripKnown(readJsonSafe(canonicalPath) || SAFE_DEFAULT_GENOME);
  const baselineId = computeGenomeId(baselineGenome);
  const summary = summarizeByGenome(ledgerRows, traceLines);

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
    // Never promote a genome whose actual knob VALUES we never captured — an id with no
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

function stripKnown(obj) {
  const out = { ...obj };
  for (const k of ["MAX_BET_SIZE", "MAX_PASS_SPEND", "POLY_MIN_ORDER"]) delete out[k];
  return out;
}

// --- CLI entrypoint --------------------------------------------------------------------------
// `node evolve.mjs [ledgerPath] [tracePath]` — standalone, idempotent gate-check. Prints the
// JSON result. Safe to run repeatedly/periodically (e.g. from a loop/cron alongside redeem.py);
// a no-promotion outcome is a normal, silent no-op, exactly like redeem.py's own
// "no redeemable conditions found" idle pass.
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [ledgerPath, tracePath] = process.argv.slice(2);
  runEvolve({
    ledgerPath: ledgerPath || DEFAULT_LEDGER_PATH,
    tracePath: tracePath || DEFAULT_TRACE_PATH,
  })
    .then((result) => {
      console.log(JSON.stringify(result, null, 2));
    })
    .catch((e) => {
      console.error("evolve.mjs error:", e.message);
      process.exitCode = 1;
    });
}
