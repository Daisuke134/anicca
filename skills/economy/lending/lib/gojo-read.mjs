// economy/lending/lib/gojo-read.mjs — plain, synchronous, READ-ONLY reader over economy/ubi's own
// existing gojo-log.jsonl (REQ-101, resolves FIND-005). Never writes to that file (ubi.js/run.sh own
// it exclusively); never touches ledger.js (this feature's own loans.jsonl is a completely different
// file this reader is not involved with).
import fs from "node:fs";

export function readGojoLogRows(gojoLogPath) {
  let raw;
  try {
    raw = fs.readFileSync(gojoLogPath, "utf8");
  } catch (e) {
    if (e && e.code === "ENOENT") return [];
    throw e;
  }
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line));
}
