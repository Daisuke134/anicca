// merge.mjs — deterministic, content-addressable dedupe/merge for append-only JSONL ledger rows
// (S4: externalize shelter state so it survives a rebuild). This is the ONE place row-identity is
// decided; store.mjs, snapshot.mjs, and restore.mjs never guess at it themselves.
//
// Everything here operates on RAW TEXT LINES, never on parsed-then-re-JSON.stringify'd rows. That
// is deliberate: JSON.stringify(JSON.parse(line)) is *usually* byte-identical to `line` in V8, but
// "usually" is not the bar for ledgers holding real settled costs and transaction signatures — a
// single float that doesn't round-trip would silently corrupt history. Parsing is used ONLY,
// transiently, to compute a dedupe key; the bytes that get written (locally or to the remote) are
// always a verbatim copy of an existing line.
//
// Dedupe key ("content-addressable enough to dedupe on (ts + jobAddress + signature)" — spec):
// built from whichever of these REAL fields a row actually carries. Never a hash of the whole row
// (that would treat two independently-recorded observations of the exact same on-chain event as
// different rows just because of incidental key ordering), and never a placeholder for a missing
// field (that could accidentally collide two unrelated rows that both happen to lack it).
//   ts          — every row in every one of these ledgers already carries this (epoch seconds).
//   jobAddress  — shelter-cost rows, deploy "posted" rows, renewal "intent"/"settled" rows.
//                 guessedAddress/address are read as fallbacks for rows where the real
//                 jobAddress was not yet confirmed at write time (deploy.mjs's "post-unknown"
//                 status; funding rows only ever have `address`, the payer, never a job).
//   signature   — present once a transaction actually lands (renewal/funding "settled" rows).
//   intentId    — present on intent rows before a signature exists yet.
// Correction rows (shelter-cost-ledger.js's appendShelterCostCorrection) are identified by WHAT
// they correct (correctsTs + correctedField + correctedJobAddress), not by their own `ts` — two
// independently-run corrections of the same original mistake must collapse into one row, exactly
// like the row they are correcting would.

/**
 * Pure: compute the dedupe key for one already-parsed ledger row.
 * @param {object} row
 * @returns {string}
 */
export function dedupeKeyForRow(row) {
  if (!row || typeof row !== "object") {
    throw new Error("dedupeKeyForRow: row must be a non-null object");
  }
  if (row.correction === true) {
    return `correction|${row.correctsTs}|${row.correctedField || ""}|${row.correctedJobAddress || ""}`;
  }
  const ts = typeof row.ts === "number" ? row.ts : "";
  const jobAddress = row.jobAddress || row.guessedAddress || row.address || "";
  const signature = row.signature || "";
  const intentId = row.intentId || "";
  return `row|${ts}|${jobAddress}|${signature}|${intentId}`;
}

/**
 * Pure: the one merge rule for a single JSONL ledger, used symmetrically by both snapshot
 * (existing=remote, incoming=local) and restore (existing=local, incoming=remote).
 *
 * Rule: `existingLines` are NEVER reordered, rewritten, or dropped — the receiving side's current
 * content is append-only sacred. Any `incomingLines` row whose dedupeKeyForRow is not already
 * present in `existingLines` is appended, verbatim, at the tail, in its original relative order.
 * This is deterministic (same inputs -> same output every time), never silently drops a row
 * either side has, and is idempotent: re-running with the same existing+incoming a second time
 * always yields toAppend = [] (nothing left that isn't already "existing").
 *
 * @param {string[]} existingLines - raw JSONL lines already on the receiving side, in file order.
 * @param {string[]} incomingLines - raw JSONL lines from the other side, in file order.
 * @returns {{toAppend: string[], merged: string[]}}
 */
export function mergeAppendOnly(existingLines, incomingLines) {
  const existing = Array.isArray(existingLines) ? existingLines : [];
  const incoming = Array.isArray(incomingLines) ? incomingLines : [];
  const seen = new Set(existing.map((line) => dedupeKeyForRow(JSON.parse(line))));
  const toAppend = [];
  for (const line of incoming) {
    const key = dedupeKeyForRow(JSON.parse(line));
    if (!seen.has(key)) {
      seen.add(key);
      toAppend.push(line);
    }
  }
  return { toAppend, merged: existing.concat(toAppend) };
}
