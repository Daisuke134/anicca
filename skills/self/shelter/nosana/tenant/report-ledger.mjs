// report-ledger.mjs — tenant-runs.jsonl round-trip: the tenant's OWN append-only history of every
// incarnation (one row per Nosana job run), stored at nosana/tenant-runs.jsonl in the SAME remote
// store persistence/ already uses (franklin-shelter-state), via whatever RemoteStateStore
// (../persistence/store.mjs's documented interface) the caller hands in — tenant/entrypoint.mjs
// hands in github-contents-store.mjs's implementation.
//
// Deliberately does NOT import ../persistence/merge.mjs's generic mergeAppendOnly/dedupeKeyForRow:
//   (1) tenant/'s in-job code has zero relative imports outside this directory (see
//       derive-address.mjs's header) — reaching into ../persistence/ would be fine dependency-graph
//       -wise for merge.mjs itself (it has no further imports), but breaks the "fixed, small,
//       self-contained file set" property the whole in-job bundle is built around.
//   (2) tenant-runs.jsonl rows already carry a strictly-increasing, caller-assigned identity
//       (`runNumber`, one per incarnation) that is simpler and more precise than the generic
//       ledger's multi-field heuristic key (ts+jobAddress+signature+intentId) — reusing that key
//       here would be solving an easier problem with a more complicated tool.

export const TENANT_RUNS_REMOTE_KEY = "nosana/tenant-runs.jsonl";

/**
 * Pure: raw text -> trimmed, non-empty lines, in order. Mirrors ../persistence/lines.mjs's
 * trim/filter behavior but operates on an in-memory string (the remote store hands back text, not
 * a file path) rather than reading a file.
 * @param {string|null} text
 * @returns {string[]}
 */
export function textToLines(text) {
  if (typeof text !== "string" || text.length === 0) return [];
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

/**
 * Pure: parse tenant-runs.jsonl text into an array of run records, in file order. Never throws on
 * a malformed line — skips it rather than letting one corrupt row block a new incarnation from
 * reading its own history.
 * @param {string|null} text
 * @returns {object[]}
 */
export function parseTenantRuns(text) {
  const lines = textToLines(text);
  const rows = [];
  for (const line of lines) {
    try {
      rows.push(JSON.parse(line));
    } catch {
      // skip malformed line
    }
  }
  return rows;
}

/**
 * Pure: shape one tenant-runs.jsonl row. Kept out of inline object literals (repo convention,
 * mirrors funding/acquire-nos.mjs's buildFundingIntentRecord/buildFundingSettledRecord) so the
 * exact field set is documented in one place. Every field here is already public information (an
 * address, a balance, a blockhash, a signature) — never the tenant's secret key.
 */
export function buildTenantRunRecord({
  ts,
  runNumber,
  tenantAddress,
  solLamports,
  nosBalance,
  blockhash,
  message,
  signature,
  x402Attempted,
  x402Reason,
  jobAddress,
}) {
  for (const [key, value] of Object.entries({ ts, runNumber, tenantAddress, blockhash, message, signature })) {
    if (value === undefined || value === null || value === "") {
      throw new Error(`buildTenantRunRecord: ${key} is required`);
    }
  }
  return {
    ts,
    runNumber,
    tenantAddress,
    solLamports: typeof solLamports === "number" ? solLamports : null,
    nosBalance: typeof nosBalance === "number" ? nosBalance : null,
    blockhash,
    message,
    signature,
    x402Attempted: Boolean(x402Attempted),
    x402Reason: x402Reason || null,
    jobAddress: jobAddress || null,
  };
}

/**
 * Pure: dedupe-by-runNumber merge — append `newLine` only if no existing line already carries the
 * same runNumber. Idempotent (re-appending the same run twice is a no-op) and never reorders or
 * drops an existing line, mirroring ../persistence/merge.mjs's append-only guarantee expressed
 * against this ledger's simpler, purpose-specific key.
 * @param {string[]} existingLines
 * @param {string} newLine
 * @returns {{toAppend: string[], merged: string[]}}
 */
export function mergeTenantRunLine(existingLines, newLine) {
  const existing = Array.isArray(existingLines) ? existingLines : [];
  const newRow = JSON.parse(newLine);
  for (const line of existing) {
    try {
      const row = JSON.parse(line);
      if (row && row.runNumber === newRow.runNumber) {
        return { toAppend: [], merged: existing };
      }
    } catch {
      // an unparsable existing line can't collide by runNumber for dedupe purposes, but it is
      // still preserved verbatim in `merged` below (never dropped).
    }
  }
  return { toAppend: [newLine], merged: [...existing, newLine] };
}

/**
 * I/O: read the tenant's full run history from `store`. Never throws on a missing/empty history
 * (a brand-new tenant's very first run) — returns priorRunCount: 0, lastRun: null.
 * @param {{store: import("../persistence/store.mjs").RemoteStateStore}} opts
 */
export async function restoreTenantRuns({ store }) {
  if (!store) throw new Error("restoreTenantRuns: store is required");
  const text = await store.getText(TENANT_RUNS_REMOTE_KEY);
  const rows = parseTenantRuns(text);
  return {
    priorRunCount: rows.length,
    lastRun: rows.length > 0 ? rows[rows.length - 1] : null,
    rows,
  };
}

/**
 * I/O: append one new run record to the remote tenant-runs.jsonl via the store's optimistic-
 * concurrency write path, deduping by runNumber (mergeTenantRunLine) so a retried job (recomputing
 * the same runNumber) can never double-write.
 * @param {{store: import("../persistence/store.mjs").RemoteStateStore, record: object}} opts
 */
export async function appendTenantRun({ store, record }) {
  if (!store) throw new Error("appendTenantRun: store is required");
  const newLine = JSON.stringify(record);
  return store.putTextWithMerge(TENANT_RUNS_REMOTE_KEY, (currentText) => {
    const existingLines = textToLines(currentText);
    const { merged } = mergeTenantRunLine(existingLines, newLine);
    return merged.join("\n") + "\n";
  });
}
