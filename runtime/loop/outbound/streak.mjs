// runtime/loop/outbound/streak.mjs — the GREEN gate's bookkeeping.
//
// A pack is GREEN when it has produced independently re-verified evidence on 7 consecutive
// calendar days. The rules are deliberately unforgiving:
//   - at most ONE increment per calendar day (a loop that runs twice cannot inflate its record)
//   - a day with zero verified results resets green_days to 0
//   - a missing day (the loop did not run at all) restarts the streak at 1, because "we have no
//     idea what happened on the 27th" is not the same as "we succeeded on the 27th"
//
// Streak state is scratch state and lives OUTSIDE the repo (OSS-3: no state in the repo). The
// pure reducer (applyDay/isGreen) is separated from the file I/O so both the pass runtime and the
// independent verifier reuse the same arithmetic.
//
// ★ PATH NOTE ★ The design doc puts this state under the legacy OpenClaw store. That root is
// FORBIDDEN in this repo: the Life Manager runtime was migrated off it (Order 5), and both
// apps/life-manager/scripts/scan-legacy-paths.js and lib/runtime-paths.js reject it outright, so
// writing there would break a currently-passing invariant. The canonical portable root is
// resolveDataRoot(): LM_DATA_DIR when set, else <home>/.local/state/life-manager — the same root
// skills/self/healthcheck-runtime-loop.sh already logs into. This module mirrors that resolution
// (it cannot require() the CommonJS helper from ESM).

import fs from "node:fs";
import path from "node:path";

export const GREEN_DAYS = 7;
export const HISTORY_LIMIT = 90;

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const DAY_MS = 86_400_000;

export function dataRoot(homeDir, env = {}) {
  const override = String((env && env.LM_DATA_DIR) || "").trim();
  if (override) return path.resolve(override);
  return path.join(String(homeDir), ".local", "state", "life-manager");
}

export function outboundStateDir(homeDir, env = {}) {
  return path.join(dataRoot(homeDir, env), "outbound");
}

export function streakStatePath(homeDir, env = {}) {
  return path.join(outboundStateDir(homeDir, env), "streak.json");
}

export function traceLedgerPath(homeDir, pack, env = {}) {
  return path.join(outboundStateDir(homeDir, env), `trace-${String(pack)}.jsonl`);
}

export function heartbeatPath(homeDir, env = {}) {
  // What skills/self/healthcheck-runtime-loop.sh stats to decide DEAD / STALE / OK once the
  // guardian is wired to this loop (spec TODO #4).
  return path.join(dataRoot(homeDir, env), ".outbound-last-pass");
}

export function emptyPackStreak() {
  return Object.freeze({ green_days: 0, last_green_date: null, history: Object.freeze([]) });
}

function previousDate(date) {
  return new Date(Date.parse(`${date}T00:00:00Z`) - DAY_MS).toISOString().slice(0, 10);
}

/**
 * Fold one day's verified count into the streak state. Pure — returns a new state object.
 * @param {object} state
 * @param {{pack: string, date: string, verifiedCount: number}} day
 */
export function applyDay(state, day = {}) {
  const pack = String(day.pack == null ? "" : day.pack).trim();
  if (!pack) throw new Error("outbound streak needs a pack name");
  const date = String(day.date == null ? "" : day.date).trim();
  if (!DATE_RE.test(date) || !Number.isFinite(Date.parse(`${date}T00:00:00Z`))) {
    throw new Error("outbound streak needs an ISO YYYY-MM-DD date");
  }
  const verified = Number(day.verifiedCount);
  if (!Number.isInteger(verified) || verified < 0) {
    throw new Error("outbound streak needs a non-negative integer verifiedCount");
  }

  const base = (state && typeof state === "object" ? state : {});
  const current = base[pack] || emptyPackStreak();
  const alreadyRecorded = (current.history || []).some((entry) => entry && entry.date === date);
  if (alreadyRecorded) return base; // one increment per calendar day, no exceptions

  const continues = current.last_green_date === previousDate(date);
  const greenDays = verified === 0 ? 0 : (continues ? Number(current.green_days || 0) + 1 : 1);
  const history = [
    ...(Array.isArray(current.history) ? current.history : []),
    { date, verified, green_days: greenDays },
  ].slice(-HISTORY_LIMIT);

  return {
    ...base,
    [pack]: {
      green_days: greenDays,
      last_green_date: verified === 0 ? null : date,
      history,
    },
  };
}

/**
 * Record what a pass CLAIMED, without touching the streak.
 *
 * The pass runtime is not allowed to advance green_days from its own report — a loop that grades
 * its own homework is exactly the failure this engine exists to prevent. Only the independent
 * verifier (scripts/outbound-verify.js), which re-reads the artifact off disk and re-runs the
 * evidence gate, may call applyDay. Pure — returns a new state object.
 */
export function applyClaim(state, claim = {}) {
  const pack = String(claim.pack == null ? "" : claim.pack).trim();
  if (!pack) throw new Error("outbound streak needs a pack name");
  const date = String(claim.date == null ? "" : claim.date).trim();
  if (!DATE_RE.test(date)) throw new Error("outbound streak needs an ISO YYYY-MM-DD date");
  const claimed = Number(claim.claimedCount);
  if (!Number.isInteger(claimed) || claimed < 0) {
    throw new Error("outbound streak needs a non-negative integer claimedCount");
  }
  const base = (state && typeof state === "object" ? state : {});
  const current = base[pack] || emptyPackStreak();
  return {
    ...base,
    [pack]: {
      green_days: Number(current.green_days || 0),
      last_green_date: current.last_green_date == null ? null : current.last_green_date,
      history: Array.isArray(current.history) ? [...current.history] : [],
      last_claim: { date, claimed },
    },
  };
}

export function isGreen(state, pack) {
  const entry = state && typeof state === "object" ? state[String(pack)] : null;
  return Number(entry && entry.green_days) >= GREEN_DAYS;
}

export function readStreak(statePath) {
  let raw;
  try {
    raw = fs.readFileSync(statePath, "utf8");
  } catch (error) {
    if (error && error.code === "ENOENT") return {};
    throw error;
  }
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("not an object");
    }
    return parsed;
  } catch (error) {
    throw new Error(`outbound streak state is not valid JSON at ${statePath}: ${error.message}`);
  }
}

export function writeStreak(statePath, state) {
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  const temp = `${statePath}.${process.pid}.tmp`;
  fs.writeFileSync(temp, `${JSON.stringify(state, null, 2)}\n`, "utf8");
  fs.renameSync(temp, statePath); // atomic swap: a crash never leaves half a streak file
}

export function touchHeartbeat(beatPath, when = new Date()) {
  fs.mkdirSync(path.dirname(beatPath), { recursive: true });
  fs.writeFileSync(beatPath, "", { flag: "a" });
  fs.utimesSync(beatPath, when, when);
  return beatPath;
}
