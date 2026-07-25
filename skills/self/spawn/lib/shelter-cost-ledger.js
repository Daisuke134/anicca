// REQ-303: append-only JSONL shelter-cost ledger. ledger.js's readChildren/appendChild are already
// generic over (file, row) despite their children-specific name — reused here unmodified rather than
// re-implementing the identical read/append logic a second time. One entry per real deploy attempt,
// {ts, settledLeaseCostUsd}, appended once the settled lease cost first becomes observable.
//
// Corrections — added after a real incident (see deploy.mjs's validateJobAddressIsNotPayer doc
// comment): a CLI stdout-parsing bug once wrote the PAYER WALLET address into `jobAddress` instead
// of the real posted job's address. This ledger is append-only (REQ-303) — a wrong row is NEVER
// rewritten or deleted. Instead, a correction row referencing the bad row by its exact `ts` is
// appended, and resolveShelterCostEntries/readShelterCostEntriesResolved is what every consumer
// (deploy.mjs's own spend-gate cap history, any future auditor) should read instead of the raw
// rows — that is what "honoring the correction" means here: the raw file keeps full history
// (mistake included, for audit), the resolved view is what decision logic actually sees.
const { readChildren, appendChild } = require("./ledger.js");

function readShelterCostEntries(file) {
  return readChildren(file);
}

function appendShelterCostEntry(file, row) {
  return appendChild(file, row);
}

/**
 * Append a correction row targeting an existing row by its exact `ts`. Never mutates or removes
 * the original (append-only) — the correction is matched back to it purely by `correctsTs` at
 * read time, via resolveShelterCostEntries.
 */
function appendShelterCostCorrection(file, { correctsTs, correctedJobAddress, reason, ts }) {
  if (typeof correctsTs !== "number" || !Number.isFinite(correctsTs)) {
    throw new Error("appendShelterCostCorrection: correctsTs must be the numeric ts of the row being corrected");
  }
  if (typeof correctedJobAddress !== "string" || correctedJobAddress.length === 0) {
    throw new Error("appendShelterCostCorrection: correctedJobAddress must be a non-empty string");
  }
  return appendChild(file, {
    ts: typeof ts === "number" && Number.isFinite(ts) ? ts : Date.now() / 1000,
    correction: true,
    correctsTs,
    correctedField: "jobAddress",
    correctedJobAddress,
    reason: reason || "correction",
  });
}

/**
 * Pure: fold correction rows onto the original rows they target, returning the RESOLVED view
 * every consumer should use. A correction never adds a second dollar amount to the cap-checking
 * history (deploy.mjs maps these rows into spend-gate.mjs's outflowRows, which sums amountUsd per
 * row) — it only overrides the `jobAddress` identity field on a COPY of its target row. Correction
 * rows themselves are excluded from the resolved list (they carry no `settledLeaseCostUsd` of
 * their own — they are metadata patches, not new spend events, so they must never be double
 * counted). Rows with no correction pass through unchanged. If more than one correction targets
 * the same `ts` (should not normally happen), the last one in file order wins — "last write wins"
 * is the least-surprising rule for an append-only log.
 */
function resolveShelterCostEntries(entries) {
  const list = Array.isArray(entries) ? entries : [];
  const correctionsByTs = new Map();
  for (const row of list) {
    if (row && row.correction === true && typeof row.correctsTs === "number") {
      correctionsByTs.set(row.correctsTs, row);
    }
  }
  return list
    .filter((row) => !(row && row.correction === true))
    .map((row) => {
      const correction = row && typeof row.ts === "number" ? correctionsByTs.get(row.ts) : undefined;
      if (!correction) return row;
      return { ...row, jobAddress: correction.correctedJobAddress, corrected: true, correctionReason: correction.reason };
    });
}

function readShelterCostEntriesResolved(file) {
  return resolveShelterCostEntries(readShelterCostEntries(file));
}

module.exports = {
  readShelterCostEntries,
  appendShelterCostEntry,
  appendShelterCostCorrection,
  resolveShelterCostEntries,
  readShelterCostEntriesResolved,
};
