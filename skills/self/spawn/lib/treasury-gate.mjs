// Pure colony-treasury gate (REQ-101/REQ-102). Zero I/O — every function here consumes
// already-fetched balances/ledger rows and returns a deterministic decision or aggregate.
import { isSelfFunded } from "../../../_shared/lib/is-self-funded.mjs";

const DAY_MS = 86400000;

// REQ-101/REQ-402: the SAME window value both consumers must share, by construction (PROP-101k/PROP-402e).
export const BOOTSTRAP_WINDOW_DAYS = 14;
export const SPAWN_COOLDOWN_DAYS = 14;

function finiteBalance(citizen) {
  const balance = citizen && citizen.balanceUsd;
  return typeof balance === "number" && Number.isFinite(balance) ? balance : 0;
}

// Shared by filterProductiveCitizens/deriveRecentSpawnAttempts/countChildrenProvisioning: groups
// ledgerRows by child_id, preserving append order within each group so "the last row" is always
// group[group.length - 1] (last-write-wins, the one reduction rule all three functions apply).
function groupLedgerRowsByChildId(ledgerRows) {
  const groups = new Map();
  for (const row of ledgerRows) {
    const id = row && row.child_id;
    if (id === undefined || id === null) continue;
    if (!groups.has(id)) groups.set(id, []);
    groups.get(id).push(row);
  }
  return groups;
}

// REQ-101: each self-funded citizen's own max(0, balance - reserve) term, individually.
// computeColonySurplusUsd is implemented by summing THIS function's output — never an
// independently-written reduce — so the aggregate and per-citizen breakdown can never diverge.
export function computePerCitizenSurplusUsd({ citizens = [], perCitizenReserveUsd = 0 } = {}) {
  return citizens
    .filter((c) => isSelfFunded(c))
    .map((c) => ({ citizenId: c.id, surplusUsd: Math.max(0, finiteBalance(c) - perCitizenReserveUsd) }));
}

export function computeColonySurplusUsd({ citizens = [], perCitizenReserveUsd = 0 } = {}) {
  return computePerCitizenSurplusUsd({ citizens, perCitizenReserveUsd }).reduce((sum, p) => sum + p.surplusUsd, 0);
}

// REQ-101: cross-references the registry (citizens) against ledger.js's own rows (ledgerRows,
// matched by id===child_id), reduced last-write-wins per child_id BEFORE applying the exclusion
// rule: excluded if the effective row is "bootstrap_failed", or "active" with a missing/non-finite
// active_since, or "active" and nowMs - active_since >= bootstrapWindowDays * DAY_MS (window-overdue).
// A citizen with no matching row passes through unfiltered.
export function filterProductiveCitizens({ citizens = [], ledgerRows = [], nowMs, bootstrapWindowDays = BOOTSTRAP_WINDOW_DAYS } = {}) {
  const groups = groupLedgerRowsByChildId(ledgerRows);
  return citizens.filter((citizen) => {
    // A null/undefined entry is excluded, never thrown on (PROP-101l) — the same graceful
    // exclusion isSelfFunded(null) already gives computeColonySurplusUsd for the identical shape.
    if (!citizen || typeof citizen !== "object") return false;
    const group = groups.get(citizen.id);
    const row = group && group[group.length - 1];
    if (!row) return true;
    if (row.status === "bootstrap_failed") return false;
    if (row.status === "active") {
      const activeSince = row.active_since;
      if (typeof activeSince !== "number" || !Number.isFinite(activeSince)) return false;
      if (nowMs - activeSince >= bootstrapWindowDays * DAY_MS) return false;
    }
    return true;
  });
}

// REQ-102: derives {ts, outcome} per child_id group from ledger.js's real rows — never one entry
// per raw row. outcome is PERMANENTLY "success" if the group ever reached "active" (a later
// bootstrap_failed row never retroactively flips it); else "failure" if the last row is "failed";
// else the group is still in-flight ("provisioning") and is excluded entirely (never double-counted
// alongside countChildrenProvisioning).
export function deriveRecentSpawnAttempts({ ledgerRows = [] } = {}) {
  const groups = groupLedgerRowsByChildId(ledgerRows);
  const attempts = [];
  for (const rows of groups.values()) {
    const everActive = rows.some((r) => r.status === "active");
    const last = rows[rows.length - 1];
    let outcome;
    if (everActive) outcome = "success";
    else if (last.status === "failed") outcome = "failure";
    else continue; // still provisioning — an in-flight attempt, not yet a resolved outcome
    attempts.push({ ts: rows[0].attempted_ms, outcome });
  }
  return attempts;
}

// REQ-102: counts child_id groups whose LAST (last-write-wins) row is exactly "provisioning" —
// a group that later resolved to "active"/"failed"/"bootstrap_failed" is never counted, closing
// both the double-counting and permanent-block hazards a naive per-row scan would create.
export function countChildrenProvisioning({ ledgerRows = [] } = {}) {
  const groups = groupLedgerRowsByChildId(ledgerRows);
  let count = 0;
  for (const rows of groups.values()) {
    if (rows[rows.length - 1].status === "provisioning") count += 1;
  }
  return count;
}

// REQ-102/REQ-303: reduces the shelter-cost ledger's append-only rows to the ONE value
// SPAWN_THRESHOLD_USD's MIN_SHELTER_USD override reads — the LAST-appended entry, never an
// average/max/first-entry read. null on an empty ledger (no real deploy has ever completed).
export function deriveMeasuredShelterCostUsd({ shelterCostLedgerRows = [] } = {}) {
  if (!Array.isArray(shelterCostLedgerRows) || shelterCostLedgerRows.length === 0) return null;
  return shelterCostLedgerRows[shelterCostLedgerRows.length - 1].settledLeaseCostUsd;
}

// REQ-102/103/104: colony-aggregate-scoped spawn gate, directly analogous to spawn-decision.js's
// decideSpawn. Check order: surplus -> cooldown -> concurrency cap (a fixture failing all three
// reports the surplus failure, PROP-102e).
export function decideColonySpawn({
  colonySurplusUsd,
  spawnThresholdUsd,
  recentSpawnAttempts = [],
  nowMs = Date.now(),
  cooldownDays = SPAWN_COOLDOWN_DAYS,
  failureCooldownCap = 3,
  childrenProvisioning = 0,
  maxConcurrentSpawns = 1,
} = {}) {
  const surplus =
    typeof colonySurplusUsd === "number" && Number.isFinite(colonySurplusUsd) && colonySurplusUsd >= 0
      ? colonySurplusUsd
      : 0;
  // Fail-closed (PROP-102l): a non-finite/malformed spawnThresholdUsd must never silently mean "no
  // threshold" — `surplus < NaN`/`surplus < undefined` is always false in JS, which would fall through
  // to eligible:true even at surplus:0. Treat it as unattainable so the surplus check can only deny.
  const threshold =
    typeof spawnThresholdUsd === "number" && Number.isFinite(spawnThresholdUsd) ? spawnThresholdUsd : Infinity;
  if (surplus < threshold) {
    return { eligible: false, reason: "insufficient_surplus" };
  }

  const windowStart = nowMs - cooldownDays * DAY_MS;
  const inWindow = recentSpawnAttempts.filter(
    (a) => a && typeof a.ts === "number" && Number.isFinite(a.ts) && a.ts >= windowStart
  );
  const hasRecentSuccess = inWindow.some((a) => a.outcome === "success");
  const failureCount = inWindow.filter((a) => a.outcome === "failure").length;
  if (hasRecentSuccess || failureCount >= failureCooldownCap) {
    return { eligible: false, reason: "rate_limited" };
  }

  // Fail-closed (PROP-102l): non-finite childrenProvisioning is treated as "at capacity" (never
  // silently bypassing the cap), and a non-finite/malformed maxConcurrentSpawns is treated as zero
  // capacity — never an infinite/no-op cap.
  const provisioning =
    typeof childrenProvisioning === "number" && Number.isFinite(childrenProvisioning) && childrenProvisioning >= 0
      ? childrenProvisioning
      : Infinity;
  const maxConcurrent =
    typeof maxConcurrentSpawns === "number" && Number.isFinite(maxConcurrentSpawns) && maxConcurrentSpawns >= 0
      ? maxConcurrentSpawns
      : 0;
  if (provisioning >= maxConcurrent) {
    return { eligible: false, reason: "max_concurrent_spawns" };
  }

  return { eligible: true, reason: "ok" };
}
