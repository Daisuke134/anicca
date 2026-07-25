// lines.mjs — read a JSONL file as raw text lines (not parsed objects). Deliberately separate
// from spawn/lib/ledger.js's readChildren (which parses every line to JSON): merge.mjs's
// byte-fidelity guarantee depends on never touching a line's bytes once it exists, so
// snapshot.mjs/restore.mjs read lines as text and only parse transiently, inside merge.mjs, to
// compute a dedupe key.

import fs from "node:fs";

/**
 * Pure I/O: non-empty, trimmed raw lines from `file`, in file order. `[]` if the file does not
 * exist yet (a freshly rebuilt house has no local ledgers at all — that is not an error).
 * @param {string} file
 * @returns {string[]}
 */
export function readRawLines(file) {
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (e) {
    if (e && e.code === "ENOENT") return [];
    throw e;
  }
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}
