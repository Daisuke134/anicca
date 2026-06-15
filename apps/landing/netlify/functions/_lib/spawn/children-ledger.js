// children.jsonl ledger (append-only, gap-safe). spec27b. Pure I/O over the colony file.
const fs = require("node:fs");
const path = require("node:path");

function readChildren(file) {
  let raw;
  try { raw = fs.readFileSync(file, "utf8"); } catch { return []; }
  return raw
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => { try { return JSON.parse(l); } catch { return null; } })
    .filter(Boolean);
}

function appendChild(file, row) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, JSON.stringify(row) + "\n");
}

// "anicca-c003" -> 3; rows without a numeric suffix for `prefix` are ignored.
function nextChildId(children = [], prefix = "anicca-c") {
  let max = 0;
  for (const c of children) {
    const id = c && c.childId;
    if (typeof id !== "string" || !id.startsWith(prefix)) continue;
    const n = parseInt(id.slice(prefix.length), 10);
    if (Number.isFinite(n) && n > max) max = n;
  }
  return prefix + String(max + 1).padStart(3, "0");
}

module.exports = { readChildren, appendChild, nextChildId };
