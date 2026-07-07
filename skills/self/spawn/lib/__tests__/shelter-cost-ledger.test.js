// VCSDD anicca-agent-spawn, Phase 2a (RED). REQ-303 shelter-cost-ledger.js — append-only JSONL,
// exactly {readShelterCostEntries, appendShelterCostEntry}, mirrors ledger.js's own no-update/upsert
// discipline. shelter-cost-ledger.js does not exist yet — expected to fail at require() time.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const os = require("node:os");
const fs = require("node:fs");
const path = require("node:path");
const { readShelterCostEntries, appendShelterCostEntry } = require("../shelter-cost-ledger");

function tmpFile() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), "anicca-shelter-cost-ledger-")), "shelter-cost.jsonl");
}

test("readShelterCostEntries returns [] when the file does not exist", () => {
  const f = path.join(os.tmpdir(), "definitely-missing-" + Date.now(), "shelter-cost.jsonl");
  assert.deepEqual(readShelterCostEntries(f), []);
});

test("appendShelterCostEntry then readShelterCostEntries round-trips one row per real deploy attempt", () => {
  const f = tmpFile();
  const row = { ts: 1720000000000, settledLeaseCostUsd: 3.5 };
  appendShelterCostEntry(f, row);
  const rows = readShelterCostEntries(f);
  assert.equal(rows.length, 1);
  assert.deepEqual(rows[0], row);
});

test("appendShelterCostEntry is append-only (preserves prior rows, never mutates them)", () => {
  const f = tmpFile();
  appendShelterCostEntry(f, { ts: 1, settledLeaseCostUsd: 3.5 });
  appendShelterCostEntry(f, { ts: 2, settledLeaseCostUsd: 4.25 });
  const rows = readShelterCostEntries(f);
  assert.deepEqual(
    rows.map((r) => r.settledLeaseCostUsd),
    [3.5, 4.25]
  );
});

test("module exports exactly {readShelterCostEntries, appendShelterCostEntry} — no update/upsert primitive (mirrors ledger.js's own discipline)", () => {
  const mod = require("../shelter-cost-ledger");
  assert.deepEqual(Object.keys(mod).sort(), ["appendShelterCostEntry", "readShelterCostEntries"]);
});
