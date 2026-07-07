// REQ-303: append-only JSONL shelter-cost ledger. Mirrors ledger.js's own no-update/upsert
// discipline exactly — one entry per real deploy attempt, {ts, settledLeaseCostUsd}, appended once
// the settled lease cost first becomes observable.
const fs = require("node:fs");
const path = require("node:path");

function readShelterCostEntries(file) {
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (e) {
    if (e && e.code === "ENOENT") return [];
    throw e;
  }
  return raw
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
    .map((l) => JSON.parse(l));
}

function appendShelterCostEntry(file, row) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, JSON.stringify(row) + "\n");
  return row;
}

module.exports = { readShelterCostEntries, appendShelterCostEntry };
