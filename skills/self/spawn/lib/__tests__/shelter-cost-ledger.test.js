// node:test — shelter-cost-ledger: the append-only correction mechanism added after a real
// incident (a CLI stdout-parsing bug wrote the PAYER WALLET address into `jobAddress` instead of
// the real posted job's address — see deploy.mjs's validateJobAddressIsNotPayer). The ledger file
// itself is NEVER rewritten or deleted (REQ-303, append-only); a correction row is appended
// instead, and resolveShelterCostEntries/readShelterCostEntriesResolved is what every consumer
// must read to see the corrected value.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {
  readShelterCostEntries,
  appendShelterCostEntry,
  appendShelterCostCorrection,
  resolveShelterCostEntries,
  readShelterCostEntriesResolved,
} = require("../shelter-cost-ledger.js");

function tmpFile() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "shelter-cost-ledger-test-"));
  return path.join(dir, "shelter-cost.jsonl");
}

const WRONG_ADDRESS = "F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T"; // the real incident's payer wallet
const REAL_JOB_ADDRESS = "FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC"; // the real incident's actual job

// ---- appendShelterCostCorrection ---------------------------------------------------------

test("appendShelterCostCorrection appends a correction row without touching the original row", () => {
  const file = tmpFile();
  appendShelterCostEntry(file, { ts: 1000, settledLeaseCostUsd: 0.01199, jobAddress: WRONG_ADDRESS });
  appendShelterCostCorrection(file, { correctsTs: 1000, correctedJobAddress: REAL_JOB_ADDRESS, reason: "wrong address" });

  const raw = readShelterCostEntries(file);
  assert.equal(raw.length, 2); // append-only: BOTH rows still present, original untouched
  assert.equal(raw[0].jobAddress, WRONG_ADDRESS); // original row is verbatim, never rewritten
  assert.equal(raw[1].correction, true);
  assert.equal(raw[1].correctsTs, 1000);
  assert.equal(raw[1].correctedJobAddress, REAL_JOB_ADDRESS);
});

test("appendShelterCostCorrection fails closed on a missing correctsTs or correctedJobAddress", () => {
  const file = tmpFile();
  assert.throws(() => appendShelterCostCorrection(file, { correctedJobAddress: REAL_JOB_ADDRESS }), /correctsTs/);
  assert.throws(() => appendShelterCostCorrection(file, { correctsTs: 1000 }), /correctedJobAddress/);
});

// ---- resolveShelterCostEntries (pure) ----------------------------------------------------

test("REGRESSION: resolveShelterCostEntries applies a correction so the resolved view shows the REAL job address, exactly the real incident's shape", () => {
  const entries = [
    { ts: 1784956463.817, settledLeaseCostUsd: 0.01199, jobAddress: WRONG_ADDRESS },
    { ts: 1784960000, correction: true, correctsTs: 1784956463.817, correctedField: "jobAddress", correctedJobAddress: REAL_JOB_ADDRESS, reason: "CLI stdout-parsing bug wrote the payer wallet instead of the job address" },
  ];
  const resolved = resolveShelterCostEntries(entries);
  assert.equal(resolved.length, 1); // the correction row itself is not a second spend row
  assert.equal(resolved[0].jobAddress, REAL_JOB_ADDRESS);
  assert.equal(resolved[0].corrected, true);
  assert.equal(resolved[0].settledLeaseCostUsd, 0.01199); // cost figure is untouched by the correction
});

test("resolveShelterCostEntries never double-counts settledLeaseCostUsd — the correction contributes no additional dollar amount", () => {
  const entries = [
    { ts: 1, settledLeaseCostUsd: 0.5, jobAddress: WRONG_ADDRESS },
    { ts: 2, correction: true, correctsTs: 1, correctedJobAddress: REAL_JOB_ADDRESS },
  ];
  const resolved = resolveShelterCostEntries(entries);
  const total = resolved.reduce((sum, r) => sum + (r.settledLeaseCostUsd || 0), 0);
  assert.equal(total, 0.5); // NOT 1.0 — the correction row carries no settledLeaseCostUsd of its own
});

test("resolveShelterCostEntries passes rows with no correction through unchanged", () => {
  const entries = [{ ts: 5, settledLeaseCostUsd: 0.02, jobAddress: REAL_JOB_ADDRESS }];
  const resolved = resolveShelterCostEntries(entries);
  assert.deepEqual(resolved, entries);
});

test("resolveShelterCostEntries: a later correction for the same ts wins (last write wins)", () => {
  const entries = [
    { ts: 1, settledLeaseCostUsd: 0.5, jobAddress: WRONG_ADDRESS },
    { ts: 2, correction: true, correctsTs: 1, correctedJobAddress: "FirstCorrectionAddress1111111111111111111" },
    { ts: 3, correction: true, correctsTs: 1, correctedJobAddress: REAL_JOB_ADDRESS },
  ];
  const resolved = resolveShelterCostEntries(entries);
  assert.equal(resolved.length, 1);
  assert.equal(resolved[0].jobAddress, REAL_JOB_ADDRESS);
});

test("resolveShelterCostEntries fails closed gracefully on non-array input (returns empty, never throws)", () => {
  assert.deepEqual(resolveShelterCostEntries(null), []);
  assert.deepEqual(resolveShelterCostEntries(undefined), []);
});

// ---- readShelterCostEntriesResolved (I/O composition) ------------------------------------

test("readShelterCostEntriesResolved reads the real file and applies corrections end to end", () => {
  const file = tmpFile();
  appendShelterCostEntry(file, { ts: 1784956463.817, settledLeaseCostUsd: 0.01199, jobAddress: WRONG_ADDRESS });
  appendShelterCostCorrection(file, {
    correctsTs: 1784956463.817,
    correctedJobAddress: REAL_JOB_ADDRESS,
    reason: "CLI stdout-parsing bug wrote the payer wallet instead of the job address",
  });

  const raw = readShelterCostEntries(file);
  assert.equal(raw.length, 2); // full audit trail on disk: mistake AND correction, both preserved

  const resolved = readShelterCostEntriesResolved(file);
  assert.equal(resolved.length, 1);
  assert.equal(resolved[0].jobAddress, REAL_JOB_ADDRESS);
  assert.equal(resolved[0].settledLeaseCostUsd, 0.01199);
});

test("readShelterCostEntriesResolved returns an empty array for a nonexistent file (matches readChildren's ENOENT-tolerant behavior)", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "shelter-cost-ledger-test-"));
  const missing = path.join(dir, "does-not-exist.jsonl");
  assert.deepEqual(readShelterCostEntriesResolved(missing), []);
});
