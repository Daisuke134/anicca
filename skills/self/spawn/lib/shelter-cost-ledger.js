// REQ-303: append-only JSONL shelter-cost ledger. ledger.js's readChildren/appendChild are already
// generic over (file, row) despite their children-specific name — reused here unmodified rather than
// re-implementing the identical read/append logic a second time. One entry per real deploy attempt,
// {ts, settledLeaseCostUsd}, appended once the settled lease cost first becomes observable.
const { readChildren, appendChild } = require("./ledger.js");

function readShelterCostEntries(file) {
  return readChildren(file);
}

function appendShelterCostEntry(file, row) {
  return appendChild(file, row);
}

module.exports = { readShelterCostEntries, appendShelterCostEntry };
